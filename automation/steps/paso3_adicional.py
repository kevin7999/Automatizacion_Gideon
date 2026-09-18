import random
from faker import Faker
from core.generadores import limpiar_texto_crm, generar_telefono_ve, generar_nombre_humano_limpio
from automation.crm_helpers import escribir_en_react, seleccionar_opcion_mui, hacer_clic_robusto

fake = Faker('es_ES')

def ejecutar_paso_3_adicional(page, id_hilo, tipo_persona, first_name, last_name_puro, phone_number, email, log_callback):
    """
    Rellena la información adicional y datos de contacto (Paso 3):
    - Proveedor anterior (Internet Provider -> 'No posee')
    - Representante legal (si es jurídica) o Género y Fecha de Nacimiento (si es natural)
    - Datos de vivienda y dirección 2
    - Checkbox de misma dirección de facturación
    - Contact Name y teléfono
    - Avanza al Paso 4 (Package Selection) con validación y auto-recuperación
    """
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(800)

    seleccionar_opcion_mui(page, "//label[contains(text(), 'Internet Provider')]/following-sibling::div | //*[contains(@id, 'internetProvider')]", "No posee", log_callback)

    rep_first = ""
    rep_last = ""

    if tipo_persona == "Persona jurídica":
        rep_first, rep_last = generar_nombre_humano_limpio()
        rep_doc = str(random.randint(12000000, 31999999))
        rep_phone = generar_telefono_ve()

        escribir_en_react(page, "//label[contains(text(), 'First Name')]/following-sibling::div//input | //input[contains(@name, 'firstName')]", rep_first)
        escribir_en_react(page, "//label[contains(text(), 'Last Name')]/following-sibling::div//input | //input[contains(@name, 'lastName')]", rep_last)
        seleccionar_opcion_mui(page, "//label[contains(text(), 'Identity Document')]/following-sibling::div", "Identification Card", log_callback)
        escribir_en_react(page, "//label[contains(text(), 'Document Number')]/following-sibling::div//input", rep_doc)
        seleccionar_opcion_mui(page, "//label[contains(text(), 'Nationality')]/following-sibling::div", "Venezuelan", log_callback)
        seleccionar_opcion_mui(page, "//label[contains(text(), 'Position of Character Representation')]/following-sibling::div", "Director", log_callback)
        seleccionar_opcion_mui(page, "//label[contains(text(), 'Supporting Document')]/following-sibling::div", "constitutive act", log_callback)
        escribir_en_react(page, "//label[contains(text(), 'Email Id')]/following-sibling::div//input", email)
        escribir_en_react(page, "//label[contains(text(), 'Mobile Phone')]/following-sibling::div//input", rep_phone)
        escribir_en_react(page, "//label[contains(text(), 'Other Mobile Phone')]/following-sibling::div//input", rep_phone)
    else:
        seleccionar_opcion_mui(page, "//label[contains(text(), 'Gender')]/following-sibling::div | //*[contains(@id, 'gender')]", "Female", log_callback)
        page.locator("input[name='dateOfBirth'], input[name='registrationDate']").first.click(force=True)
        page.wait_for_selector(".MuiDialog-root, [role='dialog']", state="visible", timeout=5000)
        page.wait_for_timeout(400)
        dia_activo = page.locator(".MuiPickersDay-daySelected, button.MuiPickersDay-root.Mui-selected, button.MuiPickersDay-today").first
        if dia_activo.is_visible():
            dia_activo.click(force=True)
        else:
            page.locator(".MuiPickersDay-root:not(.Mui-disabled)").last.click(force=True)
        page.wait_for_timeout(300)
        page.get_by_role("button", name="OK").click()
        page.wait_for_timeout(500)

    flat_num = limpiar_texto_crm(fake.bothify(text="Apto #-#"))
    ref_text = limpiar_texto_crm(f"Cerca de {fake.street_name()}")

    seleccionar_opcion_mui(page, "//label[contains(text(), 'Avenue/Street')]/following-sibling::div", "Avenida", log_callback)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Building/House')]/following-sibling::div", "Edificio", log_callback)
    escribir_en_react(page, "//label[contains(text(), 'Address 2')]/following-sibling::div//input | //label[contains(text(), 'Address 2')]/..//input", ref_text)
    escribir_en_react(page, "//label[contains(text(), 'Flat/House Number')]/following-sibling::div//input | //label[contains(text(), 'Flat/House Number')]/..//input", flat_num)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Housing Size')]/following-sibling::div", "From 70m", log_callback)

    chk_label = page.get_by_text("Keep the Billing Address same as Installation Address", exact=False)
    chk_input = page.locator("input[type='checkbox']").first
    if not chk_input.is_checked():
        chk_label.click()
        page.wait_for_timeout(500)

    contacto_nombre = f"{first_name} {last_name_puro}".strip() if tipo_persona == "Persona natural" else f"{rep_first} {rep_last}".strip()
    escribir_en_react(page, "//label[contains(text(), 'Contact Name')]/following-sibling::div//input | //label[contains(text(), 'Contact Name')]/..//input", contacto_nombre)
    
    try:
        page.evaluate("document.querySelectorAll('input').forEach(i => i.removeAttribute('maxlength'))")
    except Exception:
        pass

    escribir_en_react(page, "//label[contains(text(), 'Phone Number')]/following-sibling::div//input | //label[contains(text(), 'Phone Number')]/..//input", phone_number)
    escribir_en_react(page, "//label[contains(text(), 'References & Simple Plus')]/following-sibling::div//input | //label[contains(text(), 'References & Simple Plus')]/..//input", ref_text)

    # Avance hacia Paso 4
    paso4_cargado = False
    for intento in range(1, 4):
        log_callback(f"➡️ [Hilo {id_hilo}] (Intento {intento}/3) Enviando Paso 3 hacia Paquetes...")
        btn_proceed_step3 = page.locator("button:visible").filter(has_text="Proceed").last
        hacer_clic_robusto(page, btn_proceed_step3, f"Proceed Paso 3 (Intento {intento})")

        try:
            page.wait_for_selector("text=Package Selection", state="visible", timeout=15000)
            paso4_cargado = True
            log_callback(f"✅ [Hilo {id_hilo}] Paso 4 cargado exitosamente.")
            break
        except Exception:
            try:
                toast_err = page.locator(".MuiAlert-message, .Toastify__toast-body, div[role='alert']").first
                if toast_err.is_visible():
                    log_callback(f"⚠️ [Hilo {id_hilo}] Alerta del CRM en Paso 3: {toast_err.inner_text().strip()}")
            except Exception:
                pass
            log_callback(f"⚠️ [Hilo {id_hilo}] El CRM demoró en cargar el Paso 4. Reintentando...")
            page.wait_for_timeout(2000)

    if not paso4_cargado:
        log_callback(f"🔄 [Hilo {id_hilo}] Refrescando página para forzar carga del Paso 4...")
        page.reload(timeout=45000)
        page.wait_for_selector("text=Package Selection", state="visible", timeout=30000)

    return rep_first, rep_last
