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
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox, ttk
from ui.calendario import ModernCalendar

from core.config import (
    CONFIG_FILE, DEFAULT_CONFIG, cargar_configuracion, guardar_configuracion
)
from core.catalogos import (
    ARCHIVO_PLANES, ARCHIVO_DIRECCIONES, cargar_catalogo_planes, cargar_catalogo_direcciones, cargar_catalogo_direcciones_ott, cargar_catalogo_ott
)
from core.correlativos import (
    leer_correlativo_actual, obtener_siguiente_correlativo, actualizar_correlativo_manual
)
from core.generadores import limpiar_texto_crm
from automation.worker import crear_cuenta_individual
from automation.worker_ott import crear_cuenta_ott

CATALOGO_PLANES = cargar_catalogo_planes()
CATALOGO_DIRECCIONES = cargar_catalogo_direcciones()
CATALOGO_DIRECCIONES_OTT = cargar_catalogo_direcciones_ott()
CATALOGO_OTT = cargar_catalogo_ott()

class AppGideon(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("G.I.D.E.O.N. v3.4.2 TEST | Simplefibra FTTH Automation Hub")
        self.geometry("1120x840")
        self.minsize(1100, 820)
        self.resizable(True, True)

        self.config_sys = cargar_configuracion()
        tema_inicial = self.config_sys.get("tema_apariencia", "Dark")
        ctk.set_appearance_mode(tema_inicial)

        # Cargar icono de ventana principal
        try:
            rutas_posibles_ico = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Imagenes", "logo.ico"),
                os.path.join(getattr(sys, '_MEIPASS', ''), "Imagenes", "logo.ico"),
                os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "Imagenes", "logo.ico") if getattr(sys, 'frozen', False) else "",
                os.path.join(os.getcwd(), "Imagenes", "logo.ico"),
                os.path.join("Imagenes", "logo.ico")
            ]
            for r in rutas_posibles_ico:
                if r and os.path.exists(r):
                    self.iconbitmap(r)
                    break
        except Exception as e:
            print(f"No se pudo cargar el logo principal: {e}")

        self.matriz_cuentas = []
        self.matriz_cuentas_ott = []
        
        self.fallidas_tanda_actual = []
        self.fallidas_tanda_actual_ott = []
        
        self.cancel_event = threading.Event()
        self.cancel_event_ott = threading.Event()

        # Métricas KPIs
        self.kpi_total = 0
        self.kpi_ejecucion = 0
        self.kpi_exito = 0
        self.kpi_fallo = 0

        self.estado_hilos = {}
        self.widgets_monitor_hilos = {}
        self.after(1000, self.actualizar_cronometros_ui)

        # --- SISTEMA DE PESTAÑAS (TABVIEW ESTILO SIMPLETV) ---
        self.tabview = ctk.CTkTabview(
            self,
            command=self.al_cambiar_pestana,
            corner_radius=12,
            fg_color=("#f8f9fa", "#141517"),
            segmented_button_selected_color="#ff7800",
            segmented_button_selected_hover_color="#e66a00",
            segmented_button_unselected_color=("#e9ecef", "#212529"),
            segmented_button_unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff")
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_control = self.tabview.add("Centro de Control")
        self.tab_ott = self.tabview.add("Control OTT")
        self.tab_reportes = self.tabview.add("Historial & Reportes")
        self.tab_config = self.tabview.add("Configuración")

        # Construir cada pestaña
        self.build_tab_control()
        self.build_tab_ott()
        self.build_tab_reportes()
        self.build_tab_config()

        # Inicializar UI y cargar catálogo visual por defecto
        self.recargar_catalogo_ui()
        self.filtrar_planes()

    def al_cambiar_pestana(self):
        pestana_actual = self.tabview.get()
        if "Historial" in pestana_actual and hasattr(self, 'cargar_historial_reporte'):
            self.cargar_historial_reporte()

    # -------------------------------------------------------------
    # 🚀 PESTAÑA 1: CENTRO DE CONTROL (SIMPLETV ORANGE & WHITE)
    # -------------------------------------------------------------
    def build_tab_control(self):
        # 1. TARJETAS DE MÉTRICAS KPI (HEADER PRO CON IMÁGENES PNG)
        self.frame_kpis = ctk.CTkFrame(self.tab_control, fg_color="transparent")
        self.frame_kpis.pack(fill="x", padx=5, pady=(0, 10))

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        if not os.path.exists(assets_dir) and getattr(sys, '_MEIPASS', None):
            assets_dir = os.path.join(sys._MEIPASS, "ui", "assets")
        if not os.path.exists(assets_dir):
            assets_dir = os.path.join(os.getcwd(), "ui", "assets")

        self.card_total = self.crear_card_kpi(
            self.frame_kpis, "Total en Cola", "0", ("#d9480f", "#ff7800"),
            icono="📦", imagen_path=os.path.join(assets_dir, "kpi_cola.png")
        )
        self.card_total.pack(side="left", fill="x", expand=True, padx=4)

        self.card_ejecucion = self.crear_card_kpi(
            self.frame_kpis, "En Ejecución", "0", ("#c2410c", "#ffa94d"),
            icono="⏳", imagen_path=os.path.join(assets_dir, "kpi_ejecucion.png")
        )
        self.card_ejecucion.pack(side="left", fill="x", expand=True, padx=4)

        self.card_exito = self.crear_card_kpi(
            self.frame_kpis, "Exitosas", "0", ("#2b8a3e", "#51cf66"),
            icono="✅", imagen_path=os.path.join(assets_dir, "kpi_exito.png")
        )
        self.card_exito.pack(side="left", fill="x", expand=True, padx=4)

        self.card_fallo = self.crear_card_kpi(
            self.frame_kpis, "Fallidas", "0", ("#c92a2a", "#ff6b6b"),
            icono="❌", imagen_path=os.path.join(assets_dir, "kpi_fallo.png")
        )
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

        hdr_presets = ctk.CTkFrame(card_presets, fg_color="transparent")
        hdr_presets.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            hdr_presets,
            text="⚡ PRESETS RÁPIDOS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#d9480f", "#ff922b")
        ).pack(side="left")

        ctk.CTkLabel(
            hdr_presets,
            text="⌃",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#868e96", "#adb5bd")
        ).pack(side="right")

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

        hdr_form = ctk.CTkFrame(card_form, fg_color="transparent")
        hdr_form.pack(fill="x", padx=12, pady=(10, 8))

        ctk.CTkLabel(
            hdr_form,
            text="➕ CONFIGURACIÓN PLAN Y CUENTA",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#d9480f", "#ff922b")
        ).pack(side="left")

        ctk.CTkLabel(
            hdr_form,
            text="⌃",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#868e96", "#adb5bd")
        ).pack(side="right")

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

        # Contenedor para filtros horizontales (Velocidad y TV)
        frame_filtros_sec = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_filtros_sec.pack(fill="x", padx=12, pady=(0, 5))
        
        # Filtro de Velocidad para agrupar planes
        self.cmb_filtro_vel = ctk.CTkOptionMenu(
            frame_filtros_sec,
            values=["Velocidad: Todas", "400 Mbps", "500 Mbps", "600 Mbps", "1000 Mbps", "Otras"],
            command=self.filtrar_planes,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11),
            height=28
        )
        self.cmb_filtro_vel.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Filtro de Familia Bundle
        self.cmb_filtro_fam = ctk.CTkOptionMenu(
            frame_filtros_sec,
            values=["Bundle: Todos", "Gold", "Platino", "Diamante", "Otros"],
            command=self.filtrar_planes,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff"),
            font=ctk.CTkFont(size=11),
            height=28
        )
        self.cmb_filtro_fam.pack(side="left", fill="x", expand=True, padx=(4, 0))

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

        # ⚙️ Switch moderno para habilitar o deshabilitar promociones (Estilo Toggle Switch)
        frame_promo_switch = ctk.CTkFrame(
            card_form,
            fg_color=("#f1f3f5", "#141517"),
            corner_radius=8,
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        frame_promo_switch.pack(fill="x", padx=12, pady=(0, 10))

        inner_switch = ctk.CTkFrame(frame_promo_switch, fg_color="transparent")
        inner_switch.pack(fill="both", expand=True, padx=10, pady=7)

        lbl_switch_text = ctk.CTkLabel(
            inner_switch,
            text="⚙️ APLICAR PROMOCIÓN",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#d9480f", "#ff922b")
        )
        lbl_switch_text.pack(side="left")

        self.chk_aplicar_promo = ctk.CTkSwitch(
            inner_switch,
            text="",
            width=44,
            switch_width=40,
            switch_height=20,
            progress_color="#ff7800",
            fg_color=("#ced4da", "#2c2e33"),
            button_color="#ffffff",
            button_hover_color="#f8f9fa",
            command=self.actualizar_detalle_plan_ui
        )
        self.chk_aplicar_promo.select()
        self.chk_aplicar_promo.pack(side="right")

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

        # Fila superior: Selector de Modo de Creación (Completo vs Solo Paso 3)
        frame_modo = ctk.CTkFrame(card_exec, fg_color="transparent")
        frame_modo.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            frame_modo,
            text="🎯 Modo de Creación:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#212529", "#f8f9fa")
        ).pack(side="left", padx=(0, 8))

        modo_actual = self.config_sys.get("modo_ejecucion", "completo")
        val_modo_inicial = "✍️ Manual (Hasta Paso 3)" if modo_actual == "hasta_paso_3" else "🚀 Completa (Paso 0 al 5)"

        self.seg_modo_control = ctk.CTkSegmentedButton(
            frame_modo,
            values=["🚀 Completa (Paso 0 al 5)", "✍️ Manual (Hasta Paso 3)"],
            command=self.al_cambiar_modo_ejecucion,
            selected_color="#ff7800",
            selected_hover_color="#e66a00",
            unselected_color=("#e9ecef", "#2b2d31"),
            unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            height=28
        )
        self.seg_modo_control.set(val_modo_inicial)
        self.seg_modo_control.pack(side="left", padx=5)

        frame_exec_inner = ctk.CTkFrame(card_exec, fg_color="transparent")
        frame_exec_inner.pack(fill="x", padx=10, pady=(4, 8))

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
        texto_btn_iniciar = "✍️ INICIAR HASTA PASO 3" if modo_actual == "hasta_paso_3" else "🚀 INICIAR PROCESAMIENTO MASIVO"
        color_btn_iniciar = "#d9480f" if modo_actual == "hasta_paso_3" else "#ff7800"
        hover_btn_iniciar = "#c2410c" if modo_actual == "hasta_paso_3" else "#e66a00"

        self.btn_iniciar = ctk.CTkButton(
            frame_exec_inner,
            text=texto_btn_iniciar,
            command=self.iniciar_proceso,
            fg_color=color_btn_iniciar,
            hover_color=hover_btn_iniciar,
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34
        )
        self.btn_iniciar.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # 2.5 Panel de Monitoreo Multihilo en Vivo
        self.frame_monitor_hilos = ctk.CTkScrollableFrame(self.frame_right, corner_radius=10, fg_color="transparent", orientation="horizontal", height=75)
        self.frame_monitor_hilos.pack(fill="x", padx=0, pady=(0, 8))

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

    def crear_card_kpi(self, parent, titulo, valor_inicial, color_acento, icono="📦", imagen_path=None):
        card = ctk.CTkFrame(
            parent,
            fg_color=("#ffffff", "#1e1f23"),
            corner_radius=10,
            border_width=1,
            border_color=("#ced4da", "#2c2e33")
        )
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=12, pady=10)

        left_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True)

        lbl_badge = ctk.CTkLabel(
            left_col,
            text=titulo.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#495057", "#adb5bd"),
            anchor="w"
        )
        lbl_badge.pack(anchor="w", pady=(0, 2))

        lbl_val = ctk.CTkLabel(
            left_col,
            text=str(valor_inicial),
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=color_acento,
            anchor="w"
        )
        lbl_val.pack(anchor="w")

        # Insignia o Logo en PNG (derecha)
        card.img_ref = None
        if imagen_path and os.path.exists(imagen_path):
            try:
                pil_img = Image.open(imagen_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
                lbl_icon = ctk.CTkLabel(content_frame, text="", image=ctk_img)
                lbl_icon.pack(side="right", padx=(6, 0))
                card.img_ref = ctk_img
            except Exception:
                lbl_icon = ctk.CTkLabel(content_frame, text=icono, font=ctk.CTkFont(size=22))
                lbl_icon.pack(side="right", padx=(6, 0))
        else:
            lbl_icon = ctk.CTkLabel(content_frame, text=icono, font=ctk.CTkFont(size=22))
            lbl_icon.pack(side="right", padx=(6, 0))

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

    def build_tab_ott(self):
        # 1. TARJETAS DE MÉTRICAS KPI (HEADER PRO CON IMÁGENES PNG)
        self.frame_kpis_ott = ctk.CTkFrame(self.tab_ott, fg_color="transparent")
        self.frame_kpis_ott.pack(fill="x", padx=5, pady=(0, 10))

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        if not os.path.exists(assets_dir) and getattr(sys, '_MEIPASS', None):
            assets_dir = os.path.join(sys._MEIPASS, "ui", "assets")
        if not os.path.exists(assets_dir):
            assets_dir = os.path.join(os.getcwd(), "ui", "assets")

        self.card_total_ott = self.crear_card_kpi(
            self.frame_kpis_ott, "Total en Cola", "0", ("#d9480f", "#ff7800"),
            icono="📺", imagen_path=os.path.join(assets_dir, "kpi_cola.png")
        )
        self.card_total_ott.pack(side="left", fill="x", expand=True, padx=4)

        self.card_ejecucion_ott = self.crear_card_kpi(
            self.frame_kpis_ott, "En Ejecución", "0", ("#c2410c", "#ffa94d"),
            icono="⚡", imagen_path=os.path.join(assets_dir, "kpi_ejecucion.png")
        )
        self.card_ejecucion_ott.pack(side="left", fill="x", expand=True, padx=4)

        self.card_exito_ott = self.crear_card_kpi(
            self.frame_kpis_ott, "Exitosas", "0", ("#2b8a3e", "#51cf66"),
            icono="✅", imagen_path=os.path.join(assets_dir, "kpi_exito.png")
        )
        self.card_exito_ott.pack(side="left", fill="x", expand=True, padx=4)

        self.card_fallo_ott = self.crear_card_kpi(
            self.frame_kpis_ott, "Fallidas", "0", ("#c92a2a", "#ff6b6b"),
            icono="❌", imagen_path=os.path.join(assets_dir, "kpi_fallo.png")
        )
        self.card_fallo_ott.pack(side="left", fill="x", expand=True, padx=4)

        self.frame_ott_body = ctk.CTkFrame(self.tab_ott, fg_color="transparent")
        self.frame_ott_body.pack(fill="both", expand=True)

        # Panel Izquierdo: Formulario
        self.frame_ott_left = ctk.CTkScrollableFrame(self.frame_ott_body, width=370, corner_radius=12, fg_color=("#f1f3f5", "#141517"))
        self.frame_ott_left.pack(side="left", fill="both", expand=False, padx=(0, 5), pady=5)

        card_form = ctk.CTkFrame(self.frame_ott_left, corner_radius=10, fg_color=("#ffffff", "#1a1b1e"), border_width=1, border_color=("#ced4da", "#2c2e33"))
        card_form.pack(fill="x", padx=4, pady=(0, 10))

        hdr_form = ctk.CTkFrame(card_form, fg_color="transparent")
        hdr_form.pack(fill="x", padx=12, pady=(10, 8))
        ctk.CTkLabel(hdr_form, text="🎯 CONFIGURACIÓN PLAN OTT", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#d9480f", "#ff922b")).pack(side="left")

        # Plan OTT
        ctk.CTkLabel(card_form, text="Seleccione el Plan OTT:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(2, 2))
        planes_ott_list = list(CATALOGO_OTT.keys()) if CATALOGO_OTT else ["Litesports", "Gold", "Platino", "Diamante"]
        
        self.cmb_plan_ott = ctk.CTkOptionMenu(
            card_form, values=planes_ott_list, fg_color=("#e9ecef", "#25262b"), button_color="#ff7800", button_hover_color="#e66a00", text_color=("#212529", "#ffffff"), height=30
        )
        self.cmb_plan_ott.pack(fill="x", padx=12, pady=(0, 8))

        # Tipo de documento
        ctk.CTkLabel(card_form, text="Tipo de documento (Cliente Natural):", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(10, 2))
        self.cmb_doc_ott = ctk.CTkOptionMenu(
            card_form, values=["Venezolano", "Extranjero", "Pasaporte"], fg_color=("#e9ecef", "#25262b"), button_color="#ff7800", button_hover_color="#e66a00", text_color=("#212529", "#ffffff"), height=30
        )
        self.cmb_doc_ott.pack(fill="x", padx=12, pady=(0, 8))

        # Ubicación
        ctk.CTkLabel(card_form, text="Ubicación (Estado/Ciudad):", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(anchor="w", padx=12, pady=(10, 2))
        estados_list = list(CATALOGO_DIRECCIONES_OTT.keys()) if CATALOGO_DIRECCIONES_OTT else ["Miranda", "Caracas"]
        self.cmb_ubicacion_ott = ctk.CTkOptionMenu(
            card_form, values=estados_list, fg_color=("#e9ecef", "#25262b"), button_color="#ff7800", button_hover_color="#e66a00", text_color=("#212529", "#ffffff"), height=30
        )
        self.cmb_ubicacion_ott.pack(fill="x", padx=12, pady=(0, 8))

        # Fila de Cantidad
        frame_cant = ctk.CTkFrame(card_form, fg_color="transparent")
        frame_cant.pack(fill="x", padx=12, pady=(10, 10))
        ctk.CTkLabel(frame_cant, text="Cantidad de cuentas:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")
        self.spn_cantidad_ott = ctk.CTkEntry(frame_cant, placeholder_text="1", width=65, height=28, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"), text_color=("#212529", "#f8f9fa"))
        self.spn_cantidad_ott.insert(0, "1")
        self.spn_cantidad_ott.pack(side="right")

        # Botón Agregar
        ctk.CTkButton(
            card_form, text="➕ Agregar a la Cola OTT", command=self.agregar_lote_ott, fg_color="#ff7800", hover_color="#e66a00", text_color="#ffffff", font=ctk.CTkFont(size=13, weight="bold"), height=34
        ).pack(fill="x", padx=12, pady=(0, 12))

        # --- PANEL DERECHO: COLA, EJECUCIÓN Y CONSOLA OTT ---
        self.frame_ott_right = ctk.CTkFrame(self.frame_ott_body, corner_radius=12, fg_color="transparent")
        self.frame_ott_right.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

        card_cola = ctk.CTkFrame(self.frame_ott_right, corner_radius=10, fg_color=("#ffffff", "#1a1b1e"), border_width=1, border_color=("#ced4da", "#2c2e33"))
        card_cola.pack(fill="x", padx=0, pady=(0, 8))

        frame_cola_hdr = ctk.CTkFrame(card_cola, fg_color="transparent")
        frame_cola_hdr.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(frame_cola_hdr, text="📋 Cola de Cuentas OTT", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#d9480f", "#ff7800")).pack(side="left")
        self.lbl_cola_badge_ott = ctk.CTkLabel(frame_cola_hdr, text="0 en espera", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#495057", "#adb5bd"))
        self.lbl_cola_badge_ott.pack(side="right")

        self.frame_cola_scroll_ott = ctk.CTkScrollableFrame(card_cola, height=130, fg_color=("#f1f3f5", "#141517"), corner_radius=8)
        self.frame_cola_scroll_ott.pack(fill="x", padx=10, pady=(0, 8))

        # Acciones
        card_exec = ctk.CTkFrame(self.frame_ott_right, corner_radius=10, fg_color=("#ffffff", "#1a1b1e"), border_width=1, border_color=("#ced4da", "#2c2e33"))
        card_exec.pack(fill="x", padx=0, pady=(0, 8))

        frame_exec_inner = ctk.CTkFrame(card_exec, fg_color="transparent")
        frame_exec_inner.pack(fill="x", padx=12, pady=8)
        
        # Hilos OTT a la izquierda
        ctk.CTkLabel(frame_exec_inner, text="Concurrencia:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(0, 4))
        self.cmb_hilos_ott = ctk.CTkOptionMenu(
            frame_exec_inner,
            values=["1", "2", "3", "4"],
            width=65,
            height=28,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff")
        )
        self.cmb_hilos_ott.set(str(self.config_sys.get("hilos_simultaneos_ott", 2)))
        self.cmb_hilos_ott.pack(side="left", padx=(0, 10))

        # Botón Limpiar a la izquierda
        ctk.CTkButton(
            frame_exec_inner, text="🧹 Limpiar Cola", command=self.limpiar_cola_ott, fg_color=("#e9ecef", "#25262b"), hover_color=("#dee2e6", "#2c2e33"), text_color=("#495057", "#ced4da"), font=ctk.CTkFont(size=12, weight="bold"), height=30, width=110
        ).pack(side="left")

        # Iniciar a la derecha
        self.btn_iniciar_ott = ctk.CTkButton(
            frame_exec_inner, text="🚀 INICIAR PROCESAMIENTO", command=self.iniciar_proceso_ott, fg_color="#ff7800", hover_color="#e66a00", text_color="#ffffff", font=ctk.CTkFont(size=13, weight="bold"), height=30
        )
        self.btn_iniciar_ott.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        self.btn_cancelar_ott = ctk.CTkButton(
            frame_exec_inner, text="🛑 Cancelar", command=self.cancelar_proceso_ott, fg_color=("#f8d7da", "#401c1c"), hover_color=("#f5c2c7", "#521616"), text_color=("#721c24", "#e599f7"), font=ctk.CTkFont(size=12, weight="bold"), height=30, width=100, state="disabled"
        )
        self.btn_cancelar_ott.pack(side="right", padx=(10, 0))

        # 3. Card de Consola de Monitoreo Pro (Sólo lectura) para OTT
        card_consola_ott = ctk.CTkFrame(self.frame_ott_right, corner_radius=10, border_color=("#ced4da", "#2c2e33"), border_width=1, fg_color=("#ffffff", "#1a1b1e"))
        card_consola_ott.pack(fill="both", expand=True, padx=0, pady=(0, 0))

        frame_consola_hdr_ott = ctk.CTkFrame(card_consola_ott, fg_color="transparent")
        frame_consola_hdr_ott.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(frame_consola_hdr_ott, text="🖥️ Consola de Monitoreo OTT", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left")

        ctk.CTkButton(frame_consola_hdr_ott, text="🧹 Limpiar", width=65, height=22, command=self.limpiar_log_consola_ott, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11)).pack(side="right", padx=(5, 0))

        self.txt_log_ott = ctk.CTkTextbox(card_consola_ott, height=130, fg_color=("#18191c", "#0d0e11"), text_color="#20c997", font=ctk.CTkFont(family="Consolas", size=11), corner_radius=6, border_width=1, border_color=("#495057", "#2c2e33"))
        self.txt_log_ott.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.txt_log_ott.configure(state="disabled")

        # Refrescar vista por defecto
        self.refrescar_vista_cola_ott()

    def update_kpis_ui_ott(self, ejecucion=0, exito=0, fallo=0):
        def _actualizar():
            if ejecucion != 0:
                current = int(self.card_ejecucion_ott.lbl_val.cget("text"))
                self.card_ejecucion_ott.lbl_val.configure(text=str(max(0, current + ejecucion)))
            if exito != 0:
                current = int(self.card_exito_ott.lbl_val.cget("text"))
                self.card_exito_ott.lbl_val.configure(text=str(current + exito))
            if fallo != 0:
                current = int(self.card_fallo_ott.lbl_val.cget("text"))
                self.card_fallo_ott.lbl_val.configure(text=str(current + fallo))
        self.after(0, _actualizar)

    def log_salida_ott(self, mensaje):
        from datetime import datetime
        hora = datetime.now().strftime("%H:%M:%S")
        def _log():
            self.txt_log_ott.configure(state="normal")
            self.txt_log_ott.insert("end", f"[{hora}] {mensaje}\n")
            self.txt_log_ott.see("end")
            self.txt_log_ott.configure(state="disabled")
        self.after(0, _log)
        try:
            print(f"[OTT] [{hora}] {mensaje}")
        except UnicodeEncodeError:
            print(f"[OTT] [{hora}] {mensaje.encode('ascii', 'ignore').decode('ascii')}")

    def limpiar_log_consola_ott(self):
        self.txt_log_ott.configure(state="normal")
        self.txt_log_ott.delete("1.0", "end")
        self.txt_log_ott.configure(state="disabled")
        self.log_salida_ott("🧹 Consola OTT reiniciada.")

    def refrescar_vista_cola_ott(self):
        for child in self.frame_cola_scroll_ott.winfo_children():
            child.destroy()

        total_cuentas = len(self.matriz_cuentas_ott)
        if hasattr(self, 'lbl_cola_badge_ott'):
            self.lbl_cola_badge_ott.configure(text=f"{total_cuentas} en espera")

        if not self.matriz_cuentas_ott:
            lbl_vacio = ctk.CTkLabel(
                self.frame_cola_scroll_ott, text="La cola OTT está vacía.", text_color=("#6c757d", "#909296"), font=ctk.CTkFont(size=12)
            )
            lbl_vacio.pack(pady=25)
        else:
            for i, c in enumerate(self.matriz_cuentas_ott, start=1):
                row_frame = ctk.CTkFrame(self.frame_cola_scroll_ott, fg_color=("#ffffff", "#1e1f23"), corner_radius=8, border_width=1, border_color=("#dee2e6", "#2c2e33"), height=42)
                row_frame.pack(fill="x", pady=3, padx=2)
                row_frame.pack_propagate(False)
                
                ctk.CTkLabel(row_frame, text=f"{i}", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#ffffff"), fg_color="#ff7800", width=22, corner_radius=4).pack(side="left", padx=(6, 8), pady=10)
                ctk.CTkLabel(row_frame, text="NATURAL", font=ctk.CTkFont(size=10, weight="bold"), text_color="#1864ab", width=55).pack(side="left")
                ubic = c.get('ubicacion', 'N/A')
                ctk.CTkLabel(row_frame, text=f"{c['plan_seleccionado']} ({c['tipo_doc']}) - 📍 {ubic}", font=ctk.CTkFont(size=11), text_color=("#495057", "#ced4da")).pack(side="left", padx=(10, 0), expand=True, anchor="w")
                
                def make_remover(index):
                    return lambda: self.remover_de_cola_ott(index)
                
                btn_del = ctk.CTkButton(row_frame, text="🗑", width=26, height=26, fg_color="transparent", hover_color=("#ffe3e3", "#401c1c"), text_color=("#fa5252", "#ff6b6b"), command=make_remover(i-1))
                btn_del.pack(side="right", padx=6)

    def remover_de_cola_ott(self, indice):
        if 0 <= indice < len(self.matriz_cuentas_ott):
            del self.matriz_cuentas_ott[indice]
            self.refrescar_vista_cola_ott()

    def limpiar_cola_ott(self):
        self.matriz_cuentas_ott.clear()
        self.fallidas_tanda_actual_ott.clear()
        self.refrescar_vista_cola_ott()
        self.log_salida_ott("🗑️ Cola OTT limpiada.")

    def agregar_lote_ott(self):
        plan_ott = self.cmb_plan_ott.get()
        if not plan_ott:
            messagebox.showwarning("Plan Inválido", "Por favor selecciona un plan OTT válido.")
            return

        try:
            cant = int(self.spn_cantidad_ott.get())
        except ValueError:
            cant = 1

        tipo_doc_ott = self.cmb_doc_ott.get()
        tipo_doc_eng = "Venezuelan" if tipo_doc_ott == "Venezolano" else ("Foreigner" if tipo_doc_ott == "Extranjero" else "Passport")
        ubicacion_ott = self.cmb_ubicacion_ott.get()

        for _ in range(cant):
            item = {
                "tipo_persona": "Persona natural", 
                "ubicacion": ubicacion_ott,
                "plan_seleccionado": plan_ott,
                "aplicar_promocion": False,
                "is_ott": True,
                "tipo_doc": tipo_doc_eng
            }
            item = self.preparar_item_cuenta(item)
            self.matriz_cuentas_ott.append(item)

        self.refrescar_vista_cola_ott()
        self.log_salida_ott(f"➕ Añadidas {cant} cuentas OTT ({plan_ott}, {tipo_doc_ott}) a la Cola OTT.")

    def iniciar_proceso_ott(self):
        if not self.matriz_cuentas_ott:
            messagebox.showinfo("Cola vacía", "Agrega al menos una cuenta a la cola OTT antes de iniciar.")
            return
            
        self.btn_iniciar_ott.configure(state="disabled")
        self.btn_cancelar_ott.configure(state="normal")
        self.cancel_event_ott.clear()
        self.fallidas_tanda_actual_ott.clear()
        
        self.log_salida_ott(f"🚀 Iniciando procesamiento masivo de {len(self.matriz_cuentas_ott)} cuentas OTT...")
        threading.Thread(target=self.ejecutar_hilos_ott, daemon=True).start()

    def cancelar_proceso_ott(self):
        if not self.cancel_event_ott.is_set():
            self.cancel_event_ott.set()
            self.btn_cancelar_ott.configure(state="disabled")
            self.log_salida_ott("🛑 [SISTEMA] Solicitud de CANCELACIÓN OTT recibida...")

    def ejecutar_hilos_ott(self):
        try:
            num_hilos = int(self.cmb_hilos_ott.get())
        except ValueError:
            num_hilos = 2
            
        self.config_sys["hilos_simultaneos_ott"] = num_hilos
        guardar_configuracion(self.config_sys)
        
        tanda_cuentas = list(self.matriz_cuentas_ott)
        with ThreadPoolExecutor(max_workers=num_hilos) as executor:
            for i, config in enumerate(tanda_cuentas, start=1):
                if self.cancel_event_ott.is_set():
                    self.log_salida_ott(f"🚫 Ejecución OTT cancelada.")
                    break
                
                self.update_kpis_ui_ott(ejecucion=1)
                
                def _crear_cb(c_item):
                    def _cb(exito=0, fallo=0):
                        self.update_kpis_ui_ott(ejecucion=-1, exito=exito, fallo=fallo)
                        if fallo > 0:
                            self.fallidas_tanda_actual_ott.append(dict(c_item))
                    return _cb

                executor.submit(
                    crear_cuenta_ott,
                    i, config, self.config_sys, self.log_salida_ott,
                    _crear_cb(config),
                    self.cancel_event_ott,
                    self.update_thread_status
                )
                import time
                time.sleep(6)
        
        def _finalizar():
            if self.cancel_event_ott.is_set():
                self.log_salida_ott("🛑 Procesamiento OTT cancelado por el usuario.")
            else:
                self.log_salida_ott("✅ Proceso OTT finalizado por completo.")
            self.btn_iniciar_ott.configure(state="normal")
            self.btn_cancelar_ott.configure(state="disabled")
            if hasattr(self, 'cargar_historial_reporte'):
                self.cargar_historial_reporte()
            
        self.after(500, _finalizar)

    def build_tab_reportes(self):

        # 1. HEADER CON TARJETAS KPI DE HISTORIAL
        self.frame_kpis_historial = ctk.CTkFrame(self.tab_reportes, fg_color="transparent")
        self.frame_kpis_historial.pack(fill="x", padx=10, pady=(0, 8))

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

        self.card_hist_total = self.crear_card_kpi(
            self.frame_kpis_historial, "Total Procesadas", "0", ("#d9480f", "#ff7800"),
            icono="📦", imagen_path=os.path.join(assets_dir, "kpi_cola.png")
        )
        self.card_hist_total.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_exito = self.crear_card_kpi(
            self.frame_kpis_historial, "Cuentas Exitosas", "0", ("#2b8a3e", "#51cf66"),
            icono="✅", imagen_path=os.path.join(assets_dir, "kpi_exito.png")
        )
        self.card_hist_exito.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_tasa = self.crear_card_kpi(
            self.frame_kpis_historial, "Tasa de Éxito", "0%", ("#d9480f", "#ff7800"),
            icono="📈"
        )
        self.card_hist_tasa.pack(side="left", fill="x", expand=True, padx=4)

        self.card_hist_fallo = self.crear_card_kpi(
            self.frame_kpis_historial, "Cuentas Fallidas", "0", ("#c92a2a", "#ff6b6b"),
            icono="❌", imagen_path=os.path.join(assets_dir, "kpi_fallo.png")
        )
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

        # Filtro de Servicio
        ctk.CTkLabel(frame_toolbar, text="Servicio:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(15, 5), pady=8)
        self.cmb_filtro_servicio = ctk.CTkOptionMenu(
            frame_toolbar,
            values=["Todos los Servicios", "Solo OTT", "Solo Fibra"],
            command=lambda v: self.filtrar_historial(),
            width=140,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff")
        )
        self.cmb_filtro_servicio.pack(side="left", padx=5, pady=8)

        # Filtro de Estado
        ctk.CTkLabel(frame_toolbar, text="Estado:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(15, 5), pady=8)
        self.cmb_filtro_estado = ctk.CTkOptionMenu(
            frame_toolbar,
            values=["Todos los Estados", "Solo Exitosos", "Solo Errores"],
            command=lambda v: self.filtrar_historial(),
            width=160,
            fg_color=("#e9ecef", "#25262b"),
            button_color="#ff7800",
            button_hover_color="#e66a00",
            text_color=("#212529", "#ffffff")
        )
        self.cmb_filtro_estado.pack(side="left", padx=5, pady=8)

        # Filtro de Fechas con Calendario
        ctk.CTkLabel(frame_toolbar, text="Fecha:", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#212529", "#f8f9fa")).pack(side="left", padx=(15, 5), pady=8)
        
        self.fecha_seleccionada = None
        self.filtro_fecha_activo = False
        
        self.btn_fecha = ctk.CTkButton(
            frame_toolbar, 
            text="Seleccionar Fecha", 
            width=140,
            fg_color=("#e9ecef", "#2b2d31"),
            hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            command=self.abrir_calendario
        )
        self.btn_fecha.pack(side="left", padx=5, pady=8)

        self.btn_limpiar_fecha = ctk.CTkButton(
            frame_toolbar,
            text="✖",
            width=28,
            fg_color="#dc3545",
            hover_color="#c82333",
            text_color="white",
            command=self.limpiar_filtro_fecha
        )
        self.btn_limpiar_fecha.pack(side="left", padx=(0, 10), pady=8)

        # Botón Recargar
        ctk.CTkButton(
            frame_toolbar,
            text="Recargar",
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

        columnas = ("fecha", "servicio", "tipo", "titular", "id_cliente", "email", "ubicacion", "plan", "estado")
        self.tree_historial = ttk.Treeview(frame_tabla_container, columns=columnas, show="headings", style="Historial.Treeview", selectmode="extended")

        # Configurar Columnas
        self.tree_historial.heading("fecha", text="Fecha / Hora")
        self.tree_historial.heading("servicio", text="Servicio")
        self.tree_historial.heading("tipo", text="Tipo")
        self.tree_historial.heading("titular", text="Titular / Empresa")
        self.tree_historial.heading("id_cliente", text="N° Cliente")
        self.tree_historial.heading("email", text="Correo (Mailbox)")
        self.tree_historial.heading("ubicacion", text="Ubicación")
        self.tree_historial.heading("plan", text="Plan & Promo")
        self.tree_historial.heading("estado", text="Estado")

        self.tree_historial.column("fecha", width=140, anchor="center")
        self.tree_historial.column("servicio", width=80, anchor="center")
        self.tree_historial.column("tipo", width=95, anchor="center")
        self.tree_historial.column("titular", width=220, anchor="w")
        self.tree_historial.column("id_cliente", width=100, anchor="center")
        self.tree_historial.column("email", width=270, anchor="w")
        self.tree_historial.column("ubicacion", width=120, anchor="center")
        self.tree_historial.column("plan", width=210, anchor="w")
        self.tree_historial.column("estado", width=260, anchor="w")

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
        self.tree_historial.bind("<Control-c>", self.copiar_correo_seleccionado)
        self.tree_historial.bind("<Control-C>", self.copiar_correo_seleccionado)

        # 4. BOTONES DE ACCIONES INFERIORES
        frame_bottom = ctk.CTkFrame(self.tab_reportes, fg_color="transparent")
        frame_bottom.pack(fill="x", padx=10, pady=(0, 5))

        def _sel_todos():
            self.tree_historial.selection_set(self.tree_historial.get_children())

        def _desel_todos():
            self.tree_historial.selection_remove(self.tree_historial.get_children())

        ctk.CTkButton(frame_bottom, text="Todos", width=62, command=_sel_todos, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="Ninguno", width=68, command=_desel_todos, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="Evidencias", command=self.abrir_evidencia_seleccionada, fg_color="#ff7800", hover_color="#e66a00", text_color="#ffffff", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="Reenviar a la Cola", command=self.reintentar_cuenta_historial_seleccionada, fg_color=("#e9ecef", "#2b2d31"), hover_color=("#dee2e6", "#343a40"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="Carpeta General", command=self.abrir_carpeta_evidencias_general, fg_color=("#e9ecef", "#343a40"), hover_color=("#dee2e6", "#495057"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="CSV Excel", command=self.abrir_archivo_csv, fg_color=("#e9ecef", "#343a40"), hover_color=("#dee2e6", "#495057"), text_color=("#212529", "#ffffff"), font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(frame_bottom, text="Copiar ID", command=self.copiar_correo_seleccionado, fg_color=("#e8590c", "#d9480f"), hover_color=("#c92a2a", "#c92a2a"), text_color="#ffffff", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=3)

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
                                # Backward compatibility: if row is old (doesn't have Servicio at index 1)
                                if len(r) == 12:
                                    servicio = "OTT" if r[6].strip().upper() == "OTT" else "FTTH"
                                    r.insert(1, servicio)
                                
                                if len(r) >= 10:
                                    total_cuentas += 1
                                    estado = r[9].strip()
                                    if "EXITOSO" in estado.upper():
                                        exitosas += 1
                                    else:
                                        fallidas += 1
                                    self.datos_historial_raw.append(r)
            except Exception as e:
                print(f"Error leyendo cuentas_creadas.csv: {e}")

        # Collect unique dates - (ya no es necesario llenar dropdown, pero se deja para futura referencia)
        fechas_unicas = set()
        for r in self.datos_historial_raw:
            if r and len(r) > 0:
                fecha_solo = r[0].split(" ")[0].strip()
                fechas_unicas.add(fecha_solo)
        
        # Invertir para mostrar las más recientes arriba
        self.datos_historial_raw.reverse()

        tasa_pct = f"{(exitosas / total_cuentas * 100):.1f}%" if total_cuentas > 0 else "0%"
        self.card_hist_total.lbl_val.configure(text=str(total_cuentas))
        self.card_hist_exito.lbl_val.configure(text=str(exitosas))
        self.card_hist_tasa.lbl_val.configure(text=tasa_pct)
        self.card_hist_fallo.lbl_val.configure(text=str(fallidas))

        self.filtrar_historial()

    def abrir_calendario(self):
        if getattr(self, 'ventana_calendario', None) is not None and self.ventana_calendario.winfo_exists():
            self.ventana_calendario.focus()
            return

        self.ventana_calendario = ModernCalendar(self, self.aplicar_filtro_fecha)
        # Centrar sobre la ventana principal
        self.ventana_calendario.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (300 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (320 // 2)
        self.ventana_calendario.geometry(f"+{x}+{y}")
        
        # Hacerla modal para que no se pueda clickear atrás ni abrir infinitas veces
        self.ventana_calendario.grab_set()

    def aplicar_filtro_fecha(self, fecha_str):
        self.fecha_seleccionada = fecha_str
        self.filtro_fecha_activo = True
        self.btn_fecha.configure(text=f"{fecha_str}")
        self.filtrar_historial()

    def limpiar_filtro_fecha(self):
        self.fecha_seleccionada = None
        self.filtro_fecha_activo = False
        self.btn_fecha.configure(text="Seleccionar Fecha")
        self.filtrar_historial()

    def resolver_tipo_cliente(self, tipo_persona, doc_rif):
        doc_str = str(doc_rif).strip()
        doc_lower = doc_str.lower()
        tipo_lower = str(tipo_persona).lower()

        # 1. Personas Jurídicas (3 tipos)
        if "government" in doc_lower or doc_str.startswith("G-"):
            return "Government"
        if "personal signature" in doc_lower:
            return "Personal Signature"
        if "legal" in doc_lower or "jurídica" in tipo_lower or "juridica" in tipo_lower or doc_str.startswith("J-"):
            return "Legal"

        # 2. Personas Naturales (3 tipos)
        if "foreigner" in doc_lower or doc_str.startswith("E-"):
            return "Foreigner"
        if "passport" in doc_lower or doc_str.startswith("P-"):
            return "Passport"
        if "venezuelan" in doc_lower or doc_str.startswith("V-"):
            return "Venezuelan"

        # Fallback por defecto si no se deduce del doc
        if "jurídica" in tipo_lower or "juridica" in tipo_lower:
            return "Legal"
        return "Venezuelan"

    def filtrar_historial(self):
        # Limpiar tabla
        for item in self.tree_historial.get_children():
            self.tree_historial.delete(item)

        texto_busq = self.entry_busqueda_hist.get().strip().lower() if hasattr(self, 'entry_busqueda_hist') else ""
        filtro_estado = self.cmb_filtro_estado.get() if hasattr(self, 'cmb_filtro_estado') else "Todos los Estados"
        filtro_servicio = self.cmb_filtro_servicio.get() if hasattr(self, 'cmb_filtro_servicio') else "Todos los Servicios"

        idx = 0
        for r in self.datos_historial_raw:
            # r: [0:Fecha, 1:Servicio, 2:Tipo, 3:Doc, 4:Nombre, 5:Email, 6:Tel, 7:Ubic, 8:Plan, 9:Estado, 10:Total_seg, 11:Desglose, 12:ID_Cliente]
            estado = r[9].strip() if len(r) > 9 else ""
            es_exitoso = "EXITOSO" in estado.upper()
            servicio_val = r[1].strip().upper() if len(r) > 1 else ""

            # Filtro por servicio
            if filtro_servicio == "Solo OTT" and servicio_val != "OTT":
                continue
            if filtro_servicio == "Solo Fibra" and servicio_val != "FTTH":
                continue

            # Filtro por estado
            if filtro_estado == "Solo Exitosos" and not es_exitoso:
                continue
            if filtro_estado == "Solo Errores" and es_exitoso:
                continue

            # Filtro por fecha
            if self.filtro_fecha_activo and self.fecha_seleccionada and not r[0].startswith(self.fecha_seleccionada):
                continue

            # Filtro por búsqueda de texto
            if texto_busq:
                linea_unida = " ".join(r).lower()
                if texto_busq not in linea_unida:
                    continue

            tag_estado = "tag_exito" if es_exitoso else "tag_error"
            tag_fila = "fila_par" if idx % 2 == 0 else "fila_impar"

            servicio = r[1] if len(r) > 1 else ""
            tipo_raw = r[2] if len(r) > 2 else ""
            doc_raw = r[3] if len(r) > 3 else ""
            tipo_limpio = self.resolver_tipo_cliente(tipo_raw, doc_raw)

            id_cliente = r[12] if len(r) > 12 and r[12].strip() else "-"

            valores = (
                r[0],        # Fecha
                servicio,    # Servicio (FTTH / OTT)
                tipo_limpio, # Tipo limpio del sistema
                r[4],        # Titular / Empresa
                id_cliente,  # N° Cliente
                r[5],        # Email
                r[7],        # Ubicacion (sin telefono)
                r[8],        # Plan
                r[9]         # Estado
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
        servicio = str(valores[1]).strip().upper()
        email = str(valores[5])
        mailbox = email.split("@")[0].strip()
        fecha_solo = fecha_hora.split(" ")[0].strip()

        # Determinar carpeta base según servicio
        carpeta_base = "Evidencias_QA" if servicio == "OTT" else "Evidencias_QA_Fibra"

        # Buscar carpeta específica de evidencias
        ruta_directa = os.path.join(carpeta_base, fecha_solo, mailbox)
        if os.path.exists(ruta_directa):
            os.startfile(ruta_directa)
            return

        # Búsqueda recursiva si la fecha difiere
        encontrado = False
        if os.path.exists(carpeta_base):
            for root, dirs, files in os.walk(carpeta_base):
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

    def copiar_correo_seleccionado(self, event=None):
        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor selecciona al menos una fila para copiar su correo.")
            return

        correos = []
        for item_id in seleccion:
            item = self.tree_historial.item(item_id)
            valores = item.get("values", [])
            if valores and len(valores) >= 5:
                id_cliente = str(valores[3]).strip()
                email = str(valores[4]).strip()
                
                if id_cliente and id_cliente not in ["-", "N/A", "None", ""]:
                    correos.append(id_cliente)
                elif email and email not in ["-", "N/A", "None", ""]:
                    correos.append(email)

        if not correos:
            messagebox.showwarning("Atención", "No se encontraron correos válidos en las filas seleccionadas.")
            return

        # Copiar al portapapeles (un correo por línea)
        texto_copiado = "\n".join(correos)
        self.clipboard_clear()
        self.clipboard_append(texto_copiado)

        # Mensaje simple con la cantidad
        total = len(correos)
        if total == 1:
            messagebox.showinfo("Copiado", "✅ Identificador copiado al portapapeles exitosamente.")
        else:
            messagebox.showinfo("Copiado", f"✅ Se copiaron {total} identificadores al portapapeles exitosamente.")

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
            if not valores or len(valores) < 7:
                continue

            tipo_sistema = str(valores[1]).strip()
            ubicacion = str(valores[5]).strip()
            plan_raw = str(valores[6]).strip()

            sin_promo = "[Sin Promo]" in plan_raw
            plan_nombre = plan_raw.replace("[Sin Promo]", "").strip()

            if plan_nombre not in CATALOGO_PLANES:
                posibles = [k for k in CATALOGO_PLANES.keys() if plan_nombre.lower() in k.lower() or k.lower() in plan_nombre.lower()]
                if posibles:
                    plan_nombre = posibles[0]
                else:
                    plan_nombre = list(CATALOGO_PLANES.keys())[0] if CATALOGO_PLANES else "Compra: 400 mbps + Gold"

            if tipo_sistema in ["Legal", "Government", "Personal Signature"]:
                tipo_persona = "Persona jurídica"
                item_nuevo = {
                    "tipo_persona": tipo_persona,
                    "tipo_rif": tipo_sistema,
                    "ubicacion": ubicacion,
                    "plan_seleccionado": plan_nombre,
                    "aplicar_promocion": not sin_promo
                }
            else:
                tipo_persona = "Persona natural"
                tipo_doc = tipo_sistema if tipo_sistema in ["Venezuelan", "Foreigner", "Passport"] else "Venezuelan"
                item_nuevo = {
                    "tipo_persona": tipo_persona,
                    "tipo_doc": tipo_doc,
                    "ubicacion": ubicacion,
                    "plan_seleccionado": plan_nombre,
                    "aplicar_promocion": not sin_promo
                }

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

        ctk.CTkLabel(form_frame, text="Prefijo del Correo (Fibra):").grid(row=1, column=0, sticky="w", pady=8)
        self.entry_prefijo = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_prefijo.insert(0, self.config_sys.get("prefijo_email", DEFAULT_CONFIG["prefijo_email"]))
        self.entry_prefijo.grid(row=1, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Prefijo del Correo (OTT):").grid(row=2, column=0, sticky="w", pady=8)
        self.entry_prefijo_ott = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_prefijo_ott.insert(0, self.config_sys.get("prefijo_email_ott", DEFAULT_CONFIG.get("prefijo_email_ott", "CAMBIALO_OTT")))
        self.entry_prefijo_ott.grid(row=2, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Dominio del Correo:").grid(row=3, column=0, sticky="w", pady=8)
        self.entry_dominio = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_dominio.insert(0, self.config_sys.get("dominio_email", DEFAULT_CONFIG["dominio_email"]))
        self.entry_dominio.grid(row=3, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Usuario de Login:").grid(row=4, column=0, sticky="w", pady=8)
        self.entry_usuario = ctk.CTkEntry(form_frame, width=450, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_usuario.insert(0, self.config_sys.get("usuario_login", DEFAULT_CONFIG["usuario_login"]))
        self.entry_usuario.grid(row=4, column=1, padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Contraseña de Login:").grid(row=5, column=0, sticky="w", pady=8)
        self.entry_password = ctk.CTkEntry(form_frame, width=450, show="*", fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_password.insert(0, self.config_sys.get("password_login", DEFAULT_CONFIG["password_login"]))
        self.entry_password.grid(row=5, column=1, padx=10, pady=8)

        # Correlativo actual
        ctk.CTkLabel(form_frame, text="Contador de Correo Actual (Fibra):").grid(row=6, column=0, sticky="w", pady=8)
        correlativo_actual = leer_correlativo_actual()
        self.entry_correlativo = ctk.CTkEntry(form_frame, width=200, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_correlativo.insert(0, str(correlativo_actual))
        self.entry_correlativo.grid(row=6, column=1, sticky="w", padx=10, pady=8)

        ctk.CTkLabel(form_frame, text="Contador de Correo Actual (OTT):").grid(row=7, column=0, sticky="w", pady=8)
        correlativo_actual_ott = leer_correlativo_actual("contador_email_ott.txt")
        self.entry_correlativo_ott = ctk.CTkEntry(form_frame, width=200, fg_color=("#ffffff", "#25262b"), border_color=("#ced4da", "#373a40"))
        self.entry_correlativo_ott.insert(0, str(correlativo_actual_ott))
        self.entry_correlativo_ott.grid(row=7, column=1, sticky="w", padx=10, pady=8)

        # 6. Modo de Ejecución
        ctk.CTkLabel(form_frame, text="Modo de Ejecución:", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, sticky="w", pady=10)
        modo_actual = self.config_sys.get("modo_ejecucion", "completo")
        val_modo_inicial = "✍️ Manual (Hasta Paso 3)" if modo_actual == "hasta_paso_3" else "🚀 Completa (Paso 0 al 5)"
        
        self.seg_modo_cfg = ctk.CTkSegmentedButton(
            form_frame,
            values=["🚀 Completa (Paso 0 al 5)", "✍️ Manual (Hasta Paso 3)"],
            command=self.al_cambiar_modo_ejecucion_cfg,
            selected_color="#ff7800",
            selected_hover_color="#e66a00",
            unselected_color=("#e9ecef", "#2b2d31"),
            unselected_hover_color=("#dee2e6", "#343a40"),
            text_color=("#212529", "#ffffff"),
            height=32
        )
        self.seg_modo_cfg.set(val_modo_inicial)
        self.seg_modo_cfg.grid(row=8, column=1, sticky="w", padx=10, pady=10)

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
        self.config_sys["prefijo_email_ott"] = self.entry_prefijo_ott.get().strip()
        self.config_sys["dominio_email"] = self.entry_dominio.get().strip()
        self.config_sys["usuario_login"] = self.entry_usuario.get().strip()
        self.config_sys["password_login"] = self.entry_password.get().strip()

        tema_sel = "Dark" if "Oscuro" in self.seg_tema.get() else "Light"
        self.config_sys["tema_apariencia"] = tema_sel

        if hasattr(self, 'seg_modo_cfg'):
            modo_sel = "hasta_paso_3" if "Manual" in self.seg_modo_cfg.get() else "completo"
            self.config_sys["modo_ejecucion"] = modo_sel

        try:
            nuevo_corr = int(self.entry_correlativo.get().strip())
            actualizar_correlativo_manual(nuevo_corr)
        except ValueError:
            pass

        try:
            nuevo_corr_ott = int(self.entry_correlativo_ott.get().strip())
            actualizar_correlativo_manual(nuevo_corr_ott, "contador_email_ott.txt")
        except ValueError:
            pass

        if guardar_configuracion(self.config_sys):
            messagebox.showinfo("Éxito", "Configuración guardada exitosamente en config_gideon.json.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def al_cambiar_modo_ejecucion(self, valor):
        if "Manual" in valor or "Paso 3" in valor:
            self.config_sys["modo_ejecucion"] = "hasta_paso_3"
            self.btn_iniciar.configure(
                text="✍️ INICIAR HASTA PASO 3",
                fg_color="#d9480f",
                hover_color="#c2410c"
            )
            self.log_salida("ℹ️ Modo activo: CREACIÓN MANUAL (Paso 0 a Paso 3). El navegador se mantendrá abierto en Package Selection.")
            if hasattr(self, 'seg_modo_cfg'):
                self.seg_modo_cfg.set("✍️ Manual (Hasta Paso 3)")
        else:
            self.config_sys["modo_ejecucion"] = "completo"
            self.btn_iniciar.configure(
                text="🚀 INICIAR PROCESAMIENTO MASIVO",
                fg_color="#ff7800",
                hover_color="#e66a00"
            )
            self.log_salida("ℹ️ Modo activo: CREACIÓN COMPLETA (Paso 0 a Paso 5 con OTP).")
            if hasattr(self, 'seg_modo_cfg'):
                self.seg_modo_cfg.set("🚀 Completa (Paso 0 al 5)")
        guardar_configuracion(self.config_sys)

    def al_cambiar_modo_ejecucion_cfg(self, valor):
        if hasattr(self, 'seg_modo_control'):
            self.seg_modo_control.set(valor)
        self.al_cambiar_modo_ejecucion(valor)

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
        filtro_fam = self.cmb_filtro_fam.get() if hasattr(self, 'cmb_filtro_fam') else "Bundle: Todos"
        
        modalidad = "Compra" if "Compra" in filtro_mod else "Alquiler"
        
        planes_disponibles = list(CATALOGO_PLANES.keys())
        if not planes_disponibles:
            self.plan_seleccionado_id = None
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

        # 3. Filtrar por Familia TV
        if "todo" not in filtro_fam.lower():
            lista_filtrada = [k for k in lista_filtrada if CATALOGO_PLANES[k].get("familia", "Otros") == filtro_fam]

        if not lista_filtrada:
            lista_filtrada = [f"(Sin planes para los filtros seleccionados)"]

        # Limpiar tarjetas actuales
        if hasattr(self, 'frame_lista_planes'):
            for child in self.frame_lista_planes.winfo_children():
                child.destroy()
            self.tarjetas_planes.clear()
            
            for plan_id in lista_filtrada:
                if plan_id.startswith("(Sin planes"):
                    ctk.CTkLabel(self.frame_lista_planes, text=plan_id, font=ctk.CTkFont(size=12, slant="italic"), text_color="#adb5bd").pack(pady=20)
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
        
        # Extraer velocidades y familias únicas del catálogo para poblar los filtros
        velocidades_encontradas = set()
        familias_encontradas = set()
        for v in CATALOGO_PLANES.values():
            vel = v.get("velocidad", "Otro")
            if vel != "Otro":
                velocidades_encontradas.add(vel)
            fam = v.get("familia", "Otros")
            familias_encontradas.add(fam)
        
        ordenadas = sorted(list(velocidades_encontradas), key=lambda x: int(''.join([c for c in x if c.isdigit()]) or 0))
        opciones_filtro = ["Velocidad: Todas"] + ordenadas
        if any(v.get("velocidad") == "Otro" for v in CATALOGO_PLANES.values()):
            opciones_filtro.append("Otras")
            
        self.cmb_filtro_vel.configure(values=opciones_filtro)
        self.cmb_filtro_vel.set("Velocidad: Todas")
        
        familias_ordenadas = sorted(list(familias_encontradas))
        opciones_fam = ["Bundle: Todos"] + familias_ordenadas
        if hasattr(self, 'cmb_filtro_fam'):
            self.cmb_filtro_fam.configure(values=opciones_fam)
            self.cmb_filtro_fam.set("Bundle: Todos")
            
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
        
        self.estado_hilos.clear()
        for id_hilo, info in self.widgets_monitor_hilos.items():
            info["card"].destroy()
        self.widgets_monitor_hilos.clear()
        if hasattr(self, 'btn_reintentar_tanda'):
            self.btn_reintentar_tanda.configure(
                state="disabled",
                text="🔁 Reintentar (0)",
                fg_color=("#e9ecef", "#2b2d31"),
                text_color=("#212529", "#ffffff")
            )
        self.btn_iniciar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        if hasattr(self, 'seg_modo_control'):
            self.seg_modo_control.configure(state="disabled")
        if hasattr(self, 'seg_modo_cfg'):
            self.seg_modo_cfg.configure(state="disabled")
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

                if config.get("is_ott"):
                    executor.submit(
                        crear_cuenta_ott,
                        i, config, self.config_sys, self.log_salida,
                        _crear_cb(config),
                        self.cancel_event,
                        self.update_thread_status
                    )
                else:
                    executor.submit(
                        crear_cuenta_individual,
                        i, config, self.config_sys, self.log_salida,
                        _crear_cb(config),
                        self.cancel_event,
                        self.update_thread_status
                    )
                time.sleep(6)
        
        def _finalizar():
            if self.cancel_event.is_set():
                self.log_salida("🛑 Procesamiento detenido y cancelado por el usuario.")
            else:
                self.log_salida("🎉 Proceso finalizado por completo.")
            self.btn_iniciar.configure(state="normal")
            self.btn_cancelar.configure(state="disabled")
            if hasattr(self, 'seg_modo_control'):
                self.seg_modo_control.configure(state="normal")
            if hasattr(self, 'seg_modo_cfg'):
                self.seg_modo_cfg.configure(state="normal")
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

    def update_thread_status(self, id_hilo, paso_actual, inicio_step_timestamp, estado):
        self.estado_hilos[id_hilo] = {
            "Paso": paso_actual,
            "TiempoInicio": inicio_step_timestamp,
            "Estado": estado
        }
        # Crear widget de la tarjeta si no existe
        if id_hilo not in self.widgets_monitor_hilos and hasattr(self, 'frame_monitor_hilos'):
            card = ctk.CTkFrame(self.frame_monitor_hilos, fg_color=("#ffffff", "#1a1b1e"), border_width=1, border_color=("#ced4da", "#2c2e33"), corner_radius=6)
            card.pack(side="left", fill="x", expand=True, padx=(0, 4))
            lbl_title = ctk.CTkLabel(card, text=f"Hilo {id_hilo}", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#495057", "#ced4da"))
            lbl_title.pack(anchor="w", padx=8, pady=(4, 0))
            lbl_step = ctk.CTkLabel(card, text=paso_actual, font=ctk.CTkFont(size=11), text_color=("#212529", "#f8f9fa"))
            lbl_step.pack(anchor="w", padx=8)
            lbl_time = ctk.CTkLabel(card, text="⏱️ 00:00", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#ff7800", "#ff922b"))
            lbl_time.pack(anchor="w", padx=8, pady=(0, 4))
            self.widgets_monitor_hilos[id_hilo] = {"card": card, "lbl_step": lbl_step, "lbl_time": lbl_time}
            
    def actualizar_cronometros_ui(self):
        ahora = time.time()
        for id_hilo, info in self.estado_hilos.items():
            if id_hilo in self.widgets_monitor_hilos:
                w = self.widgets_monitor_hilos[id_hilo]
                w["lbl_step"].configure(text=info["Paso"])
                
                if info["Estado"] == "Activo":
                    transcurrido = int(ahora - info["TiempoInicio"])
                    mins = transcurrido // 60
                    secs = transcurrido % 60
                    w["lbl_time"].configure(text=f"⏱️ {mins:02d}:{secs:02d}", text_color=("#ff7800", "#ff922b"))
                elif info["Estado"] == "Exito":
                    w["lbl_step"].configure(text="Completado")
                    w["lbl_time"].configure(text_color=("#2b8a3e", "#51cf66"))
                elif info["Estado"] == "Error":
                    w["lbl_time"].configure(text_color=("#c92a2a", "#e03131"))
                    
        self.after(1000, self.actualizar_cronometros_ui)

if __name__ == "__main__":
    app = AppGideon()
    app.mainloop()
