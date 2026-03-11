#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pedidosapp.settings')

    # Agrega el directorio raíz del repo al path para que
    # las apps 'menu' y 'orders' sean encontradas
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
