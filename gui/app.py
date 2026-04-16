import tkinter as tk
from tkinter import ttk, messagebox
import threading
from gui.components import create_menu_button, InstallProgressDialog
from core.catalog_manager import CatalogManager
from core.logger import Logger, global_logger
from core.installer import Installer
from gui.components import create_menu_button, InstallProgressDialog
from gui.views import (
    show_home,
    show_profiles,
    show_applications,
    show_equipo,
    show_domain,
    show_bitacora,
    show_about
)
from gui.components import create_menu_button
from gui.styles import configure_styles
from core.config import resource_path


class AutoInstallerApp:
    "Clase principal de la aplicación"

    def __init__(self):
        self.root = tk.Tk()
        self.progress_dialog = None

        try:
            self.root.iconbitmap(resource_path("assets/favicon.ico"))
        except Exception as e:
            print(f"No se pudo cargar el icono: {e}")

        self.root.title("AutoInstaller Farinter Corporativo")
        self.root.geometry("1220x760")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#eef2f7")

        # Variables de estado
        self.current_apps = []
        self.current_mode_name = ""
        self.status_var = tk.StringVar(value="Esperando selección")
        self.progress_var = tk.IntVar()

        # Catálogo de aplicaciones
        self.catalog = CatalogManager(resource_path("data/catalogo_apps.json"))
        self.app_vars = {}
        self.apps_data = []
        self.apps_checks_frame = None
        self.selected_count_label = None

        # Configurar logger
        global_logger.set_console(None)

        # Configurar estilos
        configure_styles()

        # Crear UI
        self._setup_ui()

        # Configurar callbacks para el instalador
        installer_callbacks = {

            'set_status': self.set_status,
            'update_progress': self.update_progress,
            'enable_run_button': self.enable_run_button,
            'show_summary': self.show_summary,
            'progress_set_app': self.progress_set_app,
            'progress_set_status': self.progress_set_status,
            'progress_append_log': self.progress_append_log,
            'progress_set_value': self.progress_set_value,
            'progress_start_activity': self.progress_start_activity,
            'progress_stop_activity': self.progress_stop_activity,
        }
        
        self.installer = Installer(installer_callbacks)

        # Mostrar vista inicial
        self.show_home()
    
    def show_progress_dialog(self):
        if self.progress_dialog is None or not self.progress_dialog.winfo_exists():
            self.progress_dialog = InstallProgressDialog(self.root)
            self.progress_dialog.grab_set()

    def close_progress_dialog(self):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.progress_dialog.destroy()
            self.progress_dialog = None

    def progress_set_app(self, text):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_current_app(text))

    def progress_set_status(self, text):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_status(text))

    def progress_append_log(self, message, level="normal"):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.append_log(message, level))

    def progress_set_value(self, value, total=None):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_progress(value, total))

    def progress_start_activity(self):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, self.progress_dialog.start_activity)

    def progress_stop_activity(self):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, self.progress_dialog.stop_activity)

    def render_apps(self):
        """Reconstruye la lista de aplicaciones en checkboxes."""
        if self.apps_checks_frame is None:
            return

        for widget in self.apps_checks_frame.winfo_children():
            widget.destroy()

        self.apps_data = self.catalog.get_apps()
        self.app_vars = {}

        for index, app in enumerate(self.apps_data):
            nombre = app.get("nombre", f"Aplicación {index + 1}")
            var = tk.BooleanVar(value=False)
            self.app_vars[nombre] = {"var": var, "app": app}

            row = index // 2
            col = index % 2

            chk = tk.Checkbutton(
                self.apps_checks_frame,
                text=nombre,
                variable=var,
                bg="#ffffff",
                fg="#111827",
                font=("Segoe UI", 10),
                activebackground="#ffffff",
                command=self.update_selected_count
            )
            chk.grid(row=row, column=col, sticky="w", padx=12, pady=6)

    def update_selected_count(self):
        total = 0

        for app_name, item in self.app_vars.items():
            selected = item["var"].get()
            app_data = item["app"]

            if selected:
                if app_data.get("requiere_pais"):
                    paises = getattr(self, "app_country_vars", {}).get(app_name, {})
                    if any(var.get() for var in paises.values()):
                        total += 1
                else:
                    total += 1

        if self.selected_count_label is not None:
            self.selected_count_label.config(text=f"Aplicaciones seleccionadas: {total}")

        self.refresh_run_button_state(selected_total=total)

    def open_add_app_dialog(self):
        from gui.components import AppFormDialog

        AppFormDialog(
            self.root,
            on_save=self.save_new_app,
            title="Agregar aplicación"
        )

    def save_new_app(self, app_data):
        self.catalog.add_app(app_data)
        self.render_apps()
        self.update_selected_count()
        messagebox.showinfo("Éxito", "Aplicación agregada correctamente.")

    def open_select_app_to_edit(self):
        apps = self.catalog.get_apps()

        if not apps:
            messagebox.showwarning("Aviso", "No hay aplicaciones para editar.")
            return

        selector = tk.Toplevel(self.root)
        selector.title("Seleccionar aplicación")
        selector.geometry("380x160")
        selector.resizable(False, False)
        selector.transient(self.root)
        selector.grab_set()

        ttk.Label(
            selector,
            text="Seleccione la aplicación que desea editar:"
        ).pack(anchor="w", padx=15, pady=(15, 8))

        app_names = [app.get("nombre", "Sin nombre") for app in apps]
        selected_name = tk.StringVar(value=app_names[0])

        combo = ttk.Combobox(
            selector,
            textvariable=selected_name,
            values=app_names,
            state="readonly",
            width=40
        )
        combo.pack(padx=15, pady=5)

        def continue_edit():
            selector.destroy()
            selected_app = next((app for app in apps if app.get("nombre") == selected_name.get()), None)
            if selected_app:
                self.open_edit_app_dialog(selected_app)

        ttk.Button(selector, text="Continuar", command=continue_edit).pack(pady=15)

    def open_edit_app_dialog(self, app_data):
        from gui.components import AppFormDialog

        AppFormDialog(
            self.root,
            on_save=lambda updated_app: self.save_edited_app(app_data["nombre"], updated_app),
            app_data=app_data,
            title="Editar aplicación"
        )

    def save_edited_app(self, original_name, updated_app):
        updated = self.catalog.update_app_by_name(original_name, updated_app)

        if not updated:
            messagebox.showerror("Error", "No se pudo actualizar la aplicación.")
            return

        self.render_apps()
        self.update_selected_count()
        messagebox.showinfo("Éxito", "Aplicación editada correctamente.")

    def open_select_app_to_delete(self):
        apps = self.catalog.get_apps()

        if not apps:
            messagebox.showwarning("Aviso", "No hay aplicaciones para eliminar.")
            return

        selector = tk.Toplevel(self.root)
        selector.title("Eliminar aplicación")
        selector.geometry("380x170")
        selector.resizable(False, False)
        selector.transient(self.root)
        selector.grab_set()

        ttk.Label(
            selector,
            text="Seleccione la aplicación que desea eliminar:"
        ).pack(anchor="w", padx=15, pady=(15, 8))

        app_names = [app.get("nombre", "Sin nombre") for app in apps]
        selected_name = tk.StringVar(value=app_names[0])

        combo = ttk.Combobox(
            selector,
            textvariable=selected_name,
            values=app_names,
            state="readonly",
            width=40
        )
        combo.pack(padx=15, pady=5)

        def confirm_delete():
            name = selected_name.get()
            ok = messagebox.askyesno(
                "Confirmar eliminación",
                f"¿Desea eliminar la aplicación '{name}'?"
            )
            if not ok:
                return

            deleted = self.catalog.delete_app_by_name(name)
            selector.destroy()

            if deleted:
                self.show_applications()
                messagebox.showinfo("Éxito", "Aplicación eliminada correctamente.")
            else:
                messagebox.showerror("Error", "No se pudo eliminar la aplicación.")

        ttk.Button(selector, text="Eliminar", command=confirm_delete).pack(pady=15)

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.root, bg="#eef2f7")
        main_frame.pack(fill="both", expand=True)

        self._setup_sidebar(main_frame)
        self._setup_right_panel(main_frame)

    def _setup_sidebar(self, parent):
        """Configura la barra lateral"""
        self.sidebar = tk.Frame(parent, bg="#1f2937", width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="Grupo Farinter",
            bg="#1f2937",
            fg="white",
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        tk.Label(
            self.sidebar,
            text="Panel de navegación",
            bg="#1f2937",
            fg="#cbd5e1",
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=20, pady=(0, 20))

        self.btn_menu_inicio = create_menu_button(self.sidebar, "Inicio", self.show_home)
        self.btn_menu_inicio.pack(fill="x")

        self.btn_menu_perfiles = create_menu_button(self.sidebar, "Perfiles", self.show_profiles)
        self.btn_menu_perfiles.pack(fill="x")

        self.btn_menu_apps = create_menu_button(self.sidebar, "Aplicaciones", self.show_applications)
        self.btn_menu_apps.pack(fill="x")

        self.btn_menu_equipo = create_menu_button(self.sidebar, "Equipo", self.show_equipo)

        self.btn_menu_dominio = create_menu_button(self.sidebar, "Dominio", self.show_domain)
        self.btn_menu_dominio.pack(fill="x")

        self.btn_menu_equipo.pack(fill="x")

        self.btn_menu_bitacora = create_menu_button(self.sidebar, "Bitácora", self.show_bitacora)
        self.btn_menu_bitacora.pack(fill="x")

        self.btn_menu_acerca = create_menu_button(self.sidebar, "Acerca de", self.show_about)
        self.btn_menu_acerca.pack(fill="x")

        self.menu_buttons = [
            self.btn_menu_inicio, self.btn_menu_perfiles,
            self.btn_menu_apps, self.btn_menu_equipo,
            self.btn_menu_dominio,
            self.btn_menu_bitacora, self.btn_menu_acerca
        ]

    def _setup_right_panel(self, parent):
        """Configura el panel derecho"""
        self.right_panel = tk.Frame(parent, bg="#eef2f7")
        self.right_panel.pack(side="left", fill="both", expand=True)

        header = tk.Frame(self.right_panel, bg="#eef2f7")
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

        body = tk.Frame(self.right_panel, bg="#eef2f7")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.content_card = tk.Frame(body, bg="#ffffff", bd=1, relief="solid")
        self.content_card.pack(fill="both", expand=True)

        self.content_area = tk.Frame(self.content_card, bg="#ffffff")
        self.content_area.pack(fill="x", padx=20, pady=(18, 10))

        self.action_area = tk.Frame(self.content_card, bg="#ffffff")
        self.action_area.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_run = tk.Button(
            self.action_area,
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
            state="disabled",
            command=self.start_installation
        )
        self.btn_run.pack(side="left")

        self.status_label = tk.Label(
            self.action_area,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#374151",
            font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(side="left", padx=15)

        self.progress_bar = ttk.Progressbar(
            self.content_card,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 12))

        self.console_frame_container = tk.Frame(self.content_card, bg="#ffffff")
        self.console_frame_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        console_label = tk.Label(
            self.console_frame_container,
            text="Consola de ejecución",
            bg="#ffffff",
            fg="#111827",
            font=("Segoe UI", 11, "bold")
        )
        console_label.pack(anchor="w", pady=(0, 6))

        console_frame = tk.Frame(self.console_frame_container, bg="#ffffff")
        console_frame.pack(fill="both", expand=True)

        self.console = tk.Text(
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
        self.console.pack(side="left", fill="both", expand=True)

        console_scroll = ttk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        console_scroll.pack(side="right", fill="y")
        self.console.configure(yscrollcommand=console_scroll.set)

        global_logger.set_console(self.console)

    def hide_installation_ui(self):
        self.action_area.pack_forget()
        self.progress_bar.pack_forget()
        self.console_frame_container.pack_forget()

    def show_installation_ui(self):
        self.action_area.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 12))
        self.console_frame_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def set_active_menu(self, active_button):
        for btn in self.menu_buttons:
            btn.configure(bg="#1f2937", fg="white")
        active_button.configure(bg="#374151", fg="white")

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def set_status(self, text: str):
        self.status_var.set(text)
        self.root.update_idletasks()

    def update_progress(self, value: int):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def enable_run_button(self, enabled: bool = True):
        state = "normal" if enabled else "disabled"
        self.btn_run.config(state=state)

    def show_summary(self, summary_text: str):
        self.close_progress_dialog()
        messagebox.showinfo("Resumen final", summary_text)
    
    def show_progress_dialog(self):
        if self.progress_dialog is None or not self.progress_dialog.winfo_exists():
            self.progress_dialog = InstallProgressDialog(self.root)

    def close_progress_dialog(self):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.progress_dialog.destroy()
            self.progress_dialog = None

    def progress_set_app(self, text):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_current_app(text))

    def progress_set_status(self, text):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_status(text))

    def progress_append_log(self, message, level="normal"):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.append_log(message, level))

    def progress_set_value(self, value, total=None):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.root.after(0, lambda: self.progress_dialog.set_progress(value, total))

    def start_installation(self):
        if not self.current_apps:
            messagebox.showwarning("Selección requerida", "Debe seleccionar un perfil o aplicaciones.")
            return

        self.show_progress_dialog()

        threading.Thread(
            target=self.installer.execute_apps,
            args=(self.current_mode_name, self.current_apps),
            daemon=True
        ).start()

    def save_new_app(self, app_data):
        self.catalog.add_app(app_data)
        self.show_applications()
        messagebox.showinfo("Éxito", "Aplicación agregada correctamente.")


    def save_new_app(self, app_data):
        self.catalog.add_app(app_data)
        self.show_applications()
        messagebox.showinfo("Éxito", "Aplicación agregada correctamente.")

    def refresh_run_button_state(self, selected_total=0):
            """
            Habilita o deshabilita el botón Ejecutar según:
            - apps cargadas por perfil
            - o selección manual válida
            """
            has_profile_apps = bool(self.current_apps)
            has_manual_selection = selected_total > 0

            if has_profile_apps or has_manual_selection:
                self.btn_run.config(state="normal", bg="#2563eb", cursor="hand2")
            else:
                self.btn_run.config(state="disabled", bg="#9ca3af", cursor="arrow")

    def show_home(self):
        show_home(self)

    def show_profiles(self):
        show_profiles(self)

    def show_applications(self):
        show_applications(self)

    def show_equipo(self):
        show_equipo(self)

    def show_domain(self):
        show_domain(self)

    def show_bitacora(self):
        show_bitacora(self)

    def show_about(self):
        show_about(self)

    def run(self):
        self.root.mainloop()