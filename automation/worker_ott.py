import os
import time
import random
import re
from playwright.sync_api import sync_playwright

from core.correlativos import (
    obtener_siguiente_correlativo, formatear_error_amigable, registrar_cuenta_creada
)
from core.generadores import generar_telefono_ve, generar_nombre_humano_limpio

from core.catalogos import cargar_catalogo_direcciones_ott, cargar_catalogo_ott
from automation.worker import StepTimer

CATALOGO_DIRECCIONES_OTT = cargar_catalogo_direcciones_ott()
CATALOGO_OTT = cargar_catalogo_ott()

def obtener_codigo_otp_maildrop(email_base, correlativo, p_context, cancel_event=None):
    mailbox_name = f"{email_base}{correlativo}"
    page_maildrop = p_context.new_page()
    try:
        page_maildrop.goto(f"https://maildrop.cc/inbox/?mailbox={mailbox_name}", timeout=60000)
        
        codigo = None
        for i in range(15):
            if cancel_event and cancel_event.is_set():
                break
            page_maildrop.wait_for_timeout(3500)
            
            # Hacer clic en el primer correo de la lista (cualquiera que haya llegado)
            primer_correo = page_maildrop.locator("div[class*='truncate'], a[href*='/inbox/'], li[class*='message']").first
            if primer_correo.is_visible():
                try:
                    primer_correo.click()
                    page_maildrop.wait_for_timeout(2000)
                except:
                    pass
            
            # Buscar el código de 6 dígitos en todo el texto visible de la página o frames
            texto_visible = ""
            try:
                texto_visible += page_maildrop.inner_text("body")
                texto_visible += " " + page_maildrop.content()
            except:
                pass
                
            for frame in page_maildrop.frames:
                try:
                    texto_visible += " " + frame.inner_text("body")
                    texto_visible += " " + frame.content()
                except:
                    pass
            
            # Buscar 6 dígitos aislados (ej. 727633)
            match = re.search(r'(?<!\d)(\d{6})(?!\d)', texto_visible)
            if match:
                codigo = match.group(1)
                break
            
            page_maildrop.reload()
                
        return codigo
    except Exception as e:
        print(f"Error en maildrop: {e}")
        return None
    finally:
        page_maildrop.close()


def crear_cuenta_ott(
    id_hilo, 
    config_cuenta, 
    sys_config, 
    log_callback,
    update_kpi_callback,
    cancel_event=None,
    update_thread_status_callback=None
):
    tipo_persona = config_cuenta.get("tipo_persona")
    plan_ott = config_cuenta.get("plan_seleccionado")
    ubicacion_ott = config_cuenta.get("ubicacion", "OTT")
    
    timer = StepTimer(id_hilo, log_callback, update_thread_status_callback)
    
    # 1. Preparar Datos Generados
    timer.start_step("P0: Preparación")
    try:
        nuevo_corr = obtener_siguiente_correlativo("contador_email_ott.txt")
        telefono_completo = generar_telefono_ve()
        prefijo_tel = telefono_completo[:4]
        numero_tel = telefono_completo[4:]
        
        # Leer tipo de documento de la configuración
        tipo_doc = config_cuenta.get("tipo_doc", "Venezuelan")
        if tipo_doc == "Foreigner":
            prefijo_ced = "E"
        elif tipo_doc == "Passport":
            prefijo_ced = "P"
        else:
            prefijo_ced = "V"
            
        cedula = str(random.randint(10000000, 30000000))
        nombre, apellido = generar_nombre_humano_limpio()
        rif_completo = f"{prefijo_ced}-{cedula}"
            
        email_base = sys_config.get("prefijo_email_ott", "testgatbott")
        if "@" in email_base:
            email_base = email_base.split("@")[0]
        mailbox_name = f"{email_base}{nuevo_corr}"
        email_generado = f"{mailbox_name}@maildrop.cc"
        
        tipo_cliente_str = "Venezolano"
        if tipo_doc == "Foreigner": tipo_cliente_str = "Extranjero"
        elif tipo_doc == "Passport": tipo_cliente_str = "Pasaporte"
        elif tipo_doc == "Legal": tipo_cliente_str = "Jurídico"
        elif tipo_doc == "Government": tipo_cliente_str = "Gubernamental"
        
        fecha_hoy = time.strftime("%Y-%m-%d")
        carpeta_evidencias = os.path.join(os.getcwd(), "Evidencias_QA_OTT", fecha_hoy, mailbox_name)
        
        log_callback(f"[Hilo {id_hilo}] 📝 OTT: {nombre} {apellido} | {cedula} | {email_generado} | Plan: {plan_ott}")
        if "page" in locals(): guardar_evidencia(timer.current_step)
        timer.stop_step()
    except Exception as e:
        timer.stop_step("Error")
        err_msg = formatear_error_amigable("preparando datos OTT", e)
        log_callback(f"[Hilo {id_hilo}] ❌ Error: {err_msg}")
        update_kpi_callback(fallo=1)
        return {"exito": False, "error": err_msg, "email": ""}

    with sync_playwright() as p:
        browser = None
        try:
            # P1: Lanzar Navegador
            timer.start_step("P1: Iniciar Navegador")
            browser = p.chromium.launch(headless=False, slow_mo=50, args=["--start-maximized"]) # Mostrar UI para debugging
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            page.set_default_timeout(45000)

            # Helper para capturar evidencias
            def guardar_evidencia(nombre_paso):
                try:
                    paso_limpio = nombre_paso.replace(':', '').replace(' ', '_')
                    os.makedirs(carpeta_evidencias, exist_ok=True)
                    path = os.path.join(carpeta_evidencias, f"Hilo{id_hilo}_{paso_limpio}.png")
                    if 'page' in locals() and not page.is_closed():
                        page.screenshot(path=path, full_page=True, timeout=2000)
                except:
                    pass
            if "page" in locals(): guardar_evidencia(timer.current_step)
            timer.stop_step()

            # P2: Navegación y Selección del Plan
            timer.start_step("P2: Selección de Plan OTT")
            page.goto("https://tiendatesting.simple.com.ve/planes-streaming")
            page.wait_for_load_state("networkidle")
            
            # Buscar el paquete y la variante en el catálogo
            datos_plan = CATALOGO_OTT.get(plan_ott, {"paquete": plan_ott, "variante": ""})
            paquete_base = datos_plan["paquete"]
            variante = datos_plan["variante"]
            
            # Mapeo del botón base:
            btn_selector = ""
            if "lite" in paquete_base.lower():
                btn_selector = "text='Personalizar plan Lite'"
            elif "oro" in paquete_base.lower() or "gold" in paquete_base.lower():
                btn_selector = "text='Personalizar plan Oro'"
            elif "platino" in paquete_base.lower():
                btn_selector = "text='Personalizar plan Platino'"
            elif "diamante" in paquete_base.lower() or "diamond" in paquete_base.lower():
                btn_selector = "text='Personalizar plan Diamante'"
            else:
                btn_selector = f"text='Personalizar plan {paquete_base}'" # Fallback
            
            page.locator(btn_selector).click()
            page.wait_for_load_state("networkidle")
            
            # Seleccionar la variante si existe
            if variante:
                try:
                    log_callback(f"[Hilo {id_hilo}] Seleccionando variante: {variante}")
                    page.locator(f"text='{variante}'").first.click(force=True)
                    page.wait_for_timeout(2000)
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] ⚠️ No se pudo seleccionar la variante '{variante}': {e}")
            
            # Continuar
            if "page" in locals(): guardar_evidencia(timer.current_step)
            try:
                page.locator("button:visible:has-text('Continuar')").first.click(force=True)
            except:
                page.get_by_role("button", name="Continuar").first.click(force=True)
                
            timer.stop_step()

            # P3: Datos Básicos (Modal)
            timer.start_step("P3: Registro Simpletv+")
            page.wait_for_selector("text='Registro Simpletv+'")
            
            # Nombres y apellidos
            page.get_by_label("Nombre").fill(nombre, force=True)
            page.get_by_label("Nombre").blur()
            
            page.get_by_label("Apellido").fill(apellido, force=True)
            page.get_by_label("Apellido").blur()
            
            # Llenar Teléfono
            page.locator("input[name='phone.number']").fill(numero_tel, force=True)
            page.locator("input[name='phone.number']").blur()
            
            # Llenar Correo
            page.locator("input[name='email']").fill(email_generado, force=True)
            page.locator("input[name='email']").blur()
            time.sleep(1)
            
            # Seleccionar tipo de documento (V, E, P) mediante inyección JS
            page.evaluate(f"""(prefijo) => {{
                const selects = Array.from(document.querySelectorAll('select'));
                // Buscar el select que tenga las opciones V, E, P
                const select = selects.find(s => {{
                    const opts = Array.from(s.options).map(o => o.text.trim().toUpperCase());
                    return opts.includes('V') || opts.includes('E') || opts.includes('P') || opts.includes('V-') || opts.includes('E-');
                }});
                if(select) {{
                    const target = Array.from(select.options).find(o => o.text.trim().toUpperCase().startsWith(prefijo) || o.value.toUpperCase().startsWith(prefijo));
                    if(target) {{
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                        nativeSetter.call(select, target.value);
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
            }}""", prefijo_ced)
            time.sleep(0.5)
            
            # Checkbox: Clicar el texto
            page.locator("text='Declaro que toda la información proporcionada es real'").click(force=True)
            time.sleep(1)
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
            
            # Clicar Continuar
            btn_continuar = page.get_by_role("button", name="Continuar").last
            btn_continuar.click(force=True)
            
            # NO enviaremos Enter porque puede interactuar negativamente con el checkbox si quedó enfocado
            
            # DEBUG SCREENSHOT 1
            os.makedirs(carpeta_evidencias, exist_ok=True)
            page.screenshot(path=os.path.join(carpeta_evidencias, f"debug_{id_hilo}_after_click.png"))
            
            timer.stop_step()

            # P4: OTP Maildrop
            timer.start_step("P4: Validar OTP")
            # Esperar a que la URL cambie indicando que pasamos al OTP
            try:
                page.wait_for_url("**/*validacion-streaming=otp*", timeout=60000)
                # Esperar un poco a que termine de renderizar el modal de OTP
                time.sleep(2)
            except Exception as e:
                # DEBUG SCREENSHOT 2 (If it times out)
                os.makedirs(carpeta_evidencias, exist_ok=True)
                page.screenshot(path=os.path.join(carpeta_evidencias, f"debug_{id_hilo}_timeout_otp.png"))
                raise e
            
            # DEBUG SCREENSHOT 3 (If it succeeded)
            os.makedirs(carpeta_evidencias, exist_ok=True)
            page.screenshot(path=os.path.join(carpeta_evidencias, f"debug_{id_hilo}_reached_otp.png"))
            
            # ir a maildrop
            log_callback(f"[Hilo {id_hilo}] ⏳ Esperando código OTP en {email_generado}...")
            # Lógica de espera OTP (reutilizando crm_helpers)
            time.sleep(10) # Espera inicial
            codigo_otp = None
            for intento in range(15):
                if cancel_event and cancel_event.is_set():
                    log_callback(f"[Hilo {id_hilo}] 🛑 Búsqueda de OTP cancelada.")
                    raise Exception("Ejecución cancelada por el usuario.")
                    
                codigo_otp = obtener_codigo_otp_maildrop(email_base, nuevo_corr, context, cancel_event)
                if codigo_otp:
                    break
                log_callback(f"[Hilo {id_hilo}] OTP no encontrado, reintentando ({intento+1}/15)...")
                
                # Espera de 10 segundos, verificando cancelación cada segundo
                for _ in range(10):
                    if cancel_event and cancel_event.is_set():
                        raise Exception("Ejecución cancelada por el usuario.")
                    time.sleep(1)
                
            if not codigo_otp:
                raise Exception("Tiempo de espera agotado buscando OTP en maildrop.")
                
            log_callback(f"[Hilo {id_hilo}] ✅ Código OTP: {codigo_otp}")
            
            # Llenar casillas OTP
            for i, digito in enumerate(codigo_otp):
                # Escribimos explícitamente en otp.0, otp.1, otp.2 o equivalente
                caja = page.locator(f"input[name='otp.{i}'], input[name='otp{i}'], input[aria-label*='{i+1}']").first
                if i == 0:
                    caja.wait_for(state="visible", timeout=5000)
                caja.fill("", force=True)
                caja.press_sequentially(digito, delay=50)
                
            # Disparar blur para asegurar validación final
            caja_final = page.locator("input[name='otp.5'], input[name='otp5'], input[aria-label*='6']").first
            caja_final.blur()
                
            # Dar chance a React de actualizar el botón
            time.sleep(1)
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
                
            # Clicar Continuar
            btn_continuar_otp = page.get_by_role("button", name="Continuar").last
            btn_continuar_otp.click(force=True)
            
            # Esperar a que la página procese el OTP
            time.sleep(4)
            
            timer.stop_step()

            # P5: Carrito y Generación de contrato
            timer.start_step("P5: Carrito y Contrato")
            
            # Click Continuar en Carrito
            try:
                page.wait_for_selector("text='Debe completar el registro de datos para continuar con el pago'", state="visible", timeout=20000)
            except:
                pass # A veces no sale el texto o carga muy rápido, continuamos
            time.sleep(2)
            page.locator("button:visible:has-text('Continuar')").first.click(force=True)
            
            # El modal "Generación de contrato" aparece después del clic
            time.sleep(3)
            page.wait_for_selector("text='Generación de contrato'", state="visible", timeout=20000)
            
            # Llenar Cédula de Identidad (evitamos get_by_label por si el dropdown interfiere)
            cedula_input = page.locator("input[placeholder*='cédula de identidad'], input[placeholder*='Cédula']").first
                        # Seleccionar tipo de documento (V, E, P) mediante inyección JS
            page.evaluate("""(prefijo) => {
                const selects = Array.from(document.querySelectorAll('select'));
                // Buscar el select que tenga las opciones V, E, P
                const select = selects.find(s => {
                    const opts = Array.from(s.options).map(o => o.text.trim().toUpperCase());
                    return opts.includes('V') || opts.includes('E') || opts.includes('P') || opts.includes('V-') || opts.includes('E-');
                });
                if(select) {
                    const target = Array.from(select.options).find(o => o.text.trim().toUpperCase().startsWith(prefijo) || o.value.toUpperCase().startsWith(prefijo));
                    if(target) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                        nativeSetter.call(select, target.value);
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            }""", prefijo_ced)
            time.sleep(0.5)
            cedula_input.click(force=True)
            cedula_input.fill(cedula.replace("-",""))
            cedula_input.blur()
            
            # Checkbox P5
            page.locator("text='Declaro que toda la información proporcionada es real'").click(force=True)
            time.sleep(1)
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
            
            # Clicar Continuar
            btn_continuar_p5 = page.get_by_role("button", name="Continuar").last
            btn_continuar_p5.click(force=True)
            
            # Dar tiempo al modal para cerrarse/transicionar
            time.sleep(3)
            timer.stop_step()
            
            # P6: Dirección
            timer.start_step("P6: Dirección de Facturación")
            page.wait_for_selector("text='Dirección de facturación'")
            
            # Llenar dropdowns usando inyección nativa de React para evitar bloqueos visuales
            def react_select_by_text(p, select_name, text_match):
                p.evaluate("""([name, text]) => {
                    const select = document.querySelector(`select[name='${name}']`);
                    if (!select) throw new Error("Select no encontrado: " + name);
                    
                    const options = Array.from(select.options);
                    const target = options.find(o => o.text.toLowerCase().includes(text.toLowerCase()));
                    if (!target) throw new Error("Opcion no encontrada para: " + text);
                    
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                    nativeSetter.call(select, target.value);
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }""", [select_name, text_match])
            
            dir_data = CATALOGO_DIRECCIONES_OTT.get(ubicacion_ott, CATALOGO_DIRECCIONES_OTT.get("Caracas", {
                "state": "distrito capital", "city": "caracas", "municipality": "libertador",
                "zone": "chacaito", "postal_code": "1060"
            }))

            # Estado
            react_select_by_text(page, 'billingAddress.state', dir_data["state"])
            page.wait_for_timeout(4000) # Esperar a que cargue Ciudad
            
            # Ciudad
            react_select_by_text(page, 'billingAddress.city', dir_data["city"])
            page.wait_for_timeout(4000) # Esperar a que cargue Municipio
            
            # Municipio
            react_select_by_text(page, 'billingAddress.municipality', dir_data["municipality"])
            page.wait_for_timeout(4000) # Esperar a que cargue Zona
            
            # Zona
            react_select_by_text(page, 'billingAddress.zone', dir_data["zone"])
            page.wait_for_timeout(4000) # Esperar a que cargue Código postal
            
            # Código postal
            try:
                react_select_by_text(page, 'billingAddress.postalCode', dir_data["postal_code"])
            except:
                pass # A veces se autocompleta o es único
            page.wait_for_timeout(2000)
            
            # Tipo de calle
            react_select_by_text(page, 'billingAddress.streetType', dir_data["street_type"])
            page.wait_for_timeout(2000)
            
            # Entradas de texto
            page.locator("input[placeholder*='avenida o calle']").fill(dir_data["street_name"], force=True)
            page.locator("input[placeholder*='nombre del edificio']").fill(dir_data["building_name"], force=True)
            page.locator("input[placeholder*='número de casa']").fill(dir_data["house_number"], force=True)
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
            
            btn_continuar_p6 = page.get_by_role("button", name="Continuar").last
            btn_continuar_p6.click(force=True)
            
            # Transición a Datos Adicionales
            time.sleep(3)
            timer.stop_step()
            
            # P7: Datos Adicionales
            timer.start_step("P7: Datos Adicionales")
            page.wait_for_selector("text='Datos adicionales'")
            
            # Sexo (buscar el select cercano al texto 'Sexo' e inyectar el valor)
            page.evaluate("""() => {
                const selects = Array.from(document.querySelectorAll('select'));
                const select = selects.find(s => {
                    const label = s.closest('label') || (s.parentElement && s.parentElement.closest('label'));
                    return label && label.textContent.toLowerCase().includes('sexo');
                }) || selects.find(s => s.name && s.name.toLowerCase().includes('gender'));
                
                if(select) {
                    const options = Array.from(select.options);
                    const target = options.find(o => o.text.toLowerCase().includes('masculino'));
                    if(target) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                        nativeSetter.call(select, target.value);
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            }""")
            time.sleep(1)
            
            # Fecha de nacimiento
            # Como el input tiene type="date", Playwright puede requerir el formato YYYY-MM-DD
            try:
                page.locator("input[name='birthDate']").fill("1990-01-01", force=True)
            except:
                # Fallback por si es text normal con máscara
                page.locator("input[name='birthDate']").fill("01/01/1990", force=True)
            
            # Los demás campos no son obligatorios según la usuaria, así que los saltamos
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
            
            # Continuar P7
            # Usamos .last para asegurarnos de hacer clic en el botón del modal y no en el del carrito de fondo
            page.get_by_role("button", name="Continuar").last.click(force=True)
            
            # Transición a P8 (Aceptación de documentos)
            time.sleep(4)
            timer.stop_step()
            
            # P8: Aceptación
            timer.start_step("P8: Aceptación de documentos")
            page.wait_for_selector("text=/Aceptación/i", timeout=15000)
            
            # Marcar checkbox (forzando para evadir estilos custom)
            page.locator("input[type='checkbox']").first.check(force=True)
            
            if "page" in locals(): guardar_evidencia(timer.current_step)
            
            # Aceptar / Continuar contrato
            # Usamos regex por si el botón dice 'Aceptar' o 'Continuar'
            page.locator("button:visible").filter(has_text=re.compile(r"Continuar|Aceptar", re.IGNORECASE)).last.click(force=True)
            
            # Esperar a que vuelva al carrito con el botón "Pagar ahora" (u otro indicador de fin)
            try:
                page.wait_for_selector("button:has-text('Pagar ahora')", timeout=20000)
            except:
                pass # Si cambia el texto, no queremos crashear
            timer.stop_step("Exito")
            
            log_callback(f"[Hilo {id_hilo}] 🎉 Flujo OTT Completado! Correo: {email_generado}")
            
            # Calcular benchmark de tiempos
            tiempo_total, desglose_str = timer.print_benchmark(email_generado)
            
            update_kpi_callback(exito=1)
            
            # Guardar historial OTT exitoso
            datos_log = {
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "OTT",
                "Tipo_Persona": tipo_cliente_str,
                "Documento_RIF": rif_completo,
                "Nombre_o_Empresa": f"{nombre} {apellido}",
                "Email": email_generado,
                "Telefono": telefono_completo,
                "Ubicacion": ubicacion_ott,
                "Plan": plan_ott,
                "Estado": "EXITOSO (Pendiente Pago)",
                "Tiempo_Total_Segundos": f"{tiempo_total}s",
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": ""
            }
            registrar_cuenta_creada(datos_log)
            if browser and browser.is_connected():
                # Notificación Sonora
                try:
                    import winsound
                    winsound.Beep(1000, 300)
                    winsound.Beep(1500, 400)
                except:
                    pass
                    
                log_callback(f"[Hilo {id_hilo}] 🛑 Ejecución finalizada. El navegador quedará abierto para que realices el pago.")
                while True:
                    if cancel_event and cancel_event.is_set():
                        log_callback(f"[Hilo {id_hilo}] 🚫 Cancelación manual. Cerrando navegador.")
                        try:
                            browser.close()
                        except: pass
                        break
                        
                    try:
                        cerrado = False
                        if not browser.is_connected(): cerrado = True
                        elif 'page' in locals() and page.is_closed(): cerrado = True
                        
                        if cerrado:
                            log_callback(f"[Hilo {id_hilo}] ℹ️ Navegador cerrado manualmente tras el pago. Liberando hilo.")
                            break
                        
                        page.wait_for_timeout(1000)
                    except Exception as e:
                        log_callback(f"[Hilo {id_hilo}] ℹ️ Navegador cerrado o desconectado. Liberando hilo.")
                        break
            return {"exito": True, "error": None, "email": email_generado}
            
        except Exception as e:
            if timer.current_step:
                timer.stop_step("Error")
            err_msg = formatear_error_amigable(timer.current_step if timer.current_step else "Flujo OTT", e)
            log_callback(f"[Hilo {id_hilo}] ❌ Error en {timer.current_step}: {err_msg}")
            
            if browser:
                try:
                    if 'page' in locals() and not page.is_closed():
                        os.makedirs(carpeta_evidencias, exist_ok=True)
                        path_err = os.path.join(carpeta_evidencias, f"error_ott_{id_hilo}.png")
                        page.screenshot(path=path_err, timeout=2000)
                        log_callback(f"📸 Evidencia guardada en {path_err}")
                except:
                    pass
            
            update_kpi_callback(fallo=1)
            
            # Calcular benchmark de tiempos
            tiempo_total, desglose_str = timer.print_benchmark(email_generado)
            
            # Guardar historial OTT fallido
            datos_err = {
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "OTT",
                "Tipo_Persona": tipo_cliente_str,
                "Documento_RIF": rif_completo,
                "Nombre_o_Empresa": f"{nombre} {apellido}",
                "Email": email_generado,
                "Telefono": telefono_completo,
                "Ubicacion": ubicacion_ott,
                "Plan": plan_ott,
                "Estado": f"Error: {err_msg}",
                "Tiempo_Total_Segundos": f"{tiempo_total}s",
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": ""
            }
            registrar_cuenta_creada(datos_err)
            
            log_callback(f"[Hilo {id_hilo}] ℹ️ Hilo fallido finalizado. Cerrando navegador y liberando recursos.")
                
            return {"exito": False, "error": err_msg, "email": email_generado}
