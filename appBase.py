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
import platform
import socket
import getpass
import psutil
from datetime import datetime

log_file_path = None
current_apps = []
current_mode_name = ""
last_log_content = ""


def resource_path(relative_path: str) -> str:
    """
    Devuelve ruta absoluta tanto en .py como en .exe (PyInstaller --onefile).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


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


def write_log_file(msg: str):
    global log_file_path
    if not log_file_path:
        return

    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def log(msg: str):
    global last_log_content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    console.insert(tk.END, line + "\n")
    console.see(tk.END)
    write_log_file(line)
    last_log_content += line + "\n"


def clear_console():
    global last_log_content
    console.delete("1.0", tk.END)
    last_log_content = ""


def set_status(text: str):
    status_var.set(text)
    root.update_idletasks()


def load_json_file(filename: str):
    path = resource_path(filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo {filename}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    cfg = resource_path("config.json")
    if not os.path.exists(cfg):
        messagebox.showerror("Error", "No se encontró config.json")
        return None

    with open(cfg, "r", encoding="utf-8") as f:
        return json.load(f)


def create_log_file(mode_name: str) -> str:
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    safe_mode = mode_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"{safe_mode}_{timestamp}.log")

def get_logs_folder() -> str:
    folder = os.path.join(os.getcwd(), "logs")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_latest_log_file():
    folder = get_logs_folder()
    log_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".log")
    ]

    if not log_files:
        return None

    return max(log_files, key=os.path.getmtime)


def read_log_content(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"No se pudo leer la bitácora.\n\nDetalle: {e}"




def stage_to_temp(src_path: str) -> str:
    temp_dir = tempfile.gettempdir()
    base_name = os.path.basename(src_path)

    dst_path = os.path.join(temp_dir, base_name)
    if os.path.exists(dst_path):
        name, ext = os.path.splitext(base_name)
        dst_path = os.path.join(temp_dir, f"{name}_{int(time.time())}{ext}")

    shutil.copy2(src_path, dst_path)

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


def show_summary(mode_name, total_apps, success_count, failed_count, skipped_count, total_time, log_path):
    summary = (
        f"Modo ejecutado: {mode_name}\n"
        f"Total de aplicaciones: {total_apps}\n"
        f"Instaladas correctamente: {success_count}\n"
        f"Fallidas: {failed_count}\n"
        f"Omitidas: {skipped_count}\n"
        f"Tiempo total: {total_time:.2f} segundos\n"
        f"Bitácora guardada en:\n{log_path}"
    )

    log("=" * 70)
    log("RESUMEN FINAL")
    log("=" * 70)
    log(f"Modo ejecutado: {mode_name}")
    log(f"Total de aplicaciones: {total_apps}")
    log(f"Instaladas correctamente: {success_count}")
    log(f"Fallidas: {failed_count}")
    log(f"Omitidas: {skipped_count}")
    log(f"Tiempo total: {total_time:.2f} segundos")
    log(f"Bitácora: {log_path}")
    log("=" * 70)

    root.after(0, lambda: messagebox.showinfo("Resumen final", summary))


def execute_apps(mode_name: str, apps: list):
    global log_file_path

    start_time = time.time()
    success_count = 0
    failed_count = 0
    skipped_count = 0
    total_apps = len(apps)

    try:
        root.after(0, lambda: btn_run.config(state="disabled"))
        root.after(0, lambda: progress_var.set(0))
        root.after(0, clear_console)
        root.after(0, lambda: set_status("Preparando instalación..."))

        config = load_config()
        if not config:
            root.after(0, lambda: btn_run.config(state="normal"))
            root.after(0, lambda: set_status("Error de configuración"))
            return

        log_file_path = create_log_file(mode_name)
        root.after(0, lambda: progress_bar.config(maximum=total_apps if total_apps > 0 else 1))

        if total_apps == 0:
            log("No hay aplicaciones seleccionadas para instalar.")
            root.after(0, lambda: btn_run.config(state="normal"))
            root.after(0, lambda: set_status("Sin aplicaciones seleccionadas"))
            return

        log("AUTOINSTALLER - INICIO DE PROCESO")
        log(f"Modo seleccionado: {mode_name}")
        log(f"Total de aplicaciones: {total_apps}")
        log(f"Archivo de bitácora: {log_file_path}")
        log("")

        

        rutas_base = config.get("rutas_base", {})

        for index, app in enumerate(apps, start=1):
            nombre = app.get("nombre", "Desconocido")
            tipo = app.get("tipo", "exe")
            base = app.get("base", "")
            ruta_relativa = app.get("ruta", "")
            args = app.get("args", "")
            post = app.get("post", "")
            post_cmd = app.get("post_cmd", "")
            copiar_a_temp = app.get("copiar_a_temp", True)

            root.after(0, lambda n=nombre, i=index, t=total_apps: set_status(f"Instalando {i}/{t}: {n}"))
            log(f"[{index}/{total_apps}] Procesando: {nombre}")

            if base not in rutas_base:
                log(f"Base no definida en config.json: {base}")
                log("")
                skipped_count += 1
                root.after(0, lambda i=index: progress_var.set(i))
                continue

            ruta = os.path.join(rutas_base[base], ruta_relativa)
            log(f"Ruta de red: {ruta}")

            try:
                carpeta_red = os.path.dirname(ruta)
                os.listdir(carpeta_red)
                log("Carpeta accesible")
            except Exception as e:
                log(f"No se puede acceder a la carpeta: {e}")
                log("")
                skipped_count += 1
                root.after(0, lambda i=index: progress_var.set(i))
                continue

            if tipo == "carpeta":
                destino = app.get("destino", "")
                if not destino:
                    log("No se definió destino para la carpeta")
                    log("")
                    failed_count += 1
                    root.after(0, lambda i=index: progress_var.set(i))
                    continue

                if not os.path.exists(ruta):
                    log("Carpeta origen no encontrada en red")
                    log("")
                    skipped_count += 1
                    root.after(0, lambda i=index: progress_var.set(i))
                    continue

                try:
                    log("Copiando carpeta...")

                    if os.path.exists(destino):
                        log("Carpeta existente detectada, eliminando versión previa...")
                        shutil.rmtree(destino)

                    shutil.copytree(ruta, destino)
                    log(f"Carpeta copiada correctamente a {destino}")
                    success_count += 1

                except Exception as e:
                    log(f"Error copiando carpeta: {e}")
                    failed_count += 1

                log("")
                root.after(0, lambda i=index: progress_var.set(i))
                continue

            if not os.path.exists(ruta):
                log("Instalador no encontrado en red")
                log("Se omite esta aplicación")
                log("")
                skipped_count += 1
                root.after(0, lambda i=index: progress_var.set(i))
                continue

            ruta_ejecucion = ruta
            ruta_local = None
            install_ok = False

            if copiar_a_temp:
                try:
                    log("Copiando instalador a carpeta temporal...")
                    ruta_local = stage_to_temp(ruta)
                    ruta_ejecucion = ruta_local
                    log(f"Ruta local: {ruta_local}")
                except Exception as e:
                    log(f"Error al copiar a TEMP: {e}")
                    log("")
                    failed_count += 1
                    root.after(0, lambda i=index: progress_var.set(i))
                    continue
            else:
                log("Ejecutando desde la ubicación original")

            try:
                if tipo == "msi":
                    log("Instalando paquete MSI...")
                    msi_log = os.path.join(tempfile.gettempdir(), f"msi_{nombre.replace(' ', '_')}.log")
                    comando = f'msiexec /i "{ruta_ejecucion}" /qn /norestart /l*v "{msi_log}" {args}'.strip()
                    log(f"Log MSI: {msi_log}")
                    result = subprocess.run(comando, shell=True)
                    code = result.returncode
                else:
                    result = subprocess.run(f'"{ruta_ejecucion}" {args}', shell=True)
                    code = result.returncode

                if code != 0:
                    log(f"Error al instalar {nombre} (code {code})")
                    failed_count += 1
                    log("")
                    root.after(0, lambda i=index: progress_var.set(i))
                    continue

                log(f"Instalación completada correctamente: {nombre}")
                install_ok = True

            except Exception as e:
                log(f"Excepción durante la instalación: {e}")
                failed_count += 1
                log("")
                root.after(0, lambda i=index: progress_var.set(i))
                continue
            finally:
                if ruta_local:
                    try:
                        if os.path.exists(ruta_local):
                            os.remove(ruta_local)
                            log("Archivo temporal eliminado")
                    except Exception as e:
                        log(f"No se pudo eliminar el instalador temporal: {e}")

            if post:
                reg_path = resource_path(post) if os.path.exists(resource_path(post)) else os.path.abspath(post)
                if os.path.exists(reg_path):
                    log("Aplicando configuración adicional (.reg)...")
                    subprocess.run(f'reg import "{reg_path}"', shell=True)
                    log("Configuración adicional aplicada")
                else:
                    log(f"Archivo .reg no encontrado: {reg_path}")

            if post_cmd:
                log("Ejecutando comando posterior a la instalación...")
                try:
                    r = subprocess.run(post_cmd, shell=True)
                    if r.returncode == 0:
                        log("Post-comando ejecutado correctamente")
                    else:
                        log(f"Post-comando finalizó con code {r.returncode}")
                except Exception as e:
                    log(f"Error ejecutando post_cmd: {e}")

            if install_ok:
                success_count += 1

            log("")
            root.after(0, lambda i=index: progress_var.set(i))

        total_time = time.time() - start_time
        root.after(0, lambda: set_status("Instalación finalizada"))
        root.after(
            0,
            lambda: show_summary(
                mode_name,
                total_apps,
                success_count,
                failed_count,
                skipped_count,
                total_time,
                log_file_path
            )
        )

    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Error", str(e)))
        root.after(0, lambda: set_status("Error durante la instalación"))
    finally:
        root.after(0, lambda: btn_run.config(state="normal"))


def start_installation():
    global current_apps, current_mode_name

    if not current_apps:
        messagebox.showwarning("Selección requerida", "Debe seleccionar un perfil o aplicaciones.")
        return

    threading.Thread(
        target=execute_apps,
        args=(current_mode_name, current_apps),
        daemon=True
    ).start()


def clear_content():
    for widget in content_area.winfo_children():
        widget.destroy()


def set_active_menu(button):
    buttons = [btn_menu_inicio, btn_menu_perfiles, btn_menu_apps, btn_menu_bitacora, btn_menu_acerca, btn_menu_equipo]
    for btn in buttons:
        btn.configure(bg="#1f2937", fg="white")
    button.configure(bg="#374151", fg="white")


def show_home():
    global current_apps, current_mode_name
    set_active_menu(btn_menu_inicio)
    clear_content()
    current_apps = []
    current_mode_name = ""

    tk.Label(
        content_area,
        text="Bienvenido a AutoInstaller",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", pady=(5, 8))

    tk.Label(
        content_area,
        text="Sistema de automatización para instalación y configuración inicial de equipos corporativos.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 11),
        wraplength=700,
        justify="left"
    ).pack(anchor="w", pady=(0, 10))

    info_frame = tk.Frame(content_area, bg="#ffffff")
    info_frame.pack(anchor="w", fill="x", pady=(10, 0))

    items = [
        "• Instala software según perfiles definidos.",
        "• Permite selección manual de aplicaciones.",
        "• Genera bitácora automática de ejecución.",
        "• Presenta un resumen final del proceso.",
        "• Facilita la estandarización post-formateo."
    ]

    for item in items:
        tk.Label(
            info_frame,
            text=item,
            bg="#ffffff",
            fg="#374151",
            font=("Segoe UI", 10),
            anchor="w",
            justify="left"
        ).pack(anchor="w", pady=3)

    set_status("Pantalla principal")

def show_equipo():
    set_active_menu(btn_menu_equipo)
    clear_content()

    tk.Label(
        content_area,
        text="Información del equipo",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        content_area,
        text="Resumen técnico del equipo actual para validación previa al despliegue.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    info = get_system_info()

    table_container = tk.Frame(content_area, bg="#ffffff")
    table_container.pack(fill="both", expand=True, pady=(5, 10))

    canvas = tk.Canvas(table_container, bg="#ffffff", highlightthickness=0)
    scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#ffffff")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set, height=320)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    

    for i, (key, value) in enumerate(info.items()):
        key_label = tk.Label(
            scrollable_frame,
            text=key,
            bg="#f9fafb",
            fg="#111827",
            font=("Segoe UI", 10, "bold"),
            width=24,
            anchor="w",
            padx=10,
            pady=8,
            relief="solid",
            bd=1
        )
        key_label.grid(row=i, column=0, sticky="nsew")

        value_label = tk.Label(
            scrollable_frame,
            text=str(value),
            bg="#ffffff",
            fg="#374151",
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=500,
            padx=10,
            pady=8,
            relief="solid",
            bd=1
        )
        value_label.grid(row=i, column=1, sticky="nsew")

    def refresh_info():
        show_equipo()
        set_status("Información del equipo actualizada")

    tk.Button(
        content_area,
        text="Actualizar información",
        bg="#0d6efd",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=refresh_info
    ).pack(anchor="w", pady=(10, 0))

    set_status("Vista de información del equipo")

def show_profiles():
    global current_apps, current_mode_name
    set_active_menu(btn_menu_perfiles)
    clear_content()
    current_apps = []
    current_mode_name = ""

    tk.Label(
        content_area,
        text="Perfiles predefinidos",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        content_area,
        text="Seleccione un perfil corporativo para cargar su conjunto de aplicaciones.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    cards_frame = tk.Frame(content_area, bg="#ffffff")
    cards_frame.pack(fill="x", pady=(5, 0))

    def select_profile(filename):
        global current_apps, current_mode_name
        try:
            data = load_json_file(filename)
            current_apps = data.get("apps", [])
            current_mode_name = data.get("modo", "Perfil")
            selected_label.config(text=f"Selección actual: {current_mode_name} ({len(current_apps)} aplicaciones)")
            set_status(f"Perfil seleccionado: {current_mode_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_profile_card(parent, title, description, color, filename):
        card = tk.Frame(parent, bg="#f9fafb", bd=1, relief="solid")
        card.pack(side="left", padx=8, pady=8, fill="both", expand=True)

        color_bar = tk.Frame(card, bg=color, height=6)
        color_bar.pack(fill="x")

        tk.Label(
            card,
            text=title,
            bg="#f9fafb",
            fg="#111827",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 5))

        tk.Label(
            card,
            text=description,
            bg="#f9fafb",
            fg="#4b5563",
            font=("Segoe UI", 10),
            wraplength=260,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 12))

        tk.Button(
            card,
            text="Seleccionar perfil",
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            command=lambda: select_profile(filename)
        ).pack(anchor="w", padx=15, pady=(0, 15))

    build_profile_card(
        cards_frame,
        "Perfil Farinter",
        "Carga el conjunto de aplicaciones y configuraciones definidas para el entorno Farinter.",
        "#0d6efd",
        "farinter.json"
    )
    build_profile_card(
        cards_frame,
        "Perfil Kielsa",
        "Carga el conjunto de aplicaciones y configuraciones definidas para el entorno Kielsa.",
        "#c6ca0a",
        "kielsa.json"
    )


    selected_label = tk.Label(
        content_area,
        text="Selección actual: ninguna",
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold")
    )
    selected_label.pack(anchor="w", pady=(15, 0))


def show_applications():
    global current_apps, current_mode_name
    set_active_menu(btn_menu_apps)
    clear_content()
    current_apps = []
    current_mode_name = ""

    tk.Label(
        content_area,
        text="Instalación personalizada",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        content_area,
        text="Seleccione manualmente las aplicaciones que desea instalar.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    try:
        data = load_json_file("catalogo_apps.json")
        apps = data.get("apps", [])
    except Exception as e:
        tk.Label(
            content_area,
            text=f"No se pudo cargar catalogo_apps.json: {e}",
            bg="#ffffff",
            fg="red",
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        return

    vars_list = []

    actions_frame = tk.Frame(content_area, bg="#ffffff")
    actions_frame.pack(fill="x", pady=(0, 8))

    container = tk.Frame(content_area, bg="#ffffff")
    container.pack(fill="both", expand=False)

    canvas = tk.Canvas(container, bg="#ffffff", highlightthickness=0)
    scrollbar_apps = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#ffffff")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar_apps.set, height=260)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar_apps.pack(side="right", fill="y")

    def refresh_selection_label():
        selected_count = sum(1 for _, var in vars_list if var.get())
        selection_label.config(text=f"Aplicaciones seleccionadas: {selected_count}")

    def toggle_all(value: bool):
        for _, var in vars_list:
            var.set(value)
        refresh_selection_label()

    def load_selected_apps():
        global current_apps, current_mode_name
        selected_apps = [app for app, var in vars_list if var.get()]

        if not selected_apps:
            messagebox.showwarning("Selección requerida", "Debe seleccionar al menos una aplicación.")
            return

        current_apps = selected_apps
        current_mode_name = "Instalación personalizada"
        selection_label.config(text=f"Aplicaciones seleccionadas: {len(current_apps)}")
        set_status(f"{len(current_apps)} aplicaciones cargadas para instalación")

    tk.Button(
        actions_frame,
        text="Seleccionar todas",
        bg="#0d6efd",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 9, "bold"),
        command=lambda: toggle_all(True)
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        actions_frame,
        text="Limpiar selección",
        bg="#6b7280",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 9, "bold"),
        command=lambda: toggle_all(False)
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        actions_frame,
        text="Cargar selección",
        bg="#198754",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 9, "bold"),
        command=load_selected_apps
    ).pack(side="left")

    for idx, app in enumerate(apps):
        var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            scrollable_frame,
            text=app.get("nombre", "Aplicación"),
            variable=var,
            bg="#ffffff",
            fg="#111827",
            font=("Segoe UI", 10),
            activebackground="#ffffff",
            command=refresh_selection_label
        )
        chk.grid(row=idx // 2, column=idx % 2, sticky="w", padx=12, pady=6)
        vars_list.append((app, var))

    selection_label = tk.Label(
        content_area,
        text="Aplicaciones seleccionadas: 0",
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold")
    )
    selection_label.pack(anchor="w", pady=(10, 0))


def show_bitacora():
    set_active_menu(btn_menu_bitacora)
    clear_content()

    tk.Label(
        content_area,
        text="Bitácora",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        content_area,
        text="En esta sección se muestra el contenido de la última bitácora disponible.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    info_var = tk.StringVar()
    info_label = tk.Label(
        content_area,
        textvariable=info_var,
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold"),
        justify="left",
        wraplength=760
    )
    info_label.pack(anchor="w", pady=(0, 10))

    log_box_frame = tk.Frame(content_area, bg="#ffffff")
    log_box_frame.pack(fill="both", expand=True)

    log_box = tk.Text(
        log_box_frame,
        height=18,
        bg="#f8fafc",
        fg="#111827",
        insertbackground="#111827",
        relief="solid",
        bd=1,
        wrap="word",
        font=("Consolas", 10),
        padx=10,
        pady=10
    )
    log_box.pack(side="left", fill="both", expand=True)

    log_scroll = ttk.Scrollbar(log_box_frame, orient="vertical", command=log_box.yview)
    log_scroll.pack(side="right", fill="y")
    log_box.configure(yscrollcommand=log_scroll.set)

    def load_log_into_box():
        log_box.config(state="normal")
        log_box.delete("1.0", tk.END)

        selected_log = None

        if log_file_path and os.path.exists(log_file_path):
            selected_log = log_file_path
        else:
            selected_log = get_latest_log_file()

        if not selected_log:
            info_var.set("No se encontraron archivos de bitácora.")
            log_box.insert("1.0", "Todavía no existe ninguna bitácora para mostrar.")
            log_box.config(state="disabled")
            return

        info_var.set(f"Archivo cargado: {selected_log}")
        content = read_log_content(selected_log)
        log_box.insert("1.0", content if content.strip() else "La bitácora está vacía.")
        log_box.config(state="disabled")

    buttons_frame = tk.Frame(content_area, bg="#ffffff")
    buttons_frame.pack(fill="x", pady=(12, 0))

    def refresh_log():
        load_log_into_box()
        set_status("Bitácora actualizada")

    def open_logs_folder():
        folder = get_logs_folder()
        os.startfile(folder)

    tk.Button(
        buttons_frame,
        text="Actualizar bitácora",
        bg="#198754",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=refresh_log
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        buttons_frame,
        text="Abrir carpeta de logs",
        bg="#0d6efd",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=open_logs_folder
    ).pack(side="left")

    load_log_into_box()
    set_status("Vista de bitácora")


def show_about():
    set_active_menu(btn_menu_acerca)
    clear_content()

    tk.Label(
        content_area,
        text="Acerca del proyecto",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    info = (
        "AutoInstaller es una herramienta de automatización desarrollada en Python para "
        "estandarizar la instalación de software y la configuración inicial de equipos "
        "corporativos después de un formateo.\n\n"
        "Características principales:\n"
        "• Instalación por perfiles corporativos.\n"
        "• Selección manual de aplicaciones.\n"
        "• Ejecución silenciosa de instaladores.\n"
        "• Copia de recursos desde rutas de red.\n"
        "• Bitácora de ejecución.\n"
        "• Resumen final del proceso."
    )

    tk.Label(
        content_area,
        text=info,
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10),
        justify="left",
        wraplength=700
    ).pack(anchor="w")

    set_status("Información del sistema")


def bytes_to_gb(value):
    return round(value / (1024 ** 3), 2)

def get_ram_details():
    try:

        result = subprocess.check_output(
            'wmic memphysical get maxcapacity, memorydevices',
            shell=True, text=True, stderr=subprocess.DEVNULL
        )
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2:
            parts = lines[1].split()
            max_gb = round(int(parts[0]) / (1024**2), 2)
            slots = parts[1]
            return f"{slots} Slots (Máx. {max_gb} GB)"
    except:
        pass
    return "No disponible"

def get_extra_disks():
    try:
        discos = []
        for part in psutil.disk_partitions():

            if "fixed" in part.opts and part.mountpoint != "C:\\":
                usage = psutil.disk_usage(part.mountpoint)
                info = f"{part.mountpoint} ({bytes_to_gb(usage.total)} GB)"
                discos.append(info)
        return ", ".join(discos) if discos else "Ninguno detectado"
    except:
        return "No disponible"

def get_pc_serial():
    try:
        result = subprocess.check_output(
            'wmic bios get serialnumber',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    return "No disponible"


def get_pc_model():
    try:
        result = subprocess.check_output(
            'wmic computersystem get manufacturer,model',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    return "No disponible"


def get_domain_or_workgroup():
    try:
        result = subprocess.check_output(
            'wmic computersystem get domain',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    return "No disponible"


def get_ip_address():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return "No disponible"


def get_system_info():
    try:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "Nombre del equipo": socket.gethostname(),
            "Usuario actual": getpass.getuser(),
            "Sistema operativo": f"{platform.system()} {platform.release()}",
            "Versión": platform.version(),
            "Arquitectura": platform.machine(),
            "Procesador": platform.processor() or "No disponible",
            "RAM total (GB)": bytes_to_gb(vm.total),
            "RAM disponible (GB)": bytes_to_gb(vm.available),
            "Capacidad RAM / Slots": get_ram_details(),
            "Disco total C: (GB)": bytes_to_gb(disk.total),
            "Disco libre C: (GB)": bytes_to_gb(disk.free),
            "Discos adicionales": get_extra_disks(),
            "IP": get_ip_address(),
            "Dominio / Grupo": get_domain_or_workgroup(),
            "Fabricante / Modelo": get_pc_model(),
            "Service Tag / Serial": get_pc_serial(),
            "Último arranque": boot_time
        }
    except Exception as e:
        return {"Error": str(e)}

ensure_admin()

root = tk.Tk()
root.title("AutoInstaller Farinter Corporativo")
root.geometry("1220x760")
root.minsize(1100, 700)
root.configure(bg="#eef2f7")

style = ttk.Style()
style.theme_use("clam")
style.configure("TProgressbar", thickness=16)

main_frame = tk.Frame(root, bg="#eef2f7")
main_frame.pack(fill="both", expand=True)

# SIDEBAR
sidebar = tk.Frame(main_frame, bg="#1f2937", width=240)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

tk.Label(
    sidebar,
    text="Grupo Farinter",
    bg="#1f2937",
    fg="white",
    font=("Segoe UI", 18, "bold")
).pack(anchor="w", padx=20, pady=(20, 5))

tk.Label(
    sidebar,
    text="Panel de navegación",
    bg="#1f2937",
    fg="#cbd5e1",
    font=("Segoe UI", 10)
).pack(anchor="w", padx=20, pady=(0, 20))


def create_menu_button(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        bg="#1f2937",
        fg="white",
        activebackground="#374151",
        activeforeground="white",
        relief="flat",
        bd=0,
        cursor="hand2",
        anchor="w",
        padx=20,
        pady=12,
        font=("Segoe UI", 11, "bold"),
        command=command
    )


btn_menu_inicio = create_menu_button(sidebar, "Inicio", show_home)
btn_menu_inicio.pack(fill="x")

btn_menu_perfiles = create_menu_button(sidebar, "Perfiles", show_profiles)
btn_menu_perfiles.pack(fill="x")

btn_menu_apps = create_menu_button(sidebar, "Aplicaciones", show_applications)
btn_menu_apps.pack(fill="x")

btn_menu_equipo = create_menu_button(sidebar, "Equipo", show_equipo)
btn_menu_equipo.pack(fill="x")

btn_menu_bitacora = create_menu_button(sidebar, "Bitácora", show_bitacora)
btn_menu_bitacora.pack(fill="x")


btn_menu_acerca = create_menu_button(sidebar, "Acerca de", show_about)
btn_menu_acerca.pack(fill="x")

# RIGHT SIDE
right_panel = tk.Frame(main_frame, bg="#eef2f7")
right_panel.pack(side="left", fill="both", expand=True)

header = tk.Frame(right_panel, bg="#eef2f7")
header.pack(fill="x", padx=20, pady=(18, 10))

tk.Label(
    header,
    text="Sistema de despliegue automatizado",
    bg="#eef2f7",
    fg="#111827",
    font=("Segoe UI", 20, "bold")
).pack(anchor="w")

tk.Label(
    header,
    text="Instalación por perfiles y selección manual de aplicaciones",
    bg="#eef2f7",
    fg="#6b7280",
    font=("Segoe UI", 10)
).pack(anchor="w", pady=(3, 0))

body = tk.Frame(right_panel, bg="#eef2f7")
body.pack(fill="both", expand=True, padx=20, pady=(0, 15))

content_card = tk.Frame(body, bg="#ffffff", bd=1, relief="solid")
content_card.pack(fill="both", expand=True)

content_area = tk.Frame(content_card, bg="#ffffff")
content_area.pack(fill="x", padx=20, pady=(18, 10))

action_area = tk.Frame(content_card, bg="#ffffff")
action_area.pack(fill="x", padx=20, pady=(0, 10))

btn_run = tk.Button(
    action_area,
    text="Ejecutar instalación",
    bg="#0d6efd",
    fg="white",
    activebackground="#0b5ed7",
    activeforeground="white",
    relief="flat",
    cursor="hand2",
    font=("Segoe UI", 11, "bold"),
    padx=18,
    pady=10,
    command=start_installation
)
btn_run.pack(side="left")

status_var = tk.StringVar(value="Esperando selección")
status_label = tk.Label(
    action_area,
    textvariable=status_var,
    bg="#ffffff",
    fg="#374151",
    font=("Segoe UI", 10, "bold")
)
status_label.pack(side="left", padx=15)

progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(
    content_card,
    orient="horizontal",
    mode="determinate",
    variable=progress_var
)
progress_bar.pack(fill="x", padx=20, pady=(0, 12))

console_label = tk.Label(
    content_card,
    text="Consola de ejecución",
    bg="#ffffff",
    fg="#111827",
    font=("Segoe UI", 11, "bold")
)
console_label.pack(anchor="w", padx=20, pady=(0, 6))

console_frame = tk.Frame(content_card, bg="#ffffff")
console_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

console = tk.Text(
    console_frame,
    bg="#f8fafc",
    fg="#111827",
    insertbackground="#111827",
    relief="solid",
    bd=1,
    wrap="word",
    font=("Consolas", 10),
    padx=12,
    pady=12
)
console.pack(side="left", fill="both", expand=True)

console_scroll = ttk.Scrollbar(console_frame, orient="vertical", command=console.yview)
console_scroll.pack(side="right", fill="y")
console.configure(yscrollcommand=console_scroll.set)

show_home()

root.mainloop()