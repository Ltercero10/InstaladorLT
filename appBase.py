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


def log(msg: str):
    console.insert(tk.END, msg + "\n")
    console.see(tk.END)


def load_config():
    if not os.path.exists("config.json"):
        messagebox.showerror("Error", "No se encontró config.json")
        return None

    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def stage_to_temp(src_path: str) -> str:
    """Copia el instalador desde red (UNC) a %TEMP% y lo desbloquea."""
    temp_dir = tempfile.gettempdir()
    base_name = os.path.basename(src_path)

    dst_path = os.path.join(temp_dir, base_name)
    if os.path.exists(dst_path):
        name, ext = os.path.splitext(base_name)
        dst_path = os.path.join(temp_dir, f"{name}_{int(time.time())}{ext}")

    shutil.copy2(src_path, dst_path)

    # Desbloquear (Mark-of-the-Web)
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


def run_installation(json_file: str):
    try:
        if not os.path.exists(json_file):
            messagebox.showerror("Error", f"No se encontró el archivo {json_file}")
            return

        config = load_config()
        if not config:
            return

        with open(json_file, "r", encoding="utf-8") as f:
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

        for index, app in enumerate(apps, start=1):
            nombre = app.get("nombre", "Desconocido")
            tipo = app.get("tipo", "exe")  # exe | msi | carpeta
            base = app.get("base", "")
            ruta_relativa = app.get("ruta", "")
            args = app.get("args", "")
            post = app.get("post", "")
            post_cmd = app.get("post_cmd", "")
            copiar_a_temp = app.get("copiar_a_temp", True)

            log(f"[{index}/{total_apps}] Instalando: {nombre}")

            # Validar base
            if base not in config.get("rutas_base", {}):
                log(f"❌ Base no definida en config.json: {base}\n")
                progress_var.set(index)
                root.update_idletasks()
                continue

            # Construir ruta red
            ruta = os.path.join(config["rutas_base"][base], ruta_relativa)
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

            # =============== TIPO: CARPETA ===============
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

            # Validar instalador (exe/msi) exista en red
            if not os.path.exists(ruta):
                log("❌ Instalador no encontrado en red")
                log("⚠ Se omite esta aplicación\n")
                progress_var.set(index)
                root.update_idletasks()
                continue

            # Definir ruta de ejecución
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

            # Ejecutar instalación (SIN SAP)
            try:
                if tipo == "msi":
                    log("Instalando paquete MSI (msiexec)...")
                    comando = f'msiexec /i "{ruta_ejecucion}" /qn /norestart {args}'.strip()
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

            # Post: .reg
            if post:
                reg_path = os.path.abspath(post)
                if os.path.exists(reg_path):
                    log("Aplicando configuración (.reg)...")
                    subprocess.run(f'reg import "{reg_path}"', shell=True)
                    log("✔ Configuración aplicada")
                else:
                    log(f"⚠ Archivo .reg no encontrado: {reg_path}")

            # Post: comando
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


def start(json_file: str):
    threading.Thread(target=run_installation, args=(json_file,), daemon=True).start()


ensure_admin()

root = tk.Tk()
root.title("AutoInstalador")

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
