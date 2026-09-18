from automation.crm_helpers import escribir_en_react, seleccionar_opcion_mui, hacer_clic_robusto

def ejecutar_paso_2_direccion(page, id_hilo, direccion_hilo, log_callback):
    """
    Rellena la dirección de instalación (Paso 2):
    - Estado, Ciudad, Municipio, Parroquia, Código Postal
    - Edificio / Casa
    - Ejecuta 'Locate' y 'Check & Confirm' en el mapa con auto-reparación
    - Avanza al Paso 3 con confirmación de visibilidad de indicadores
    """
    page.wait_for_selector("text=Installation Address", state="visible", timeout=35000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    seleccionar_opcion_mui(page, "//label[contains(text(), 'State')]/following-sibling::div | //*[contains(@id, 'state')]", direccion_hilo["state"], log_callback)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'City')]/following-sibling::div | //*[contains(@id, 'city')]", direccion_hilo["city"], log_callback)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Municipality')]/following-sibling::div | //*[contains(@id, 'municipality')]", direccion_hilo["municipality"], log_callback)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Neighbourhood')]/following-sibling::div | //*[contains(@id, 'neighbourhood')]", direccion_hilo["neighbourhood"], log_callback)
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Postal Code')]/following-sibling::div | //*[contains(@id, 'postalCode')]", direccion_hilo["postal_code"], log_callback)

    escribir_en_react(page, "#addrLine6", direccion_hilo["building_house"])
    page.evaluate("document.activeElement.blur()")
    page.wait_for_timeout(1500)

    btn_locate = page.locator("button:visible").filter(has_text="Locate").first
    btn_locate.wait_for(state="visible", timeout=30000)
    hacer_clic_robusto(page, btn_locate, "Locate")
    
    log_callback(f"🗺️ [Hilo {id_hilo}] Localizando en mapa...")
    page.wait_for_timeout(3000)

    btn_check_confirm = page.locator("button:visible").filter(has_text="Check & Confirm").first
    btn_check_confirm.wait_for(state="visible", timeout=30000)
    hacer_clic_robusto(page, btn_check_confirm, "Check & Confirm")

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Auto-reparación si el mapa pide reintento de localización
    for _ in range(2):
        modal_error = page.locator("text=Service not available, text=Invalid Address, text=Unable to locate").first
        if modal_error.is_visible():
            log_callback(f"⚠️ [Hilo {id_hilo}] Fallo de localización. Reintentando Locate...")
            hacer_clic_robusto(page, btn_locate, "Locate Reintento")
            page.wait_for_timeout(3000)
            hacer_clic_robusto(page, btn_check_confirm, "Check & Confirm Reintento")
            page.wait_for_timeout(2000)

    # Avance seguro del Paso 2 al Paso 3
    btn_proceed_step2 = page.locator("button:visible").filter(has_text="Proceed").first
    if btn_proceed_step2.is_visible():
        hacer_clic_robusto(page, btn_proceed_step2, "Proceed Step 2")

    # Indicador inequívoco del Paso 3 (Internet Provider o Date of Birth)
    indicador_paso3 = page.get_by_text("Internet Provider").or_(page.locator("[id*='internetProvider']")).or_(page.locator("input[name='dateOfBirth'], input[name='registrationDate']"))

    try:
        indicador_paso3.first.wait_for(state="visible", timeout=12000)
    except Exception:
        if page.locator("#addrLine6").is_visible() and btn_proceed_step2.is_visible():
            log_callback(f"⏳ [Hilo {id_hilo}] Reintentando Proceed en Paso 2...")
            hacer_clic_robusto(page, btn_proceed_step2, "Proceed Step 2 Reintento")
        indicador_paso3.first.wait_for(state="visible", timeout=25000)
