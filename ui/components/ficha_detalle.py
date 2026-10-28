"""
Módulo de Diagnóstico, Ficha de Detalle y Menú Contextual para el Historial de G.I.D.E.O.N.
Compatible con CustomTkinter, Python 3.12, Windows 11.
"""

import os
import sys
import subprocess
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


def buscar_captura_error(mailbox: str, fecha_str: str, servicio: str) -> Optional[str]:
    """
    Rastrea capturas de pantalla de error asociadas a una cuenta
    tanto en logs/screenshots como en Evidencias_QA_*.
    """
    servicio_clean = str(servicio).upper()
    carpeta_base = "Evidencias_QA_OTT" if "OTT" in servicio_clean else "Evidencias_QA_Fibra"
    mailbox_clean = str(mailbox).split("@")[0].strip().lower()
    fecha_solo = str(fecha_str).split(" ")[0].strip()

    # 1. Buscar en Evidencias_QA_<Servicio>/<fecha>/<mailbox>
    posible_dir = os.path.join(carpeta_base, fecha_solo, mailbox_clean)
    if os.path.exists(posible_dir):
        for f in os.listdir(posible_dir):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                return os.path.join(posible_dir, f)

    # 2. Búsqueda recursiva en la carpeta base si la fecha difiere
    if os.path.exists(carpeta_base):
        for root, _, files in os.walk(carpeta_base):
            if os.path.basename(root).lower() == mailbox_clean:
                for f in files:
                    if f.lower().endswith((".png", ".jpg", ".jpeg")):
                        return os.path.join(root, f)

    # 3. Buscar en logs/screenshots
    dir_screenshots = os.path.join("logs", "screenshots")
    if os.path.exists(dir_screenshots):
        # Buscar por mailbox si está en el nombre
        for f in os.listdir(dir_screenshots):
            if mailbox_clean in f.lower() and f.lower().endswith((".png", ".jpg")):
                return os.path.join(dir_screenshots, f)

    return None


class FichaDetalleCuenta(ctk.CTkToplevel):
    """
    Modal de inspección y diagnóstico completo de una cuenta del historial.
    Muestra telemetría de tiempos, datos completos de cliente y diagnóstico de fallos.
    """

    def __init__(
        self,
        parent: tk.Misc,
        datos: Dict[str, Any],
        on_requeue: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_open_evidence: Optional[Callable[[str, str, str], None]] = None,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.datos = datos
        self.on_requeue = on_requeue
        self.on_open_evidence = on_open_evidence

        self.title("G.I.D.E.O.N. - Ficha de Cuenta")
        self.geometry("720x640")
        self.minsize(680, 580)
        self.resizable(False, False)

        # Modalidad y foco
        self.transient(parent)
        self.grab_set()

        # Determinar estado
        estado_raw = str(datos.get("estado", "")).strip()
        self.es_exitoso = "EXITOSO" in estado_raw.upper()
        self.servicio = str(datos.get("servicio", "FTTH")).strip().upper()
        self.mailbox = str(datos.get("email", "")).split("@")[0].strip()
        self.fecha_hora = str(datos.get("fecha_hora", ""))

        # Buscar captura si fue fallo
        self.ruta_captura = None
        if not self.es_exitoso:
            self.ruta_captura = buscar_captura_error(self.mailbox, self.fecha_hora, self.servicio)

        self._centrar_ventana()
        self._construir_ui()

        # Atajos
        self.bind("<Escape>", lambda e: self.destroy())

    def _centrar_ventana(self):
        self.update_idletasks()
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            w, h = 720, 640
            x = px + (pw // 2) - (w // 2)
            y = py + (ph // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _construir_ui(self):
        # 1. HEADER (Estado + Servicio + Fecha)
        header_frame = ctk.CTkFrame(self, fg_color=("#f1f3f5", "#1a1b1e"), corner_radius=10)
        header_frame.pack(fill="x", padx=16, pady=(16, 10))

        # Badge de Estado
        if self.es_exitoso:
            badge_estado = ctk.CTkLabel(
                header_frame,
                text="  ✅ CREADA EXITOSAMENTE  ",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#d3f9d8", "#1b3a24"),
                text_color=("#2b8a3e", "#51cf66"),
                corner_radius=6
            )
        else:
            badge_estado = ctk.CTkLabel(
                header_frame,
                text="  ❌ FALLO EN EJECUCIÓN  ",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#ffe3e3", "#3b1d1d"),
                text_color=("#c92a2a", "#ff6b6b"),
                corner_radius=6
            )
        badge_estado.pack(side="left", padx=12, pady=10)

        # Badge Servicio
        servicio_icono = "📺 OTT" if self.servicio == "OTT" else "🌐 FTTH FIBRA"
        badge_serv = ctk.CTkLabel(
            header_frame,
            text=f"  {servicio_icono}  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e9ecef", "#2c2e33"),
            text_color=("#495057", "#adb5bd"),
            corner_radius=6
        )
        badge_serv.pack(side="left", padx=6, pady=10)

        # Fecha y Hora (derecha)
        lbl_fecha = ctk.CTkLabel(
            header_frame,
            text=f"📅 {self.fecha_hora}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#868e96", "#adb5bd")
        )
        lbl_fecha.pack(side="right", padx=14, pady=10)

        # 2. CONTENIDO SCROLLABLE
        scroll_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_content.pack(fill="both", expand=True, padx=16, pady=4)

        # --- SECCIÓN A: DATOS DEL CLIENTE ---
        card_cliente = ctk.CTkFrame(scroll_content, fg_color=("#ffffff", "#212226"), corner_radius=10, border_width=1, border_color=("#e9ecef", "#2c2e33"))
        card_cliente.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            card_cliente,
            text="👤 INFORMACIÓN DEL CLIENTE Y SERVICIO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ff7800"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        grid_frame = ctk.CTkFrame(card_cliente, fg_color="transparent")
        grid_frame.pack(fill="x", padx=14, pady=(0, 12))
        grid_frame.columnconfigure((0, 1), weight=1)

        campos = [
            ("Titular / Razón Social:", self.datos.get("nombre_o_empresa", "-")),
            ("Documento / RIF:", self.datos.get("documento_rif", "-")),
            ("N° Cliente CRM:", self.datos.get("id_cliente", "-")),
            ("Correo (Mailbox):", self.datos.get("email", "-")),
            ("Teléfono de Contacto:", self.datos.get("telefono", "-")),
            ("Tipo de Persona:", self.datos.get("tipo_persona", "-")),
            ("Ubicación Geográfica:", self.datos.get("ubicacion", "-")),
            ("Plan & Promoción:", self.datos.get("plan", "-")),
        ]

        row = 0
        col = 0
        for label_text, valor in campos:
            f_item = ctk.CTkFrame(grid_frame, fg_color="transparent")
            f_item.grid(row=row, column=col, sticky="w", padx=8, pady=4)

            ctk.CTkLabel(
                f_item,
                text=label_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=("#868e96", "#909296")
            ).pack(anchor="w")

            val_label = ctk.CTkLabel(
                f_item,
                text=str(valor) if str(valor).strip() else "-",
                font=ctk.CTkFont(size=12, weight="bold" if col == 0 and row == 0 else "normal"),
                text_color=("#212529", "#f8f9fa"),
                anchor="w",
                wraplength=280
            )
            val_label.pack(anchor="w")

            col += 1
            if col > 1:
                col = 0
                row += 1

        # --- SECCIÓN B: TELEMETRÍA Y TIEMPOS ---
        card_tiempos = ctk.CTkFrame(scroll_content, fg_color=("#ffffff", "#212226"), corner_radius=10, border_width=1, border_color=("#e9ecef", "#2c2e33"))
        card_tiempos.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            card_tiempos,
            text="⏱️ RENDIMIENTO Y TELEMETRÍA",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ff7800"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        frame_t_body = ctk.CTkFrame(card_tiempos, fg_color="transparent")
        frame_t_body.pack(fill="x", padx=14, pady=(0, 12))

        tiempo_total = str(self.datos.get("tiempo_total_segundos", "")).strip()
        if not tiempo_total:
            tiempo_total = "N/D"
        elif not tiempo_total.endswith("s"):
            tiempo_total = f"{tiempo_total}s"

        col_izq = ctk.CTkFrame(frame_t_body, fg_color=("#f8f9fa", "#1a1b1e"), corner_radius=8, width=140)
        col_izq.pack(side="left", padx=(0, 12), pady=2, fill="y")

        ctk.CTkLabel(col_izq, text="TIEMPO TOTAL", font=ctk.CTkFont(size=9, weight="bold"), text_color=("#868e96", "#adb5bd")).pack(padx=10, pady=(8, 0))
        ctk.CTkLabel(col_izq, text=tiempo_total, font=ctk.CTkFont(size=20, weight="bold"), text_color="#ff7800").pack(padx=10, pady=(0, 8))

        # Desglose de fases
        desglose_raw = str(self.datos.get("desglose_tiempos", "")).strip()
        col_der = ctk.CTkFrame(frame_t_body, fg_color="transparent")
        col_der.pack(side="left", fill="both", expand=True)

        if desglose_raw and desglose_raw not in ["-", "None", "{}"]:
            ctk.CTkLabel(col_der, text="Desglose por etapas:", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#868e96", "#adb5bd")).pack(anchor="w", pady=(0, 2))
            
            # Limpiar string si viene como JSON, dict o separado por pipes/comas
            desglose_limpio = desglose_raw.replace("{", "").replace("}", "").replace("'", "").replace('"', '')
            delimitador = "|" if "|" in desglose_limpio else ","
            partes = [p.strip() for p in desglose_limpio.split(delimitador) if p.strip()]
            for p in partes:
                ctk.CTkLabel(
                    col_der,
                    text=f"• {p}",
                    font=ctk.CTkFont(size=11),
                    text_color=("#495057", "#ced4da")
                ).pack(anchor="w", pady=1)
        else:
            ctk.CTkLabel(
                col_der,
                text="Sin desglose registrado para esta cuenta.",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=("#868e96", "#6c757d")
            ).pack(anchor="w", pady=6)

        # --- SECCIÓN C: DIAGNÓSTICO DE ERROR (Solo si no fue exitoso) ---
        if not self.es_exitoso:
            card_error = ctk.CTkFrame(scroll_content, fg_color=("#fff5f5", "#2a1b1e"), corner_radius=10, border_width=1, border_color=("#ffc9c9", "#5c2b2b"))
            card_error.pack(fill="x", pady=(0, 10))

            header_err = ctk.CTkFrame(card_error, fg_color="transparent")
            header_err.pack(fill="x", padx=14, pady=(10, 4))

            ctk.CTkLabel(
                header_err,
                text="⚠️ DIAGNÓSTICO DEL FALLO",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#c92a2a", "#ff8787")
            ).pack(side="left")

            if self.ruta_captura and os.path.exists(self.ruta_captura):
                ctk.CTkButton(
                    header_err,
                    text="📸 Ver Captura de Pantalla",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#c92a2a",
                    hover_color="#a61e1e",
                    height=26,
                    command=self._abrir_captura
                ).pack(side="right")

            txt_error = ctk.CTkTextbox(
                card_error,
                height=90,
                font=ctk.CTkFont(family="Consolas", size=10),
                fg_color=("#ffffff", "#1e1517"),
                text_color=("#c92a2a", "#ffa8a8"),
                border_width=1,
                border_color=("#ffc9c9", "#442327"),
                corner_radius=6
            )
            txt_error.pack(fill="x", padx=14, pady=(4, 12))
            txt_error.insert("1.0", str(self.datos.get("estado", "Error no especificado")))
            txt_error.configure(state="disabled")

        # 3. BARRA INFERIOR DE ACCIONES
        bottom_frame = ctk.CTkFrame(self, fg_color=("#f1f3f5", "#1a1b1e"), corner_radius=10)
        bottom_frame.pack(fill="x", padx=16, pady=(4, 16))

        ctk.CTkButton(
            bottom_frame,
            text="📋 Copiar Todo",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            width=110,
            command=self._copiar_resumen
        ).pack(side="left", padx=8, pady=8)

        ctk.CTkButton(
            bottom_frame,
            text="📁 Abrir Evidencias",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            width=130,
            command=self._abrir_carpeta_evidencias
        ).pack(side="left", padx=4, pady=8)

        if self.on_requeue:
            ctk.CTkButton(
                bottom_frame,
                text="🔁 Reenviar a Cola",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#ff7800",
                hover_color="#e66a00",
                text_color="#ffffff",
                width=130,
                command=self._reenviar_cola
            ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            bottom_frame,
            text="Cerrar",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#ced4da", "#343a40"),
            hover_color=("#adb5bd", "#495057"),
            text_color=("#212529", "#ffffff"),
            width=90,
            command=self.destroy
        ).pack(side="right", padx=8, pady=8)

    def _abrir_captura(self):
        if self.ruta_captura and os.path.exists(self.ruta_captura):
            try:
                os.startfile(self.ruta_captura)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la captura: {e}")
        else:
            messagebox.showinfo("Captura no disponible", "No se encontró archivo de captura asociado.")

    def _abrir_carpeta_evidencias(self):
        if self.on_open_evidence:
            self.on_open_evidence(self.mailbox, self.fecha_hora, self.servicio)
        else:
            servicio_clean = str(self.servicio).upper()
            carpeta_base = "Evidencias_QA_OTT" if "OTT" in servicio_clean else "Evidencias_QA_Fibra"
            if os.path.exists(carpeta_base):
                os.startfile(carpeta_base)

    def _reenviar_cola(self):
        if self.on_requeue:
            self.on_requeue(self.datos)
            self.destroy()

    def _copiar_resumen(self):
        lineas = [
            f"=== FICHA DE CUENTA G.I.D.E.O.N. ===",
            f"Fecha/Hora: {self.fecha_hora}",
            f"Servicio: {self.servicio}",
            f"Estado: {self.datos.get('estado', '')}",
            f"Titular: {self.datos.get('nombre_o_empresa', '')}",
            f"Doc/RIF: {self.datos.get('documento_rif', '')}",
            f"N° Cliente: {self.datos.get('id_cliente', '')}",
            f"Email: {self.datos.get('email', '')}",
            f"Teléfono: {self.datos.get('telefono', '')}",
            f"Ubicación: {self.datos.get('ubicacion', '')}",
            f"Plan: {self.datos.get('plan', '')}",
            f"Duración: {self.datos.get('tiempo_total_segundos', '')}s",
            f"Desglose: {self.datos.get('desglose_tiempos', '')}",
        ]
        texto = "\n".join(lineas)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        messagebox.showinfo("Copiado", "✅ Ficha completa copiada al portapapeles.")


def mostrar_menu_contextual(
    tree: tk.Misc,
    event: tk.Event,
    datos_fila: Dict[str, Any],
    callbacks: Optional[Dict[str, Callable]] = None,
) -> None:
    """
    Despliega un menú contextual moderno en la posición del puntero.
    """
    callbacks = callbacks or {}

    apariencia = ctk.get_appearance_mode().lower()
    if apariencia == "dark":
        bg = "#25262b"
        fg = "#f8f9fa"
        active_bg = "#ff7800"
        active_fg = "#ffffff"
    else:
        bg = "#ffffff"
        fg = "#212529"
        active_bg = "#ff7800"
        active_fg = "#ffffff"

    menu = tk.Menu(
        tree,
        tearoff=False,
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=active_fg,
        bd=1,
        relief="solid",
        font=("Segoe UI", 9)
    )

    id_cliente = str(datos_fila.get("id_cliente", "")).strip()
    email = str(datos_fila.get("email", "")).strip()
    doc_rif = str(datos_fila.get("documento_rif", "")).strip()
    estado_raw = str(datos_fila.get("estado", "")).upper()
    es_error = "EXITOSO" not in estado_raw

    # 1. Ver Ficha (Acción primaria)
    if callbacks.get("ver_ficha"):
        menu.add_command(
            label="🔍 Ver Ficha Completa y Diagnóstico (Enter)",
            command=lambda: callbacks["ver_ficha"](datos_fila)
        )

    menu.add_separator()

    # 2. Copias rápidas
    if id_cliente and id_cliente not in ["-", "N/A", "None"]:
        menu.add_command(
            label=f"📋 Copiar ID de Cliente ({id_cliente})",
            command=lambda: _copiar_clipboard(tree, id_cliente)
        )

    if email and email not in ["-", "N/A", "None"]:
        menu.add_command(
            label=f"📧 Copiar Correo ({email.split('@')[0]})",
            command=lambda: _copiar_clipboard(tree, email)
        )

    if doc_rif and doc_rif not in ["-", "N/A", "None"]:
        menu.add_command(
            label=f"🪪 Copiar Cédula / RIF ({doc_rif})",
            command=lambda: _copiar_clipboard(tree, doc_rif)
        )

    menu.add_separator()

    # 3. Evidencias y Capturas
    if callbacks.get("abrir_evidencias"):
        menu.add_command(
            label="📁 Abrir Carpeta de Evidencias",
            command=lambda: callbacks["abrir_evidencias"](datos_fila)
        )

    if es_error and callbacks.get("ver_captura"):
        menu.add_command(
            label="📸 Ver Captura del Fallo",
            command=lambda: callbacks["ver_captura"](datos_fila)
        )

    # 4. Reenviar a Cola
    if callbacks.get("reenviar"):
        menu.add_separator()
        menu.add_command(
            label="🔁 Reenviar esta cuenta a la Cola",
            command=lambda: callbacks["reenviar"](datos_fila)
        )

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def _copiar_clipboard(widget: tk.Misc, texto: str):
    widget.clipboard_clear()
    widget.clipboard_append(texto)
    widget.update()
