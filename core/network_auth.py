import subprocess
from pathlib import Path
from tkinter import messagebox

from gui.login_dialog import NetworkLoginDialog

def disconnect_share(share_path: str):
    """
    Desconecta una ruta de red si ya existe una sesión previa.
    """
    try:
        subprocess.run(
            ["net", "use", share_path, "/delete", "/y"],
            capture_output=True,
            text=True,
            shell=True
        )
    except Exception:
        pass


def connect_to_share(share_path: str, username: str, password: str, domain: str = ""):
    """
    Conecta a un recurso compartido SMB usando credenciales.
    Retorna: (success: bool, message: str)
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
        shell=True
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


    #dialog = NetworkLoginDialog(root, default_share=share_path)
    #root.wait_window(dialog)

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
        messagebox.showerror(
            "Error",
            "Se autenticó, pero no se pudo acceder a la carpeta compartida."
        )
        return False

    return True