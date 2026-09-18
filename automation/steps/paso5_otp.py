import os
import re
from automation.crm_helpers import hacer_clic_robusto

def ejecutar_paso_5_otp_y_confirmacion(page, context, id_hilo, email, ruta_evidencia, log_callback):
    """
    Gestiona el Paso 5:
    - Entrada a Order Details
    - Disparo de contrato por email
    - Lectura de Maildrop y enlace de aceptación
    - Relleno de consentimiento y extracción robusta de OTP de 6 dígitos
    - Validación y envío de OTP en el CRM
    - Confirmación final de la orden y captura QA de cuenta creada
    """
    log_callback(f"📝 [Hilo {id_hilo}] Llegando a Order Confirmation...")
    page.wait_for_selector("button:has-text('Send Contract Via Email'), button:has-text('Send Contract')", state="visible", timeout=35000)
    page.wait_for_timeout(2000)

    # 📸 CAPTURA DE EVIDENCIA QA: INGRESO AL PASO 5 (ORDER DETAILS)
    archivo_paso5_inicio = os.path.join(ruta_evidencia, "02_Paso5_Order_Details.png")
    page.screenshot(path=archivo_paso5_inicio, full_page=False)
    log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Entrada a Paso 5 guardada.")

    max_intentos_otp = 3
    otp_confirmado = False

    for intento in range(1, max_intentos_otp + 1):
        log_callback(f"🔄 [Hilo {id_hilo}] Intento {intento}/{max_intentos_otp} de verificación OTP...")

        btn_send_contract = page.locator("button:visible").filter(has_text=re.compile(r"Send Contract Via Email|Send Contract", re.I)).first
        btn_send_contract.wait_for(state="visible", timeout=15000)
        hacer_clic_robusto(page, btn_send_contract, "Send Contract Via Email")
        
        log_callback(f"📨 [Hilo {id_hilo}] Disparo de contrato ejecutado (1 solo clic). Consultando Maildrop ({email})...")
        page.wait_for_timeout(3000)

        mailbox_name = email.split('@')[0]
        page_maildrop = None
        page_form = None
        codigo_otp = None
        id_cliente_extraido = ""

        try:
            page_maildrop = context.new_page()
            page_maildrop.goto(f"https://maildrop.cc/inbox/?mailbox={mailbox_name}", timeout=60000)

            correo_encontrado = False
            for i in range(1, 11):
                log_callback(f"⏳ [Hilo {id_hilo}] Esperando correo en Maildrop... Intento {i}/10 ({i*3.5:.1f}s transcurridos)")
                item_correo = page_maildrop.locator("text=Bienvenido a Simplefibra").first
                if not item_correo.is_visible():
                    item_correo = page_maildrop.locator("text=Simplefibra").first
                
                if item_correo.is_visible():
                    item_correo.click()
                    correo_encontrado = True
                    break
                page_maildrop.reload()
                page_maildrop.wait_for_timeout(3500)

            if not correo_encontrado:
                log_callback(f"⚠️ [Hilo {id_hilo}] Correo no detectado en intento {intento}. Reintentando...")
                continue

            page_maildrop.wait_for_timeout(1500)

            # 📸 CAPTURA DE EVIDENCIA QA: CORREO CONTRATO EN MAILDROP
            try:
                archivo_maildrop = os.path.join(ruta_evidencia, "03_Maildrop_Correo_Contrato.png")
                captured_mail = False
                for frame in page_maildrop.frames:
                    try:
                        content_str = frame.content()
                        if "Responder formulario" in content_str or "Simplefibra" in content_str:
                            frame.locator("body").screenshot(path=archivo_maildrop)
                            captured_mail = True
                            
                            # Extraer N° de Cliente desde el HTML del correo
                            if not id_cliente_extraido:
                                match_id = re.search(r'cliente\D*(\d{4,})', content_str, re.IGNORECASE)
                                if match_id:
                                    id_cliente_extraido = match_id.group(1).strip()
                                    log_callback(f"👤 [Hilo {id_hilo}] N° de Cliente Extraído del correo de Maildrop: {id_cliente_extraido}")
                            
                            break
                    except Exception:
                        pass
                if not captured_mail:
                    page_maildrop.screenshot(path=archivo_maildrop, full_page=True)
                log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Correo en Maildrop guardada.")
            except Exception:
                pass

            enlace_form = page_maildrop.evaluate("""() => {
                let links = Array.from(document.querySelectorAll('a'));
                let target = links.find(a => a.innerText && a.innerText.includes('Responder formulario'));
                return target ? target.href : null;
            }""")

            if not enlace_form:
                for frame in page_maildrop.frames:
                    try:
                        enlace = frame.evaluate("""() => {
                            let links = Array.from(document.querySelectorAll('a'));
                            let target = links.find(a => a.innerText && a.innerText.includes('Responder formulario'));
                            return target ? target.href : null;
                        }""")
                        if enlace:
                            enlace_form = enlace
                            break
                    except Exception:
                        continue

            if not enlace_form:
                log_callback(f"⚠️ [Hilo {id_hilo}] No se pudo extraer enlace en intento {intento}.")
                continue

            log_callback(f"📝 [Hilo {id_hilo}] Abriendo formulario de aceptación...")
            page_form = context.new_page()
            page_form.goto(enlace_form, timeout=60000)
            page_form.wait_for_load_state("networkidle")
            page_form.wait_for_timeout(1500)

            checkboxes = page_form.locator("input[type='checkbox']")
            for c_idx in range(checkboxes.count()):
                try:
                    checkboxes.nth(c_idx).check(force=True)
                except Exception:
                    pass

            page_form.wait_for_timeout(800)

            # 📸 CAPTURA DE EVIDENCIA QA: FORMULARIO DE CONSENTIMIENTO
            try:
                archivo_form_check = os.path.join(ruta_evidencia, "04_Formulario_Encuesta_Consentimiento.png")
                page_form.screenshot(path=archivo_form_check, full_page=True)
                log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Encuesta Completa con Consentimiento guardada.")
            except Exception:
                pass

            try:
                page_form.get_by_role("button", name=re.compile(r"Generar c[oó]digo", re.I)).click()
            except Exception:
                page_form.locator("#submit_form, #saveForm, input[type='submit'], button").first.click(force=True)

            try:
                # 1. Espera activa a que aparezca la pantalla del código OTP (hasta 15 segundos)
                try:
                    page_form.wait_for_selector(
                        "text=/c[oó]digo de verificaci[oó]n|expira en|asesor de ventas/i, #element_3",
                        state="visible",
                        timeout=15000
                    )
                except Exception:
                    page_form.wait_for_timeout(3000)

                # 2. Ciclo de extracción para asegurar que el elemento renderizó su valor
                for _ in range(5):
                    # Método A: Input tradicional #element_3 (formularios clásicos)
                    elem_otp = page_form.locator("#element_3").first
                    if elem_otp.is_visible():
                        try:
                            val = elem_otp.input_value()
                            if val and re.match(r'^\d{6}$', val.strip()):
                                codigo_otp = val.strip()
                                break
                        except Exception:
                            pass
                        try:
                            val_txt = elem_otp.inner_text()
                            if val_txt and re.match(r'^\d{6}$', val_txt.strip()):
                                codigo_otp = val_txt.strip()
                                break
                        except Exception:
                            pass

                    # Método B: Buscar en el texto visible de la pantalla (body inner_text)
                    try:
                        texto_formulario = page_form.inner_text("body")
                        
                        # Prioridad B1: 6 dígitos inmediatamente precedidos por palabras clave del formulario
                        match_cerca = re.search(r'(?:c[oó]digo|verificaci[oó]n|aqu[ií]\s+est[aá])[^\d]*(\d{6})\b', texto_formulario, re.IGNORECASE)
                        if match_cerca:
                            codigo_otp = match_cerca.group(1)
                            break

                        # Prioridad B2: Cualquier número de 6 dígitos visible en pantalla descartando falsos positivos
                        matches = [m for m in re.findall(r'\b\d{6}\b', texto_formulario) if m != "333333"]
                        if matches:
                            codigo_otp = matches[0]
                            break
                    except Exception:
                        pass

                    page_form.wait_for_timeout(1000)

                # Método C (Respaldo extremo sin CSS): Si aún no se extrajo, buscar en HTML pero LIMPIANDO estilos y scripts
                if not codigo_otp or not re.match(r'^\d{6}$', str(codigo_otp)):
                    try:
                        html_crudo = page_form.content()
                        # Eliminar bloques <style> y <script> y colores hex para evitar leer códigos CSS (#333333)
                        html_sin_estilos = re.sub(r'<style.*?>.*?</style>', '', html_crudo, flags=re.DOTALL | re.IGNORECASE)
                        html_sin_estilos = re.sub(r'<script.*?>.*?</script>', '', html_sin_estilos, flags=re.DOTALL | re.IGNORECASE)
                        html_sin_estilos = re.sub(r'#[0-9a-fA-F]{6}', '', html_sin_estilos)
                        
                        matches_html = [m for m in re.findall(r'\b\d{6}\b', html_sin_estilos) if m != "333333"]
                        if matches_html:
                            codigo_otp = matches_html[0]
                    except Exception:
                        pass

                # Extraer N° de Cliente si existe en el texto (como respaldo por si no estaba en el correo)
                if not id_cliente_extraido:
                    try:
                        texto_completo = page_form.inner_text("body")
                        # Buscar la palabra cliente seguida de caracteres no numericos y luego al menos 5 digitos
                        match_id = re.search(r'cliente\D*(\d{4,})', texto_completo, re.IGNORECASE)
                        
                        if not match_id:
                            # Respaldo buscando en el HTML crudo
                            match_id = re.search(r'cliente\D*(\d{4,})', page_form.content(), re.IGNORECASE)
                            
                        if match_id:
                            id_cliente_extraido = match_id.group(1).strip()
                            log_callback(f"👤 [Hilo {id_hilo}] N° de Cliente Extraído del formulario: {id_cliente_extraido}")
                    except Exception as e_id:
                        log_callback(f"⚠️ [Hilo {id_hilo}] No se pudo extraer N° de Cliente en form: {e_id}")

                # 📸 CAPTURA DE EVIDENCIA QA: CÓDIGO OTP
                try:
                    archivo_form_otp = os.path.join(ruta_evidencia, "05_Formulario_Codigo_OTP.png")
                    page_form.screenshot(path=archivo_form_otp, full_page=True)
                    log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Código OTP guardada.")
                except Exception:
                    pass
            except Exception as e_extract:
                log_callback(f"⚠️ [Hilo {id_hilo}] Incidencia al extraer OTP: {e_extract}")
                codigo_otp = None
        finally:
            if page_form:
                try:
                    page_form.close()
                except Exception:
                    pass
            if page_maildrop:
                try:
                    page_maildrop.close()
                except Exception:
                    pass

        if not codigo_otp or len(codigo_otp) < 5:
            log_callback(f"⚠️ [Hilo {id_hilo}] OTP no válido extraído en intento {intento}.")
            continue

        log_callback(f"🔑 [Hilo {id_hilo}] Código OTP Extraído: {codigo_otp}")

        page.bring_to_front()
        input_otp_crm = page.locator("input[placeholder*='OTP' i], input[name*='otp' i], fieldset:has-text('Enter OTP') input").first
        input_otp_crm.wait_for(state="visible", timeout=5000)
        input_otp_crm.fill("")
        input_otp_crm.fill(codigo_otp)
        page.wait_for_timeout(800)

        btn_submit_otp = page.locator("button:visible").filter(has_text="Submit").first
        hacer_clic_robusto(page, btn_submit_otp, "Submit OTP")

        try:
            page.wait_for_selector("text=OTP verification is success", state="visible", timeout=12000)
            log_callback(f"✅ [Hilo {id_hilo}] OTP verificado con éxito en intento {intento}.")
            otp_confirmado = True
            break
        except Exception:
            log_callback(f"❌ [Hilo {id_hilo}] El CRM rechazó el OTP en intento {intento}. Reintentando flujo...")
            page.wait_for_timeout(2000)

    if not otp_confirmado:
        raise Exception(f"Fallaron los {max_intentos_otp} intentos de validación de OTP.")

    page.wait_for_timeout(1000)
    hacer_clic_robusto(page, page.locator("button:visible").filter(has_text="Confirm").last, "Confirm Final")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 📸 CAPTURA DE EVIDENCIA QA: CUENTA CREADA
    archivo_exito = os.path.join(ruta_evidencia, "06_CRM_Cuenta_Creada.png")
    page.screenshot(path=archivo_exito, full_page=False)
    log_callback(f"📸 [Hilo {id_hilo}] Evidencia final de Cuenta Creada en CRM guardada.")
    
    return id_cliente_extraido
