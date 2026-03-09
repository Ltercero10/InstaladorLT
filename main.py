import sys
import os

# Asegurar que podemos importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.admin import ensure_admin
from gui.app import AutoInstallerApp

def main():
    """Punto de entrada principal de la aplicación"""
    ensure_admin()
    
    app = AutoInstallerApp()
    app.run()

if __name__ == "__main__":
    main()