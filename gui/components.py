# -*- coding: utf-8 -*-

import tkinter as tk

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