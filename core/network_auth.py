import subprocess
from pathlib import Path
from tkinter import messagebox
from gui.login_dialog import NetworkLoginDialog
def disconnect_share(share_path: str):
    """
    Desconecta una ruta de red específica si ya existe una sesión previa.
    """
    try:
        subprocess.run(
            ["net", "use", share_path, "/delete", "/y"],
            capture_output=True,
            text=True,
            shell=False
        )
    except Exception:
        pass


def disconnect_server_connections(server_host: str):
    """
    Desconecta conexiones previas al servidor para evitar error 1219.
    """
    try:
        result = subprocess.run(
            ["net", "use"],
            capture_output=True,
            text=True,
            shell=False
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        lines = output.splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Buscar recursos UNC activos que apunten al mismo host
            if server_host.lower() in line.lower():
                parts = line.split()
                unc_targets = [p for p in parts if p.startswith("\\\\")]

                for unc in unc_targets:
                    try:
                        subprocess.run(
                            ["net", "use", unc, "/delete", "/y"],
                            capture_output=True,
                            text=True,
                            shell=False
                        )
                    except Exception:
                        pass
    except Exception:
        pass


def connect_to_share(share_path: str, username: str, password: str, domain: str = ""):
    """
    Conecta a un recurso compartido SMB usando credenciales.
    """
    full_user = f"{domain}\\{username}" if domain else username

    cmd = [
        "net", "use", share_path,
        password,
        f"/user:{full_user}",
        "/persistent:no"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=False
    )

    if result.returncode == 0:
        return True, "Conexión establecida correctamente."

    error_msg = (result.stderr or result.stdout or "No se pudo establecer conexión.").strip()
    return False, error_msg


def verify_share_access(share_path: str):
    """
    Verifica si la ruta compartida es accesible.
    """
    try:
        return Path(share_path).exists()
    except Exception:
        return False


def ensure_network_access(root, share_path: str):
    dialog = NetworkLoginDialog(root, default_share=share_path)
    root.wait_window(dialog)

    if not dialog.result:
        return False

    share = dialog.result["share"]
    domain = dialog.result["domain"]
    username = dialog.result["username"]
    password = dialog.result["password"]

    server_host = ""
    try:
        if share.startswith("\\\\"):
            parts = share.split("\\")
            if len(parts) >= 4:
                server_host = f"\\\\{parts[2]}"
    except Exception:
        server_host = ""

    # Limpiar conexiones previas
    if server_host:
        disconnect_server_connections(server_host)

    disconnect_share(share)

    ok, msg = connect_to_share(share, username, password, domain)
    if not ok:
        messagebox.showerror("Error de autenticación", msg)
        return False

    if not verify_share_access(share):
        messagebox.showerror(
            "Error",
            "Se autenticó, pero no se pudo acceder a la carpeta compartida."
        )
        return False

    return True