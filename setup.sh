#!/bin/bash
# Setup inicial de Backyard Bar - Sistema de Menú QR

set -e

echo "========================================"
echo "  Backyard Bar - Setup del sistema QR   "
echo "========================================"

# Crear y activar entorno virtual
if [ ! -d "venv" ]; then
    echo "[1/5] Creando entorno virtual..."
    python3 -m venv venv
fi

echo "[2/5] Activando entorno e instalando dependencias..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "[3/5] Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

echo "[4/5] Cargando datos de ejemplo..."
python manage.py seed_data

echo "[5/5] Creando superusuario admin..."
echo ""
python manage.py createsuperuser

echo ""
echo "========================================"
echo "  Setup completo!"
echo "========================================"
echo ""
echo "Para iniciar el servidor:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
echo "URLs:"
echo "  Menu publico:  http://localhost:8000/"
echo "  Admin:         http://localhost:8000/admin/"
echo "  QR Dashboard:  http://localhost:8000/admin-tools/qr-dashboard/"
echo ""
