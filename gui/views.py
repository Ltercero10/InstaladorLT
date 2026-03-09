import tkinter as tk
import os
from tkinter import messagebox
from core.config import load_json_file
from core.logger import global_logger as logger
from utils.system_info import get_system_info
from gui.components import create_profile_card, create_info_table
from utils.system_info import (get_system_info,open_driver_support_page,update_drivers)
from tkinter import ttk
# ============= VISTA INICIO =============
def show_home(app):
    """Muestra la pantalla de inicio"""
    app.set_active_menu(app.btn_menu_inicio)
    app.clear_content()
    app.current_apps = []
    app.current_mode_name = ""

    app.show_installation_ui()

    tk.Label(
        app.content_area,
        text="Bienvenido a AutoInstaller",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", pady=(5, 8))

    tk.Label(
        app.content_area,
        text="Sistema de automatización para instalación y configuración inicial de equipos corporativos.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 11),
        wraplength=700,
        justify="left"
    ).pack(anchor="w", pady=(0, 10))

    info_frame = tk.Frame(app.content_area, bg="#ffffff")
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

    app.set_status("Pantalla principal")


# ============= VISTA PERFILES =============
def show_profiles(app):
    """Muestra la pantalla de perfiles predefinidos"""
    app.set_active_menu(app.btn_menu_perfiles)
    app.clear_content()
    app.current_apps = []
    app.current_mode_name = ""

    tk.Label(
        app.content_area,
        text="Perfiles predefinidos",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        app.content_area,
        text="Seleccione un perfil corporativo para cargar su conjunto de aplicaciones.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    cards_frame = tk.Frame(app.content_area, bg="#ffffff")
    cards_frame.pack(fill="x", pady=(5, 0))

    def select_profile(filename):
        try:
            data = load_json_file(filename)
            app.current_apps = data.get("apps", [])
            app.current_mode_name = data.get("modo", "Perfil")
            selected_label.config(text=f"Selección actual: {app.current_mode_name} ({len(app.current_apps)} aplicaciones)")
            app.set_status(f"Perfil seleccionado: {app.current_mode_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Crear tarjetas de perfiles
    create_profile_card(
        cards_frame,
        "Perfil Farinter",
        "Carga el conjunto de aplicaciones y configuraciones definidas para el entorno Farinter.",
        "#0d6efd",
        lambda: select_profile("farinter.json")
    )
    
    create_profile_card(
        cards_frame,
        "Perfil Kielsa",
        "Carga el conjunto de aplicaciones y configuraciones definidas para el entorno Kielsa.",
        "#c6ca0a",
        lambda: select_profile("kielsa.json")
    )

    selected_label = tk.Label(
        app.content_area,
        text="Selección actual: ninguna",
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold")
    )
    selected_label.pack(anchor="w", pady=(15, 0))


# ============= VISTA APLICACIONES =============
def show_applications(app):
    """Muestra la pantalla de selección manual de aplicaciones"""
    app.set_active_menu(app.btn_menu_apps)
    app.clear_content()
    app.current_apps = []
    app.current_mode_name = ""

    
    app.show_installation_ui()

    tk.Label(
        app.content_area,
        text="Instalación personalizada",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        app.content_area,
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
            app.content_area,
            text=f"No se pudo cargar catalogo_apps.json: {e}",
            bg="#ffffff",
            fg="red",
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        return

    vars_list = []

    actions_frame = tk.Frame(app.content_area, bg="#ffffff")
    actions_frame.pack(fill="x", pady=(0, 8))

    # Crear área de selección con scroll
    container = tk.Frame(app.content_area, bg="#ffffff")
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
        selected_apps = [app for app, var in vars_list if var.get()]

        if not selected_apps:
            messagebox.showwarning("Selección requerida", "Debe seleccionar al menos una aplicación.")
            return

        app.current_apps = selected_apps
        app.current_mode_name = "Instalación personalizada"
        selection_label.config(text=f"Aplicaciones seleccionadas: {len(app.current_apps)}")
        app.set_status(f"{len(app.current_apps)} aplicaciones cargadas para instalación")

    # Botones de acción
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

    # Crear checkboxes para cada aplicación
    for idx, app_item in enumerate(apps):
        var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            scrollable_frame,
            text=app_item.get("nombre", "Aplicación"),
            variable=var,
            bg="#ffffff",
            fg="#111827",
            font=("Segoe UI", 10),
            activebackground="#ffffff",
            command=refresh_selection_label
        )
        chk.grid(row=idx // 2, column=idx % 2, sticky="w", padx=12, pady=6)
        vars_list.append((app_item, var))

    selection_label = tk.Label(
        app.content_area,
        text="Aplicaciones seleccionadas: 0",
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold")
    )
    selection_label.pack(anchor="w", pady=(10, 0))


# ============= VISTA EQUIPO =============
def show_equipo(app):
    """Muestra la información del equipo"""
    app.set_active_menu(app.btn_menu_equipo)
    app.clear_content()

    app.hide_installation_ui() 
    

    tk.Label(
        app.content_area,
        text="Información del equipo",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        app.content_area,
        text="Resumen técnico del equipo actual para validación previa al despliegue.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    info = get_system_info()

    table_container = tk.Frame(app.content_area, bg="#ffffff")
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

    # Crear tabla de información
    create_info_table(scrollable_frame, info)

    buttons_frame = tk.Frame(app.content_area, bg="#ffffff")
    buttons_frame.pack(fill="x", pady=(15, 5))

    def refresh_info():
        show_equipo(app)
        app.set_status("Información del equipo actualizada")

    def on_open_drivers():
        try:
            msg = open_driver_support_page()
            messagebox.showinfo("Drivers", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))


    def on_update_drivers():
        try:
            ok, msg = update_drivers()
            if ok:
                messagebox.showinfo("Drivers", msg)
            else:
                messagebox.showwarning("Drivers", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(
        app.content_area,
        text="Actualizar información",
        bg="#0d6efd",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=refresh_info
    ).pack(anchor="w", pady=(10, 0))

    spacer = tk.Frame(buttons_frame, bg="#ffffff", width=20)
    spacer.pack(side="left")

    separator_label = tk.Label(
    buttons_frame,
    text="┃",
    bg="#ffffff",
    fg="#dee2e6",
    font=("Segoe UI", 14)
    )
    separator_label.pack(side="left", padx=5)

    app.set_status("Vista de información del equipo")

    tk.Button(
        buttons_frame,
        text="Buscar drivers (Web)",
        bg="#198754",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=on_open_drivers
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        buttons_frame,
        text="Actualizar drivers",
        bg="#dc3545",
        fg="white",
        relief="flat",
        cursor="hand2",
        font=("Segoe UI", 10, "bold"),
        command=on_update_drivers
    ).pack(side="left")

    info_label = tk.Label(
        app.content_area,
        text="Nota: La actualización automática solo está disponible para equipos Dell con Dell Command Update instalado.",
        bg="#ffffff",
        fg="#6c757d",
        font=("Segoe UI", 9, "italic"),
        justify="left",
        wraplength=700
    )
    info_label.pack(anchor="w", pady=(8, 0))

    app.set_status("Vista de información del equipo")



# ============= VISTA BITÁCORA =============
def show_bitacora(app):
    """Muestra la bitácora de ejecuciones"""
    app.set_active_menu(app.btn_menu_bitacora)
    app.clear_content()

    app.show_installation_ui()

    tk.Label(
        app.content_area,
        text="Bitácora",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", pady=(5, 10))

    tk.Label(
        app.content_area,
        text="En esta sección se muestra el contenido de la última bitácora disponible.",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(0, 12))

    info_var = tk.StringVar()
    info_label = tk.Label(
        app.content_area,
        textvariable=info_var,
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10, "bold"),
        justify="left",
        wraplength=760
    )
    info_label.pack(anchor="w", pady=(0, 10))

    log_box_frame = tk.Frame(app.content_area, bg="#ffffff")
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

        # Determinar qué log mostrar
        selected_log = None

        # Primero intentar con el log actual de la sesión
        if logger.log_file_path and os.path.exists(logger.log_file_path):
            selected_log = logger.log_file_path
        else:
            selected_log = logger.get_latest_log_file()

        if not selected_log:
            info_var.set("No se encontraron archivos de bitácora.")
            log_box.insert("1.0", "Todavía no existe ninguna bitácora para mostrar.")
            log_box.config(state="disabled")
            return

        info_var.set(f"Archivo cargado: {selected_log}")
        content = logger.read_log_content(selected_log)
        log_box.insert("1.0", content if content.strip() else "La bitácora está vacía.")
        log_box.config(state="disabled")

    buttons_frame = tk.Frame(app.content_area, bg="#ffffff")
    buttons_frame.pack(fill="x", pady=(12, 0))

    def refresh_log():
        load_log_into_box()
        app.set_status("Bitácora actualizada")

    def open_logs_folder():
        folder = logger.get_logs_folder()
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
    app.set_status("Vista de bitácora")


# ============= VISTA ACERCA DE =============
def show_about(app):
    """Muestra información acerca del proyecto"""
    app.set_active_menu(app.btn_menu_acerca)
    app.clear_content()

    tk.Label(
        app.content_area,
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
        app.content_area,
        text=info,
        bg="#ffffff",
        fg="#374151",
        font=("Segoe UI", 10),
        justify="left",
        wraplength=700
    ).pack(anchor="w")

    app.set_status("Información del sistema")