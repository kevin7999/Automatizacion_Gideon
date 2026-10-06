import customtkinter as ctk
from typing import Callable
from ui.theme import *

class Sidebar(ctk.CTkFrame):
    """
    Barra lateral de navegación (SaaS Style) para G.I.D.E.O.N. 4.0.
    Reemplaza al antiguo sistema de pestañas CTkTabview.
    """
    def __init__(self, master, on_nav_click: Callable[[str], None], **kwargs):
        # Fondo oscuro para el sidebar y borde fino a la derecha
        super().__init__(master, fg_color=BG_SIDEBAR, width=220, corner_radius=0, **kwargs)
        self.on_nav_click = on_nav_click
        self.nav_buttons = {}
        
        # --- Cabecera: Logo / Titulo ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(20, 30), padx=15)
        
        self.lbl_logo = ctk.CTkLabel(
            self.header_frame, 
            text="G.I.D.E.O.N.", 
            font=FONT_TITLE,
            text_color=PRIMARY_ORANGE
        )
        self.lbl_logo.pack(anchor="w")
        
        self.lbl_sub = ctk.CTkLabel(
            self.header_frame,
            text="RPA Command Center",
            font=FONT_MINI,
            text_color=TEXT_SECONDARY
        )
        self.lbl_sub.pack(anchor="w", pady=(0, 0))
        
        # --- Botones de Navegación ---
        self.crear_boton("FTTH Masivo", "FTTH Masivo")
        self.crear_boton("OTT Cuentas", "OTT Cuentas")
        self.crear_boton("Telemetría", "Telemetría")
        
        # --- Espaciador ---
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        
        # --- Footer: Configuración ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", side="bottom", pady=15, padx=0)
        
        btn_config = ctk.CTkButton(
            self.footer_frame,
            text="  Configuración",
            anchor="w",
            font=FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=BG_CARD,
            text_color=TEXT_SECONDARY,
            height=40,
            corner_radius=6,
            command=lambda: self._click_interno("Sistema")
        )
        btn_config.pack(fill="x", padx=10, pady=2)
        self.nav_buttons["Sistema"] = btn_config

    def crear_boton(self, raw_id: str, display_text: str):
        """Crea un botón de navegación. raw_id es el string exacto usado en el switch de vistas."""
        btn = ctk.CTkButton(
            self,
            text=f"  {display_text}",
            anchor="w",
            font=FONT_BODY_BOLD,
            fg_color="transparent",
            hover_color=BG_CARD,
            text_color=TEXT_SECONDARY,
            height=40,
            corner_radius=6,
            command=lambda: self._click_interno(raw_id)
        )
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons[raw_id] = btn

    def _click_interno(self, nav_id: str):
        self.set_active(nav_id)
        self.on_nav_click(nav_id)

    def set_active(self, nav_id: str):
        """Cambia los colores para reflejar cuál sección está activa."""
        for nid, btn in self.nav_buttons.items():
            if nid == nav_id:
                btn.configure(
                    fg_color=BG_INPUT, 
                    text_color=PRIMARY_ORANGE,
                    hover_color=BG_INPUT
                )
            else:
                btn.configure(
                    fg_color="transparent", 
                    text_color=TEXT_SECONDARY,
                    hover_color=BG_CARD
                )
