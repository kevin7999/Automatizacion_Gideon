import os
import json
import threading

CONFIG_FILE = "config_gideon.json"

DEFAULT_CONFIG = {
    "prefijo_email": "CAMBIALO_Fibrastest",
    "prefijo_email_ott": "CAMBIALO_OTT",
    "usuario_login": "TestSebastian",
    "password_login": "I4FiJJ02aPY0af2",
    "hilos_simultaneos": 2,
    "hilos_simultaneos_ott": 2,
    "modo_headless": False,
    "dominio_email": "maildrop.cc",
    "tema_apariencia": "Dark",
    "modo_ejecucion": "completo"
}

URL_LOGIN = "https://eccb-dev-simple-ftth.evergent.com/login"
URL_CREATE_ACCOUNT = "https://eccb-dev-simple-ftth.evergent.com/galaxyOTTFTTH/createAccount"

# Mutexes globales para sincronización de hilos concurrentes
lock_correlativo = threading.Lock()
lock_registro = threading.Lock()
lock_login = threading.Lock()

def cargar_configuracion(ruta_archivo=CONFIG_FILE):
    if os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
                config = dict(DEFAULT_CONFIG)
                config.update(datos)
                return config
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def guardar_configuracion(config, ruta_archivo=CONFIG_FILE):
    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False
