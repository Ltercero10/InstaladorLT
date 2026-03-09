# -*- coding: utf-8 -*-

import os
from datetime import datetime
import tkinter as tk

class Logger:
    """Sistema de logging para la aplicación"""
    
    def __init__(self, console_widget=None):
        self.log_file_path = None
        self.console = console_widget
        self.last_log_content = ""
    
    def set_console(self, console_widget):
        """Establece el widget de consola para mostrar logs"""
        self.console = console_widget
    
    def create_log_file(self, mode_name: str) -> str:
        """Crea un nuevo archivo de log para una ejecución"""
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)

        safe_mode = mode_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(log_dir, f"{safe_mode}_{timestamp}.log")
        return self.log_file_path

    def get_logs_folder(self) -> str:
        """Retorna la carpeta de logs"""
        folder = os.path.join(os.getcwd(), "logs")
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_latest_log_file(self):
        """Obtiene el archivo de log más reciente"""
        folder = self.get_logs_folder()
        log_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".log")
        ]

        if not log_files:
            return None

        return max(log_files, key=os.path.getmtime)

    def read_log_content(self, path: str) -> str:
        """Lee el contenido de un archivo de log"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"No se pudo leer la bitácora.\n\nDetalle: {e}"

    def log(self, msg: str):
        """Registra un mensaje en consola y archivo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        
        # Mostrar en consola si existe
        if self.console:
            self.console.insert(tk.END, line + "\n")
            self.console.see(tk.END)
        
        # Escribir en archivo
        self._write_to_file(line)
        self.last_log_content += line + "\n"

    def _write_to_file(self, line: str):
        """Escribe una línea en el archivo de log"""
        if not self.log_file_path:
            return

        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def clear(self):
        """Limpia la consola"""
        if self.console:
            self.console.delete("1.0", tk.END)
        self.last_log_content = ""

# Instancia global del logger
global_logger = Logger()