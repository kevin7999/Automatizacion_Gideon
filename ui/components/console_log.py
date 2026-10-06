import customtkinter as ctk
from datetime import datetime
from ui.theme import *

class ConsoleLog(ctk.CTkFrame):
    """
    Consola estilo DevTools con tags de colores.
    """
    def __init__(self, master, title="Terminal", **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_SUBTLE, **kwargs)
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header.pack(fill="x", padx=10, pady=5)
        
        lbl_title = ctk.CTkLabel(self.header, text=title, font=FONT_SUBTITLE, text_color=TEXT_PRIMARY)
        lbl_title.pack(side="left")
        
        btn_clear = ctk.CTkButton(
            self.header, 
            text="Limpiar", 
            width=60, 
            height=24,
            fg_color=BG_INPUT,
            hover_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY,
            font=FONT_MINI,
            command=self.clear
        )
        btn_clear.pack(side="right")
        
        # Textbox
        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=BG_APP,
            text_color=TEXT_PRIMARY,
            font=FONT_CONSOLE,
            corner_radius=6,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.textbox.configure(state="disabled")
        
        # Configurar tags de colores
        self.textbox.tag_config("timestamp", foreground=TEXT_SECONDARY)
        self.textbox.tag_config("info", foreground=STATUS_INFO)
        self.textbox.tag_config("success", foreground=STATUS_SUCCESS)
        self.textbox.tag_config("error", foreground=STATUS_ERROR)
        self.textbox.tag_config("warning", foreground=STATUS_WARNING)
        self.textbox.tag_config("otp", foreground=STATUS_WARNING)

    def write_log(self, text: str):
        """Escribe un mensaje en la consola analizando su contenido para asignarle color."""
        # Se asume que este método será envuelto en self.after() desde el invocador si viene de un hilo.
        hora = datetime.now().strftime("%H:%M:%S")
        
        # Detección simple de tipo basada en prefijos comunes del sistema
        tag = None
        if "[SUCCESS]" in text or "Éxito" in text or "Exito" in text or "OK" in text:
            tag = "success"
        elif "[ERROR]" in text or "Error" in text or "Falló" in text or "Excepción" in text:
            tag = "error"
        elif "[OTP]" in text or "OTP" in text:
            tag = "otp"
        elif "[INFO]" in text or "Iniciando" in text:
            tag = "info"
        
        self.textbox.configure(state="normal")
        
        # Insertar timestamp
        self.textbox.insert("end", f"[{hora}] ", "timestamp")
        
        # Insertar texto con el tag (o sin tag si es texto normal)
        if tag:
            self.textbox.insert("end", f"{text}\n", tag)
        else:
            self.textbox.insert("end", f"{text}\n")
            
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
        
    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
