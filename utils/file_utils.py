# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import time
import subprocess

def stage_to_temp(src_path: str) -> str:
    """
    Copia un archivo a la carpeta temporal y lo desbloquea (PowerShell)
    """
    temp_dir = tempfile.gettempdir()
    base_name = os.path.basename(src_path)

    dst_path = os.path.join(temp_dir, base_name)
    if os.path.exists(dst_path):
        name, ext = os.path.splitext(base_name)
        dst_path = os.path.join(temp_dir, f"{name}_{int(time.time())}{ext}")

    shutil.copy2(src_path, dst_path)

    # Desbloquear archivo en Windows (quitar marca de "procedente de otro equipo")
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f'Unblock-File -Path "{dst_path}"'
            ],
            capture_output=True,
            text=True
        )
    except Exception:
        pass

    return dst_path

def ensure_directory(path: str) -> bool:
    """Asegura que un directorio existe, lo crea si no"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False