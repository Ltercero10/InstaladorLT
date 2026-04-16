import sys
import os
import ctypes

# Asegurar que podemos importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.admin import ensure_admin
from core.network_auth import ensure_network_access
from gui.app import AutoInstallerApp
from version.github_updater import check_and_update

updated = check_and_update()
if updated:
    sys.exit(0)


def main():
    """Punto de entrada principal de la aplicación"""
    ensure_admin()

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("farinter.configurador")
    except Exception:
        pass

    app = AutoInstallerApp()

    share_root = r"\\10.0.5.157\Soporte"
    ok = ensure_network_access(app.root, share_root)

    if not ok:
        app.root.destroy()
        return

    app.run()


if __name__ == "__main__":
    main()