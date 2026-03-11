#!/bin/bash
# ============================================================
#  Backyard Bar - Setup / Deploy / Rollback
#
#  Desarrollo local:   bash setup.sh
#  Producción (VPS):   sudo bash setup.sh
#  Rollback:           sudo bash setup.sh --rollback
#
#  Forzar modo:        bash setup.sh --dev
#                      sudo bash setup.sh --prod
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()  { echo -e "\n${BOLD}${YELLOW}── $1${NC}"; }

# ── Detectar modo ────────────────────────────────────────────
if   [ "${1:-}" = "--dev" ];      then MODE="dev"
elif [ "${1:-}" = "--prod" ];     then MODE="prod"
elif [ "${1:-}" = "--rollback" ]; then MODE="rollback"
elif [ "$EUID" -eq 0 ];          then MODE="prod"
else                                   MODE="dev"
fi

[ "$MODE" = "prod"     ] && [ "$EUID" -ne 0 ] && error "Producción requiere root: sudo bash setup.sh"
[ "$MODE" = "rollback" ] && [ "$EUID" -ne 0 ] && error "Rollback requiere root: sudo bash setup.sh --rollback"

# ── Configuración producción ─────────────────────────────────
DOMAIN="menu.backyardbar.fun"
ORDERS_DOMAIN="pedidos.backyardbar.fun"
APP_USER="backyardbar"
APP_DIR="/var/www/backyardbar"
REPO_DIR="$APP_DIR/app"
VENV_DIR="$APP_DIR/venv"
SOCK="$APP_DIR/gunicorn.sock"
SERVICE="backyardbar"
RELEASES_DIR="$APP_DIR/releases"
KEEP_RELEASES=5
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Encabezado ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════${NC}"
case "$MODE" in
  prod)     echo -e "${BOLD}  Backyard Bar · Deploy producción${NC}" ;;
  rollback) echo -e "${BOLD}  Backyard Bar · Rollback${NC}" ;;
  *)        echo -e "${BOLD}  Backyard Bar · Setup desarrollo${NC}" ;;
esac
echo -e "${BOLD}════════════════════════════════════════${NC}"
echo ""

# ── Credenciales del superusuario (solo en setup/deploy) ─────
if [ "$MODE" != "rollback" ]; then
    read -rp  "  Usuario admin: "       DJANGO_SU_NAME
    read -rp  "  Email (opcional): "    DJANGO_SU_EMAIL
    read -rs -p "  Contraseña: "        DJANGO_SU_PASSWORD; echo ""
    read -rs -p "  Confirmar contraseña: " DJANGO_SU_PASSWORD2; echo ""
    [ "$DJANGO_SU_PASSWORD" != "$DJANGO_SU_PASSWORD2" ] && error "Las contraseñas no coinciden."
fi

# ── Credenciales Twilio SMS (solo producción) ─────────────────
TWILIO_SID=""
TWILIO_TOKEN=""
TWILIO_PHONE=""
if [ "$MODE" = "prod" ]; then
    echo ""
    echo -e "  ${BOLD}Twilio SMS (Enter para omitir):${NC}"
    read -rp  "  Account SID:   " TWILIO_SID
    if [ -n "$TWILIO_SID" ]; then
        read -rs -p "  Auth Token:    " TWILIO_TOKEN; echo ""
        read -rp  "  Número Twilio (ej: +15005550006): " TWILIO_PHONE
    fi
fi

# ════════════════════════════════════════════════════════════
# MODO DESARROLLO LOCAL
# ════════════════════════════════════════════════════════════
if [ "$MODE" = "dev" ]; then

    step "1/5  Entorno virtual"
    [ ! -d "venv" ] && python3 -m venv venv
    # shellcheck source=/dev/null
    source venv/bin/activate
    info "venv activo"

    step "2/5  Instalando dependencias"
    pip install -r requirements.txt --quiet
    info "Dependencias instaladas"

    step "3/5  Migraciones"
    python manage.py makemigrations
    python manage.py migrate
    info "Migraciones aplicadas"

    step "4/5  Datos de ejemplo"
    python manage.py seed_data
    info "Datos cargados"

    step "5/5  Superusuario"
    DJANGO_SUPERUSER_USERNAME="$DJANGO_SU_NAME" \
    DJANGO_SUPERUSER_EMAIL="$DJANGO_SU_EMAIL" \
    DJANGO_SUPERUSER_PASSWORD="$DJANGO_SU_PASSWORD" \
    python manage.py createsuperuser --noinput
    info "Superusuario '$DJANGO_SU_NAME' creado"

    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  Setup completo!${NC}"
    echo -e "${BOLD}${GREEN}════════════════════════════════════════${NC}"
    echo ""
    echo "  Para iniciar el servidor:"
    echo "    source venv/bin/activate"
    echo "    python manage.py runserver 0.0.0.0:8000"
    echo ""
    echo "  URLs:"
    echo "    Menu público:  http://localhost:8000/"
    echo "    Admin:         http://localhost:8000/admin/"
    echo "    QR Dashboard:  http://localhost:8000/admin-tools/qr-dashboard/"
    echo ""
    exit 0
fi

# ════════════════════════════════════════════════════════════
# MODO ROLLBACK
# ════════════════════════════════════════════════════════════
if [ "$MODE" = "rollback" ]; then

    mkdir -p "$RELEASES_DIR"
    LAST_RELEASE=$(ls -1t "$RELEASES_DIR" 2>/dev/null | head -1 || true)
    [ -z "$LAST_RELEASE" ] && error "No hay releases guardados para hacer rollback."

    step "Rollback a release: $LAST_RELEASE"

    systemctl stop "$SERVICE" 2>/dev/null || true

    if [ -d "$RELEASES_DIR/$LAST_RELEASE/app" ]; then
        rsync -a --delete \
          --exclude='db.sqlite3' \
          "$RELEASES_DIR/$LAST_RELEASE/app/" "$REPO_DIR/"
        chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
        info "Código restaurado"
    else
        warn "No se encontró snapshot de código para este release."
    fi

    if [ -f "$RELEASES_DIR/$LAST_RELEASE/db.sqlite3.bak" ]; then
        cp "$RELEASES_DIR/$LAST_RELEASE/db.sqlite3.bak" "$APP_DIR/db.sqlite3"
        chown "$APP_USER:$APP_USER" "$APP_DIR/db.sqlite3"
        info "Base de datos restaurada"
    else
        warn "No se encontró backup de BD para este release (se mantiene la actual)."
    fi

    systemctl start "$SERVICE"
    sleep 2
    systemctl is-active --quiet "$SERVICE" \
      && info "Servicio reiniciado correctamente" \
      || error "El servicio no inició tras el rollback. Revisá: journalctl -u $SERVICE -n 40"

    echo ""
    echo -e "${BOLD}${GREEN}  Rollback completado → $LAST_RELEASE${NC}"
    echo ""
    echo -e "  ${YELLOW}Releases disponibles:${NC}"
    ls -1t "$RELEASES_DIR" | head -5 | sed 's/^/    /'
    echo ""
    exit 0
fi

# ════════════════════════════════════════════════════════════
# MODO PRODUCCIÓN (VPS)
# ════════════════════════════════════════════════════════════

step "1/10  Actualizando sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv python3-dev \
  nginx certbot python3-certbot-nginx \
  git curl rsync build-essential \
  libjpeg-dev zlib1g-dev libfreetype6-dev
info "Sistema y dependencias instalados"

step "2/10  Configurando usuario del sistema"
id "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"
mkdir -p "$REPO_DIR" "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/logs" "$RELEASES_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
info "Usuario '$APP_USER' y directorios listos"

step "3/10  Guardando snapshot para rollback"
RELEASE_TAG="$(date +%Y%m%d_%H%M%S)"
RELEASE_PATH="$RELEASES_DIR/$RELEASE_TAG"
mkdir -p "$RELEASE_PATH/app"

if [ -d "$REPO_DIR" ] && [ "$(ls -A "$REPO_DIR" 2>/dev/null)" ]; then
    rsync -a \
      --exclude='__pycache__' --exclude='*.pyc' --exclude='*.sock' \
      "$REPO_DIR/" "$RELEASE_PATH/app/"
    info "Snapshot de código guardado"
else
    info "Primera instalación, no hay código previo que respaldar"
fi

if [ -f "$APP_DIR/db.sqlite3" ]; then
    cp "$APP_DIR/db.sqlite3" "$RELEASE_PATH/db.sqlite3.bak"
    info "Backup de BD guardado"
else
    info "Primera instalación, no hay BD previa que respaldar"
fi

# Limpiar releases viejos (mantener los últimos KEEP_RELEASES)
RELEASE_COUNT=$(ls -1t "$RELEASES_DIR" | wc -l)
if [ "$RELEASE_COUNT" -gt "$KEEP_RELEASES" ]; then
    ls -1t "$RELEASES_DIR" | tail -n +"$((KEEP_RELEASES + 1))" | \
      xargs -I{} rm -rf "$RELEASES_DIR/{}"
    info "Releases antiguos eliminados (se conservan $KEEP_RELEASES)"
fi

step "4/10  Copiando código"
rsync -a --delete \
  --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.git' --exclude='db.sqlite3' --exclude='media' \
  --exclude='staticfiles' --exclude='*.sock' --exclude='releases' \
  "$SOURCE_DIR/" "$REPO_DIR/"
chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
info "Código copiado a $REPO_DIR"

step "5/10  Instalando dependencias Python"
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt" -q
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install gunicorn -q
info "Virtualenv listo en $VENV_DIR"

step "6/10  Configurando Django para producción"
SECRET_KEY=$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#%^&*-_=+'
print(''.join(secrets.choice(chars) for _ in range(50)))
")

cat > "$REPO_DIR/backyardbar/settings_prod.py" << PYEOF
from .settings import *

DEBUG = False
SECRET_KEY = '${SECRET_KEY}'
ALLOWED_HOSTS = ['${DOMAIN}', 'www.${DOMAIN}', '${ORDERS_DOMAIN}']

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

CSRF_TRUSTED_ORIGINS = [
    'https://${DOMAIN}',
    'http://${DOMAIN}',
    'https://${ORDERS_DOMAIN}',
    'http://${ORDERS_DOMAIN}',
]

SECURE_BROWSER_XSS_FILTER  = True
X_FRAME_OPTIONS             = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Twilio SMS
TWILIO_ACCOUNT_SID = '${TWILIO_SID}'
TWILIO_AUTH_TOKEN  = '${TWILIO_TOKEN}'
TWILIO_PHONE_NUMBER = '${TWILIO_PHONE}'
PYEOF

chown "$APP_USER:$APP_USER" "$REPO_DIR/backyardbar/settings_prod.py"
info "settings_prod.py generado"

sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" migrate --noinput
info "Migraciones aplicadas"

sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" seed_data 2>/dev/null || true
info "Datos de ejemplo cargados"

sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" collectstatic --noinput -v 0
info "Archivos estáticos recolectados"

step "7/10  Creando superusuario"
if sudo -u "$APP_USER" env \
  DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  DJANGO_SUPERUSER_USERNAME="$DJANGO_SU_NAME" \
  DJANGO_SUPERUSER_EMAIL="$DJANGO_SU_EMAIL" \
  DJANGO_SUPERUSER_PASSWORD="$DJANGO_SU_PASSWORD" \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" createsuperuser --noinput; then
  info "Superusuario '$DJANGO_SU_NAME' creado"
else
  warn "No se pudo crear el superusuario (¿ya existe o la contraseña no cumple los requisitos?)."
  warn "Podés crearlo manualmente:"
  warn "  sudo -u $APP_USER env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod $VENV_DIR/bin/python $REPO_DIR/manage.py createsuperuser"
fi

step "8/10  Configurando Gunicorn"
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

step "9/10  Configurando Nginx"
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

# Nginx para menú
ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"

# Nginx para pedidos (mismo backend, diferente dominio)
cat > "/etc/nginx/sites-available/$ORDERS_DOMAIN" << NGEOF2
server {
    listen 80;
    server_name ${ORDERS_DOMAIN};

    client_max_body_size 20M;

    access_log ${APP_DIR}/logs/nginx_pedidos_access.log;
    error_log  ${APP_DIR}/logs/nginx_pedidos_error.log;

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
NGEOF2

ln -sf "/etc/nginx/sites-available/$ORDERS_DOMAIN" "/etc/nginx/sites-enabled/$ORDERS_DOMAIN"
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
info "Nginx configurado (menú + pedidos)"

step "10/10  Instalando SSL (Let's Encrypt)"
SSL_EMAIL="${DJANGO_SU_EMAIL:-admin@${DOMAIN}}"
SSL_OK=false
if certbot --nginx \
      -d "$DOMAIN" -d "$ORDERS_DOMAIN" \
      --non-interactive \
      --agree-tos \
      --email "$SSL_EMAIL" \
      --redirect \
      2>&1 | grep -q "Congratulations\|Certificate not yet due"; then
  info "SSL instalado correctamente para ambos dominios"
  SSL_OK=true
else
  warn "SSL no pudo instalarse (posiblemente el DNS aún no propagó)."
fi

systemctl enable certbot.timer 2>/dev/null || true

sudo -u "$APP_USER" env DJANGO_SETTINGS_MODULE=backyardbar.settings_prod \
  "$VENV_DIR/bin/python" "$REPO_DIR/manage.py" shell << PYEOF 2>/dev/null || true
from menu.models import SiteConfig
c = SiteConfig.get_config()
c.base_url = 'https://${DOMAIN}'
c.save()
PYEOF
info "URL base del QR actualizada a https://${DOMAIN}"

echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════╗"
echo -e "║       Backyard Bar · Deploy completado        ║"
echo -e "╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Menú QR:         ${GREEN}https://${DOMAIN}/${NC}"
echo -e "  Pedidos online:  ${GREEN}https://${ORDERS_DOMAIN}/${NC}"
echo -e "  Panel gestión:   ${GREEN}https://${ORDERS_DOMAIN}/panel/pedidos/${NC}"
echo -e "  Panel menú:      ${GREEN}https://${DOMAIN}/panel/login/${NC}"
echo ""
echo -e "  ${BOLD}Credenciales del panel:${NC}"
echo -e "    Usuario: ${YELLOW}${DJANGO_SU_NAME}${NC}"
echo ""
echo -e "  ${BOLD}Snapshot guardado:${NC} $RELEASE_TAG"
echo -e "  ${BOLD}Para hacer rollback:${NC} sudo bash setup.sh --rollback"
echo ""
if [ "$SSL_OK" = false ]; then
echo -e "  ${BOLD}${RED}SSL pendiente — ejecutá cuando ambos DNS propaguen:${NC}"
echo -e "    ${YELLOW}certbot --nginx -d $DOMAIN -d $ORDERS_DOMAIN --non-interactive --agree-tos --email $SSL_EMAIL --redirect${NC}"
echo ""
fi
echo -e "  ${BOLD}Comandos útiles:${NC}"
echo -e "    systemctl status  ${SERVICE}"
echo -e "    systemctl restart ${SERVICE}"
echo -e "    journalctl -u ${SERVICE} -f"
echo -e "    tail -f ${APP_DIR}/logs/gunicorn_error.log"
echo ""
