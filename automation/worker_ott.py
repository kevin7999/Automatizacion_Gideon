import os
import time
import random
import re
from playwright.sync_api import sync_playwright

from core.correlativos import obtener_siguiente_correlativo, registrar_cuenta_creada, formatear_error_amigable
from core.generadores import generar_telefono_ve

from automation.worker import StepTimer

def obtener_codigo_otp_maildrop(email_base, correlativo, p_context):
    mailbox_name = f"{email_base}{correlativo}"
    page_maildrop = p_context.new_page()
    try:
        page_maildrop.goto(f"https://maildrop.cc/inbox/?mailbox={mailbox_name}", timeout=60000)
        
        codigo = None
        for i in range(5):
            page_maildrop.wait_for_timeout(3500)
            
            # Hacer clic en el primer correo de la lista (cualquiera que haya llegado)
            primer_correo = page_maildrop.locator("div[class*='truncate']").first
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
            except:
                pass
                
            for frame in page_maildrop.frames:
                try:
                    texto_visible += " " + frame.inner_text("body")
                except:
                    pass
            
            # Buscar 6 dígitos aislados (ej. 727633)
            match = re.search(r'\b(\d{6})\b', texto_visible)
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
    
    timer = StepTimer(id_hilo, log_callback, update_thread_status_callback)
    
    # 1. Preparar Datos Generados
    timer.start_step("P0: Preparación")
    try:
        nuevo_corr = obtener_siguiente_correlativo()
        telefono_completo = generar_telefono_ve()
        prefijo_tel = telefono_completo[:4]
        numero_tel = telefono_completo[4:]
        
        # OTT siempre es Persona Natural
        prefijo_ced = "V"
        cedula = str(random.randint(10000000, 30000000))
        nombre = "Gideon"
        apellido = "Test"
        rif_completo = f"V-{cedula}"
            
        email_base = sys_config.get("email_test_generico", "testgatb")
        if "@" in email_base:
            email_base = email_base.split("@")[0]
        email_generado = f"{email_base}{nuevo_corr}@maildrop.cc"
        
        log_callback(f"[Hilo {id_hilo}] 📝 OTT: {nombre} {apellido} | {cedula} | {email_generado} | Plan: {plan_ott}")
        timer.stop_step()
    except Exception as e:
        timer.stop_step("Error")
        err_msg = formatear_error_amigable(e, "preparando datos OTT")
        log_callback(f"[Hilo {id_hilo}] ❌ Error: {err_msg}")
        update_kpi_callback(fallo=1)
        return {"exito": False, "error": err_msg, "email": ""}

    with sync_playwright() as p:
        browser = None
        try:
            # P1: Lanzar Navegador
            timer.start_step("P1: Iniciar Navegador")
            browser = p.chromium.launch(headless=False, slow_mo=50) # Mostrar UI para debugging
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.set_default_timeout(45000)
            timer.stop_step()

            # P2: Navegación y Selección del Plan
            timer.start_step("P2: Selección de Plan OTT")
            page.goto("https://tiendatesting.simple.com.ve/planes-streaming")
            page.wait_for_load_state("networkidle")
            
            # Buscar el plan correspondiente. Ej: si es "Litesports", buscamos "Plan Lite"
            # Mapeo:
            btn_selector = ""
            if plan_ott.lower() == "litesports":
                btn_selector = "text='Personalizar plan Lite'"
            elif plan_ott.lower() == "gold":
                btn_selector = "text='Personalizar plan Oro'"
            elif plan_ott.lower() == "platino":
                btn_selector = "text='Personalizar plan Platino'"
            elif plan_ott.lower() == "diamante":
                btn_selector = "text='Personalizar plan Diamante'"
            else:
                btn_selector = f"text='Personalizar plan {plan_ott}'" # Fallback
            
            page.locator(btn_selector).click()
            page.wait_for_load_state("networkidle")
            
            # Seleccionar la primera variante (o la gratuita)
            # En la pantalla de variantes, hay botones "Ver canales" o el precio. Hacemos clic en el contenedor.
            # Simplemente le damos a Continuar, por defecto asume la base.
            page.locator("button:visible:has-text('Continuar')").first.click(force=True)
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
            
            # Checkbox: Clicar el texto
            page.locator("text='Declaro que toda la información proporcionada es real'").click(force=True)
            time.sleep(1)
            
            # Clicar Continuar
            btn_continuar = page.get_by_role("button", name="Continuar").last
            btn_continuar.click(force=True)
            
            # NO enviaremos Enter porque puede interactuar negativamente con el checkbox si quedó enfocado
            
            # DEBUG SCREENSHOT 1
            page.screenshot(path=os.path.join(os.getcwd(), "Evidencias_QA", f"debug_{id_hilo}_after_click.png"))
            
            timer.stop_step()

            # P4: OTP Maildrop
            timer.start_step("P4: Validar OTP")
            # Esperar a que la URL cambie indicando que pasamos al OTP
            try:
                page.wait_for_url("**/*validacion-streaming=otp*", timeout=20000)
                # Esperar un poco a que termine de renderizar el modal de OTP
                time.sleep(2)
            except Exception as e:
                # DEBUG SCREENSHOT 2 (If it times out)
                page.screenshot(path=os.path.join(os.getcwd(), "Evidencias_QA", f"debug_{id_hilo}_timeout_otp.png"))
                raise e
            
            # DEBUG SCREENSHOT 3 (If it succeeded)
            page.screenshot(path=os.path.join(os.getcwd(), "Evidencias_QA", f"debug_{id_hilo}_reached_otp.png"))
            
            # ir a maildrop
            log_callback(f"[Hilo {id_hilo}] ⏳ Esperando código OTP en {email_generado}...")
            # Lógica de espera OTP (reutilizando crm_helpers)
            time.sleep(10) # Espera inicial
            codigo_otp = None
            for intento in range(15):
                codigo_otp = obtener_codigo_otp_maildrop(email_base, nuevo_corr, context)
                if codigo_otp:
                    break
                log_callback(f"[Hilo {id_hilo}] OTP no encontrado, reintentando ({intento+1}/15)...")
                time.sleep(10)
                
            if not codigo_otp:
                raise Exception("Tiempo de espera agotado buscando OTP en maildrop.")
                
            log_callback(f"[Hilo {id_hilo}] ✅ Código OTP: {codigo_otp}")
            
            # Llenar casillas OTP
            for i, digito in enumerate(codigo_otp):
                # Escribimos explícitamente en otp.0, otp.1, otp.2...
                caja = page.locator(f"input[name='otp.{i}']")
                caja.click()
                caja.press_sequentially(digito, delay=50)
                
            # Disparar blur para asegurar validación final
            page.locator(f"input[name='otp.5']").blur()
                
            # Dar chance a React de actualizar el botón
            time.sleep(1)
                
            # Clicar Continuar
            btn_continuar_otp = page.get_by_role("button", name="Continuar").last
            btn_continuar_otp.click(force=True)
            
            timer.stop_step()

            # P5: Carrito y Generación de contrato
            timer.start_step("P5: Carrito y Contrato")
            
            # Click Continuar en Carrito
            page.wait_for_selector("text='Debe completar el registro de datos para continuar con el pago'", timeout=20000)
            page.locator("button:visible:has-text('Continuar')").first.click(force=True)
            
            # El modal "Generación de contrato" aparece después del clic
            page.wait_for_selector("text='Generación de contrato'", timeout=20000)
            
            # Llenar Cédula de Identidad (evitamos get_by_label por si el dropdown interfiere)
            cedula_input = page.locator("input[placeholder*='cédula de identidad'], input[placeholder*='Cédula']").first
            cedula_input.click(force=True)
            cedula_input.fill(cedula.replace("-",""))
            cedula_input.blur()
            
            # Checkbox P5
            page.locator("text='Declaro que toda la información proporcionada es real'").click(force=True)
            time.sleep(1)
            
            # Clicar Continuar
            btn_continuar_p5 = page.get_by_role("button", name="Continuar").last
            btn_continuar_p5.click(force=True)
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
            
            # Estado
            react_select_by_text(page, 'billingAddress.state', 'distrito capital')
            time.sleep(2) # Esperar a que cargue Ciudad
            
            # Ciudad
            react_select_by_text(page, 'billingAddress.city', 'caracas')
            time.sleep(2) # Esperar a que cargue Municipio
            
            # Municipio
            react_select_by_text(page, 'billingAddress.municipality', 'libertador')
            time.sleep(2) # Esperar a que cargue Zona
            
            # Zona
            react_select_by_text(page, 'billingAddress.zone', 'chacaito')
            time.sleep(2) # Esperar a que cargue Código postal
            
            # Código postal
            try:
                react_select_by_text(page, 'billingAddress.postalCode', '1050')
            except:
                pass # A veces se autocompleta o es único
            time.sleep(1)
            
            # Tipo de calle
            react_select_by_text(page, 'billingAddress.streetType', 'avenida')
            time.sleep(1)
            
            # Entradas de texto
            page.locator("input[placeholder*='avenida o calle']").fill("Av Venezuela", force=True)
            page.locator("input[placeholder*='nombre del edificio']").fill("torre directv", force=True)
            page.locator("input[placeholder*='número de casa']").fill("533", force=True)
            
            btn_continuar_p6 = page.get_by_role("button", name="Continuar").last
            btn_continuar_p6.click(force=True)
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
            
            # Continuar
            page.locator("button:visible:has-text('Continuar')").first.click(force=True)
            timer.stop_step()
            
            # P8: Aceptación
            timer.start_step("P8: Aceptación de documentos")
            page.wait_for_selector("text='Aceptación de documentos'")
            page.locator("input[type='checkbox']").check()
            page.locator("button:has-text('Continuar')").click()
            
            # Esperar a que vuelva al carrito con el botón "Pagar ahora"
            page.wait_for_selector("button:has-text('Pagar ahora')", timeout=20000)
            timer.stop_step("Exito")
            
            log_callback(f"[Hilo {id_hilo}] 🎉 Flujo OTT Completado! Correo: {email_generado}")
            
            # Registrar en catálogo
            registrar_cuenta_creada(
                email=email_generado,
                plan=plan_ott,
                direccion="Miranda - Chacao",
                cliente=tipo_persona,
                correlativo=nuevo_corr,
                metodo_pago="N/A",
                monto="0"
            )
            
            update_kpi_callback(exito=1)
            
            # Mantener el navegador abierto hasta que se cancele
            log_callback(f"[Hilo {id_hilo}] 🛑 Ejecución finalizada. El navegador quedará abierto.")
            while not (cancel_event and cancel_event.is_set()):
                time.sleep(1)
            
            return {"exito": True, "error": None, "email": email_generado}
            
        except Exception as e:
            if timer.current_step:
                timer.stop_step("Error")
            err_msg = formatear_error_amigable(e, timer.current_step if timer.current_step else "Flujo OTT")
            log_callback(f"[Hilo {id_hilo}] ❌ Error en {timer.current_step}: {err_msg}")
            
            if browser:
                try:
                    path_err = os.path.join(os.getcwd(), "Evidencias_QA", f"error_ott_{id_hilo}.png")
                    page.screenshot(path=path_err)
                    log_callback(f"📸 Evidencia guardada en {path_err}")
                except:
                    pass
            
            update_kpi_callback(fallo=1)
            
            # Mantener el navegador abierto en caso de error
            log_callback(f"[Hilo {id_hilo}] 🛑 Ejecución pausada por error. El navegador quedará abierto.")
            while not (cancel_event and cancel_event.is_set()):
                time.sleep(1)
                
            return {"exito": False, "error": err_msg, "email": email_generado}
