import os
import re
import csv
import json
from .config import lock_correlativo, lock_registro

ARCHIVO_CONTADOR = "contador_email.txt"
ARCHIVO_CSV = "cuentas_creadas.csv"
ARCHIVO_JSON = "historial_cuentas.json"

def leer_correlativo_actual(archivo=ARCHIVO_CONTADOR, valor_inicial=236):
    with lock_correlativo:
        if not os.path.exists(archivo):
            return valor_inicial
        else:
            try:
                with open(archivo, "r") as f:
                    contenido = f.read().strip()
                    return int(contenido) if contenido.isdigit() else valor_inicial
            except Exception:
                return valor_inicial

def obtener_siguiente_correlativo(archivo=ARCHIVO_CONTADOR, valor_inicial=236):
    with lock_correlativo:
        if not os.path.exists(archivo):
            numero = valor_inicial
        else:
            try:
                with open(archivo, "r") as f:
                    contenido = f.read().strip()
                    numero = int(contenido) if contenido.isdigit() else valor_inicial
            except Exception:
                numero = valor_inicial
        
        with open(archivo, "w") as f:
            f.write(str(numero + 1))
            
        return numero

def actualizar_correlativo_manual(nuevo_valor, archivo=ARCHIVO_CONTADOR):
    with lock_correlativo:
        try:
            with open(archivo, "w") as f:
                f.write(str(nuevo_valor))
            return True
        except Exception:
            return False

def formatear_error_amigable(paso, err):
    err_str = str(err).strip()
    err_lower = err_str.lower()
    
    # 1. Fallos de OTP específicos
    if "validación de otp" in err_lower or "otp" in err_lower:
        if "correo" in err_lower or "maildrop" in err_lower:
            return f"[{paso}] No se recibió el correo de confirmación en Maildrop tras varios reintentos."
        elif "rechazó" in err_lower or "no válido" in err_lower or "invalido" in err_lower:
            return f"[{paso}] El CRM rechazó el código OTP o el formulario generó un código inválido."
        else:
            return f"[{paso}] Falló la validación del código OTP en el CRM (3 intentos agotados)."

    # 1.1. Fallos de CRM Lento o Congestionado y Login
    if "congestionado" in err_lower or "congelado" in err_lower:
        return f"[{paso}] El CRM estuvo excesivamente lento o congestionado al responder."
    if "iniciar sesión en el crm" in err_lower or "intentos de login" in err_lower:
        return f"[{paso}] El CRM no permitió el acceso o dio error de servidor tras 3 intentos de login."

    # 2. Timeouts de Playwright
    if "timeout" in err_lower or "waiting for locator" in err_lower:
        if "#accounttype" in err_lower or "accounttype" in err_lower or "login" in err_lower:
            return f"[{paso}] El CRM demoró en responder en el login o al abrir Paso 1."
        elif "internetprovider" in err_lower or "internet provider" in err_lower:
            return f"[{paso}] Demora al cargar o seleccionar el proveedor de internet anterior (Paso 3)."
        elif "installation address" in err_lower or "locate" in err_lower or "confirm address" in err_lower:
            return f"[{paso}] Demora en georreferenciación de dirección o validación de cobertura (Paso 2)."
        elif "packagetype" in err_lower or "package type" in err_lower or "package selection" in err_lower:
            return f"[{paso}] El CRM demoró en cargar la pantalla de paquetes (Paso 4)."
        elif "list of equipments" in err_lower or "router" in err_lower or "equipments" in err_lower:
            return f"[{paso}] Demora cargando la lista de equipos y routers (Paso 4.1)."
        elif "order details" in err_lower or "order confirmation" in err_lower or "order" in err_lower:
            return f"[{paso}] Demora cargando la pantalla final de confirmación de orden (Paso 5)."
        else:
            match = re.search(r'waiting for (locator\([^)]+\)|"[^"]+")', err_str)
            loc = match.group(1) if match else "elemento del CRM"
            return f"[{paso}] Tiempo de espera agotado esperando {loc}."

    # 3. Fallos de elemento no conectado o DOM inestable
    if "is not attached to the dom" in err_lower or "target closed" in err_lower or "context or browser has been closed" in err_lower:
        return f"[{paso}] La sesión del navegador o pestaña del CRM se cerró o reinició inesperadamente."

    # 4. Mensajes generales
    err_limpio = err_str.split("\n")[0].strip()
    if len(err_limpio) > 110:
        err_limpio = err_limpio[:107] + "..."
    return f"[{paso}] {err_limpio}"

def registrar_cuenta_creada(datos_cuenta, archivo_csv=ARCHIVO_CSV, archivo_json=ARCHIVO_JSON):
    with lock_registro:
        datos_limpios = {}
        for k, v in datos_cuenta.items():
            if isinstance(v, str):
                datos_limpios[k] = " ".join(v.split())
            else:
                datos_limpios[k] = v

        file_exists = os.path.exists(archivo_csv)
        campos = ["Fecha_Hora", "Servicio", "Tipo_Persona", "Documento_RIF", "Nombre_o_Empresa", "Email", "Telefono", "Ubicacion", "Plan", "Estado", "Tiempo_Total_Segundos", "Desglose_Tiempos", "ID_Cliente"]
        try:
            with open(archivo_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(datos_limpios)
        except Exception as e:
            print(f"Error escribiendo en CSV: {e}")

        historial = []
        if os.path.exists(archivo_json):
            try:
                with open(archivo_json, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        historial = datos
            except Exception:
                historial = []

        historial.append(datos_limpios)
        try:
            with open(archivo_json, "w", encoding="utf-8") as f:
                json.dump(historial, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error escribiendo en JSON: {e}")
