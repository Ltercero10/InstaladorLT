# -*- coding: utf-8 -*-

import os
import subprocess
import time
import shutil
import tempfile
import threading
from tkinter import messagebox

from core.config import load_config, resource_path
from core.logger import global_logger as logger
from utils.file_utils import stage_to_temp

class Installer:
    """Clase encargada de la lógica de instalación"""
    
    def __init__(self, gui_callbacks):
        """
        Inicializa el instalador
        
        Args:
            gui_callbacks: Diccionario con funciones de callback para la GUI
                - set_status: Actualizar barra de estado
                - update_progress: Actualizar progreso
                - enable_run_button: Habilitar botón de ejecución
                - show_summary: Mostrar resumen
        """
        self.callbacks = gui_callbacks
    
    def execute_apps(self, mode_name: str, apps: list):
        """Ejecuta la instalación de las aplicaciones"""
        
        start_time = time.time()
        success_count = 0
        failed_count = 0
        skipped_count = 0
        total_apps = len(apps)

        try:
            # Actualizar UI
            self._update_ui_start(total_apps)
            
            config = load_config()
            if not config:
                self._show_error("Error de configuración")
                return

            # Crear archivo de log
            log_file_path = logger.create_log_file(mode_name)
            
            if total_apps == 0:
                logger.log("No hay aplicaciones seleccionadas para instalar.")
                self._finish_installation()
                return

            # Registrar inicio
            self._log_start(mode_name, total_apps, log_file_path)

            rutas_base = config.get("rutas_base", {})

            for index, app in enumerate(apps, start=1):
                success = self._process_app(app, index, total_apps, rutas_base)
                
                if success == "success":
                    success_count += 1
                elif success == "failed":
                    failed_count += 1
                elif success == "skipped":
                    skipped_count += 1
                
                # Actualizar progreso
                self.callbacks['update_progress'](index)

            # Mostrar resumen
            total_time = time.time() - start_time
            self._show_final_summary(
                mode_name, total_apps, success_count, 
                failed_count, skipped_count, total_time, log_file_path
            )

        except Exception as e:
            self._show_error(str(e))
        finally:
            self.callbacks['enable_run_button']()

    def _process_app(self, app, index, total_apps, rutas_base):
        """Procesa una aplicación individual"""
        
        nombre = app.get("nombre", "Desconocido")
        tipo = app.get("tipo", "exe")
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")
        args = app.get("args", "")
        post = app.get("post", "")
        post_cmd = app.get("post_cmd", "")
        copiar_a_temp = app.get("copiar_a_temp", True)

        self.callbacks['set_status'](f"Instalando {index}/{total_apps}: {nombre}")
        logger.log(f"[{index}/{total_apps}] Procesando: {nombre}")

        # Validar base
        if base not in rutas_base:
            logger.log(f"Base no definida en config.json: {base}")
            logger.log("")
            return "skipped"

        # Construir ruta
        ruta = os.path.join(rutas_base[base], ruta_relativa)
        logger.log(f"Ruta de red: {ruta}")

        # Verificar acceso a carpeta
        if not self._check_folder_access(ruta):
            return "skipped"

        # Procesar según tipo
        if tipo == "carpeta":
            return self._install_folder(app, ruta)
        
        return self._install_executable(
            app, ruta, tipo, args, post, post_cmd, copiar_a_temp
        )

    def _check_folder_access(self, ruta):
        """Verifica si se puede acceder a la carpeta"""
        try:
            carpeta_red = os.path.dirname(ruta)
            os.listdir(carpeta_red)
            logger.log("Carpeta accesible")
            return True
        except Exception as e:
            logger.log(f"No se puede acceder a la carpeta: {e}")
            logger.log("")
            return False

    def _install_folder(self, app, ruta_origen):
        """Instala una carpeta (copia)"""
        destino = app.get("destino", "")
        nombre = app.get("nombre", "Desconocido")

        if not destino:
            logger.log("No se definió destino para la carpeta")
            logger.log("")
            return "failed"

        if not os.path.exists(ruta_origen):
            logger.log("Carpeta origen no encontrada en red")
            logger.log("")
            return "skipped"

        try:
            logger.log("Copiando carpeta...")

            if os.path.exists(destino):
                logger.log("Carpeta existente detectada, eliminando versión previa...")
                shutil.rmtree(destino)

            shutil.copytree(ruta_origen, destino)
            logger.log(f"Carpeta copiada correctamente a {destino}")
            logger.log("")
            return "success"

        except Exception as e:
            logger.log(f"Error copiando carpeta: {e}")
            logger.log("")
            return "failed"

    def _install_executable(self, app, ruta, tipo, args, post, post_cmd, copiar_a_temp):
        """Instala un ejecutable (exe/msi)"""
        nombre = app.get("nombre", "Desconocido")
        install_ok = False

        if not os.path.exists(ruta):
            logger.log("Instalador no encontrado en red")
            logger.log("Se omite esta aplicación")
            logger.log("")
            return "skipped"

        ruta_ejecucion = ruta
        ruta_local = None

        # Copiar a temp si es necesario
        if copiar_a_temp:
            try:
                logger.log("Copiando instalador a carpeta temporal...")
                ruta_local = stage_to_temp(ruta)
                ruta_ejecucion = ruta_local
                logger.log(f"Ruta local: {ruta_local}")
            except Exception as e:
                logger.log(f"Error al copiar a TEMP: {e}")
                logger.log("")
                return "failed"
        else:
            logger.log("Ejecutando desde la ubicación original")

        # Ejecutar instalador
        install_success = self._run_installer(ruta_ejecucion, tipo, args, nombre)
        
        if not install_success:
            self._cleanup_temp(ruta_local)
            logger.log("")
            return "failed"

        install_ok = True

        # Aplicar post-instalación (.reg)
        if post:
            self._apply_reg_file(post)

        # Ejecutar comando post-instalación
        if post_cmd:
            self._run_post_command(post_cmd)

        # Limpiar temp
        self._cleanup_temp(ruta_local)

        if install_ok:
            logger.log("")
            return "success"
        
        return "failed"

    def _run_installer(self, ruta_ejecucion, tipo, args, nombre):
        """Ejecuta el instalador y retorna True si tiene éxito"""
        try:
            if tipo == "msi":
                logger.log("Instalando paquete MSI...")
                msi_log = os.path.join(tempfile.gettempdir(), f"msi_{nombre.replace(' ', '_')}.log")
                comando = f'msiexec /i "{ruta_ejecucion}" /qn /norestart /l*v "{msi_log}" {args}'.strip()
                logger.log(f"Log MSI: {msi_log}")
                result = subprocess.run(comando, shell=True)
                code = result.returncode
            else:
                result = subprocess.run(f'"{ruta_ejecucion}" {args}', shell=True)
                code = result.returncode

            if code != 0:
                logger.log(f"Error al instalar {nombre} (code {code})")
                return False

            logger.log(f"Instalación completada correctamente: {nombre}")
            return True

        except Exception as e:
            logger.log(f"Excepción durante la instalación: {e}")
            return False

    def _apply_reg_file(self, post):
        """Aplica un archivo .reg"""
        from core.config import resource_path
        
        reg_path = resource_path(post) if os.path.exists(resource_path(post)) else os.path.abspath(post)
        if os.path.exists(reg_path):
            logger.log("Aplicando configuración adicional (.reg)...")
            subprocess.run(f'reg import "{reg_path}"', shell=True)
            logger.log("Configuración adicional aplicada")
        else:
            logger.log(f"Archivo .reg no encontrado: {reg_path}")

    def _run_post_command(self, post_cmd):
        """Ejecuta un comando post-instalación"""
        logger.log("Ejecutando comando posterior a la instalación...")
        try:
            r = subprocess.run(post_cmd, shell=True)
            if r.returncode == 0:
                logger.log("Post-comando ejecutado correctamente")
            else:
                logger.log(f"Post-comando finalizó con code {r.returncode}")
        except Exception as e:
            logger.log(f"Error ejecutando post_cmd: {e}")

    def _cleanup_temp(self, ruta_local):
        """Limpia archivos temporales"""
        if ruta_local:
            try:
                if os.path.exists(ruta_local):
                    os.remove(ruta_local)
                    logger.log("Archivo temporal eliminado")
            except Exception as e:
                logger.log(f"No se pudo eliminar el instalador temporal: {e}")

    def _update_ui_start(self, total_apps):
        """Actualiza la UI al inicio de la instalación"""
        self.callbacks['enable_run_button'](False)
        self.callbacks['update_progress'](0)
        logger.clear()
        self.callbacks['set_status']("Preparando instalación...")

    def _log_start(self, mode_name, total_apps, log_file_path):
        """Registra el inicio de la instalación en el log"""
        logger.log("AUTOINSTALLER - INICIO DE PROCESO")
        logger.log(f"Modo seleccionado: {mode_name}")
        logger.log(f"Total de aplicaciones: {total_apps}")
        logger.log(f"Archivo de bitácora: {log_file_path}")
        logger.log("")

    def _show_final_summary(self, mode_name, total_apps, success_count, 
                           failed_count, skipped_count, total_time, log_path):
        """Muestra el resumen final"""
        logger.log("=" * 70)
        logger.log("RESUMEN FINAL")
        logger.log("=" * 70)
        logger.log(f"Modo ejecutado: {mode_name}")
        logger.log(f"Total de aplicaciones: {total_apps}")
        logger.log(f"Instaladas correctamente: {success_count}")
        logger.log(f"Fallidas: {failed_count}")
        logger.log(f"Omitidas: {skipped_count}")
        logger.log(f"Tiempo total: {total_time:.2f} segundos")
        logger.log(f"Bitácora: {log_path}")
        logger.log("=" * 70)

        summary = (
            f"Modo ejecutado: {mode_name}\n"
            f"Total de aplicaciones: {total_apps}\n"
            f"Instaladas correctamente: {success_count}\n"
            f"Fallidas: {failed_count}\n"
            f"Omitidas: {skipped_count}\n"
            f"Tiempo total: {total_time:.2f} segundos\n"
            f"Bitácora guardada en:\n{log_path}"
        )

        self.callbacks['show_summary'](summary)

    def _show_error(self, error_msg):
        """Muestra un error"""
        self.callbacks['set_status']("Error durante la instalación")
        messagebox.showerror("Error", error_msg)

    def _finish_installation(self):
        """Finaliza la instalación"""
        self.callbacks['set_status']("Sin aplicaciones seleccionadas")
        self.callbacks['enable_run_button']()