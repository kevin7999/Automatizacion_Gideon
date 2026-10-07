import os
import json
import gspread
from google.oauth2.service_account import Credentials
from core.config import lock_registro, cargar_configuracion
from core.catalogos import PASSWORD_DEFAULT

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def obtener_cliente_sheets():
    # La credencial está un nivel arriba de GIDEON (GIDEON 3.1/credenciales_google.json)
    ruta_credenciales = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "credenciales_google.json")
    if not os.path.exists(ruta_credenciales):
        # Fallback al directorio actual
        ruta_credenciales = "credenciales_google.json"
        if not os.path.exists(ruta_credenciales):
            raise FileNotFoundError(f"No se encontró el archivo de credenciales_google.json")
    
    credentials = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
    return gspread.authorize(credentials)

def sincronizar_hacia_google_sheets(url_sheet, archivo_json="historial_cuentas.json", log_callback=None):
    if not url_sheet:
        raise ValueError("URL del Google Sheet no configurada.")
        
    try:
        if log_callback: log_callback("🔄 Conectando con Google Cloud y verificando acceso al Sheet...")
        client = obtener_cliente_sheets()
        spreadsheet = client.open_by_url(url_sheet)
    except Exception as e:
        raise Exception(f"Fallo al conectar con Google Sheets. ¿Verificaste si compartiste el Excel con el bot?: {str(e)}")

    with lock_registro:
        if not os.path.exists(archivo_json):
            if log_callback: log_callback("⚠️ No hay historial local para sincronizar.")
            return 0

        with open(archivo_json, "r", encoding="utf-8") as f:
            try:
                historial = json.load(f)
            except json.JSONDecodeError:
                historial = []

        config = cargar_configuracion()
        agente_id = config.get("agente_id", "Operador_Sin_Nombre")
        
        # --- Lógica Multiusuario: Una hoja (pestaña) por Agente ---
        try:
            sheet = spreadsheet.worksheet(agente_id)
        except gspread.exceptions.WorksheetNotFound:
            if log_callback: log_callback(f"📝 Creando nueva pestaña en el Excel para el operador: {agente_id}")
            sheet = spreadsheet.add_worksheet(title=agente_id, rows=1000, cols=20)

        # 1. Escaneo Inteligente (Smart Scan): Leer la nube primero (solo la hoja de este agente)
        try:
            encabezados = sheet.row_values(1)
            if not encabezados:
                sheet.append_row(["Fecha", "Correo Electrónico", "Contraseña", "Estado/Ciudad", "Cp_Customer", "Doc", "IVA", "Plan Base", "Equipo", "Resultado", "Agente"])
                correos_existentes = set()
            else:
                # Descargar la columna B (Correos) omitiendo el encabezado
                correos_existentes = set(sheet.col_values(2)[1:])
        except Exception:
            sheet.append_row(["Fecha", "Correo Electrónico", "Contraseña", "Estado/Ciudad", "Cp_Customer", "Doc", "IVA", "Plan Base", "Equipo", "Resultado", "Agente"])
            correos_existentes = set()

        # 2. Cruce de datos (Filtrado)
        pendientes = []
        banderas_actualizadas = False

        for cta in historial:
            status = cta.get("Estado", cta.get("status", ""))
            es_exito = ("EXITO" in status.upper() or "EXITOSO" in status.upper())
            ya_sincronizado = cta.get("synced_n8n", False)
            plan = cta.get("Plan", cta.get("plan", "")).upper()
            email_cta = cta.get("Email", cta.get("email", ""))
            
            es_ftth = cta.get("Servicio", "").upper() != "OTT"
            en_nube = email_cta and (email_cta in correos_existentes)
            
            if en_nube:
                # Ya existe allá arriba, lo marcamos localmente para no procesarlo más
                if not ya_sincronizado:
                    cta["synced_n8n"] = True
                    banderas_actualizadas = True
            elif es_ftth and not ya_sincronizado:
                pendientes.append(cta)
        
        if banderas_actualizadas:
            with open(archivo_json, "w", encoding="utf-8") as f:
                json.dump(historial, f, indent=4, ensure_ascii=False)

        if not pendientes:
            if log_callback: log_callback("✅ No hay cuentas nuevas para sincronizar.")
            return 0


        # Preparar el lote de filas a insertar
        lote_filas = []
        for cta in pendientes:
            # 1. Fecha sin hora (solo YYYY-MM-DD)
            fecha_raw = cta.get("Fecha_Hora", cta.get("end_time", ""))
            fecha_limpia = fecha_raw.split(" ")[0] if fecha_raw else ""

            # 2. Lógica de IVA: Nueva Esparta = Sin IVA, resto = Con IVA
            ubicacion = cta.get("Ubicacion", cta.get("ubicacion", ""))
            estado_iva = "Sin IVA" if "esparta" in ubicacion.lower() else "Con IVA"

            # 3. Tipo de documento limpio (solo prefijo, sin número)
            doc_raw = cta.get("Documento_RIF", cta.get("documento", ""))
            doc_limpio = doc_raw.split(":")[0].strip() if doc_raw else ""

            # 4. Desglose de Plan Base y Equipo desde la cadena compuesta
            # Ej: "Compra: 400 mbps + Platino Wifi 5"
            #   → plan_base = "400 mbps + Platino"
            #   → equipo    = "Compra Wifi 5"
            plan_raw = cta.get("Plan", cta.get("plan", ""))
            plan_base = plan_raw
            equipo = ""

            if ":" in plan_raw:
                partes = plan_raw.split(":", 1)
                modalidad = partes[0].strip()   # "Compra" o "Alquiler"
                detalles = partes[1].strip()    # "400 mbps + Platino Wifi 5"

                if "+" in detalles:
                    subpartes = detalles.split("+", 1)
                    velocidad = subpartes[0].strip()          # "400 mbps"
                    paquete_completo = subpartes[1].strip()   # "Platino Wifi 5"

                    # Separar el nombre del paquete de la generación wifi
                    # El formato es siempre "Nombre Wifi N" al final
                    import re
                    wifi_match = re.search(r"(Wifi\s+\d+)\s*$", paquete_completo, re.IGNORECASE)
                    if wifi_match:
                        wifi_gen = wifi_match.group(1)                              # "Wifi 5"
                        nombre_paquete = paquete_completo[:wifi_match.start()].strip() # "Platino"
                        plan_base = f"{velocidad} + {nombre_paquete}"              # "400 mbps + Platino"
                        equipo = f"{modalidad} {wifi_gen}"                          # "Compra Wifi 5"
                    else:
                        plan_base = f"{velocidad} + {paquete_completo}"
                        equipo = modalidad
                else:
                    plan_base = detalles
                    equipo = modalidad

            # 5. Determinar Resultado (Exitoso / Fallido) para la columna J
            status_text = cta.get("Estado", cta.get("status", ""))
            if ("EXITO" in status_text.upper() or "EXITOSO" in status_text.upper()):
                resultado_final = "EXITOSO"
            else:
                resultado_final = "FALLIDO"

            fila = [
                fecha_limpia,                                                # A: Fecha
                cta.get("Email", cta.get("email", "")),                      # B: Correo Electrónico
                cta.get("Password", cta.get("password", PASSWORD_DEFAULT)),  # C: Contraseña (Ingreso-1)
                ubicacion,                                                   # D: Estado/Ciudad
                cta.get("ID_Cliente", cta.get("id_cliente", "")),            # E: Cp_Customer
                doc_limpio,                                                  # F: Doc (solo tipo)
                estado_iva,                                                  # G: IVA
                plan_base,                                                   # H: Plan Base
                equipo,                                                      # I: Equipo (con modalidad)
                resultado_final,                                             # J: Resultado
                agente_id                                                    # K: Nombre del Operador
            ]
            lote_filas.append(fila)

        # Inyectar a Google Sheets en una sola llamada de red (Batch)
        if log_callback: log_callback(f"🚀 Inyectando {len(lote_filas)} cuentas a la base central...")
        sheet.append_rows(lote_filas)

        # Marcar las cuentas como procesadas localmente
        for cta in pendientes:
            cta["synced_n8n"] = True

        with open(archivo_json, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=4, ensure_ascii=False)

        if log_callback: log_callback(f"✅ Operación exitosa: {len(lote_filas)} cuentas sincronizadas.")
        return len(lote_filas)
