#!/bin/bash
# ============================================================
#  Backyard Bar - Deploy automático en VPS Hostinger
#  Dominio: menu.backyardbar.fun
#  Uso:
#    git clone <repo> /tmp/backyardBarapp
#    cd /tmp/backyardBarapp
#    sudo bash deploy.sh
# ============================================================

set -euo pipefail

DOMAIN="menu.backyardbar.fun"
APP_USER="backyardbar"
APP_DIR="/var/www/backyardbar"
REPO_DIR="$APP_DIR/app"
VENV_DIR="$APP_DIR/venv"
SOCK="$APP_DIR/gunicorn.sock"
SERVICE="backyardbar"
ADMIN_USER="admin"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()  { echo -e "\n${BOLD}${YELLOW}── $1${NC}"; }

[ "$EUID" -ne 0 ] && error "Ejecutá como root: sudo bash deploy.sh"

# ── 1. Sistema ───────────────────────────────────────────────
step "1/9  Actualizando sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv python3-dev \
  nginx certbot python3-certbot-nginx \
  git curl rsync build-essential \
  libjpeg-dev zlib1g-dev libfreetype6-dev
info "Sistema y dependencias instalados"

# ── 2. Usuario ───────────────────────────────────────────────
step "2/9  Configurando usuario del sistema"
id "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"
mkdir -p "$REPO_DIR" "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
info "Usuario '$APP_USER' y directorios listos"

# ── 3. Código ────────────────────────────────────────────────
step "3/9  Copiando código de la aplicación"
rsync -a --delete \
  --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.git' --exclude='db.sqlite3' --exclude='media' \
  --exclude='staticfiles' --exclude='*.sock' \
  "$SOURCE_DIR/" "$REPO_DIR/"
chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
info "Código copiado a $REPO_DIR"

# ── 4. Python y dependencias ─────────────────────────────────
step "4/9  Instalando dependencias Python"
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" -q
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install gunicorn -q
info "Virtualenv listo en $VENV_DIR"

# ── 5. Settings de producción ────────────────────────────────
step "5/9  Configurando Django para producción"
SECRET_KEY=$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#%^&*-_=+'
print(''.join(secrets.choice(chars) for _ in range(50)))
")

cat > "$REPO_DIR/backyardbar/settings_prod.py" << PYEOF
from .settings import *

DEBUG = False
SECRET_KEY = '${SECRET_KEY}'
ALLOWED_HOSTS = ['${DOMAIN}', 'www.${DOMAIN}']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '${APP_DIR}/db.sqlite3',
    }
}

STATIC_ROOT  = '${APP_DIR}/staticfiles'
MEDIA_ROOT   = '${APP_DIR}/media'
MEDIA_URL    = '/media/'
STATIC_URL   = '/static/'

CSRF_TRUSTED_ORIGINS = ['https://${DOMAIN}', 'http://${DOMAIN}']

SECURE_BROWSER_XSS_FILTER  = True
X_FRAME_OPTIONS             = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
PYEOF

chown "$APP_USER:$APP_USER" "$REPO_DIR/backyardbar/settings_prod.py"
info "settings_prod.py generado"

# Migraciones
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" migrate --noinput
info "Migraciones aplicadas"

# Datos de ejemplo (solo si la BD está vacía)
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" seed_data 2>/dev/null || true
info "Datos de ejemplo cargados"

# Static files
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" collectstatic --noinput -v 0
info "Archivos estáticos recolectados"

# ── 6. Superusuario automático ───────────────────────────────
step "6/9  Creando superusuario administrador"
ADMIN_PASS=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(16)))")

sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" shell << PYEOF 2>/dev/null || true
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${ADMIN_USER}').exists():
    User.objects.create_superuser('${ADMIN_USER}', 'admin@${DOMAIN}', '${ADMIN_PASS}')
    print("Superusuario creado.")
else:
    print("El superusuario ya existe.")
PYEOF
info "Superusuario '$ADMIN_USER' listo"

# ── 7. Gunicorn (systemd) ────────────────────────────────────
step "7/9  Configurando Gunicorn"
cat > "/etc/systemd/system/${SERVICE}.service" << SVCEOF
[Unit]
Description=Gunicorn · Backyard Bar
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${REPO_DIR}
Environment="DJANGO_SETTINGS_MODULE=backyardbar.settings_prod"
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --workers 3 \\
    --bind unix:${SOCK} \\
    --timeout 120 \\
    --access-logfile ${APP_DIR}/logs/gunicorn_access.log \\
    --error-logfile  ${APP_DIR}/logs/gunicorn_error.log \\
    backyardbar.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"
sleep 2

systemctl is-active --quiet "$SERVICE" \
  && info "Gunicorn corriendo" \
  || error "Gunicorn no inició. Revisá: journalctl -u $SERVICE -n 40"

# ── 8. Nginx ─────────────────────────────────────────────────
step "8/9  Configurando Nginx"
cat > "/etc/nginx/sites-available/$DOMAIN" << NGEOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    client_max_body_size 20M;

    access_log ${APP_DIR}/logs/nginx_access.log;
    error_log  ${APP_DIR}/logs/nginx_error.log;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass         http://unix:${SOCK};
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_redirect     off;
        proxy_read_timeout 120;
    }
}
NGEOF

ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
info "Nginx configurado"

# ── 9. SSL con Let's Encrypt ─────────────────────────────────
step "9/9  Instalando SSL (Let's Encrypt)"
if certbot --nginx \
      -d "$DOMAIN" \
      --non-interactive \
      --agree-tos \
      --email "admin@${DOMAIN}" \
      --redirect \
      2>&1 | grep -q "Congratulations\|Certificate not yet due"; then
  info "SSL instalado correctamente"
else
  warn "SSL no pudo instalarse ahora (posiblemente el DNS aún no propagó)."
  warn "Ejecutá esto cuando el DNS esté listo:"
  warn "  certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect"
fi

# Renovación automática
systemctl enable certbot.timer 2>/dev/null || true

# ── Actualizar la URL base del QR ────────────────────────────
sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" shell << PYEOF 2>/dev/null || true
from menu.models import SiteConfig
c = SiteConfig.get_config()
c.base_url = 'https://${DOMAIN}'
c.save()
PYEOF
info "URL base del QR actualizada a https://${DOMAIN}"

# ── Resumen ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════╗"
echo -e "║       Backyard Bar · Deploy completado        ║"
echo -e "╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Menú público:    ${GREEN}https://${DOMAIN}/${NC}"
echo -e "  Panel de gestión:${GREEN}https://${DOMAIN}/panel/login/${NC}"
echo ""
echo -e "  ${BOLD}Credenciales del panel:${NC}"
echo -e "    Usuario:    ${YELLOW}${ADMIN_USER}${NC}"
echo -e "    Contraseña: ${YELLOW}${ADMIN_PASS}${NC}"
echo ""
echo -e "  ${BOLD}Comandos útiles:${NC}"
echo -e "    systemctl status  ${SERVICE}"
echo -e "    systemctl restart ${SERVICE}"
echo -e "    journalctl -u ${SERVICE} -f"
echo -e "    tail -f ${APP_DIR}/logs/gunicorn_error.log"
echo ""
echo -e "  ${YELLOW}Guarda la contraseña — no se vuelve a mostrar.${NC}"
echo ""
