# -*- coding: utf-8 -*-

import os
import json
import sys

def resource_path(relative_path: str) -> str:
    """
    Devuelve ruta absoluta tanto en .py como en .exe (PyInstaller --onefile).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def load_json_file(filename: str) -> dict:
    """
    Carga un archivo JSON desde la carpeta data/
    """
    # Intentar primero en la carpeta data
    data_path = os.path.join("data", filename)
    path = resource_path(data_path)
    
    # Si no existe, intentar en la raíz (para compatibilidad)
    if not os.path.exists(path):
        path = resource_path(filename)
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo {filename}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_config() -> dict:
    """Carga la configuración principal desde config.json"""
    try:
        return load_json_file("config.json")
    except FileNotFoundError:
        return None