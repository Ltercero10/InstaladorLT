# -*- coding: utf-8 -*-

import platform
import socket
import getpass
import subprocess
import psutil
import os
import webbrowser
from datetime import datetime

def bytes_to_gb(value):
    """Convierte bytes a gigabytes"""
    return round(value / (1024 ** 3), 2)

def get_ram_details():
    """Obtiene detalles de la RAM"""
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
    """Obtiene información de discos adicionales (no C:)"""
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
    """Obtiene el número de serie del equipo"""
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
    """Obtiene el modelo del equipo"""
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
    """Obtiene el dominio o grupo de trabajo"""
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
    """Obtiene la dirección IP"""
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return "No disponible"
    
def detect_manufacturer():
    try:
        result = subprocess.check_output(
            'wmic computersystem get manufacturer',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1].lower()
    except Exception:
        pass
    return ""    

def get_system_info():
    """Obtiene toda la información del sistema"""
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
    
def open_driver_support_page():
    manufacturer = detect_manufacturer()
    serial = get_pc_serial()

    if "dell" in manufacturer:
        if serial and serial != "No disponible":
            webbrowser.open(f"https://www.dell.com/support/home/es-hn/product-support/servicetag/{serial}")
        else:
            webbrowser.open("https://www.dell.com/support/home/es-hn")
        return "Se abrió la página de soporte de Dell."

    elif "lenovo" in manufacturer:
        webbrowser.open("https://pcsupport.lenovo.com/")
        return "Se abrió la página de soporte de Lenovo."

    elif "hp" in manufacturer or "hewlett" in manufacturer:
        webbrowser.open("https://support.hp.com/")
        return "Se abrió la página de soporte de HP."

    else:
        webbrowser.open("https://www.catalog.update.microsoft.com/")
        return "Fabricante no identificado. Se abrió Microsoft Update Catalog."


def update_drivers():
    manufacturer = detect_manufacturer()

    if "dell" in manufacturer:
        possible_paths = [
            r"C:\Program Files\Dell\CommandUpdate\dcu-cli.exe",
            r"C:\Program Files (x86)\Dell\CommandUpdate\dcu-cli.exe"
        ]

        dcu_path = next((p for p in possible_paths if os.path.exists(p)), None)

        if dcu_path:
            subprocess.Popen(f'"{dcu_path}" /scan -silent', shell=True)
            return True, "Se inició el escaneo de drivers con Dell Command Update."

        return False, "No se encontró Dell Command Update instalado en este equipo."

    elif "lenovo" in manufacturer:
        return False, "Para Lenovo se recomienda usar Lenovo Vantage o Lenovo System Update."

    elif "hp" in manufacturer or "hewlett" in manufacturer:
        return False, "Para HP se recomienda usar HP Support Assistant."

    return False, "Fabricante no identificado. Se recomienda usar Windows Update o la herramienta oficial del fabricante."