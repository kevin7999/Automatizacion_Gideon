from .config import (
    CONFIG_FILE, DEFAULT_CONFIG, URL_LOGIN, URL_CREATE_ACCOUNT,
    lock_correlativo, lock_registro, lock_login,
    cargar_configuracion, guardar_configuracion
)
from .generadores import (
    limpiar_texto_crm, generar_telefono_ve, generar_documento_ve,
    generar_nombre_humano_limpio, PREFIJOS_VE
)
from .catalogos import (
    ARCHIVO_DIRECCIONES, ARCHIVO_PLANES, PASSWORD_DEFAULT,
    cargar_catalogo_direcciones, cargar_catalogo_direcciones_ott,
    cargar_catalogo_planes
)
from .correlativos import (
    leer_correlativo_actual, obtener_siguiente_correlativo,
    actualizar_correlativo_manual, formatear_error_amigable,
    registrar_cuenta_creada
)
from .database import (
    DB_PATH, get_conn, cerrar_conn_hilo,
    inicializar_base_datos, migrar_datos_legacy_si_necesario,
    registrar_cuenta_en_bd, consultar_historial_y_kpis
)
from .paths import DIR_RAIZ, resolver_ruta
