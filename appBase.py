import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import subprocess
import os
import shutil
import tempfile
import time
import sys
import ctypes


# -----------------------------
# PyInstaller: rutas de recursos
# -----------------------------
def resource_path(relative_path: str) -> str:
    """
    Devuelve ruta absoluta tanto en .py como en .exe (PyInstaller --onefile).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # carpeta temporal donde PyInstaller extrae
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# -----------------------------
# Elevación a Administrador
# -----------------------------
def ensure_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


# -----------------------------
# UI helpers
# -----------------------------
def log(msg: str):
    console.insert(tk.END, msg + "\n")
    console.see(tk.END)


# -----------------------------
# Config/JSON
# -----------------------------
def load_config():
    cfg = resource_path("config.json")
    if not os.path.exists(cfg):
        messagebox.showerror("Error", "No se encontró config.json")
        return None

    with open(cfg, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# Stage installers to TEMP
# -----------------------------
def stage_to_temp(src_path: str) -> str:
    """
    Copia el instalador desde red (UNC) a %TEMP% y lo desbloquea
    (Unblock-File) para reducir avisos/Mark-of-the-Web.
    """
    temp_dir = tempfile.gettempdir()
    base_name = os.path.basename(src_path)

    dst_path = os.path.join(temp_dir, base_name)
    if os.path.exists(dst_path):
        name, ext = os.path.splitext(base_name)
        dst_path = os.path.join(temp_dir, f"{name}_{int(time.time())}{ext}")

    shutil.copy2(src_path, dst_path)

    # Desbloquear Mark-of-the-Web si aplica
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", f'Unblock-File -Path "{dst_path}"'],
            capture_output=True,
            text=True
        )
    except Exception:
        pass

    return dst_path


# -----------------------------
# Instalación principal
# -----------------------------
def run_installation(json_filename: str):
    try:
        config = load_config()
        if not config:
            return

        json_path = resource_path(json_filename)
        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"No se encontró el archivo {json_filename}")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        apps = data.get("apps", [])
        total_apps = len(apps)

        progress_bar["maximum"] = total_apps
        progress_var.set(0)

        if total_apps == 0:
            log("⚠ No hay aplicaciones definidas en el JSON")
            return

        log(f"Modo seleccionado: {data.get('modo', 'N/D')}")
        log(f"Total de aplicaciones: {total_apps}")
        log("Iniciando instalación...\n")

        rutas_base = config.get("rutas_base", {})

        for index, app in enumerate(apps, start=1):
            nombre = app.get("nombre", "Desconocido")
            tipo = app.get("tipo", "exe")  # exe | msi | carpeta
            base = app.get("base", "")
            ruta_relativa = app.get("ruta", "")
            args = app.get("args", "")
            post = app.get("post", "")
            post_cmd = app.get("post_cmd", "")
            copiar_a_temp = app.get("copiar_a_temp", True)

            log(f"[{index}/{total_apps}] Procesando: {nombre}")

            # Validar base
            if base not in rutas_base:
                log(f"❌ Base no definida en config.json: {base}\n")
                progress_var.set(index)
                root.update_idletasks()
                continue

            # Construir ruta real (UNC)
            ruta = os.path.join(rutas_base[base], ruta_relativa)
            log(f"Ruta (red): {ruta}")

            # Verificar acceso a carpeta
            try:
                carpeta_red = os.path.dirname(ruta)
                os.listdir(carpeta_red)
                log("✔ Carpeta accesible")
            except Exception as e:
                log(f"❌ No se puede acceder a la carpeta: {e}\n")
                progress_var.set(index)
                root.update_idletasks()
                continue

            # -----------------------------
            # TIPO: CARPETA (copiar)
            # -----------------------------
            if tipo == "carpeta":
                destino = app.get("destino", "")
                if not destino:
                    log("❌ No se definió destino para la carpeta\n")
                    progress_var.set(index)
                    root.update_idletasks()
                    continue

                if not os.path.exists(ruta):
                    log("❌ Carpeta origen no encontrada en red\n")
                    progress_var.set(index)
                    root.update_idletasks()
                    continue

                try:
                    log("Copiando carpeta...")

                    if os.path.exists(destino):
                        log("Carpeta ya existe en destino, eliminando...")
                        shutil.rmtree(destino)

                    shutil.copytree(ruta, destino)
                    log(f"✔ Carpeta copiada correctamente a {destino}\n")

                except Exception as e:
                    log(f"❌ Error copiando carpeta: {e}\n")

                progress_var.set(index)
                root.update_idletasks()
                continue

            # -----------------------------
            # TIPO: EXE/MSI (instalación)
            # -----------------------------
            if not os.path.exists(ruta):
                log("❌ Instalador no encontrado en red")
                log("⚠ Se omite esta aplicación\n")
                progress_var.set(index)
                root.update_idletasks()
                continue

            ruta_ejecucion = ruta
            ruta_local = None

            # Copiar a TEMP (si aplica)
            if copiar_a_temp:
                try:
                    log("Copiando instalador a TEMP...")
                    ruta_local = stage_to_temp(ruta)
                    ruta_ejecucion = ruta_local
                    log(f"Ruta (local): {ruta_local}")
                except Exception as e:
                    log(f"❌ Error al copiar a TEMP: {e}\n")
                    progress_var.set(index)
                    root.update_idletasks()
                    continue
            else:
                log("⚠ Ejecutando desde carpeta original (no se copia a TEMP)")

            # Ejecutar instalación
            try:
                if tipo == "msi":
                    log("Instalando paquete MSI (msiexec)...")
                    # Log MSI para diagnóstico
                    msi_log = os.path.join(tempfile.gettempdir(), f"msi_{nombre.replace(' ', '_')}.log")
                    comando = f'msiexec /i "{ruta_ejecucion}" /qn /norestart /l*v "{msi_log}" {args}'.strip()
                    log(f"MSI log: {msi_log}")
                    result = subprocess.run(comando, shell=True)
                    code = result.returncode
                else:
                    result = subprocess.run(f'"{ruta_ejecucion}" {args}', shell=True)
                    code = result.returncode

                if code != 0:
                    log(f"❌ Error al instalar {nombre} (code {code})\n")
                    progress_var.set(index)
                    root.update_idletasks()
                    continue

                log(f"✔ Instalación completada: {nombre}")

            except Exception as e:
                log(f"❌ Excepción durante la instalación: {e}\n")
                progress_var.set(index)
                root.update_idletasks()
                continue
            finally:
                # Borrar temporal solo si lo copiamos
                if ruta_local:
                    try:
                        if os.path.exists(ruta_local):
                            os.remove(ruta_local)
                            log("✔ Instalador temporal eliminado")
                    except Exception as e:
                        log(f"⚠ No se pudo eliminar el instalador temporal: {e}")

            # -----------------------------
            # Post: .reg
            # -----------------------------
            if post:
                reg_path = resource_path(post) if os.path.exists(resource_path(post)) else os.path.abspath(post)
                if os.path.exists(reg_path):
                    log("Aplicando configuración (.reg)...")
                    subprocess.run(f'reg import "{reg_path}"', shell=True)
                    log("✔ Configuración aplicada")
                else:
                    log(f"⚠ Archivo .reg no encontrado: {reg_path}")

            # -----------------------------
            # Post: comando
            # -----------------------------
            if post_cmd:
                log("Ejecutando comando post-instalación...")
                try:
                    r = subprocess.run(post_cmd, shell=True)
                    if r.returncode == 0:
                        log("✔ Post-comando ejecutado")
                    else:
                        log(f"⚠ Post-comando terminó con code {r.returncode}")
                except Exception as e:
                    log(f"⚠ Error ejecutando post_cmd: {e}")

            log("")
            progress_var.set(index)
            root.update_idletasks()

        log("Proceso finalizado ✔\n")

    except json.JSONDecodeError:
        messagebox.showerror("Error", "El archivo JSON tiene un formato inválido")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def start(json_filename: str):
    threading.Thread(target=run_installation, args=(json_filename,), daemon=True).start()


# -----------------------------
# MAIN
# -----------------------------
ensure_admin()

root = tk.Tk()
root.title("AutoInstaller")

frame = tk.Frame(root)
frame.pack(padx=20, pady=20)

tk.Button(frame, text="Instalación Kielsa", width=25,
          command=lambda: start("kielsa.json")).pack(pady=5)

tk.Button(frame, text="Instalación Farinter", width=25,
          command=lambda: start("farinter.json")).pack(pady=5)

console = tk.Text(root, height=15, width=90)
console.pack(padx=10, pady=10)

progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(
    root,
    orient="horizontal",
    length=700,
    mode="determinate",
    variable=progress_var
)
progress_bar.pack(pady=10)

root.mainloop()
