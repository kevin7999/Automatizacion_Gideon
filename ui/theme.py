# 🎨 Constantes de Diseño y Estilo Visual (GIDEON 4.0 - Obsidian & SimpleTV)

# --- FONDOS PRINCIPALES (OBSIDIAN DARK) ---
BG_APP = "#0D0E11"          # Fondo general oscuro de alta fidelidad
BG_SIDEBAR = "#121418"      # Sidebar contrastado
BG_CARD = "#181A20"         # Tarjetas y contenedores elevados
BG_INPUT = "#20232B"        # Campos de texto y selectores
BORDER_SUBTLE = "#2A2E39"   # Bordes finos de 1px

# --- COLORES PRIMARIOS (SIMPLETV ORANGE) ---
PRIMARY_ORANGE = "#FF7800"
PRIMARY_HOVER = "#E66A00"
PRIMARY_GLOW = "#FFA94D"

# --- COLORES DE ESTADO (SEMÁFORO Y ALERTAS) ---
STATUS_SUCCESS = "#10B981"  # Verde esmeralda
STATUS_ERROR = "#EF4444"    # Rojo carmesí
STATUS_WARNING = "#F59E0B"  # Ámbar OTP
STATUS_INFO = "#3B82F6"     # Azul cian

# --- TEXTOS ---
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#9CA3AF"  # Gris claro (mutado)
TEXT_DISABLED = "#4B5563"

# --- TIPOGRAFÍA (Tokens de Escala) ---
# Se asume disponibilidad en Windows (Segoe UI) o fallback estándar
FONT_TITLE = ("Segoe UI Semibold", 18)
FONT_SUBTITLE = ("Segoe UI Semibold", 14)
FONT_BODY = ("Segoe UI", 12)
FONT_BODY_BOLD = ("Segoe UI Semibold", 12)
FONT_CONSOLE = ("Consolas", 11)
FONT_CONSOLE_BOLD = ("Consolas", 11, "bold")
FONT_MINI = ("Segoe UI", 10)

# --- PALETAS DE KPIs (Compatible con diseño viejo para evitar rupturas) ---
KPI_COLORS = {
    "total": (PRIMARY_ORANGE, PRIMARY_ORANGE),
    "ejecucion": (STATUS_WARNING, STATUS_WARNING),
    "exito": (STATUS_SUCCESS, STATUS_SUCCESS),
    "fallo": (STATUS_ERROR, STATUS_ERROR)
}
