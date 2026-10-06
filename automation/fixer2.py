import re

with open(r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py', 'r', encoding='latin-1') as f:
    text = f.read()

# Buscamos desde: # Pantalla del Carrito ... hasta: # ── CONTRATO PASO 3/4: Dirección de instalación ── o similar
start_idx = text.find('timer.start_step("F2: Carrito")')
end_idx = text.find('timer.start_step("F3: Contrato P3/4')

if start_idx == -1 or end_idx == -1:
    print('No se encontró el inicio o el fin')
else:
    # Ajustamos start_idx a la línea del comentario
    start_idx = text.rfind('# Pantalla del Carrito', 0, start_idx)
    # Ajustamos end_idx a la línea del comentario
    end_idx = text.rfind('#', 0, end_idx)

    # Bloque nuevo (sin caracteres raros y cuidando indentacion)
    new_block = '''            # Pantalla del Carrito
            timer.start_step("F2: Carrito")
            try:
                page.wait_for_selector("text='Carrito'", timeout=15000)
            except Exception:
                pass
            log_callback(f"[Hilo {id_hilo}] 🛒 Carrito cargado. Avanzando al registro...")
            page.wait_for_timeout(2000)

            page.locator("button:visible").filter(has_text="Continuar").first.click(force=True)
            page.wait_for_timeout(3000)
            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 3 — GENERACIÓN DE CONTRATO (4 PASOS)
            # ────────────────────────────────────────────────────────────────────────────────

            # ── CONTRATO PASO 1/4: Datos básicos + Cédula ──
            timer.start_step("F3: Contrato P1/4 Identidad")
            page.wait_for_selector("text='Generación de contrato'", timeout=20000)
            log_callback(f"[Hilo {id_hilo}] 📄 Contrato abierto. Llenando datos de identidad...")

            log_callback(f"[Hilo {id_hilo}] 👤 Seleccionando Tipo de cliente: Persona natural")
            try:
                page.locator("select[name='clientType']").select_option(label="Persona natural", force=True)
            except Exception:
                try:
                    page.locator("select[name='clientType']").select_option(index=1, force=True)
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] ⚠️ Falló la selección del tipo de cliente: {e}")
            page.wait_for_timeout(500)

            try:
                page.get_by_label("Nombre").fill(nombre, force=True)
                page.get_by_label("Nombre").blur()
                page.get_by_label("Apellido").fill(apellido, force=True)
                page.get_by_label("Apellido").blur()
            except Exception:
                pass

            try:
                selects_cedula = page.locator("select")
                for i in range(selects_cedula.count()):
                    opciones = selects_cedula.nth(i).inner_text().upper()
                    if "V" in opciones and "E" in opciones:
                        selects_cedula.nth(i).select_option(label=prefijo_ced, force=True)
                        break
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] ⚠️ Falló la selección del prefijo de cédula: {e}")
            page.wait_for_timeout(300)

            campo_cedula = page.locator(
                "input[placeholder*='cédula'], input[placeholder*='Cédula'], input[name*='cedula'], input[name*='identity']"
            ).first
            campo_cedula.click(force=True)
            campo_cedula.fill(cedula)
            campo_cedula.blur()
            page.wait_for_timeout(500)

            try:
                selects_tel = page.locator("select")
                for i in range(selects_tel.count()):
                    opciones = selects_tel.nth(i).inner_text()
                    if "0412" in opciones or "0414" in opciones:
                        selects_tel.nth(i).select_option(label=prefijo_tel, force=True)
                        break
                page.locator("input[name='phone.number']").fill(numero_tel, force=True)
                page.locator("input[name='phone.number']").blur()
            except Exception:
                pass

            try:
                chk_declaro = page.locator("input[name='informationDeclaration']").first
                chk_declaro.wait_for(state="attached", timeout=5000)
                chk_declaro.click(force=True)
            except Exception:
                page.locator("text=/Declaro que toda la informaci.n/i").first.click(force=True)
            page.wait_for_timeout(1000)

            guardar_evidencia(timer.current_step)

            _esperar_captcha_si_presente(page, id_hilo, 'Contrato P1 submit', log_callback, cancel_event, solo_fullpage=True)

            page.get_by_role("button", name="Continuar").last.click(force=True)
            page.wait_for_timeout(3000)
            timer.stop_step()

            # ── CONTRATO PASO 2/4: OTP ──
            timer.start_step("F3: Contrato P2/4 OTP")
            try:
                page.wait_for_selector(
                    "text=/Verificaci.n de correo electr.nico/i, text=/ingresa el c.digo enviado/i, input[placeholder='0']",
                    timeout=30000
                )
            except Exception:
                os.makedirs(carpeta_evidencias, exist_ok=True)
                page.screenshot(
                    path=os.path.join(carpeta_evidencias, f"debug_H{id_hilo}_timeout_otp_ecom.png")
                )
                raise Exception("El formulario de OTP no apareció a tiempo.")

            log_callback(f"[Hilo {id_hilo}] ⏳ Esperando OTP en {email_generado}...")
            import time
            time.sleep(10)

            codigo_otp = None
            for intento in range(15):
                if cancel_event and cancel_event.is_set():
                    raise Exception("Ejecución cancelada por el usuario.")

                codigo_otp = _obtener_otp_maildrop_ecom(
                    email_base, nuevo_corr, context, id_hilo, log_callback, cancel_event
                )
                if codigo_otp:
                    break

                for _ in range(10):
                    if cancel_event and cancel_event.is_set():
                        raise Exception("Ejecución cancelada por el usuario.")
                    time.sleep(1)

            if not codigo_otp:
                os.makedirs(carpeta_evidencias, exist_ok=True)
                page.screenshot(
                    path=os.path.join(carpeta_evidencias, f"debug_H{id_hilo}_otp_no_recibido.png")
                )
                raise Exception("Tiempo agotado: no se recibió el OTP en Maildrop.")

            try:
                import re
                cajas = page.locator("input[placeholder='0'], input[name^='otp.'], input[maxlength='1']")
                if cajas.count() >= 6:
                    for i, digito in enumerate(codigo_otp):
                        caja = cajas.nth(i)
                        caja.click(force=True)
                        caja.press_sequentially(digito, delay=50)
                    cajas.nth(5).blur()
                else:
                    modal_otp = page.locator("div").filter(has_text=re.compile(r"Verificaci.n de correo electr.nico", re.I)).last
                    inputs_modal = modal_otp.locator("input")
                    if inputs_modal.count() >= 6:
                        for i, digito in enumerate(codigo_otp):
                            inputs_modal.nth(i).click(force=True)
                            inputs_modal.nth(i).press_sequentially(digito, delay=50)
                        inputs_modal.nth(5).blur()
                    else:
                        raise Exception("No se encontraron 6 casillas individuales.")
            except Exception:
                campo_otp_unico = page.locator(
                    "input[placeholder*='código'], input[placeholder*='Código'], input[type='number'], input[name*='otp']"
                ).first
                campo_otp_unico.fill(codigo_otp, force=True)
                campo_otp_unico.blur()

            page.wait_for_timeout(1000)
            guardar_evidencia(timer.current_step)

            page.get_by_role("button", name="Continuar").last.click(force=True)
            page.wait_for_timeout(4000)
            timer.stop_step()

'''
    text = text[:start_idx] + new_block + text[end_idx:]
    with open(r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Reemplazo completado con exito!')
