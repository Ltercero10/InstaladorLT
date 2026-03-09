import tkinter as tk
from tkinter import ttk, messagebox
import threading

from core.logger import Logger, global_logger
from core.installer import Installer
from gui.views import (
    show_home,
    show_profiles,
    show_applications,
    show_equipo,
    show_bitacora,
    show_about
)
from gui.components import create_menu_button
from gui.styles import configure_styles

from core.network_auth import ensure_network_access


class AutoInstallerApp:
    """Clase principal de la aplicación"""

    def __init__(self):
        self.root = tk.Tk()

        share_path = r"\\10.0.5.157\Soporte"

        if not ensure_network_access(self.root, share_path):
            messagebox.showwarning(
                "Acceso requerido",
                "No se pudo acceder a la carpeta compartida."
            )
            self.root.destroy()
            self.root = None
            return

        self.root.title("AutoInstaller Farinter Corporativo")
        self.root.geometry("1220x760")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#eef2f7")




        
        # Variables de estado
        self.current_apps = []
        self.current_mode_name = ""
        self.status_var = tk.StringVar(value="Esperando selección")
        self.progress_var = tk.IntVar()

        
        # Configurar logger
        global_logger.set_console(None)  # Se asignará después
        
        # Configurar estilos
        configure_styles()
        
        # Crear UI
        self._setup_ui()
        
        # Configurar callbacks para el instalador
        installer_callbacks = {
            'set_status': self.set_status,
            'update_progress': self.update_progress,
            'enable_run_button': self.enable_run_button,
            'show_summary': self.show_summary
        }
        self.installer = Installer(installer_callbacks)
        
        # Mostrar vista inicial
        self.show_home()
    
    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        main_frame = tk.Frame(self.root, bg="#eef2f7")
        main_frame.pack(fill="both", expand=True)

        # SIDEBAR
        self._setup_sidebar(main_frame)

        # RIGHT PANEL
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

        # Botones del menú
        self.btn_menu_inicio = create_menu_button(
            self.sidebar, "Inicio", self.show_home
        )
        self.btn_menu_inicio.pack(fill="x")

        self.btn_menu_perfiles = create_menu_button(
            self.sidebar, "Perfiles", self.show_profiles
        )
        self.btn_menu_perfiles.pack(fill="x")

        self.btn_menu_apps = create_menu_button(
            self.sidebar, "Aplicaciones", self.show_applications
        )
        self.btn_menu_apps.pack(fill="x")

        self.btn_menu_equipo = create_menu_button(
            self.sidebar, "Equipo", self.show_equipo
        )
        self.btn_menu_equipo.pack(fill="x")

        self.btn_menu_bitacora = create_menu_button(
            self.sidebar, "Bitácora", self.show_bitacora
        )
        self.btn_menu_bitacora.pack(fill="x")

        self.btn_menu_acerca = create_menu_button(
            self.sidebar, "Acerca de", self.show_about
        )
        self.btn_menu_acerca.pack(fill="x")

        # Lista de botones para gestionar estado activo
        self.menu_buttons = [
            self.btn_menu_inicio, self.btn_menu_perfiles, 
            self.btn_menu_apps, self.btn_menu_equipo,
            self.btn_menu_bitacora, self.btn_menu_acerca
        ]
    
    def _setup_right_panel(self, parent):
        """Configura el panel derecho"""
        self.right_panel = tk.Frame(parent, bg="#eef2f7")
        self.right_panel.pack(side="left", fill="both", expand=True)

        # Header
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

        # Body
        body = tk.Frame(self.right_panel, bg="#eef2f7")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Content card
        self.content_card = tk.Frame(body, bg="#ffffff", bd=1, relief="solid")
        self.content_card.pack(fill="both", expand=True)

        self.content_area = tk.Frame(self.content_card, bg="#ffffff")
        self.content_area.pack(fill="x", padx=20, pady=(18, 10))

        # Action area (guardamos referencia para poder ocultarla)
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

        # Progress bar (guardamos referencia)
        self.progress_bar = ttk.Progressbar(
            self.content_card,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 12))

        # Console area (guardamos referencia del contenedor completo)
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

        # Asignar console al logger
        global_logger.set_console(self.console)
    
    # ===== NUEVOS MÉTODOS PARA OCULTAR/MOSTRAR UI DE INSTALACIÓN =====
    def hide_installation_ui(self):
        """Oculta los elementos de instalación (para la pantalla de equipo)"""
        self.action_area.pack_forget()
        self.progress_bar.pack_forget()
        self.console_frame_container.pack_forget()

    def show_installation_ui(self):
        """Muestra los elementos de instalación (para las demás pantallas)"""
        self.action_area.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 12))
        self.console_frame_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    # ===== FIN DE NUEVOS MÉTODOS =====
    
    def set_active_menu(self, active_button):
        """Marca un botón del menú como activo"""
        for btn in self.menu_buttons:
            btn.configure(bg="#1f2937", fg="white")
        active_button.configure(bg="#374151", fg="white")
    
    def clear_content(self):
        """Limpia el área de contenido"""
        for widget in self.content_area.winfo_children():
            widget.destroy()
    
    def set_status(self, text: str):
        """Actualiza la barra de estado"""
        self.status_var.set(text)
        self.root.update_idletasks()
    
    def update_progress(self, value: int):
        """Actualiza la barra de progreso"""
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def enable_run_button(self, enabled: bool = True):
        """Habilita/deshabilita el botón de ejecución"""
        state = "normal" if enabled else "disabled"
        self.btn_run.config(state=state)
    
    def show_summary(self, summary_text: str):
        """Muestra el resumen final"""
        messagebox.showinfo("Resumen final", summary_text)
    
    def start_installation(self):
        """Inicia el proceso de instalación en un hilo separado"""
        if not self.current_apps:
            messagebox.showwarning("Selección requerida", "Debe seleccionar un perfil o aplicaciones.")
            return

        threading.Thread(
            target=self.installer.execute_apps,
            args=(self.current_mode_name, self.current_apps),
            daemon=True
        ).start()
    def ensure_network_access(root, share_path):
        if verify_share_access(share_path):
            return True

        dialog = NetworkLoginDialog(root, default_share=share_path)
        root.wait_window(dialog)

        if not dialog.result:
            return False

        share = dialog.result["share"]
        domain = dialog.result["domain"]
        username = dialog.result["username"]
        password = dialog.result["password"]

        disconnect_share(share)

        ok, msg = connect_to_share(share, username, password, domain)
        if not ok:
            messagebox.showerror("Error de autenticación", msg)
            return False

        if not verify_share_access(share):
            messagebox.showerror("Error", "Se autenticó, pero no se pudo acceder a la carpeta compartida.")
            return False

        return True
    # Métodos para mostrar vistas (delegan a las funciones en views.py)
    def show_home(self):
        show_home(self)
    
    def show_profiles(self):
        show_profiles(self)
    
    def show_applications(self):
        show_applications(self)
    
    def show_equipo(self):
        show_equipo(self)
    
    def show_bitacora(self):
        show_bitacora(self)
    
    def show_about(self):
        show_about(self)
    
    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()