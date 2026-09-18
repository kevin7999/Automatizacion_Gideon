import sys
import os
import time
import re
import json
import csv
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from core.config import (
    CONFIG_FILE, DEFAULT_CONFIG, cargar_configuracion, guardar_configuracion
)
from core.catalogos import (
    ARCHIVO_PLANES, ARCHIVO_DIRECCIONES, cargar_catalogo_planes, cargar_catalogo_direcciones
)
from core.correlativos import (
    leer_correlativo_actual, obtener_siguiente_correlativo, actualizar_correlativo_manual
)
from core.generadores import limpiar_texto_crm
from automation.worker import crear_cuenta_individual

CATALOGO_PLANES = cargar_catalogo_planes()
CATALOGO_DIRECCIONES = cargar_catalogo_direcciones()

class AppGideon(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🤖 G.I.D.E.O.N. v3.0 | Simplefibra FTTH Automation Hub")
        self.geometry("1120x840")
        self.minsize(1100, 820)
        self.resizable(True, True)

        self.config_sys = cargar_configuracion()
        tema_inicial = self.config_sys.get("tema_apariencia", "Dark")
        ctk.set_appearance_mode(tema_inicial)

        self.matriz_cuentas = []
        self.fallidas_tanda_actual = []
        self.cancel_event = threading.Event()

        # Métricas KPIs
        self.kpi_total = 0
        self.kpi_ejecucion = 0
        self.kpi_exito = 0
        self.kpi_fallo = 0

        # --- SISTEMA DE PESTAÑAS (TABVIEW ESTILO SIMPLETV) ---
        self.tabview = ctk.CTkTabview(
            self,
            command=self.al_cambiar_pestana,
            corner_radius=10,
            fg_color=("#f8f9fa", "#141517"),
            segmented_button_selected_color="#ff7800",
            segmented_button_selected_hover_color="#e66a00",
            segmented_button_unselected_color=("#e9ecef", "#212529"),
            segmented_button_unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff")
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_control = self.tabview.add("🚀 Centro de Control")
        self.tab_reportes = self.tabview.add("📊 Historial & Reportes")
        self.tab_config = self.tabview.add("⚙️ Configuración")

        # Construir cada pestaña
        self.build_tab_control()
        self.build_tab_reportes()
        self.build_tab_config()

        # Inicializar tarjeta de previsualización del plan
        self.actualizar_detalle_plan_ui()

    def al_cambiar_pestana(self):
        pestana_actual = self.tabview.get()
        if "Historial" in pestana_actual and hasattr(self, 'cargar_historial_reporte'):
            self.cargar_historial_reporte()

    # -------------------------------------------------------------
    # 🚀 PESTAÑA 1: CENTRO DE CONTROL (SIMPLETV ORANGE & WHITE)
    # -------------------------------------------------------------
    def build_tab_control(self):
        # 1. TARJETAS DE MÉTRICAS KPI (HEADER PRO)
        self.frame_kpis = ctk.CTkFrame(self.tab_control, fg_color="transparent")
        self.frame_kpis.pack(fill="x", padx=5, pady=(0, 10))

        self.card_total = self.crear_card_kpi(self.frame_kpis, "Total en Cola", "0", ("#d9480f", "#ff7800"), icono="📦")
        self.card_total.pack(side="left", fill="x", expand=True, padx=4)

        self.card_ejecucion = self.crear_card_kpi(self.frame_kpis, "En Ejecución", "0", ("#c2410c", "#ffa94d"), icono="⏳")
        self.card_ejecucion.pack(side="left", fill="x", expand=True, padx=4)

        self.card_exito = self.crear_card_kpi(self.frame_kpis, "Exitosas", "0", ("#2b8a3e", "#51cf66"), icono="✅")
        self.card_exito.pack(side="left", fill="x", expand=True, padx=4)

        self.card_fallo = self.crear_card_kpi(self.frame_kpis, "Fallidas", "0", ("#c92a2a", "#ff6b6b"), icono="❌")
        self.card_fallo.pack(side="left", fill="x", expand=True, padx=4)

        # 2. CUERPO PRINCIPAL (IZQ: FORMULARIO, DER: COLA Y CONSOLA)
        self.frame_body = ctk.CTkFrame(self.tab_control, fg_color="transparent")
        self.frame_body.pack(fill="both", expand=True)

        # Panel Izquierdo: Formularios & Presets (Scrollable y estructurado en bloques)
        self.frame_left = ctk.CTkScrollableFrame(self.frame_body, width=370, corner_radius=12, fg_color=("#f1f3f5", "#141517"))
        self.frame_left.pack(side="left", fill="both", expand=False, padx=(0, 5), pady=5)

        # --- BLOQUE 1: PRESETS RÁPIDOS ---
        card_presets = ctk.CTkFrame(
            self.frame_left,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        card_presets.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(
            card_presets,
            text="⚡ Presets Rápidos de Prueba",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#d9480f", "#ff922b")
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.cmb_preset = ctk.CTkOptionMenu(
            card_presets,
            values=[
                "Seleccionar Preset...",
                "Matriz 6 Perfiles (3 Estados)",
                "⚡ Matriz 6 Perfiles - Caracas",
                "⚡ Matriz 6 Perfiles - Miranda",
                "⚡ Matriz 6 Perfiles - Nueva Esparta",
                "Solo 3 Jurídicos",
                "Solo 3 Naturales"
            ],
            command=self.aplicar_preset,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            height=32
        )
        self.cmb_preset.pack(fill="x", padx=12, pady=(0, 8))

        # Botones de JSON en fila compacta
        frame_json_btns = ctk.CTkFrame(card_presets, fg_color="transparent")
        frame_json_btns.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            frame_json_btns,
            text="💾 Guardar JSON",
            command=self.guardar_perfil_json,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            frame_json_btns,
            text="📂 Cargar JSON",
            command=self.cargar_perfil_json,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28
        ).pack(side="right", fill="x", expand=True, padx=(3, 0))

        # --- BLOQUE 2: FORMULARIO DE CLIENTE Y SERVICIO ---
        card_form = ctk.CTkFrame(
            self.frame_left,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        card_form.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(
            card_form,
            text="➕ Configuración de Cuenta & Plan",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#d9480f", "#ff922b")
        ).pack(anchor="w", padx=12, pady=(10, 8))

        # Tipo de Persona (Segmented Button moderno)
        ctk.CTkLabel(card_form, text="Tipo de Cliente:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(2, 2))
        self.cmb_persona = ctk.CTkSegmentedButton(
            card_form,
            values=["Persona natural", "Persona jurídica"],
            command=self.actualizar_subopciones,
            selected_color="#ff7800",
            selected_hover_color="#e66a00",
            unselected_color=("#e9ecef", "#25262b"),
            unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            height=30
        )
        self.cmb_persona.set("Persona natural")
        self.cmb_persona.pack(fill="x", padx=12, pady=(0, 8))

        # Cuadrícula para Documento y Ubicación (2 columnas)
        frame_grid_fields = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_grid_fields.pack(fill="x", padx=12, pady=(0, 8))
        frame_grid_fields.grid_columnconfigure(0, weight=1)
        frame_grid_fields.grid_columnconfigure(1, weight=1)

        frame_ub_hdr = ctk.CTkFrame(frame_grid_fields, fg_color="transparent")
        frame_ub_hdr.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ctk.CTkLabel(frame_ub_hdr, text="Ubicación:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")
        ctk.CTkButton(frame_ub_hdr, text="📍 CSV", width=48, height=18, command=self.abrir_csv_direcciones, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=9, weight="bold")).pack(side="right")

        self.cmb_doc = ctk.CTkOptionMenu(
            frame_grid_fields,
            values=["Venezuelan", "Foreigner", "Passport"],
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            height=30
        )
        self.cmb_doc.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(2, 0))

        self.cmb_ubicacion = ctk.CTkOptionMenu(
            frame_grid_fields,
            values=list(CATALOGO_DIRECCIONES.keys()) if CATALOGO_DIRECCIONES else ["Caracas", "Miranda", "Nueva Esparta"],
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            height=30
        )
        self.cmb_ubicacion.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(2, 0))

        # Encabezado Plan y Herramientas del Catálogo
        frame_plan_hdr = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_plan_hdr.pack(fill="x", padx=12, pady=(6, 4))

        ctk.CTkLabel(frame_plan_hdr, text="Plan y Equipo:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")

        # Botón de Recargar Catálogo estilizado y comprensible
        ctk.CTkButton(
            frame_plan_hdr,
            text="🔄 Actualizar",
            width=92,
            height=24,
            command=self.recargar_catalogo_ui,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(side="right", padx=(4, 0))

        # Botón de Abrir CSV
        ctk.CTkButton(
            frame_plan_hdr,
            text="📂 CSV",
            width=62,
            height=24,
            command=self.abrir_csv_catalogo,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(side="right")

        # Selector de Modalidad (Compra vs Alquiler)
        self.cmb_modalidad = ctk.CTkSegmentedButton(
            card_form,
            values=["🛒 Compra", "🔄 Alquiler"],
            command=self.filtrar_planes,
            selected_color="#ff7800",
            selected_hover_color="#e66a00",
            unselected_color=("#e9ecef", "#25262b"),
            unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            height=30
        )
        self.cmb_modalidad.set("🛒 Compra")
        self.cmb_modalidad.pack(fill="x", padx=12, pady=(0, 6))

        # Filtro de Velocidad para agrupar planes
        self.cmb_filtro_vel = ctk.CTkOptionMenu(
            card_form,
            values=["Velocidad: Todas", "400 Mbps", "500 Mbps", "600 Mbps", "1000 Mbps", "Otras"],
            command=self.filtrar_planes,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11),
            height=28
        )
        self.cmb_filtro_vel.pack(fill="x", padx=12, pady=(0, 5))

        # Lista Desplazable de Planes (Cards) en lugar de OptionMenu
        self.frame_lista_planes = ctk.CTkScrollableFrame(
            card_form,
            height=140,
            fg_color=("#e9ecef", "#1e1f23"),
            corner_radius=8
        )
        self.frame_lista_planes.pack(fill="x", padx=12, pady=(0, 6))
        
        self.plan_seleccionado_id = None
        self.tarjetas_planes = {}

        # 🏷️ Tarjeta de Previsualización en Tiempo Real (Live Plan Card)
        self.frame_plan_card = ctk.CTkFrame(
            card_form,
            fg_color=("#f1f3f5", "#141517"),
            corner_radius=8,
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        self.frame_plan_card.pack(fill="x", padx=12, pady=(0, 8))

        self.lbl_card_paquete = ctk.CTkLabel(self.frame_plan_card, text="📦 Paquete: -", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#d9480f", "#ff922b"), anchor="w")
        self.lbl_card_paquete.pack(fill="x", padx=8, pady=(4, 1))

        self.lbl_card_promo = ctk.CTkLabel(self.frame_plan_card, text="🏷️ Promo: -", font=ctk.CTkFont(size=10), text_color=("#495057", "#ced4da"), anchor="w")
        self.lbl_card_promo.pack(fill="x", padx=8, pady=1)

        self.lbl_card_router = ctk.CTkLabel(self.frame_plan_card, text="📡 Router: -", font=ctk.CTkFont(size=10), text_color=("#1864ab", "#74c0fc"), anchor="w")
        self.lbl_card_router.pack(fill="x", padx=8, pady=(1, 4))

        # Checkbox para habilitar o deshabilitar promociones
        self.chk_aplicar_promo = ctk.CTkCheckBox(
            card_form,
            text="Aplicar Promoción del Catálogo",
            command=self.actualizar_detalle_plan_ui,
            fg_color="#ff7800",
            hover_color="#e66a00",
            text_color=("#212529", "#f8f9fa"),
            font=ctk.CTkFont(size=11, weight="bold"),
            checkbox_width=18,
            checkbox_height=18
        )
        self.chk_aplicar_promo.select()
        self.chk_aplicar_promo.pack(anchor="w", padx=12, pady=(0, 8))

        # Fila de Cantidad
        frame_cant = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_cant.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(frame_cant, text="Cantidad de cuentas:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")
        self.spn_cantidad = ctk.CTkEntry(
            frame_cant,
            placeholder_text="1",
            width=65,
            height=28,
            fg_color=("#ffffff", "#25262b"),
            border_color=("#ced4da", "#373a40"),
            text_color=("#212529", "#f8f9fa")
        )
        self.spn_cantidad.insert(0, "1")
        self.spn_cantidad.pack(side="right")

        # Botones principales de adición
        ctk.CTkButton(
            card_form,
            text="➕ Agregar a la Cola",
            command=self.agregar_lote,
            fg_color="#ff7800",
            hover_color="#e66a00",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34
        ).pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkButton(
            card_form,
            text="⚖️ Agregar Par Mixto (1 Nat + 1 Jur)",
            command=self.agregar_par_mixto,
            fg_color=("#e8590c", "#d9480f"),
            hover_color="#c92a2a",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=30
        ).pack(fill="x", padx=12, pady=(0, 12))

        # --- PANEL DERECHO: COLA, EJECUCIÓN Y CONSOLA ---
        self.frame_right = ctk.CTkFrame(self.frame_body, corner_radius=12, fg_color="transparent")
        self.frame_right.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

        # 1. Card de Cola de Cuentas
        card_cola = ctk.CTkFrame(
            self.frame_right,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        card_cola.pack(fill="x", padx=0, pady=(0, 8))

        frame_cola_hdr = ctk.CTkFrame(card_cola, fg_color="transparent")
        frame_cola_hdr.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            frame_cola_hdr,
            text="📋 Cola de Cuentas Programadas",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#d9480f", "#ff7800")
        ).pack(side="left")

        self.lbl_cola_badge = ctk.CTkLabel(
            frame_cola_hdr,
            text="0 en espera",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#495057", "#adb5bd")
        )
        self.lbl_cola_badge.pack(side="right")

        self.frame_cola_scroll = ctk.CTkScrollableFrame(
            card_cola,
            height=165,
            fg_color=("#f1f3f5", "#141517"),
            corner_radius=8
        )
        self.frame_cola_scroll.pack(fill="x", padx=10, pady=(0, 8))

        # 2. Card de Opciones y Acciones de Ejecución
        card_exec = ctk.CTkFrame(
            self.frame_right,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        card_exec.pack(fill="x", padx=0, pady=(0, 8))

        frame_exec_inner = ctk.CTkFrame(card_exec, fg_color="transparent")
        frame_exec_inner.pack(fill="x", padx=10, pady=8)

        # Hilos a la izquierda
        ctk.CTkLabel(frame_exec_inner, text="Concurrencia:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(0, 4))
        self.cmb_hilos = ctk.CTkOptionMenu(
            frame_exec_inner,
            values=["1", "2", "3", "4"],
            width=65,
            height=28,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff")
        )
        self.cmb_hilos.set(str(self.config_sys.get("hilos_simultaneos", 2)))
        self.cmb_hilos.pack(side="left", padx=(0, 10))

        # Limpiar
        ctk.CTkButton(
            frame_exec_inner,
            text="🧹 Limpiar",
            command=self.limpiar_cola,
            fg_color=("#e9ecef", "#343a40"),
            hover_color=("#dee2e6", "#495057"),
            text_color=("#212529", "#ffffff"),
            width=85,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(side="left", padx=(0, 8))

        # Cancelar
        self.btn_cancelar = ctk.CTkButton(
            frame_exec_inner,
            text="⏹️ CANCELAR",
            command=self.cancelar_proceso,
            fg_color="#c92a2a",
            hover_color="#a61e1e",
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            state="disabled",
            width=100,
            height=30
        )
        self.btn_cancelar.pack(side="left", padx=(0, 8))

        # Reintentar fallidas de la tanda activa
        self.btn_reintentar_tanda = ctk.CTkButton(
            frame_exec_inner,
            text="🔁 Reintentar (0)",
            command=self.reintentar_fallidas_tanda,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11, weight="bold"),
            state="disabled",
            width=125,
            height=30
        )
        self.btn_reintentar_tanda.pack(side="left")

        # Iniciar masivo (destacado)
        self.btn_iniciar = ctk.CTkButton(
            frame_exec_inner,
            text="🚀 INICIAR PROCESAMIENTO MASIVO",
            command=self.iniciar_proceso,
            fg_color="#ff7800",
            hover_color="#e66a00",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34
        )
        self.btn_iniciar.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # 3. Card de Consola de Monitoreo Pro (Sólo lectura)
        card_consola = ctk.CTkFrame(
            self.frame_right,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        card_consola.pack(fill="both", expand=True, padx=0, pady=0)

        frame_consola_hdr = ctk.CTkFrame(card_consola, fg_color="transparent")
        frame_consola_hdr.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            frame_consola_hdr,
            text="💻 Consola de Monitoreo en Tiempo Real",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#212529", "#f8f9fa")
        ).pack(side="left")

        self.lbl_console_status = ctk.CTkLabel(
            frame_consola_hdr,
            text="🟢 En Línea",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#2b8a3e", "#51cf66")
        )
        self.lbl_console_status.pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            frame_consola_hdr,
            text="🧹 Limpiar",
            width=65,
            height=22,
            command=self.limpiar_log_consola,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            frame_consola_hdr,
            text="📋 Copiar",
            width=60,
            height=22,
            command=self.copiar_log_consola,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            card_consola,
            height=150,
            fg_color=("#18191c", "#0d0e11"),
            text_color="#ff922b",
            font=ctk.CTkFont(family="monospace", size=11),
            corner_radius=6
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt_log.configure(state="disabled")

    def copiar_log_consola(self):
        try:
            texto = self.txt_log.get("1.0", "end").strip()
            if texto:
                self.clipboard_clear()
                self.clipboard_append(texto)
                self.log_salida("📋 Registro de consola copiado al portapapeles.")
        except Exception as e:
            self.log_salida(f"⚠️ Error al copiar log: {e}")

    def limpiar_log_consola(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        self.log_salida("🧹 Consola reiniciada.")

    def crear_card_kpi(self, parent, titulo, valor_inicial, color_acento, icono="📦"):
        card = ctk.CTkFrame(
            parent,
            fg_color=("#ffffff", "#1e1f23"),
            corner_radius=10,
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        hdr_frame = ctk.CTkFrame(card, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=12, pady=(8, 0))

        lbl_badge = ctk.CTkLabel(
            hdr_frame,
            text=f"{icono} {titulo.upper()}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#495057", "#adb5bd")
        )
        lbl_badge.pack(side="left")

        lbl_val = ctk.CTkLabel(
            card,
            text=str(valor_inicial),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=color_acento
        )
        lbl_val.pack(anchor="w", padx=12, pady=(2, 8))
        card.lbl_val = lbl_val
        return card

    def update_kpis_ui(self, total=None, ejecucion=None, exito=None, fallo=None):
        def _actualizar():
            if total is not None: self.kpi_total = total
            if ejecucion is not None: self.kpi_ejecucion += ejecucion
            if exito is not None: self.kpi_exito += exito
            if fallo is not None: self.kpi_fallo += fallo

            self.card_total.lbl_val.configure(text=str(len(self.matriz_cuentas) if total is None else total))
            self.card_ejecucion.lbl_val.configure(text=str(max(0, self.kpi_ejecucion)))
            self.card_exito.lbl_val.configure(text=str(self.kpi_exito))
            self.card_fallo.lbl_val.configure(text=str(self.kpi_fallo))
        self.after(0, _actualizar)

    # -------------------------------------------------------------
    # 📊 PESTAÑA 2: HISTORIAL Y REPORTES AVANZADO (SIMPLETV THEME)
    # -------------------------------------------------------------
    def build_tab_reportes(self):
        # 1. HEADER CON TARJETAS KPI DE HISTORIAL
        self.frame_kpis_historial = ctk.CTkFrame(self.tab_reportes, fg_color="transparent")
        self.frame_kpis_historial.pack(fill="x", padx=10, pady=(0, 8))

        self.card_hist_total = self.crear_card_kpi(self.frame_kpis_historial, "Total Procesadas", "0", ("#d9480f", "#ff7800"), icono="📦")
        self.card_hist_total.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_exito = self.crear_card_kpi(self.frame_kpis_historial, "Cuentas Exitosas", "0", ("#2b8a3e", "#51cf66"), icono="✅")
        self.card_hist_exito.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_tasa = self.crear_card_kpi(self.frame_kpis_historial, "Tasa de Éxito", "0%", ("#d9480f", "#ff7800"), icono="📈")
        self.card_hist_tasa.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_fallo = self.crear_card_kpi(self.frame_kpis_historial, "Cuentas Fallidas", "0", ("#c92a2a", "#ff6b6b"), icono="❌")
        self.card_hist_fallo.pack(side="left", fill="x", expand=True, padx=4)

        # 2. BARRA DE HERRAMIENTAS: BÚSQUEDA Y FILTROS
        frame_toolbar = ctk.CTkFrame(
            self.tab_reportes,
            corner_radius=10,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        frame_toolbar.pack(fill="x", padx=10, pady=(0, 8))

        # Buscador en vivo
        ctk.CTkLabel(frame_toolbar, text="🔍", font=ctk.CTkFont(size=14)).pack(side="left", padx=(12, 2), pady=8)
        self.entry_busqueda_hist = ctk.CTkEntry(
            frame_toolbar,
            placeholder_text="Buscar por nombre, correo, cédula/RIF, plan o estado...",
            width=360,
            fg_color=("#ffffff", "#25262b"),
            border_color=("#ced4da", "#373a40"),
            text_color=("#212529", "#f8f9fa")
        )
        self.entry_busqueda_hist.pack(side="left", padx=5, pady=8)
        self.entry_busqueda_hist.bind("<KeyRelease>", lambda e: self.filtrar_historial())

        # Filtro de Estado
        ctk.CTkLabel(frame_toolbar, text="Estado:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(15, 5), pady=8)
        self.cmb_filtro_estado = ctk.CTkOptionMenu(
            frame_toolbar,
            values=["Todos los Estados", "✅ Solo Exitosos", "❌ Solo Errores"],
            command=lambda v: self.filtrar_historial(),
            width=160,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff")
        )
        self.cmb_filtro_estado.pack(side="left", padx=5, pady=8)

        # Botón Recargar
        ctk.CTkButton(
            frame_toolbar,
            text="🔄 Recargar",
            command=self.cargar_historial_reporte,
            fg_color="#ff7800",
            hover_color="#e66a00",
            text_color="#ffffff",
            font=ctk.CTkFont(weight="bold"),
            width=110
        ).pack(side="right", padx=10, pady=8)

        # 3. TABLA MODERNA TREEVIEW CON ESTILO DINÁMICO
        frame_tabla_container = ctk.CTkFrame(
            self.tab_reportes,
            corner_radius=10,
            fg_color=("#ffffff", "#141517"),
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        frame_tabla_container.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        columnas = ("fecha", "tipo", "documento", "titular", "email", "telefono", "ubicacion", "plan", "estado")
        self.tree_historial = ttk.Treeview(frame_tabla_container, columns=columnas, show="headings", style="Historial.Treeview", selectmode="extended")

        # Configurar Columnas
        self.tree_historial.heading("fecha", text="🕒 Fecha / Hora")
        self.tree_historial.heading("tipo", text="👤 Tipo")
        self.tree_historial.heading("documento", text="🪪 Documento / RIF")
        self.tree_historial.heading("titular", text="🏷️ Titular / Empresa")
        self.tree_historial.heading("email", text="📧 Correo (Mailbox)")
        self.tree_historial.heading("telefono", text="📱 Teléfono")
        self.tree_historial.heading("ubicacion", text="📍 Ubicación")
        self.tree_historial.heading("plan", text="📦 Plan & Promo")
        self.tree_historial.heading("estado", text="⚡ Estado")

        self.tree_historial.column("fecha", width=130, anchor="center")
        self.tree_historial.column("tipo", width=110, anchor="center")
        self.tree_historial.column("documento", width=130, anchor="w")
        self.tree_historial.column("titular", width=160, anchor="w")
        self.tree_historial.column("email", width=210, anchor="w")
        self.tree_historial.column("telefono", width=105, anchor="center")
        self.tree_historial.column("ubicacion", width=95, anchor="center")
        self.tree_historial.column("plan", width=160, anchor="w")
        self.tree_historial.column("estado", width=220, anchor="w")

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(frame_tabla_container, orient="vertical", command=self.tree_historial.yview)
        scrollbar_x = ttk.Scrollbar(frame_tabla_container, orient="horizontal", command=self.tree_historial.xview)
        self.tree_historial.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.tree_historial.pack(fill="both", expand=True)

        # Aplicar estilo ttk y tags según el tema actual (Light/Dark)
        self.actualizar_estilo_treeview()

        # Doble clic en fila para abrir carpeta de evidencias
        self.tree_historial.bind("<Double-1>", lambda e: self.abrir_evidencia_seleccionada())

        # 4. BOTONES DE ACCIONES INFERIORES
        frame_bottom = ctk.CTkFrame(self.tab_reportes, fg_color="transparent")
        frame_bottom.pack(fill="x", padx=10, pady=(0, 5))

        def _sel_todos():
            self.tree_historial.selection_set(self.tree_historial.get_children())

        def _desel_todos():
            self.tree_historial.selection_remove(self.tree_historial.get_children())

        ctk.CTkButton(frame_bottom, text="☑️ Todos", width=62, command=_sel_todos, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="⬜ Ninguno", width=68, command=_desel_todos, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="📸 Evidencias", command=self.abrir_evidencia_seleccionada, fg_color="#ff7800", hover_color="#e66a00", text_color="#ffffff", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="🔁 Reenviar a la Cola", command=self.reintentar_cuenta_historial_seleccionada, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="📁 Carpeta General", command=self.abrir_carpeta_evidencias_general, fg_color=("#e9ecef", "#343a40"), hover_color=("#dee2e6", "#495057"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="📂 CSV Excel", command=self.abrir_archivo_csv, fg_color=("#e9ecef", "#343a40"), hover_color=("#dee2e6", "#495057"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="📋 Copiar Correo", command=self.copiar_correo_seleccionado, fg_color=("#e8590c", "#d9480f"), hover_color=("#c92a2a", "#c92a2a"), text_color="#ffffff", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)

        self.datos_historial_raw = []
        self.cargar_historial_reporte()

    def cargar_historial_reporte(self):
        self.datos_historial_raw = []
        archivo_csv = "cuentas_creadas.csv"
        total_cuentas = 0
        exitosas = 0
        fallidas = 0

        if os.path.exists(archivo_csv):
            try:
                with open(archivo_csv, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    filas = list(reader)
                    if filas:
                        for r in filas[1:]:
                            if len(r) >= 9:
                                total_cuentas += 1
                                estado = r[8].strip()
                                if "EXITOSO" in estado.upper():
                                    exitosas += 1
                                else:
                                    fallidas += 1
                                self.datos_historial_raw.append(r)
            except Exception as e:
                print(f"Error leyendo cuentas_creadas.csv: {e}")

        # Invertir para mostrar las más recientes arriba
        self.datos_historial_raw.reverse()

        tasa_pct = f"{(exitosas / total_cuentas * 100):.1f}%" if total_cuentas > 0 else "0%"
        self.card_hist_total.lbl_val.configure(text=str(total_cuentas))
        self.card_hist_exito.lbl_val.configure(text=str(exitosas))
        self.card_hist_tasa.lbl_val.configure(text=tasa_pct)
        self.card_hist_fallo.lbl_val.configure(text=str(fallidas))

        self.filtrar_historial()

    def filtrar_historial(self):
        # Limpiar tabla
        for item in self.tree_historial.get_children():
            self.tree_historial.delete(item)

        texto_busq = self.entry_busqueda_hist.get().strip().lower() if hasattr(self, 'entry_busqueda_hist') else ""
        filtro_estado = self.cmb_filtro_estado.get() if hasattr(self, 'cmb_filtro_estado') else "Todos los Estados"

        idx = 0
        for r in self.datos_historial_raw:
            # r: [0:Fecha_Hora, 1:Tipo_Persona, 2:Documento_RIF, 3:Nombre_o_Empresa, 4:Email, 5:Telefono, 6:Ubicacion, 7:Plan, 8:Estado]
            estado = r[8].strip()
            es_exitoso = "EXITOSO" in estado.upper()

            # Filtro por estado
            if filtro_estado == "✅ Solo Exitosos" and not es_exitoso:
                continue
            if filtro_estado == "❌ Solo Errores" and es_exitoso:
                continue

            # Filtro por búsqueda de texto
            if texto_busq:
                linea_unida = " ".join(r).lower()
                if texto_busq not in linea_unida:
                    continue

            tag_estado = "tag_exito" if es_exitoso else "tag_error"
            tag_fila = "fila_par" if idx % 2 == 0 else "fila_impar"

            valores = (
                r[0], # Fecha
                r[1], # Tipo
                r[2], # Documento
                r[3], # Titular / Empresa
                r[4], # Email
                r[5], # Telefono
                r[6], # Ubicacion
                r[7], # Plan
                r[8]  # Estado
            )
            self.tree_historial.insert("", "end", values=valores, tags=(tag_fila, tag_estado))
            idx += 1

    def abrir_evidencia_seleccionada(self):
        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor selecciona una cuenta de la lista para ver sus evidencias.")
            return

        item = self.tree_historial.item(seleccion[0])
        valores = item["values"]
        if not valores or len(valores) < 5:
            return

        fecha_hora = str(valores[0])
        email = str(valores[4])
        mailbox = email.split("@")[0].strip()
        fecha_solo = fecha_hora.split(" ")[0].strip()

        # Buscar carpeta específica de evidencias
        ruta_directa = os.path.join("Evidencias_QA", fecha_solo, mailbox)
        if os.path.exists(ruta_directa):
            os.startfile(ruta_directa)
            return

        # Búsqueda recursiva si la fecha difiere
        encontrado = False
        if os.path.exists("Evidencias_QA"):
            for root, dirs, files in os.walk("Evidencias_QA"):
                if os.path.basename(root).lower() == mailbox.lower():
                    os.startfile(root)
                    encontrado = True
                    break

        if not encontrado:
            if os.path.exists("Evidencias_QA"):
                os.startfile("Evidencias_QA")
            else:
                messagebox.showinfo("Evidencias", f"No se encontró carpeta de evidencias para la cuenta: {mailbox}")

    def abrir_carpeta_evidencias_general(self):
        if os.path.exists("Evidencias_QA"):
            os.startfile("Evidencias_QA")
        else:
            os.makedirs("Evidencias_QA", exist_ok=True)
            os.startfile("Evidencias_QA")

    def copiar_correo_seleccionado(self):
        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor selecciona una fila para copiar su correo.")
            return

        item = self.tree_historial.item(seleccion[0])
        valores = item["values"]
        if valores and len(valores) >= 5:
            email = str(valores[4]).strip()
            self.clipboard_clear()
            self.clipboard_append(email)
            messagebox.showinfo("Copiado", f"Correo copiado al portapapeles:\n{email}")

    def abrir_archivo_csv(self):
        archivo = "cuentas_creadas.csv"
        if os.path.exists(archivo):
            if sys.platform == "win32":
                os.startfile(archivo)
            elif sys.platform == "darwin":
                subprocess.call(["open", archivo])
            else:
                subprocess.call(["xdg-open", archivo])
        else:
            messagebox.showinfo("Información", "El archivo cuentas_creadas.csv aún no ha sido creado.")

    def reintentar_cuenta_historial_seleccionada(self):
        # 1. Proteger ejecución activa: Si hay pruebas corriendo, no interferir en la cola
        if hasattr(self, 'btn_iniciar') and self.btn_iniciar.cget("state") == "disabled":
            messagebox.showwarning(
                "Procesamiento en Curso",
                "Hay pruebas ejecutándose en este momento.\n\nEspera a que finalice la tanda actual para reenviar cuentas a la cola sin interferir en los navegadores activos."
            )
            return

        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor selecciona al menos una cuenta en la tabla para reenviarla a la cola.")
            return

        agregadas = 0
        for item_id in seleccion:
            item = self.tree_historial.item(item_id)
            valores = item.get("values", [])
            if not valores or len(valores) < 8:
                continue

            tipo_persona = str(valores[1]).strip()
            doc_str = str(valores[2]).strip()
            doc_tipo = doc_str.split(":")[0].strip() if ":" in doc_str else ("Venezuelan" if tipo_persona == "Persona natural" else "Legal")
            ubicacion = str(valores[6]).strip()
            plan_raw = str(valores[7]).strip()

            sin_promo = "[Sin Promo]" in plan_raw
            plan_nombre = plan_raw.replace("[Sin Promo]", "").strip()

            if plan_nombre not in CATALOGO_PLANES:
                posibles = [k for k in CATALOGO_PLANES.keys() if plan_nombre.lower() in k.lower() or k.lower() in plan_nombre.lower()]
                if posibles:
                    plan_nombre = posibles[0]
                else:
                    plan_nombre = list(CATALOGO_PLANES.keys())[0] if CATALOGO_PLANES else "Compra: 400 mbps + Gold"

            item_nuevo = {
                "tipo_persona": tipo_persona,
                "ubicacion": ubicacion,
                "plan_seleccionado": plan_nombre,
                "aplicar_promocion": not sin_promo
            }
            if tipo_persona == "Persona natural":
                item_nuevo["tipo_doc"] = doc_tipo
            else:
                item_nuevo["tipo_rif"] = doc_tipo

            self.matriz_cuentas.append(self.preparar_item_cuenta(item_nuevo))
            agregadas += 1

        self.refrescar_vista_cola()
        self.log_salida(f"🔁 {agregadas} cuenta(s) del Historial reincorporadas a la cola con datos frescos. Ve al Centro de Control para procesarlas.")

    # -------------------------------------------------------------
    # ⚙️ PESTAÑA 3: CONFIGURACIÓN
    # -------------------------------------------------------------
    def build_tab_config(self):
        frame_box = ctk.CTkFrame(
            self.tab_config,
            corner_radius=12,
            fg_color=("#ffffff", "#1a1b1e"),
            border_width=1,
            border_color=("#dee2e6", "#2c2e33")
        )
        frame_box.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame_box,
            text="⚙️ Ajustes del Sistema y Preferencias",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ff7800"
        ).pack(anchor="w", padx=24, pady=(20, 15))

        # Formulario de ajustes
        form_frame = ctk.CTkFrame(frame_box, fg_color="transparent")
        form_frame.pack(fill="x", padx=24, pady=5)

        # 1. Apariencia y Tema Dual
        ctk.CTkLabel(form_frame, text="🎨 Apariencia / Tema:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        tema_actual = self.config_sys.get("tema_apariencia", "Dark")
        valor_defecto = "🌙 Modo Oscuro (Dark)" if tema_actual == "Dark" else "☀️ Modo Claro (Light)"
        self.seg_tema = ctk.CTkSegmentedButton(
            form_frame,
            values=["🌙 Modo Oscuro (Dark)", "☀️ Modo Claro (Light)"],
            command=self.cambiar_tema_ui,
            selected_color="#ff7800",
            selected_hover_color="#e66a00",
            unselected_color=("#e9ecef", "#2b2d31"),
            unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            height=32
        )
        self.seg_tema.set(valor_defecto)
        self.seg_tema.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(form_frame, text="Prefijo del Correo:").grid(row=1, column=0, sticky="w", pady=8)
        self.entry_prefijo = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_prefijo.insert(0, self.config_sys.get("prefijo_email", DEFAULT_CONFIG["prefijo_email"]))
        self.entry_prefijo.grid(row=1, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Dominio del Correo:").grid(row=2, column=0, sticky="w", pady=8)
        self.entry_dominio = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_dominio.insert(0, self.config_sys.get("dominio_email", DEFAULT_CONFIG["dominio_email"]))
        self.entry_dominio.grid(row=2, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Usuario de Login:").grid(row=3, column=0, sticky="w", pady=8)
        self.entry_usuario = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_usuario.insert(0, self.config_sys.get("usuario_login", DEFAULT_CONFIG["usuario_login"]))
        self.entry_usuario.grid(row=3, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Contraseña de Login:").grid(row=4, column=0, sticky="w", pady=8)
        self.entry_password = ctk.CTkEntry(form_frame, width=450, show="*", fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_password.insert(0, self.config_sys.get("password_login", DEFAULT_CONFIG["password_login"]))
        self.entry_password.grid(row=4, column=1, padx=10, pady=8)

        # Correlativo actual
        ctk.CTkLabel(form_frame, text="Contador de Correo Actual:").grid(row=5, column=0, sticky="w", pady=8)
        correlativo_actual = obtener_siguiente_correlativo() - 1
        self.entry_correlativo = ctk.CTkEntry(form_frame, width=200, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_correlativo.insert(0, str(correlativo_actual))
        self.entry_correlativo.grid(row=5, column=1, sticky="w", padx=10, pady=8)

        frame_actions_cfg = ctk.CTkFrame(frame_box, fg_color="transparent")
        frame_actions_cfg.pack(anchor="w", padx=24, pady=25)

        ctk.CTkButton(
            frame_actions_cfg,
            text="💾 Guardar Cambios",
            command=self.guardar_ajustes_ui,
            fg_color="#ff7800",
            hover_color="#e66a00",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            frame_actions_cfg,
            text="📂 Catálogo Planes (CSV)",
            command=self.abrir_csv_catalogo,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions_cfg,
            text="📍 Catálogo Ubicaciones (CSV)",
            command=self.abrir_csv_direcciones,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36
        ).pack(side="left", padx=5)

    def cambiar_tema_ui(self, valor):
        modo = "Dark" if "Oscuro" in valor else "Light"
        ctk.set_appearance_mode(modo)
        self.config_sys["tema_apariencia"] = modo
        guardar_configuracion(self.config_sys)
        self.actualizar_estilo_treeview(modo)
        self.log_salida(f"🎨 Tema visual cambiado a: {modo}")

    def actualizar_estilo_treeview(self, modo=None):
        if not modo:
            modo = self.config_sys.get("tema_apariencia", "Dark")
        style = ttk.Style()
        style.theme_use("clam")
        if modo == "Light":
            style.configure("Historial.Treeview",
                            background="#ffffff",
                            foreground="#212529",
                            fieldbackground="#ffffff",
                            rowheight=30,
                            borderwidth=0,
                            font=("Segoe UI", 9))
            style.configure("Historial.Treeview.Heading",
                            background="#e9ecef",
                            foreground="#d9480f",
                            relief="flat",
                            font=("Segoe UI", 9, "bold"))
            style.map("Historial.Treeview",
                      background=[('selected', '#ff7800')],
                      foreground=[('selected', '#ffffff')])
            style.map("Historial.Treeview.Heading",
                      background=[('active', '#dee2e6')])
            if hasattr(self, 'tree_historial'):
                self.tree_historial.tag_configure('fila_par', background='#ffffff')
                self.tree_historial.tag_configure('fila_impar', background='#f1f3f5')
                self.tree_historial.tag_configure('tag_exito', foreground='#2b8a3e')
                self.tree_historial.tag_configure('tag_error', foreground='#c92a2a')
        else:
            style.configure("Historial.Treeview",
                            background="#1a1b1e",
                            foreground="#f8f9fa",
                            fieldbackground="#1a1b1e",
                            rowheight=30,
                            borderwidth=0,
                            font=("Segoe UI", 9))
            style.configure("Historial.Treeview.Heading",
                            background="#25262b",
                            foreground="#ff7800",
                            relief="flat",
                            font=("Segoe UI", 9, "bold"))
            style.map("Historial.Treeview",
                      background=[('selected', '#ff7800')],
                      foreground=[('selected', '#ffffff')])
            style.map("Historial.Treeview.Heading",
                      background=[('active', '#2c2e33')])
            if hasattr(self, 'tree_historial'):
                self.tree_historial.tag_configure('fila_par', background='#1a1b1e')
                self.tree_historial.tag_configure('fila_impar', background='#212226')
                self.tree_historial.tag_configure('tag_exito', foreground='#51cf66')
                self.tree_historial.tag_configure('tag_error', foreground='#ff6b6b')

    def guardar_ajustes_ui(self):
        self.config_sys["prefijo_email"] = self.entry_prefijo.get().strip()
        self.config_sys["dominio_email"] = self.entry_dominio.get().strip()
        self.config_sys["usuario_login"] = self.entry_usuario.get().strip()
        self.config_sys["password_login"] = self.entry_password.get().strip()

        tema_sel = "Dark" if "Oscuro" in self.seg_tema.get() else "Light"
        self.config_sys["tema_apariencia"] = tema_sel

        try:
            nuevo_corr = int(self.entry_correlativo.get().strip())
            actualizar_correlativo_manual(nuevo_corr)
        except ValueError:
            pass

        if guardar_configuracion(self.config_sys):
            messagebox.showinfo("Éxito", "Configuración guardada exitosamente en config_gideon.json.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    # -------------------------------------------------------------
    # 📦 GESTIÓN DINÁMICA DE PLANES SIMPLEFIBRA
    # -------------------------------------------------------------
    def actualizar_detalle_plan_ui(self, plan_nombre=None):
        if not plan_nombre or not isinstance(plan_nombre, str):
            if hasattr(self, 'plan_seleccionado_id') and self.plan_seleccionado_id:
                plan_nombre = self.plan_seleccionado_id
            else:
                plan_nombre = None

        sin_promo_keywords = ["", "sin promo", "sin_promo", "ninguna", "ninguno", "n/a", "none", "-"]

        datos = CATALOGO_PLANES.get(plan_nombre) if plan_nombre else None
        if datos:
            paquete = datos.get("paquete", "-")
            promo_cat = datos.get("promocion", "").strip()
            router = datos.get("router", "-")
            tarifa = datos.get("tarifa", "$0")

            aplicar_promo = True
            if hasattr(self, 'chk_aplicar_promo'):
                aplicar_promo = bool(self.chk_aplicar_promo.get())

            if not aplicar_promo or not promo_cat or promo_cat.lower() in sin_promo_keywords:
                promo_texto = "Ninguna (Tarifa Estándar)"
            else:
                promo_texto = promo_cat
            
            if hasattr(self, 'lbl_card_paquete'):
                self.lbl_card_paquete.configure(text=f"📦 Paquete: {paquete}")
            if hasattr(self, 'lbl_card_promo'):
                self.lbl_card_promo.configure(text=f"🏷️ Promo: {promo_texto} | Tarifa: {tarifa}")
            if hasattr(self, 'lbl_card_router'):
                self.lbl_card_router.configure(text=f"📡 Router: {router}")
        else:
            if hasattr(self, 'lbl_card_paquete'):
                self.lbl_card_paquete.configure(text="📦 Paquete: (Ningún plan seleccionado)")
            if hasattr(self, 'lbl_card_promo'):
                self.lbl_card_promo.configure(text="🏷️ Promo: - | Tarifa: -")
            if hasattr(self, 'lbl_card_router'):
                self.lbl_card_router.configure(text="📡 Router: -")

    def filtrar_planes(self, *args):
        filtro_vel = self.cmb_filtro_vel.get() if hasattr(self, 'cmb_filtro_vel') else "Velocidad: Todas"
        filtro_mod = self.cmb_modalidad.get() if hasattr(self, 'cmb_modalidad') else "🛒 Compra"
        
        modalidad = "Compra" if "Compra" in filtro_mod else "Alquiler"
        
        planes_disponibles = list(CATALOGO_PLANES.keys())
        if not planes_disponibles:
            self.cmb_plan.configure(values=["(Catálogo vacío)"])
            self.cmb_plan.set("(Catálogo vacío)")
            self.actualizar_detalle_plan_ui()
            return

        # 1. Filtrar por Modalidad
        lista_filtrada = [k for k, v in CATALOGO_PLANES.items() if v.get("modalidad") == modalidad]

        # 2. Filtrar por Velocidad
        if "todas" not in filtro_vel.lower():
            if "otras" in filtro_vel.lower():
                lista_filtrada = [k for k in lista_filtrada if CATALOGO_PLANES[k].get("velocidad") == "Otro"]
            else:
                vel_num = "".join([c for c in filtro_vel if c.isdigit()])
                lista_filtrada = [
                    k for k in lista_filtrada 
                    if vel_num in CATALOGO_PLANES[k].get("velocidad", "") or vel_num in k or vel_num in CATALOGO_PLANES[k].get("paquete", "")
                ]

        if not lista_filtrada:
            lista_filtrada = [f"(Sin planes para {modalidad} - {filtro_vel})"]

        # Limpiar tarjetas actuales
        if hasattr(self, 'frame_lista_planes'):
            for child in self.frame_lista_planes.winfo_children():
                child.destroy()
            self.tarjetas_planes.clear()
            
            for plan_id in lista_filtrada:
                if plan_id.startswith("(Sin planes"):
                    ctk.CTkLabel(self.frame_lista_planes, text=plan_id, font=ctk.CTkFont(size=12, italic=True), text_color="#adb5bd").pack(pady=20)
                    continue
                
                datos = CATALOGO_PLANES.get(plan_id, {})
                paquete = datos.get("paquete", "-")
                promocion = datos.get("promocion", "").strip()
                router = datos.get("router", "-")
                
                if not promocion or promocion.lower() in ["", "sin promo", "sin_promo", "ninguna", "ninguno", "n/a", "none", "-"]:
                    promo_txt = "Tarifa Estándar"
                    color_promo = ("#495057", "#adb5bd")
                else:
                    promo_txt = f"🏷️ {promocion}"
                    color_promo = ("#d9480f", "#ff922b")
                
                card = ctk.CTkFrame(
                    self.frame_lista_planes,
                    fg_color=("#ffffff", "#25262b"),
                    corner_radius=8,
                    border_width=2,
                    border_color=("#ced4da", "#373a40"),
                    cursor="hand2"
                )
                card.pack(fill="x", padx=4, pady=4)
                
                def hacer_click(event, pid=plan_id):
                    self.seleccionar_tarjeta_plan(pid)
                
                card.bind("<Button-1>", hacer_click)
                
                lbl_title = ctk.CTkLabel(card, text=f"⚡ {paquete}", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#212529", "#f8f9fa"), cursor="hand2")
                lbl_title.pack(anchor="w", padx=10, pady=(6, 0))
                lbl_title.bind("<Button-1>", hacer_click)
                
                lbl_promo = ctk.CTkLabel(card, text=promo_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color=color_promo, cursor="hand2")
                lbl_promo.pack(anchor="w", padx=10, pady=(0, 0))
                lbl_promo.bind("<Button-1>", hacer_click)
                
                lbl_router = ctk.CTkLabel(card, text=f"📡 Router: {router}", font=ctk.CTkFont(size=10), text_color=("#1864ab", "#74c0fc"), cursor="hand2")
                lbl_router.pack(anchor="w", padx=10, pady=(0, 6))
                lbl_router.bind("<Button-1>", hacer_click)
                
                self.tarjetas_planes[plan_id] = card
                
            # Seleccionar el primero o mantener actual
            if hasattr(self, 'plan_seleccionado_id') and self.plan_seleccionado_id in lista_filtrada:
                self.seleccionar_tarjeta_plan(self.plan_seleccionado_id)
            elif lista_filtrada and not lista_filtrada[0].startswith("(Sin planes"):
                self.seleccionar_tarjeta_plan(lista_filtrada[0])
            else:
                self.plan_seleccionado_id = None
                self.actualizar_detalle_plan_ui()

    def seleccionar_tarjeta_plan(self, plan_id):
        self.plan_seleccionado_id = plan_id
        for pid, card in self.tarjetas_planes.items():
            if pid == plan_id:
                card.configure(border_color="#ff7800", fg_color=("#fff4e6", "#2b1c10"))
            else:
                card.configure(border_color=("#ced4da", "#373a40"), fg_color=("#ffffff", "#25262b"))
        self.actualizar_detalle_plan_ui(plan_id)

    def recargar_catalogo_ui(self):
        global CATALOGO_PLANES, CATALOGO_DIRECCIONES
        CATALOGO_PLANES = cargar_catalogo_planes()
        CATALOGO_DIRECCIONES = cargar_catalogo_direcciones()
        
        # Extraer velocidades únicas del catálogo para poblar el filtro
        velocidades_encontradas = set()
        for v in CATALOGO_PLANES.values():
            vel = v.get("velocidad", "Otro")
            if vel != "Otro":
                velocidades_encontradas.add(vel)
        
        ordenadas = sorted(list(velocidades_encontradas), key=lambda x: int(''.join([c for c in x if c.isdigit()]) or 0))
        opciones_filtro = ["Velocidad: Todas"] + ordenadas
        if any(v.get("velocidad") == "Otro" for v in CATALOGO_PLANES.values()):
            opciones_filtro.append("Otras")
            
        self.cmb_filtro_vel.configure(values=opciones_filtro)
        self.cmb_filtro_vel.set("Velocidad: Todas")
        self.filtrar_planes()
        
        # Actualizar opciones del menú de ubicaciones
        nuevas_ubicaciones = list(CATALOGO_DIRECCIONES.keys())
        if hasattr(self, 'cmb_ubicacion'):
            self.cmb_ubicacion.configure(values=nuevas_ubicaciones)
            if self.cmb_ubicacion.get() not in nuevas_ubicaciones and nuevas_ubicaciones:
                self.cmb_ubicacion.set(nuevas_ubicaciones[0])

        total_p = len(CATALOGO_PLANES)
        total_u = len(CATALOGO_DIRECCIONES)
        self.log_salida(f"🔄 Catálogos actualizados: {total_p} planes desde '{ARCHIVO_PLANES}' y {total_u} ubicaciones desde '{ARCHIVO_DIRECCIONES}'.")

    def abrir_csv_catalogo(self):
        if not os.path.exists(ARCHIVO_PLANES):
            cargar_catalogo_planes()
        try:
            os.startfile(ARCHIVO_PLANES)
            self.log_salida(f"📂 Abriendo '{ARCHIVO_PLANES}' en Excel o visor del sistema...")
        except Exception as e:
            self.log_salida(f"⚠️ No se pudo abrir automáticamente '{ARCHIVO_PLANES}': {e}")

    def abrir_csv_direcciones(self):
        if not os.path.exists(ARCHIVO_DIRECCIONES):
            cargar_catalogo_direcciones()
        try:
            os.startfile(ARCHIVO_DIRECCIONES)
            self.log_salida(f"📍 Abriendo '{ARCHIVO_DIRECCIONES}' en Excel o visor del sistema...")
        except Exception as e:
            self.log_salida(f"⚠️ No se pudo abrir automáticamente '{ARCHIVO_DIRECCIONES}': {e}")

    # -------------------------------------------------------------
    # 🛠️ MÉTODOS Y EVENTOS PRINCIPALES
    # -------------------------------------------------------------
    def actualizar_subopciones(self, choice):
        if choice == "Persona natural":
            self.cmb_doc.configure(values=["Venezuelan", "Foreigner", "Passport"])
            self.cmb_doc.set("Venezuelan")
        else:
            self.cmb_doc.configure(values=["Legal", "Government", "Personal Signature"])
            self.cmb_doc.set("Legal")

    def preparar_item_cuenta(self, item):
        return dict(item)

    def agregar_lote(self):
        plan_seleccionado = getattr(self, 'plan_seleccionado_id', None)
        if plan_seleccionado not in CATALOGO_PLANES:
            messagebox.showwarning(
                "Plan Inválido",
                f"No hay un plan válido seleccionado ('{plan_seleccionado}').\n\n"
                "Por favor selecciona una velocidad que contenga planes o agrégalos en el archivo CSV."
            )
            return

        tipo_persona = self.cmb_persona.get()
        doc_rif = self.cmb_doc.get()
        ubicacion = self.cmb_ubicacion.get()
        aplicar_promo = bool(self.chk_aplicar_promo.get()) if hasattr(self, 'chk_aplicar_promo') else True
        
        try:
            cant = int(self.spn_cantidad.get())
        except ValueError:
            cant = 1

        for _ in range(cant):
            item = {
                "tipo_persona": tipo_persona, 
                "ubicacion": ubicacion,
                "plan_seleccionado": plan_seleccionado,
                "aplicar_promocion": aplicar_promo
            }
            if tipo_persona == "Persona natural":
                item["tipo_doc"] = doc_rif
            else:
                item["tipo_rif"] = doc_rif
            item = self.preparar_item_cuenta(item)
            self.matriz_cuentas.append(item)

        self.refrescar_vista_cola()

    def agregar_par_mixto(self):
        plan_seleccionado = getattr(self, 'plan_seleccionado_id', None)
        if plan_seleccionado not in CATALOGO_PLANES:
            messagebox.showwarning(
                "Plan Inválido",
                f"No hay un plan válido seleccionado ('{plan_seleccionado}').\n\n"
                "Por favor selecciona una velocidad que contenga planes o agrégalos en el archivo CSV."
            )
            return

        ubicacion = self.cmb_ubicacion.get()
        aplicar_promo = bool(self.chk_aplicar_promo.get()) if hasattr(self, 'chk_aplicar_promo') else True
        par = [
            self.preparar_item_cuenta({"tipo_persona": "Persona natural", "tipo_doc": "Venezuelan", "ubicacion": ubicacion, "plan_seleccionado": plan_seleccionado, "aplicar_promocion": aplicar_promo}),
            self.preparar_item_cuenta({"tipo_persona": "Persona jurídica", "tipo_rif": "Legal", "ubicacion": ubicacion, "plan_seleccionado": plan_seleccionado, "aplicar_promocion": aplicar_promo})
        ]
        self.matriz_cuentas.extend(par)
        self.refrescar_vista_cola()
        promo_txt = "" if aplicar_promo else " [Sin Promo]"
        self.log_salida(f"➕ Añadido Par Mixto (1 Nat + 1 Jur) en {ubicacion} con plan {plan_seleccionado}{promo_txt}")

    def generar_matriz_estado(self, ubicacion, plan=None):
        if not plan:
            plan = getattr(self, 'plan_seleccionado_id', None)
            if not plan: plan = list(CATALOGO_PLANES.keys())[0] if CATALOGO_PLANES else "Compra: 400 mbps"
        return [
            {"tipo_persona": "Persona natural", "tipo_doc": "Venezuelan", "ubicacion": ubicacion, "plan_seleccionado": plan},
            {"tipo_persona": "Persona natural", "tipo_doc": "Foreigner", "ubicacion": ubicacion, "plan_seleccionado": plan},
            {"tipo_persona": "Persona natural", "tipo_doc": "Passport", "ubicacion": ubicacion, "plan_seleccionado": plan},
            {"tipo_persona": "Persona jurídica", "tipo_rif": "Legal", "ubicacion": ubicacion, "plan_seleccionado": plan},
            {"tipo_persona": "Persona jurídica", "tipo_rif": "Government", "ubicacion": ubicacion, "plan_seleccionado": plan},
            {"tipo_persona": "Persona jurídica", "tipo_rif": "Personal Signature", "ubicacion": ubicacion, "plan_seleccionado": plan}
        ]

    def aplicar_preset(self, choice):
        nuevas = []
        plan_base = getattr(self, 'plan_seleccionado_id', None)
        if not plan_base: plan_base = list(CATALOGO_PLANES.keys())[0] if CATALOGO_PLANES else "Compra: 400 mbps"
        
        if choice == "Matriz 6 Perfiles (3 Estados)":
            nuevas = [
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Legal", "ubicacion": "Caracas", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Government", "ubicacion": "Miranda", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Personal Signature", "ubicacion": "Nueva Esparta", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona natural", "tipo_doc": "Venezuelan", "ubicacion": "Caracas", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona natural", "tipo_doc": "Foreigner", "ubicacion": "Miranda", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona natural", "tipo_doc": "Passport", "ubicacion": "Nueva Esparta", "plan_seleccionado": plan_base}
            ]
        elif choice == "⚡ Matriz 6 Perfiles - Caracas":
            nuevas = self.generar_matriz_estado("Caracas", plan_base)
        elif choice == "⚡ Matriz 6 Perfiles - Miranda":
            nuevas = self.generar_matriz_estado("Miranda", plan_base)
        elif choice == "⚡ Matriz 6 Perfiles - Nueva Esparta":
            nuevas = self.generar_matriz_estado("Nueva Esparta", plan_base)
        elif choice == "Solo 3 Jurídicos":
            nuevas = [
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Legal", "ubicacion": "Caracas", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Government", "ubicacion": "Miranda", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona jurídica", "tipo_rif": "Personal Signature", "ubicacion": "Nueva Esparta", "plan_seleccionado": plan_base}
            ]
        elif choice == "Solo 3 Naturales":
            nuevas = [
                {"tipo_persona": "Persona natural", "tipo_doc": "Venezuelan", "ubicacion": "Caracas", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona natural", "tipo_doc": "Foreigner", "ubicacion": "Miranda", "plan_seleccionado": plan_base},
                {"tipo_persona": "Persona natural", "tipo_doc": "Passport", "ubicacion": "Nueva Esparta", "plan_seleccionado": plan_base}
            ]

        if nuevas:
            self.matriz_cuentas = [self.preparar_item_cuenta(c) for c in nuevas]
            self.refrescar_vista_cola()
        self.cmb_preset.set("Seleccionar Preset...")

    def guardar_perfil_json(self):
        if not self.matriz_cuentas:
            messagebox.showwarning("Atención", "La cola está vacía. Agrega cuentas antes de guardar un perfil.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json")],
            title="Guardar Perfil de Trabajo"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.matriz_cuentas, f, indent=4, ensure_ascii=False)
                self.log_salida(f"💾 Perfil guardado exitosamente en: {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el perfil: {str(e)}")

    def cargar_perfil_json(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Archivos JSON", "*.json")],
            title="Cargar Perfil de Trabajo"
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        self.matriz_cuentas = [self.preparar_item_cuenta(c) for c in datos]
                        self.refrescar_vista_cola()
                        self.log_salida(f"📂 Perfil cargado exitosamente desde: {filepath}")
                    else:
                        messagebox.showerror("Error", "El archivo JSON no tiene el formato de lista válido.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el perfil: {str(e)}")

    def eliminar_item_por_indice(self, idx):
        if 0 <= idx < len(self.matriz_cuentas):
            item_eliminado = self.matriz_cuentas.pop(idx)
            self.refrescar_vista_cola()
            self.log_salida(f"🗑️ Eliminada cuenta N° {idx + 1} ({item_eliminado.get('tipo_persona')}) de la cola.")

    def limpiar_cola(self):
        self.matriz_cuentas.clear()
        self.refrescar_vista_cola()

    def reintentar_fallidas_tanda(self):
        if not self.fallidas_tanda_actual:
            messagebox.showinfo("Información", "No hay cuentas fallidas registradas en la tanda actual.")
            return

        cuentas_a_cargar = [dict(c) for c in self.fallidas_tanda_actual]
        self.fallidas_tanda_actual.clear()
        self.btn_reintentar_tanda.configure(
            state="disabled",
            text="🔁 Reintentar (0)",
            fg_color=("#e9ecef", "#2b2d31"),
            text_color=("#212529", "#ffffff")
        )
        self.matriz_cuentas.extend(cuentas_a_cargar)
        self.refrescar_vista_cola()
        self.log_salida(f"🔄 Reincorporadas {len(cuentas_a_cargar)} cuenta(s) fallidas de la tanda actual a la cola.")

    def refrescar_vista_cola(self):
        for child in self.frame_cola_scroll.winfo_children():
            child.destroy()

        correlativo_base = leer_correlativo_actual()
        prefijo = self.config_sys.get("prefijo_email", "CAMBIALO_Fibrastest")
        dominio = self.config_sys.get("dominio_email", "maildrop.cc")

        total_cuentas = len(self.matriz_cuentas)
        if hasattr(self, 'lbl_cola_badge'):
            self.lbl_cola_badge.configure(text=f"{total_cuentas} en espera")

        if not self.matriz_cuentas:
            lbl_vacio = ctk.CTkLabel(
                self.frame_cola_scroll,
                text="La cola de ejecución está vacía.\nAgrega cuentas individuales o selecciona un preset rápido.",
                text_color=("#6c757d", "#909296"),
                font=ctk.CTkFont(size=12)
            )
            lbl_vacio.pack(pady=25)
        else:
            for i, c in enumerate(self.matriz_cuentas, start=1):
                row_frame = ctk.CTkFrame(
                    self.frame_cola_scroll,
                    fg_color=("#ffffff", "#1e1f23"),
                    corner_radius=8,
                    border_width=1,
                    border_color=("#dee2e6", "#2c2e33")
                )
                row_frame.pack(fill="x", padx=4, pady=3)

                doc = c.get("tipo_doc", c.get("tipo_rif", "N/A"))
                plan_str = c.get("plan_seleccionado", "Compra")
                icono = "👤" if c["tipo_persona"] == "Persona natural" else "🏢"

                # Tag de número
                lbl_num = ctk.CTkLabel(
                    row_frame,
                    text=f"#{i:02d}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#ff7800",
                    width=32
                )
                lbl_num.pack(side="left", padx=(8, 4), pady=4)

                # Info principal
                promo_tag = "" if c.get("aplicar_promocion", True) else " [Sin Promo]"
                texto_desc = f"{icono} {c['tipo_persona']} | {doc} | 📍 {c['ubicacion']} | ⚡ {plan_str}{promo_tag}"
                lbl_desc = ctk.CTkLabel(
                    row_frame,
                    text=texto_desc,
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color=("#212529", "#f8f9fa")
                )
                lbl_desc.pack(side="left", padx=4, pady=4, fill="x", expand=True)

                # Botón de eliminar
                btn_del = ctk.CTkButton(
                    row_frame,
                    text="✕",
                    width=26,
                    height=22,
                    fg_color=("#fee2e2", "#3b1219"),
                    hover_color=("#fca5a5", "#c92a2a"),
                    text_color=("#b91c1c", "#ff8787"),
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda idx=(i - 1): self.eliminar_item_por_indice(idx)
                )
                btn_del.pack(side="right", padx=6, pady=3)

        self.update_kpis_ui(total=total_cuentas)

    def log_salida(self, mensaje):
        def _log():
            timestamp = time.strftime("[%H:%M:%S] ")
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"{timestamp}{mensaje}\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(0, _log)

    def iniciar_proceso(self):
        if not self.matriz_cuentas:
            self.log_salida("⚠️ La cola de ejecución está vacía. Agrega cuentas o selecciona un preset antes de iniciar.")
            return

        self.cancel_event.clear()
        self.fallidas_tanda_actual.clear()
        if hasattr(self, 'btn_reintentar_tanda'):
            self.btn_reintentar_tanda.configure(
                state="disabled",
                text="🔁 Reintentar (0)",
                fg_color=("#e9ecef", "#2b2d31"),
                text_color=("#212529", "#ffffff")
            )
        self.btn_iniciar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        if hasattr(self, 'lbl_console_status'):
            self.lbl_console_status.configure(text="🟠 Procesando...", text_color="#e8590c")

        num_hilos = int(self.cmb_hilos.get())
        
        modo_headless = False 
        self.config_sys["hilos_simultaneos"] = num_hilos
        self.config_sys["modo_headless"] = modo_headless

        self.log_salida(f"🔥 Iniciando procesamiento masivo de {len(self.matriz_cuentas)} cuentas con {num_hilos} hilos (Navegador Visible)...")
        threading.Thread(target=self.ejecutar_hilos, daemon=True).start()

    def cancelar_proceso(self):
        if not self.cancel_event.is_set():
            self.cancel_event.set()
            self.btn_cancelar.configure(state="disabled")
            self.log_salida("🛑 [SISTEMA] Solicitud de CANCELACIÓN recibida. Deteniendo hilos activos y cancelando cuentas pendientes...")

    def ejecutar_hilos(self):
        num_hilos = self.config_sys.get("hilos_simultaneos", 2)
        # Snapshot protegido: se procesa una copia fija para que modificaciones externas no colisionen
        tanda_cuentas = list(self.matriz_cuentas)
        with ThreadPoolExecutor(max_workers=num_hilos) as executor:
            for i, config in enumerate(tanda_cuentas, start=1):
                if self.cancel_event.is_set():
                    self.log_salida(f"⚠️ [SISTEMA] Ejecución cancelada. Se omitieron {len(tanda_cuentas) - i + 1} cuentas pendientes en cola.")
                    break
                self.update_kpis_ui(ejecucion=1)
                
                # Callback por cuenta que registra fallos para el botón de reintento de tanda
                def _crear_cb(c_item):
                    def _cb(exito=0, fallo=0):
                        self.update_kpis_ui(ejecucion=-1, exito=exito, fallo=fallo)
                        if fallo > 0:
                            self.fallidas_tanda_actual.append(dict(c_item))
                    return _cb

                executor.submit(
                    crear_cuenta_individual,
                    i, config, self.config_sys, self.log_salida,
                    _crear_cb(config),
                    self.cancel_event
                )
                time.sleep(6)
        
        def _finalizar():
            if self.cancel_event.is_set():
                self.log_salida("🛑 Procesamiento detenido y cancelado por el usuario.")
            else:
                self.log_salida("🎉 Proceso finalizado por completo.")
            self.btn_iniciar.configure(state="normal")
            self.btn_cancelar.configure(state="disabled")
            if hasattr(self, 'lbl_console_status'):
                self.lbl_console_status.configure(text="🟢 En Línea", text_color="#2b8a3e")
            
            # Auto-refrescar la tabla del Historial para reflejar los resultados de inmediato
            if hasattr(self, 'cargar_historial_reporte'):
                self.cargar_historial_reporte()

            # Comprobar si hubo fallos exclusivos de esta tanda
            total_fallos = len(self.fallidas_tanda_actual)
            if hasattr(self, 'btn_reintentar_tanda'):
                if total_fallos > 0:
                    self.btn_reintentar_tanda.configure(
                        state="normal",
                        text=f"🔁 Reintentar ({total_fallos})",
                        fg_color="#ff7800",
                        hover_color="#e66a00",
                        text_color="#ffffff"
                    )
                    self.log_salida(f"💡 [REINTENTO] {total_fallos} cuenta(s) presentaron fallo en esta tanda. Pulsa '🔁 Reintentar ({total_fallos})' para reincorporarlas a la cola.")
                else:
                    self.btn_reintentar_tanda.configure(
                        state="disabled",
                        text="🔁 Reintentar (0)",
                        fg_color=("#e9ecef", "#2b2d31"),
                        text_color=("#212529", "#ffffff")
                    )
        self.after(0, _finalizar)

if __name__ == "__main__":
    app = AppGideon()
    app.mainloop()
