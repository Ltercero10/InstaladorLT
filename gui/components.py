# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
from core.config import load_config

def create_menu_button(parent, text, command):
    """Crea un botón de menú con estilo consistente"""
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


def create_profile_card(parent, title, description, color, callback):
    """Crea una tarjeta de perfil"""
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
        command=callback
    ).pack(anchor="w", padx=15, pady=(0, 15))

    return card


def create_info_table(parent, data):
    """Crea una tabla de información clave-valor"""
    for i, (key, value) in enumerate(data.items()):
        key_label = tk.Label(
            parent,
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
            parent,
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

class InstallProgressDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Progreso de instalación")
        self.geometry("580x360")
        self.minsize(580, 360)
        self.maxsize(580, 360)
        self.resizable(False, False)
        self.transient(parent)
        self.configure(bg="#eef2f7")
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.status_var = tk.StringVar(value="Preparando instalación...")
        self.current_app_var = tk.StringVar(value="Esperando...")
        self.progress_var = tk.IntVar(value=0)

        self._center_window(parent)
        self._build_ui()

    def _center_window(self, parent):
        self.update_idletasks()
        width = 580
        height = 360

        if parent and parent.winfo_exists():
            parent.update_idletasks()
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()

            x = parent_x + (parent_w // 2) - (width // 2)
            y = parent_y + (parent_h // 2) - (height // 2)
        else:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = (screen_w // 2) - (width // 2)
            y = (screen_h // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        outer = tk.Frame(self, bg="#eef2f7")
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        card = tk.Frame(
            outer,
            bg="white",
            highlightbackground="#d9e2ec",
            highlightthickness=1,
            bd=0
        )
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            text="Instalación en progreso",
            bg="white",
            fg="#1f2937",
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 6))

        tk.Label(
            card,
            textvariable=self.current_app_var,
            bg="white",
            fg="#2563eb",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=20, pady=(0, 4))

        tk.Label(
            card,
            textvariable=self.status_var,
            bg="white",
            fg="#4b5563",
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=20, pady=(0, 12))

        self.progress = ttk.Progressbar(
            card,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_var,
            maximum=100
        )
        self.progress.pack(fill="x", padx=20, pady=(0, 14))

        self.log_box = tk.Text(
            card,
            height=10,
            bg="#f8fafc",
            fg="#111827",
            font=("Consolas", 10),
            relief="solid",
            bd=1,
            wrap="word",
            padx=10,
            pady=10
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        self.log_box.config(state="disabled")

        self.log_box.tag_configure("success", foreground="#15803d")
        self.log_box.tag_configure("error", foreground="#b91c1c")
        self.log_box.tag_configure("info", foreground="#2563eb")
        self.log_box.tag_configure("normal", foreground="#111827")

    def set_current_app(self, text):
        self.current_app_var.set(text)
        self.update_idletasks()

    def set_status(self, text):
        self.status_var.set(text)
        self.update_idletasks()

    def start_activity(self):
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.update_idletasks()

    def stop_activity(self):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.update_idletasks()

    def set_progress(self, value, total=None):
        self.progress.configure(mode="determinate")
        if total and total > 0:
            percent = int((value / total) * 100)
        else:
            percent = int(value)
        self.progress_var.set(percent)
        self.update_idletasks()

    def append_log(self, message, level="normal"):
        self.log_box.config(state="normal")
        self.log_box.insert("end", message + "\n", level)
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.update_idletasks()


class AppFormDialog(tk.Toplevel):
    def __init__(self, parent, on_save, app_data=None, title="Aplicación"):
        super().__init__(parent)
        self.title(title)
        self.geometry("760x690")
        self.minsize(760, 690)
        self.maxsize(760, 690)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#eef2f7")

        self.on_save = on_save
        self.app_data = app_data or {}
        self.default_base = "soporte"


        config = load_config() or {}
        rutas_base = config.get("rutas_base", {})
        self.network_root = rutas_base.get(self.default_base, r"\\10.0.5.157\Soporte")

        self.nombre_var = tk.StringVar(value=self.app_data.get("nombre", ""))
        self.tipo_var = tk.StringVar(value=self.app_data.get("tipo", ""))
        self.base_var = tk.StringVar(value=self.app_data.get("base", self.default_base))
        self.categoria_var = tk.StringVar(value=self.app_data.get("categoria", "basica"))
        self.ruta_var = tk.StringVar(value=self.app_data.get("ruta", ""))
        self.args_var = tk.StringVar(value=self.app_data.get("args", ""))
        self.copiar_temp_var = tk.BooleanVar(value=self.app_data.get("copiar_a_temp", True))
        self.modo_argumentos_var = tk.StringVar(value="automatico")
        self.tipo_origen_var = tk.StringVar(value="archivo")
        self.show_advanced_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Seleccione un archivo o carpeta para comenzar.")

        self._build_ui()
        self._sync_detected_type()
        self._toggle_advanced()

    def _build_ui(self):
        outer = tk.Frame(self, bg="#eef2f7")
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        card = tk.Frame(
            outer,
            bg="white",
            highlightbackground="#d9e2ec",
            highlightthickness=1,
            bd=0
        )
        card.pack(fill="both", expand=True)

        header = tk.Frame(card, bg="white")
        header.pack(fill="x", padx=24, pady=(20, 10))

        tk.Label(
            header,
            text=self.title(),
            font=("Segoe UI", 16, "bold"),
            bg="white",
            fg="#1f2937"
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Complete la información de la aplicación. El sistema detectará automáticamente el tipo según el archivo seleccionado.",
            font=("Segoe UI", 10),
            bg="white",
            fg="#6b7280",
            wraplength=680,
            justify="left"
        ).pack(anchor="w", pady=(6, 0))

        body = tk.Frame(card, bg="white")
        body.pack(fill="both", expand=True, padx=24, pady=(4, 0), anchor="n")

        self._label(body, "Nombre", 0)
        ttk.Entry(body, textvariable=self.nombre_var).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self._label(body, "Categoría", 2)
        ttk.Combobox(
            body,
            textvariable=self.categoria_var,
            values=["basica", "corporativa"],
            state="readonly",
            width=20
        ).grid(row=3, column=0, sticky="w", pady=(0, 12))

        self._label(body, "Tipo detectado", 2, column=1)
        ttk.Entry(body, textvariable=self.tipo_var, state="readonly", width=30).grid(
            row=3, column=1, sticky="w", pady=(0, 12), padx=(10, 0)
        )

        self._label(body, "Base", 2, column=2)
        ttk.Entry(body, textvariable=self.base_var, state="readonly", width=20).grid(
            row=3, column=2, sticky="w", pady=(0, 12), padx=(10, 0)
        )

        self._label(body, "Origen", 4)
        origen_frame = tk.Frame(body, bg="white")
        origen_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Radiobutton(
            origen_frame,
            text="Archivo instalador",
            variable=self.tipo_origen_var,
            value="archivo"
        ).pack(side="left", padx=(0, 14))

        ttk.Radiobutton(
            origen_frame,
            text="Carpeta",
            variable=self.tipo_origen_var,
            value="carpeta"
        ).pack(side="left")

        self._label(body, "Ruta seleccionada", 6)
        ruta_frame = tk.Frame(body, bg="white")
        ruta_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ruta_frame.grid_columnconfigure(0, weight=1)

        self.ruta_entry = ttk.Entry(ruta_frame, textvariable=self.ruta_var)
        self.ruta_entry.grid(row=0, column=0, sticky="ew")

        ttk.Button(
            ruta_frame,
            text="Buscar",
            command=self._browse_source
        ).grid(row=0, column=1, padx=(10, 0))

        tk.Label(
            body,
            text="Seleccione el archivo o carpeta desde la compartida corporativa. Si la ruta pertenece a la base de instaladores, se guardará como relativa.",
            font=("Segoe UI", 9),
            bg="white",
            fg="#6b7280",
            wraplength=680,
            justify="left"
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Checkbutton(
            body,
            text="Copiar el instalador al equipo antes de ejecutar (recomendado)",
            variable=self.copiar_temp_var
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(0, 12))

        self._label(body, "Modo de instalación", 10)
        modo_frame = tk.Frame(body, bg="white")
        modo_frame.grid(row=11, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Radiobutton(
            modo_frame,
            text="Automática recomendada",
            variable=self.modo_argumentos_var,
            value="automatico",
            command=self._apply_recommended_args
        ).pack(side="left", padx=(0, 14))

        ttk.Radiobutton(
            modo_frame,
            text="Personalizada avanzada",
            variable=self.modo_argumentos_var,
            value="manual"
        ).pack(side="left")

        ttk.Checkbutton(
            body,
            text="Mostrar opciones avanzadas",
            variable=self.show_advanced_var,
            command=self._toggle_advanced
        ).grid(row=12, column=0, columnspan=3, sticky="w", pady=(4, 8))

        self.advanced_frame = tk.Frame(body, bg="#f8fafc", highlightbackground="#e5e7eb", highlightthickness=1)
        self.advanced_frame.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.advanced_frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            self.advanced_frame,
            text="Argumentos avanzados",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#1f2937"
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        ttk.Entry(self.advanced_frame, textvariable=self.args_var).grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 10)
        )

        tk.Label(
            self.advanced_frame,
            text="Use esta opción solo si necesita sobrescribir los argumentos sugeridos automáticamente.",
            font=("Segoe UI", 9),
            bg="#f8fafc",
            fg="#6b7280",
            wraplength=650,
            justify="left"
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))

        tk.Label(
            body,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="white",
            fg="#2563eb",
            wraplength=680,
            justify="left"
        ).grid(row=14, column=0, columnspan=3, sticky="w", pady=(6, 0))

        footer = tk.Frame(card, bg="white")
        footer.pack(fill="x", side="bottom", padx=24, pady=(8, 20))
        footer.grid_columnconfigure(0, weight=1)

        ttk.Button(footer, text="Cancelar", command=self.destroy).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(footer, text="Guardar", command=self._save).grid(row=0, column=2)

    def _label(self, parent, text, row, column=0):
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#374151"
        ).grid(row=row, column=column, sticky="w", pady=(0, 6))

    def _toggle_advanced(self):
        if self.show_advanced_var.get():
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

    def _browse_source(self):
        from tkinter import filedialog
        import os

        try:
            initial_dir = self.network_root if os.path.exists(self.network_root) else os.getcwd()
        except Exception:
            initial_dir = os.getcwd()

        if self.tipo_origen_var.get() == "carpeta":
            selected = filedialog.askdirectory(
                parent=self,
                title="Seleccionar carpeta",
                initialdir=initial_dir
            )
        else:
            selected = filedialog.askopenfilename(
                parent=self,
                title="Seleccionar instalador",
                initialdir=initial_dir,
                filetypes=[
                    ("Instaladores", "*.exe *.msi"),
                    ("Ejecutables", "*.exe"),
                    ("Paquetes MSI", "*.msi"),
                    ("Todos los archivos", "*.*"),
                ]
            )

        if not selected:
            return

        relative_path = self._to_relative_instaladores(selected)
        self.ruta_var.set(relative_path)
        self._sync_detected_type(selected)
        self._apply_recommended_args()

    def _to_relative_instaladores(self, selected_path):
        import os

        normalized_selected = os.path.normpath(selected_path)
        normalized_root = os.path.normpath(self.network_root)

        try:
            common = os.path.commonpath([normalized_selected, normalized_root])
            if common.lower() == normalized_root.lower():
                rel = os.path.relpath(normalized_selected, normalized_root)
                rel = rel.replace("\\", "/")
                return rel
        except Exception:
            pass

        return selected_path.replace("\\", "/")

    def _sync_detected_type(self, selected_path=None):
        ruta = selected_path or self.ruta_var.get().strip()
        ruta_lower = ruta.lower()

        if self.tipo_origen_var.get() == "carpeta":
            detected = "copy_folder"
            self.copiar_temp_var.set(False)
        elif ruta_lower.endswith(".msi"):
            detected = "msi"
            self.copiar_temp_var.set(True)
        elif ruta_lower.endswith(".exe"):
            detected = "exe"
            self.copiar_temp_var.set(True)
        else:
            detected = self.app_data.get("tipo", "exe") if self.app_data else "exe"

        self.tipo_var.set(detected)
        self.status_var.set(f"Tipo detectado automáticamente: {detected}")

    def _apply_recommended_args(self):
        tipo = self.tipo_var.get().strip().lower()

        if self.modo_argumentos_var.get() != "automatico":
            return

        if tipo == "msi":
            self.args_var.set("")
        elif tipo == "exe":
            existing = self.app_data.get("args", "").strip() if self.app_data else ""
            self.args_var.set(existing)
        else:
            self.args_var.set("")

    def _save(self):
        nombre = self.nombre_var.get().strip()
        ruta = self.ruta_var.get().strip()
        tipo = self.tipo_var.get().strip()
        categoria = self.categoria_var.get().strip()

        if not nombre:
            messagebox.showwarning("Validación", "El nombre es obligatorio.", parent=self)
            return

        if not ruta:
            messagebox.showwarning("Validación", "Debe seleccionar una ruta.", parent=self)
            return

        if tipo not in ["exe", "msi", "copy_folder", "carpeta"]:
            messagebox.showwarning("Validación", "No se pudo detectar el tipo de aplicación.", parent=self)
            return

        args = self.args_var.get().strip()
        copiar_temp = self.copiar_temp_var.get()

        if tipo in ["copy_folder", "carpeta"]:
            copiar_temp = False
            args = ""

        app_data = {
            "nombre": nombre,
            "tipo": tipo,
            "base": self.base_var.get().strip() or self.default_base,
            "categoria": categoria,
            "ruta": ruta,
            "args": args,
            "copiar_a_temp": copiar_temp
        }

        self.on_save(app_data)
        self.destroy()

    