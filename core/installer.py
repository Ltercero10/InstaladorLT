# -*- coding: utf-8 -*-

import os
import subprocess
import time
import shutil
import tempfile
from tkinter import messagebox
import signal

from core.config import load_config
from core.logger import global_logger as logger
from utils.file_utils import stage_to_temp
from utils.subprocess_utils import hidden_run
from utils.subprocess_utils import hidden_popen



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
            self._update_ui_start(total_apps)

            config = load_config()
            if not config:
                self._show_error("Error de configuración")
                return

            log_file_path = logger.create_log_file(mode_name)

            if total_apps == 0:
                logger.log("No hay aplicaciones seleccionadas para instalar.")
                self._finish_installation()
                return

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

                self.callbacks["update_progress"](index)

                if "progress_set_value" in self.callbacks:
                    self.callbacks["progress_set_value"](index, total_apps)

            total_time = time.time() - start_time
            self._show_final_summary(
                mode_name,
                total_apps,
                success_count,
                failed_count,
                skipped_count,
                total_time,
                log_file_path,
            )

        except Exception as e:
            self._show_error(str(e))
        finally:
            self.callbacks["enable_run_button"]()
    def _process_app(self, app, index, total_apps, rutas_base):
        """Procesa una aplicación individual"""

        nombre = app.get("nombre", "Desconocido")
        tipo = app.get("tipo", "exe").lower()

        self.callbacks["set_status"](f"Instalando {index}/{total_apps}: {nombre}")

        if "progress_set_app" in self.callbacks:
            self.callbacks["progress_set_app"](f"{nombre}")

        if "progress_set_status" in self.callbacks:
            self.callbacks["progress_set_status"](f"Instalando {index} de {total_apps}")

        if "progress_append_log" in self.callbacks:
            self.callbacks["progress_append_log"](f"Iniciando instalación de {nombre}", "info")

        if "progress_start_activity" in self.callbacks:
            self.callbacks["progress_start_activity"]()

        logger.log(f"[{index}/{total_apps}] Procesando: {nombre}")

        try:
            if tipo == "special":
                result = self._process_special_app(app, rutas_base)

            elif app.get("requiere_pais"):
                result = self._process_country_app(app, rutas_base)

            else:
                base = app.get("base", "")
                ruta_relativa = app.get("ruta", "")
                args = app.get("args", "")
                post = app.get("post", "")
                post_cmd = app.get("post_cmd", "")
                copiar_a_temp = app.get("copiar_a_temp", True)

                if tipo in ["carpeta", "copy_folder"]:
                    ruta = self._build_path(base, ruta_relativa, rutas_base)
                    if not ruta:
                        result = "skipped"
                    else:
                        logger.log(f"Ruta origen: {ruta}")

                        if not self._check_source_access(ruta):
                            result = "skipped"
                        else:
                            result = self._install_folder(app, ruta)
                else:
                    ruta = self._build_path(base, ruta_relativa, rutas_base)
                    if not ruta:
                        result = "skipped"
                    else:
                        logger.log(f"Ruta de red: {ruta}")

                        if not self._check_source_access(ruta):
                            result = "skipped"
                        else:
                            result = self._install_executable(
                                app, ruta, tipo, args, post, post_cmd, copiar_a_temp
                            )

            if "progress_append_log" in self.callbacks:
                if result == "success":
                    self.callbacks["progress_append_log"](f"{nombre}: instalación completada", "success")
                elif result == "failed":
                    self.callbacks["progress_append_log"](f"{nombre}: instalación fallida", "error")
                elif result == "skipped":
                    self.callbacks["progress_append_log"](f"{nombre}: instalación omitida", "normal")

            return result

        finally:
            if "progress_stop_activity" in self.callbacks:
                self.callbacks["progress_stop_activity"]()

    def _process_country_app(self, app, rutas_base):
        """Procesa aplicaciones que requieren uno o varios países"""
        nombre = app.get("nombre", "Desconocido")
        tipo = app.get("tipo", "").lower()
        paises = app.get("paises_seleccionados", [])
        paises_config = app.get("paises_config", {})

        if not paises:
            logger.log(f"{nombre} requiere al menos un país seleccionado.")
            logger.log("")
            return "failed"

        if tipo not in ["carpeta", "copy_folder"]:
            logger.log(f"{nombre} requiere país, pero el tipo '{tipo}' no está soportado para esta lógica.")
            logger.log("")
            return "failed"

        hubo_error = False
        hubo_exito = False

        for pais in paises:
            logger.log(f"Procesando país: {pais}")

            config_pais = paises_config.get(pais)
            if not config_pais:
                logger.log(f"No existe configuración para {nombre} - {pais}")
                logger.log("")
                hubo_error = True
                continue

            origen = config_pais.get("origen", "").strip()
            destino = config_pais.get("destino", "").strip()

            if not origen or not destino:
                logger.log(f"Configuración incompleta para {nombre} - {pais}")
                logger.log("")
                hubo_error = True
                continue

            ruta_origen = self._resolve_country_source(origen, rutas_base)

            logger.log(f"Origen [{pais}]: {ruta_origen}")
            logger.log(f"Destino [{pais}]: {destino}")

            if not self._check_source_access(ruta_origen):
                hubo_error = True
                continue

            result = self._copy_folder(ruta_origen, destino)

            if result == "success":
                hubo_exito = True
            else:
                hubo_error = True

            logger.log("")

        if hubo_exito and hubo_error:
            return "failed"

        if hubo_exito:
            return "success"

        return "failed"

    def _build_path(self, base, ruta_relativa, rutas_base):
        """Construye la ruta final a partir de base + ruta relativa"""
        if base not in rutas_base:
            logger.log(f"Base no definida en config.json: {base}")
            logger.log("")
            return None

        return os.path.join(rutas_base[base], ruta_relativa)

    def _resolve_country_source(self, origen, rutas_base):
        """
        Resuelve el origen para apps por país.
        Si viene UNC o absoluta, la usa directamente.
        Si viene relativa y existe base 'instaladores', la combina.
        """
        if os.path.isabs(origen) or origen.startswith("\\\\"):
            return origen

        base_instaladores = rutas_base.get("instaladores")
        if base_instaladores:
            return os.path.join(base_instaladores, origen)

        return origen

    def _check_source_access(self, ruta):
        """Verifica si se puede acceder al recurso origen"""
        try:
            if os.path.isdir(ruta):
                os.listdir(ruta)
            else:
                carpeta = os.path.dirname(ruta)
                if carpeta:
                    os.listdir(carpeta)
            logger.log("Origen accesible")
            return True
        except Exception as e:
            logger.log(f"No se puede acceder al origen: {e}")
            logger.log("")
            return False

    def _install_folder(self, app, ruta_origen):
        """Instala una carpeta (copia)"""
        destino = app.get("destino", "")
        nombre = app.get("nombre", "Desconocido")

        if not destino:
            logger.log(f"No se definió destino para la carpeta: {nombre}")
            logger.log("")
            return "failed"

        return self._copy_folder(ruta_origen, destino)

    def _copy_folder(self, origen, destino):
        """Copia una carpeta completa al destino"""
        if not os.path.exists(origen):
            logger.log(f"Carpeta origen no encontrada: {origen}")
            logger.log("")
            return "skipped"

        try:
            logger.log("Copiando carpeta...")

            parent_dir = os.path.dirname(destino)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            if os.path.exists(destino):
                logger.log("Carpeta existente detectada, eliminando versión previa...")
                shutil.rmtree(destino)

            shutil.copytree(origen, destino)
            logger.log(f"Carpeta copiada correctamente a {destino}")
            self._grant_folder_permissions(destino)
            return "success"

        except Exception as e:
            logger.log(f"Error copiando carpeta: {e}")
            return "failed"

    def _install_executable(self, app, ruta, tipo, args, post, post_cmd, copiar_a_temp):
        """Instala un ejecutable (exe/msi)"""
        nombre = app.get("nombre", "Desconocido")

        if not os.path.exists(ruta):
            logger.log("Instalador no encontrado en red")
            logger.log("Se omite esta aplicación")
            logger.log("")
            return "skipped"

        ruta_ejecucion = ruta
        ruta_local = None

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

        # IMPORTANTE: siempre asignar install_success aquí
        install_success = self._run_installer(ruta_ejecucion, tipo, args, nombre, app)

        if not install_success:
            self._cleanup_temp(ruta_local)
            logger.log("")
            return "failed"

        if post:
            self._apply_reg_file(post)

        if post_cmd:
            self._run_post_command(post_cmd)

        self._cleanup_temp(ruta_local)

        logger.log("")
        return "success"
    
    def _get_silent_candidates(self, app, installer_path=None):
        """
        Devuelve candidatos silenciosos según el motor detectado.
        """
        nombre = (app.get("nombre") or "").lower()
        ruta = (app.get("ruta") or "").lower()

        # Reglas conocidas primero
        if "anydesk" in nombre or "anydesk" in ruta:
            return [
                '--install "C:\\Program Files (x86)\\AnyDesk" --start-with-win --silent',
                "--silent",
                "/silent",
            ]

        if "chrome" in nombre or "chromesetup" in ruta:
            return [
                "/silent /install",
                "/install",
                "/silent",
            ]

        if "realvnc" in nombre or "vnc" in nombre or "vnc" in ruta:
            return [
                "/silent /suppressmsgboxes /norestart",
                "/silent",
            ]

        if "outputmessenger" in nombre or "output messenger" in nombre:
            return [
                "/silent /suppressmsgboxes /norestart",
                "/silent",
            ]

        engine = self._detect_installer_engine(installer_path or "")

        if engine == "inno":
            return [
                "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART",
                "/SILENT /SUPPRESSMSGBOXES /NORESTART",
                "/VERYSILENT",
                "/SILENT",
            ]

        if engine == "nsis":
            return [
                "/S",
            ]

        if engine == "installshield":
            return [
                "/s",
                "/silent",
            ]

        if engine == "burn":
            return [
                "/quiet",
                "/passive",
            ]

        return [
            "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART",
            "/S",
            "/quiet",
        ]
        

    def _run_command_with_timeout(self, command, timeout=120):
        """
        Ejecuta un comando y mata el árbol completo si se excede el tiempo.
        """
        try:
            process = subprocess.Popen(command, shell=True)

            try:
                process.wait(timeout=timeout)
                return process.returncode, False

            except subprocess.TimeoutExpired:
                logger.log(f"Tiempo excedido ({timeout}s). Intentando finalizar árbol de procesos...")

                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                        shell=False
                    )
                except Exception as e:
                    logger.log(f"No se pudo cerrar el árbol del proceso: {e}")

                return -999, True

        except Exception as e:
            logger.log(f"Error ejecutando comando: {e}")
            return -1, False

    def _try_exe_silent_install(self, app, ruta_ejecucion, nombre):
        """
        Prueba argumentos silenciosos según el motor detectado.
        """
        engine = self._detect_installer_engine(ruta_ejecucion)
        candidates = self._get_silent_candidates(app, ruta_ejecucion)

        logger.log(f"Motor detectado: {engine}")
        logger.log("No se definieron argumentos. Se probarán parámetros compatibles...")

        for index, candidate in enumerate(candidates, start=1):
            args_label = candidate if candidate else "[sin argumentos]"
            logger.log(f"Intento {index}/{len(candidates)} con argumentos: {args_label}")

            command = f'"{ruta_ejecucion}" {candidate}'.strip()
            code, timed_out = self._run_command_with_timeout(command, timeout=120)

            if timed_out:
                logger.log("El instalador excedió el tiempo permitido. Se probará el siguiente conjunto.")
                continue

            if code in (0, 1641, 3010):
                logger.log(f"Instalación completada con argumentos: {args_label}")
                app["args"] = candidate
                return True

            logger.log(f"El intento finalizó con código {code}. Se probará el siguiente conjunto.")

        logger.log(f"No se encontró un conjunto de argumentos funcional para {nombre}.")
        logger.log("Este programa probablemente requiere argumentos específicos o instalación manual.")
        return False

    def _run_installer(self, ruta_ejecucion, tipo, args, nombre, app=None):
        """Ejecuta el instalador y retorna True si tiene éxito"""
        try:
            if tipo == "msi":
                logger.log("Instalando paquete MSI...")
                msi_log = os.path.join(
                    tempfile.gettempdir(),
                    f"msi_{nombre.replace(' ', '_')}.log"
                )
                comando = f'msiexec /i "{ruta_ejecucion}" /qn /norestart /l*v "{msi_log}" {args}'.strip()
                logger.log(f"Log MSI: {msi_log}")
                result = hidden_run(comando, shell=True)
                code = result.returncode

                if code not in (0, 1641, 3010):
                    logger.log(f"Error al instalar {nombre} (code {code})")
                    return False

                logger.log(f"Instalación completada correctamente: {nombre}")
                return True

            logger.log("Instalando ejecutable...")

            # Si ya viene args definido, respetarlo
            if args and args.strip():
                command = f'"{ruta_ejecucion}" {args}'.strip()
                code, timed_out = self._run_command_with_timeout(command, timeout=120)

                if timed_out:
                    logger.log(f"El instalador excedió el tiempo permitido: {nombre}")
                    return False

                if code not in (0, 1641, 3010):
                    logger.log(f"Error al instalar {nombre} (code {code})")
                    return False

                logger.log(f"Instalación completada correctamente: {nombre}")
                return True

            # Si no trae args, probar candidatos
            return self._try_exe_silent_install(app or {}, ruta_ejecucion, nombre)

        except Exception as e:
            logger.log(f"Excepción durante la instalación: {e}")
            return False

    def _apply_reg_file(self, post):
        """Aplica un archivo .reg"""
        from core.config import resource_path

        reg_path = resource_path(post) if os.path.exists(resource_path(post)) else os.path.abspath(post)

        if os.path.exists(reg_path):
            logger.log("Aplicando configuración adicional (.reg)...")
            hidden_run(f'reg import "{reg_path}"', shell=True)
            logger.log("Configuración adicional aplicada")
        else:
            logger.log(f"Archivo .reg no encontrado: {reg_path}")

    def _run_post_command(self, post_cmd):
        """Ejecuta un comando post-instalación"""
        logger.log("Ejecutando comando posterior a la instalación...")
        try:
            result = hidden_run(post_cmd, shell=True)
            if result.returncode == 0:
                logger.log("Post-comando ejecutado correctamente")
            else:
                logger.log(f"Post-comando finalizó con code {result.returncode}")
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
        self.callbacks["enable_run_button"](False)
        self.callbacks
        logger.clear()
        self.callbacks["set_status"]("Preparando instalación...")
        

    def _log_start(self, mode_name, total_apps, log_file_path):
        """Registra el inicio de la instalación en el log"""
        logger.log("AUTOINSTALLER - INICIO DE PROCESO")
        logger.log(f"Modo seleccionado: {mode_name}")
        logger.log(f"Total de aplicaciones: {total_apps}")
        logger.log(f"Archivo de bitácora: {log_file_path}")
        logger.log("")

    def _show_final_summary(
        self,
        mode_name,
        total_apps,
        success_count,
        failed_count,
        skipped_count,
        total_time,
        log_path,
    ):
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

        self.callbacks["show_summary"](summary)

    def _show_error(self, error_msg):
        """Muestra un error"""
        self.callbacks["set_status"]("Error durante la instalación")
        messagebox.showerror("Error", error_msg)

    def _finish_installation(self):
        """Finaliza la instalación"""
        self.callbacks["set_status"]("Sin aplicaciones seleccionadas")
        self.callbacks["enable_run_button"]()
    def _grant_folder_permissions(self, path):
        """Otorga permisos completos a la carpeta copiada."""
        try:
            if not os.path.exists(path):
                logger.log(f"No se puede asignar permisos, la ruta no existe: {path}")
                return False

            cmd = f'icacls "{path}" /grant Users:(OI)(CI)F /T /C'
            result = hidden_run(cmd, shell=True)

            if result.returncode == 0:
                logger.log(f"Permisos otorgados correctamente a: {path}")
                return True

            logger.log(f"No se pudieron asignar permisos a: {path}")
            return False

        except Exception as e:
            logger.log(f"Error asignando permisos a {path}: {e}")
            return False
        
    def _process_special_app(self, app, rutas_base):
        handler = app.get("special_handler", "").lower()

        if handler == "office_odt":
            return self._install_office_odt(app, rutas_base)
        if handler == "vnc_with_license":
            return self._install_vnc_with_license(app, rutas_base)
        if handler == "output_messenger":
            return self._install_output_messenger(app, rutas_base)
        if handler == "sql_express_kielsa":
            return self._install_sql_express_kielsa(app, rutas_base)
        if handler == "ssms_silent":
            return self._install_ssms_silent(app, rutas_base)

        logger.log(f"Handler especial no soportado: {handler}")
        logger.log("")
        return "failed"


    def _install_office_odt(self, app, rutas_base):
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")

        office_dir = self._build_path(base, ruta_relativa, rutas_base)
        if not office_dir:
            return "skipped"

        setup_path = os.path.join(office_dir, "setup.exe")
        xml_path = os.path.join(office_dir, "Configuration.xml")

        logger.log(f"Ruta ODT: {office_dir}")

        if not os.path.exists(setup_path):
            logger.log("No se encontró setup.exe de ODT")
            logger.log("")
            return "failed"

        if not os.path.exists(xml_path):
            logger.log("No se encontró Configuration.xml")
            logger.log("")
            return "failed"

        try:
            logger.log("Iniciando instalación de Office con ODT...")
            command = f'"{setup_path}" /configure "{xml_path}"'
            result = subprocess.run(command, shell=True, cwd=office_dir)

            if result.returncode == 0:
                logger.log("Office instalado correctamente con ODT")
                logger.log("")
                return "success"

            logger.log(f"La instalación de Office finalizó con código {result.returncode}")
            logger.log("")
            return "failed"

        except Exception as e:
            logger.log(f"Error instalando Office con ODT: {e}")
            logger.log("")
            return "failed"
        
    def _install_vnc_with_license(self, app, rutas_base):
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")
        tipo = "exe"
        args = app.get("args", "")
        post_cmd = app.get("post_cmd", "")
        copiar_a_temp = app.get("copiar_a_temp", True)

        ruta = self._build_path(base, ruta_relativa, rutas_base)
        if not ruta:
            return "skipped"

        logger.log(f"Ruta de VNC: {ruta}")

        if not self._check_source_access(ruta):
            return "skipped"

        result = self._install_executable(
            app,
            ruta,
            tipo,
            args,
            "",
            post_cmd,
            copiar_a_temp
        )

        return result
    def _install_output_messenger(self, app, rutas_base):
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")
        tipo = "exe"
        args = app.get("args", "")
        copiar_a_temp = app.get("copiar_a_temp", True)

        ruta = self._build_path(base, ruta_relativa, rutas_base)
        if not ruta:
            return "skipped"

        logger.log(f"Ruta de Output Messenger: {ruta}")

        if not self._check_source_access(ruta):
            return "skipped"

        return self._install_executable(
            app,
            ruta,
            tipo,
            args,
            "",
            "",
            copiar_a_temp
        )
    
    def _install_sql_express_kielsa(self, app, rutas_base):
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")
        copiar_a_temp = app.get("copiar_a_temp", True)

        ruta = self._build_path(base, ruta_relativa, rutas_base)
        if not ruta:
            return "skipped"

        logger.log(f"Ruta de SQL Express: {ruta}")

        if not self._check_source_access(ruta):
            return "skipped"

        ruta_ejecucion = ruta
        ruta_local = None

        if copiar_a_temp:
            try:
                logger.log("Copiando instalador SQL Express a carpeta temporal...")
                ruta_local = stage_to_temp(ruta)
                ruta_ejecucion = ruta_local
                logger.log(f"Ruta local SQL Express: {ruta_local}")
            except Exception as e:
                logger.log(f"Error al copiar SQL Express a TEMP: {e}")
                logger.log("")
                return "failed"

        comando = (
            f'"{ruta_ejecucion}" '
            '/Q /ACTION=Install /FEATURES=SQLEngine '
            '/INSTANCENAME=SQLEXPRESS '
            '/SQLCOLLATION=SQL_Latin1_General_CP1_CI_AS '
            '/SECURITYMODE=SQL '
            '/SAPWD="FARMACIA" '
            '/ADDCURRENTUSERASSQLADMIN '
            '/IACCEPTSQLSERVERLICENSETERMS'
        )

        try:
            logger.log("Iniciando instalación silenciosa de SQL Server Express...")
            result = subprocess.run(comando, shell=True)

            if result.returncode in (0, 1641, 3010):
                logger.log("SQL Server Express instalado correctamente.")
                logger.log("")
                self._cleanup_temp(ruta_local)
                return "success"

            logger.log(f"La instalación de SQL Express finalizó con código {result.returncode}")
            logger.log("")
            self._cleanup_temp(ruta_local)
            return "failed"

        except Exception as e:
            logger.log(f"Error instalando SQL Express: {e}")
            logger.log("")
            self._cleanup_temp(ruta_local)
            return "failed"
        
    def _install_ssms_silent(self, app, rutas_base):
        base = app.get("base", "")
        ruta_relativa = app.get("ruta", "")
        copiar_a_temp = app.get("copiar_a_temp", True)

        ruta = self._build_path(base, ruta_relativa, rutas_base)
        if not ruta:
            return "skipped"

        logger.log(f"Ruta de SSMS: {ruta}")

        if not self._check_source_access(ruta):
            return "skipped"

        ruta_ejecucion = ruta
        ruta_local = None

        if copiar_a_temp:
            try:
                logger.log("Copiando instalador SSMS a carpeta temporal...")
                ruta_local = stage_to_temp(ruta)
                ruta_ejecucion = ruta_local
                logger.log(f"Ruta local SSMS: {ruta_local}")
            except Exception as e:
                logger.log(f"Error al copiar SSMS a TEMP: {e}")
                logger.log("")
                return "failed"

        comando = f'"{ruta_ejecucion}" --quiet --norestart'

        try:
            logger.log("Iniciando instalación silenciosa de SSMS...")
            result = subprocess.run(comando, shell=True)

            if result.returncode in (0, 1641, 3010):
                logger.log("SSMS instalado correctamente.")
                logger.log("")
                self._cleanup_temp(ruta_local)
                return "success"

            logger.log(f"La instalación de SSMS finalizó con código {result.returncode}")
            logger.log("")
            self._cleanup_temp(ruta_local)
            return "failed"

        except Exception as e:
            logger.log(f"Error instalando SSMS: {e}")
            logger.log("")
            self._cleanup_temp(ruta_local)
            return "failed"


    def _detect_installer_engine(self, installer_path):
        """
        Intenta detectar el motor del instalador leyendo strings del binario.
        Retorna: inno, nsis, installshield, msi, unknown
        """
        path_lower = installer_path.lower()

        if path_lower.endswith(".msi"):
            return "msi"

        try:
            with open(installer_path, "rb") as f:
                data = f.read(2 * 1024 * 1024)  # leer hasta 2 MB
            text = data.decode("latin1", errors="ignore").lower()

            if "inno setup" in text:
                return "inno"
            if "nullsoft install system" in text or "nsis" in text:
                return "nsis"
            if "installshield" in text:
                return "installshield"
            if "wix burn" in text or "burn engine" in text:
                return "burn"

        except Exception:
            pass

        return "unknown"