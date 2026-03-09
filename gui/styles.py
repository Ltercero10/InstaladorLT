# -*- coding: utf-8 -*-

from tkinter import ttk

def configure_styles():
    """Configura los estilos globales de la aplicación"""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TProgressbar", thickness=16)