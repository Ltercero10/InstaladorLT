# version/github_updater.py
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from urllib.request import Request, urlopen
from tkinter import Tk, messagebox

APP_NAME = "Configurador Farinter"
APP_VERSION = "1.0.2"
GITHUB_OWNER = "Ltercero10"
GITHUB_REPO = "ConfiguradorFarinter"
ASSET_NAME = "ConfiguradorFarinter.exe"

GITHUB_TOKEN = None

LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def normalize_version(version_text: str):
    version_text = version_text.strip().lower().lstrip("v")
    parts = re.findall(r"\d+", version_text)
    return tuple(int(p) for p in parts) if parts else (0, 0, 0)


def is_frozen():
    return getattr(sys, "frozen", False)


def ensure_hidden_root():
    root = Tk()
    root.withdraw()
    return root


def get_headers(api_download=False):
    headers = {
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
    }

    if api_download:
        headers["Accept"] = "application/octet-stream"
    else:
        headers["Accept"] = "application/vnd.github+json"

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def fetch_latest_release():
    req = Request(LATEST_RELEASE_API, headers=get_headers())
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def find_asset_api_url(release_data: dict, asset_name: str):
    for asset in release_data.get("assets", []):
        if asset.get("name") == asset_name:
            return asset.get("url")
    return None


def download_asset_from_api(asset_api_url: str, output_path: str):
    req = Request(asset_api_url, headers=get_headers(api_download=True))
    with urlopen(req, timeout=120) as response, open(output_path, "wb") as f:
        shutil.copyfileobj(response, f)


def build_update_bat(current_exe: str, new_exe: str):
    exe_name = os.path.basename(current_exe)
    return f"""@echo off
title Actualizando {APP_NAME}
timeout /t 2 /nobreak >nul

:waitloop
tasklist | find /i "{exe_name}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)

copy /y "{new_exe}" "{current_exe}" >nul
start "" "{current_exe}"

timeout /t 2 /nobreak >nul
del "%~f0"
"""


def check_and_update(parent=None):
    hidden_root = None
    try:
        if parent is None:
            hidden_root = ensure_hidden_root()
            parent = hidden_root

        release_data = fetch_latest_release()
        remote_tag = release_data.get("tag_name", "").strip()
        remote_version = normalize_version(remote_tag)
        local_version = normalize_version(APP_VERSION)

        if remote_version <= local_version:
            return False

        asset_api_url = find_asset_api_url(release_data, ASSET_NAME)
        if not asset_api_url:
            messagebox.showerror(
                "Actualización",
                f"No se encontró el asset '{ASSET_NAME}' en la última release.",
                parent=parent
            )
            return False

        answer = messagebox.askyesno(
            "Actualización disponible",
            f"Versión actual: {APP_VERSION}\n"
            f"Nueva versión: {remote_tag}\n\n"
            f"¿Desea actualizar ahora?",
            parent=parent
        )
        if not answer:
            return False

        if not is_frozen():
            messagebox.showinfo(
                "Actualización",
                "La actualización automática solo funciona desde el .exe compilado.",
                parent=parent
            )
            return False

        current_exe = sys.executable
        temp_dir = tempfile.mkdtemp(prefix="cf_update_")
        new_exe_path = os.path.join(temp_dir, ASSET_NAME)
        bat_path = os.path.join(temp_dir, "update.bat")

        download_asset_from_api(asset_api_url, new_exe_path)

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(build_update_bat(current_exe, new_exe_path))

        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True

    except Exception as e:
        messagebox.showerror(
            "Actualización",
            f"No se pudo actualizar:\n{e}",
            parent=parent
        )
        return False

    finally:
        if hidden_root is not None:
            hidden_root.destroy()