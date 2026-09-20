import os
import re
import time
import threading
from playwright.sync_api import sync_playwright

from core.config import URL_LOGIN, URL_CREATE_ACCOUNT, DEFAULT_CONFIG
from core.catalogos import cargar_catalogo_direcciones, cargar_catalogo_planes
from core.correlativos import (
    obtener_siguiente_correlativo, formatear_error_amigable, registrar_cuenta_creada
)
from core.generadores import generar_telefono_ve
from automation.steps import (
    ejecutar_paso_0_login,
    ejecutar_paso_1_datos_basicos,
    ejecutar_paso_2_direccion,
    ejecutar_paso_3_adicional,
    ejecutar_paso_4_paquetes,
    ejecutar_paso_4_2_addons,
    ejecutar_paso_5_otp_y_confirmacion
)

login_lock = threading.Lock()

class StepTimer:
    def __init__(self, id_hilo, log_callback, update_thread_status_callback=None):
        self.id_hilo = id_hilo
        self.log_callback = log_callback
        self.update_thread_status = update_thread_status_callback
        self.start_total = time.perf_counter()
        self.start_epoch = time.time()
        self.step_start = None
        self.current_step = None
        self.tiempos = {}
        if self.update_thread_status:
            self.update_thread_status(self.id_hilo, "Preparación", self.start_epoch, "Activo")

    def start_step(self, step_name):
        self.current_step = step_name
        self.step_start = time.perf_counter()
        if self.update_thread_status:
            self.update_thread_status(self.id_hilo, self.current_step, self.start_epoch, "Activo")
        
    def stop_step(self, final_status="Activo"):
        if self.current_step and self.step_start:
            elapsed = time.perf_counter() - self.step_start
            self.tiempos[self.current_step] = elapsed
            acumulado = time.perf_counter() - self.start_total
            self.log_callback(f"⏱️ [Hilo {self.id_hilo}] [{self.current_step.split(':')[0]}] Completado en {elapsed:.1f}s | Total: {acumulado:.1f}s")
            self.current_step = None
            self.step_start = None
        if self.update_thread_status and final_status != "Activo":
            self.update_thread_status(self.id_hilo, "Completado" if final_status == "Exito" else "Error", self.start_epoch, final_status)

    def print_benchmark(self, email):
        total = sum(self.tiempos.values())
        if total == 0: total = 0.1
        self.log_callback(f"")
        self.log_callback(f"📊 BENCHMARK [Hilo {self.id_hilo}] [{email}]")
        desglose = []
        for step, t in self.tiempos.items():
            pct = (t / total) * 100
            step_short = step.split(':')[0]
            self.log_callback(f"├── {step_short}: {t:.1f}s ({pct:.0f}%)")
            desglose.append(f"{step_short}:{t:.1f}s")
        self.log_callback(f"⏱️ TIEMPO TOTAL ACTIVO: {total:.1f}s")
        self.log_callback(f"")
        return round(total, 1), "|".join(desglose)

def crear_cuenta_individual(id_hilo, config_cuenta, sys_config, log_callback, update_kpi_callback, cancel_event=None, update_thread_status_callback=None):
    """
    Orquestador principal de automatización de una cuenta individual:
    Ejecuta en secuencia desacoplada los Pasos 0 al 5, gestiona evidencias QA
    y registra el resultado final (éxito o fallo) en los historiales.
    """
    paso_actual = "Paso 0: Preparación"
    
    def check_cancel():
        if cancel_event and cancel_event.is_set():
            raise Exception("Proceso detenido por cancelación del usuario.")

    # Cargar catálogos frescos
    catalogo_planes = cargar_catalogo_planes()
    catalogo_direcciones = cargar_catalogo_direcciones()

    modo_ejecucion = config_cuenta.get("modo_ejecucion") or sys_config.get("modo_ejecucion", "completo")

    email = config_cuenta.get("email")
    prefijo = sys_config.get("prefijo_email", DEFAULT_CONFIG["prefijo_email"])
    dominio = sys_config.get("dominio_email", DEFAULT_CONFIG["dominio_email"])
    if not email:
        correlativo = obtener_siguiente_correlativo()
        email = f"{prefijo}{correlativo}@{dominio}"
    else:
        correlativo = config_cuenta.get("correlativo", "")

    phone_number = generar_telefono_ve()
    
    tipo_persona = config_cuenta["tipo_persona"]
    ubicacion = config_cuenta["ubicacion"]
    plan_seleccionado = config_cuenta.get("plan_seleccionado", "Compra: 400 mbps + Gold")
    
    datos_plan = catalogo_planes.get(plan_seleccionado)
    if not datos_plan:
        primer_plan = list(catalogo_planes.keys())[0]
        log_callback(f"⚠️ [Hilo {id_hilo}] Plan '{plan_seleccionado}' no encontrado en catálogo. Usando fallback '{primer_plan}'")
        plan_seleccionado = primer_plan
        datos_plan = catalogo_planes[plan_seleccionado]

    paquete_nombre = datos_plan.get("paquete", "")
    promocion_nombre = datos_plan.get("promocion", "")
    if not config_cuenta.get("aplicar_promocion", True):
        promocion_nombre = ""
    tarifa_inst = datos_plan.get("tarifa", "$0")
    router_nombre = datos_plan.get("router", "")

    direccion_hilo = catalogo_direcciones.get(ubicacion)
    if not direccion_hilo:
        posibles_dirs = [v for k, v in catalogo_direcciones.items() if k.lower() == ubicacion.lower()]
        direccion_hilo = posibles_dirs[0] if posibles_dirs else list(catalogo_direcciones.values())[0]

    company_name = ""
    first_name = ""
    last_name = ""
    doc_id = ""

    url_login = URL_LOGIN
    url_create = URL_CREATE_ACCOUNT
    usuario_login = sys_config.get("usuario_login", DEFAULT_CONFIG["usuario_login"])
    password_login = sys_config.get("password_login", DEFAULT_CONFIG["password_login"])

    # Carpeta de evidencia QA
    fecha_hoy = time.strftime("%Y-%m-%d")
    nombre_carpeta_cliente = email.split('@')[0]
    ruta_evidencia = os.path.join("Evidencias_QA_Fibra", fecha_hoy, nombre_carpeta_cliente)
    os.makedirs(ruta_evidencia, exist_ok=True)

    log_callback(f"🚀 [Hilo {id_hilo}] INICIANDO | {tipo_persona} | {ubicacion} | {plan_seleccionado} | Email: {email}")

    check_cancel()
    timer = StepTimer(id_hilo, log_callback, update_thread_status_callback)

    pw = sync_playwright().start()
    cerrar_navegador = True
    try:
        try:
            browser = pw.chromium.launch(channel="chrome", headless=False, args=["--start-maximized"])
        except Exception:
            browser = pw.chromium.launch(headless=False, args=["--start-maximized"])
        
        context = None
        page = None
        id_cliente_extraido = ""

        try:
            check_cancel()

            # --- PASO 0: LOGIN ---
            paso_actual = "Paso 0: Login en CRM"
            timer.start_step(paso_actual)
            with login_lock:
                log_callback(f"🚦 [Hilo {id_hilo}] Semáforo verde. Entrando al portal de login...")
                context, page = ejecutar_paso_0_login(
                    browser=browser,
                    id_hilo=id_hilo,
                    url_login=url_login,
                    url_create=url_create,
                    usuario_login=usuario_login,
                    password_login=password_login,
                    log_callback=log_callback,
                    check_cancel=check_cancel
                )
                time.sleep(3) # Delay escalonado para no saturar al mismo ms
            timer.stop_step()

            # --- PASO 1: DATOS BÁSICOS ---
            paso_actual = "Paso 1: Datos Básicos"
            check_cancel()
            timer.start_step(paso_actual)
            company_name, first_name, last_name, last_name_puro, doc_id = ejecutar_paso_1_datos_basicos(
                page=page,
                config_cuenta=config_cuenta,
                correlativo=correlativo,
                phone_number=phone_number,
                email=email,
                log_callback=log_callback
            )
            timer.stop_step()

            # --- PASO 2: DIRECCIÓN ---
            paso_actual = "Paso 2: Dirección y Localización"
            check_cancel()
            timer.start_step(paso_actual)
            try:
                ejecutar_paso_2_direccion(
                    page=page,
                    id_hilo=id_hilo,
                    direccion_hilo=direccion_hilo,
                    log_callback=log_callback
                )
            except Exception as e_paso2:
                if "timeout" in str(e_paso2).lower() or "waiting for" in str(e_paso2).lower():
                    log_callback(f"⚠️ [Hilo {id_hilo}] Timeout en Paso 2. CRM con lag. Recargando página (F5) y reintentando...")
                    page.reload()
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                    ejecutar_paso_2_direccion(
                        page=page,
                        id_hilo=id_hilo,
                        direccion_hilo=direccion_hilo,
                        log_callback=log_callback
                    )
                else:
                    raise e_paso2
            timer.stop_step()

            # --- PASO 3: ADICIONAL ---
            paso_actual = "Paso 3: Información Adicional"
            check_cancel()
            timer.start_step(paso_actual)
            ejecutar_paso_3_adicional(
                page=page,
                id_hilo=id_hilo,
                tipo_persona=tipo_persona,
                first_name=first_name,
                last_name_puro=last_name_puro,
                phone_number=phone_number,
                email=email,
                log_callback=log_callback
            )
            timer.stop_step()

            # --- DETENCIÓN EN MODO CREACIÓN MANUAL (HASTA PASO 3) ---
            if modo_ejecucion == "hasta_paso_3":
                cerrar_navegador = False  # Dejar el navegador abierto para interacción manual
                timer.stop_step("Exito")
                tiempo_total, desglose_str = timer.print_benchmark(email)
                
                # 📸 Captura de evidencia QA de Paso 3 finalizado
                archivo_paso3_fin = os.path.join(ruta_evidencia, "03_Paso3_Finalizado_Package_Selection.png")
                try:
                    page.screenshot(path=archivo_paso3_fin, full_page=False)
                    log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Paso 3 finalizado (Package Selection) guardada.")
                except Exception:
                    pass

                nombre_o_empresa = company_name if tipo_persona == "Persona jurídica" else f"{first_name} {last_name}".strip()
                doc_tipo = config_cuenta.get("tipo_doc", config_cuenta.get("tipo_rif", "N/A"))

                datos_log = {
                    "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Servicio": "FTTH",
                    "Tipo_Persona": tipo_persona,
                    "Documento_RIF": f"{doc_tipo}: {doc_id}",
                    "Nombre_o_Empresa": nombre_o_empresa,
                    "Email": email,
                    "Telefono": phone_number,
                    "Ubicacion": ubicacion,
                    "Plan": plan_seleccionado,
                    "Estado": "EXITOSO (Creación Manual - Hasta Paso 3)",
                    "Tiempo_Total_Segundos": tiempo_total,
                    "Desglose_Tiempos": desglose_str,
                    "ID_Cliente": ""
                }
                registrar_cuenta_creada(datos_log)
                update_kpi_callback(exito=1)
                log_callback(f"✍️ [Hilo {id_hilo}] CREACIÓN MANUAL: Datos completados hasta Paso 3. Navegador listo para continuar.")
                if update_thread_status_callback:
                    update_thread_status_callback(id_hilo, "Creación manual", timer.start_epoch, "Activo")
                
                # Mantener el hilo vivo para que Playwright no se cierre ni lance errores
                while cancel_event and not cancel_event.is_set():
                    try:
                        if not browser.is_connected():
                            break
                        page.wait_for_timeout(1000)
                    except Exception:
                        break
                return

            # --- PASO 4: PAQUETES Y ROUTER ---
            paso_actual = "Paso 4: Configuración de Plan y Promociones"
            check_cancel()
            timer.start_step(paso_actual)
            try:
                ejecutar_paso_4_paquetes(
                    page=page,
                    id_hilo=id_hilo,
                    paquete_nombre=paquete_nombre,
                    promocion_nombre=promocion_nombre,
                    tarifa_inst=tarifa_inst,
                    router_nombre=router_nombre,
                    ruta_evidencia=ruta_evidencia,
                    log_callback=log_callback
                )
            except Exception as e_paso4:
                if "timeout" in str(e_paso4).lower() or "waiting for" in str(e_paso4).lower() or "lista lenta" in str(e_paso4).lower():
                    log_callback(f"⚠️ [Hilo {id_hilo}] Timeout o Lista lenta en Paso 4. Recargando página (F5) y reintentando...")
                    page.reload()
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                    ejecutar_paso_4_paquetes(
                        page=page,
                        id_hilo=id_hilo,
                        paquete_nombre=paquete_nombre,
                        promocion_nombre=promocion_nombre,
                        tarifa_inst=tarifa_inst,
                        router_nombre=router_nombre,
                        ruta_evidencia=ruta_evidencia,
                        log_callback=log_callback
                    )
                else:
                    raise e_paso4
            timer.stop_step()

            # --- PASO 4.2: ADD-ONS ---
            paso_actual = "Paso 4.2: Omitir Add-Ons"
            check_cancel()
            timer.start_step(paso_actual)
            ejecutar_paso_4_2_addons(
                page=page,
                id_hilo=id_hilo,
                log_callback=log_callback
            )
            timer.stop_step()

            # --- PASO 5: OTP Y CONFIRMACIÓN ---
            paso_actual = "Paso 5: Envío y Validación OTP"
            check_cancel()
            timer.start_step(paso_actual)
            id_cliente_extraido = ejecutar_paso_5_otp_y_confirmacion(
                page=page,
                context=context,
                id_hilo=id_hilo,
                email=email,
                ruta_evidencia=ruta_evidencia,
                log_callback=log_callback
            )
            if not id_cliente_extraido:
                id_cliente_extraido = ""
            timer.stop_step()

            # --- CIERRE DE CICLO EXITOSO ---
            timer.stop_step("Exito")
            tiempo_total, desglose_str = timer.print_benchmark(email)
            
            nombre_o_empresa = company_name if tipo_persona == "Persona jurídica" else f"{first_name} {last_name}".strip()
            doc_tipo = config_cuenta.get("tipo_doc", config_cuenta.get("tipo_rif", "N/A"))

            sin_promo_keywords = ["", "sin promo", "sin_promo", "ninguna", "ninguno", "n/a", "none", "-"]
            promo_activa = bool(promocion_nombre and promocion_nombre.strip().lower() not in sin_promo_keywords)

            datos_log = {
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "FTTH",
                "Tipo_Persona": tipo_persona,
                "Documento_RIF": f"{doc_tipo}: {doc_id}",
                "Nombre_o_Empresa": nombre_o_empresa,
                "Email": email,
                "Telefono": phone_number,
                "Ubicacion": ubicacion,
                "Plan": f"{plan_seleccionado} [Sin Promo]" if not promo_activa else plan_seleccionado,
                "Estado": "EXITOSO (Cuenta Activada)",
                "Tiempo_Total_Segundos": tiempo_total,
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": id_cliente_extraido
            }
            registrar_cuenta_creada(datos_log)
            update_kpi_callback(exito=1)

            log_callback(f"🎉 [Hilo {id_hilo}] PROCESO COMPLETADO Y CUENTA CREADA CON ÉXITO.")
            page.wait_for_timeout(2000)

        except Exception as err:
            timer.stop_step("Error")
            tiempo_total, desglose_str = timer.print_benchmark(email)
            
            error_amigable = formatear_error_amigable(paso_actual, err)
            log_callback(f"❌ [Hilo {id_hilo} - {paso_actual}]: {error_amigable}")
            
            paso_slug = re.sub(r'[^a-zA-Z0-9_]', '_', paso_actual.replace(" ", "_").replace(":", ""))
            timestamp_err = time.strftime("%Y%m%d_%H%M%S")
            nombre_foto_error = f"ERROR_hilo{id_hilo}_{paso_slug}_{timestamp_err}.png"

            archivo_error_evidencia = os.path.join(ruta_evidencia, nombre_foto_error)
            archivo_error_logs = os.path.join("logs", "screenshots", nombre_foto_error)
            os.makedirs(os.path.join("logs", "screenshots"), exist_ok=True)

            try:
                if page:
                    page.screenshot(path=archivo_error_evidencia, full_page=True)
                    page.screenshot(path=archivo_error_logs, full_page=True)
                    log_callback(f"📸 [Hilo {id_hilo}] Captura de error guardada: {nombre_foto_error}")
            except Exception as cam_err:
                log_callback(f"⚠️ No se pudo tomar captura de error: {cam_err}")

            doc_tipo = config_cuenta.get("tipo_doc", config_cuenta.get("tipo_rif", "N/A"))
            datos_error = {
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "FTTH",
                "Tipo_Persona": tipo_persona,
                "Documento_RIF": f"{doc_tipo}: {doc_id}" if doc_id else doc_tipo,
                "Nombre_o_Empresa": company_name if tipo_persona == "Persona jurídica" else f"{first_name} {last_name}".strip(),
                "Email": email,
                "Telefono": phone_number,
                "Ubicacion": ubicacion,
                "Plan": plan_seleccionado,
                "Estado": f"FALLÓ: {error_amigable}",
                "Tiempo_Total_Segundos": tiempo_total,
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": id_cliente_extraido
            }
            registrar_cuenta_creada(datos_error)
            update_kpi_callback(fallo=1)

        finally:
            if cerrar_navegador:
                try:
                    browser.close()
                except Exception:
                    pass
                try:
                    pw.stop()
                except Exception:
                    pass
    except Exception as e_pw:
        if cerrar_navegador:
            try:
                pw.stop()
            except Exception:
                pass
        raise e_pw
