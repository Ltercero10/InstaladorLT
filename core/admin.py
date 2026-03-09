# -*- coding: utf-8 -*-

import sys
import ctypes
import os

def ensure_admin():
    """
    Verifica si el programa se ejecuta como administrador.
    Si no es así, solicita elevación de privilegios.
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def is_admin() -> bool:
    """Retorna True si el programa tiene privilegios de administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False