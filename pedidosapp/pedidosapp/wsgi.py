import os
import sys
from pathlib import Path

# Agrega la raíz del repo al path
repo_root = str(Path(__file__).resolve().parent.parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pedidosapp.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
