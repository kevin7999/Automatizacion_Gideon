import re

def escribir_en_react(page, selector, texto):
    """Escribe un texto en un input de React limpiando el valor previo y disparando eventos de cambio."""
    input_elem = page.locator(selector).first
    input_elem.wait_for(state="visible", timeout=30000)
    
    try:
        input_elem.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
        
    try:
        input_elem.click(timeout=3000)
    except Exception:
        try:
            input_elem.click(force=True, timeout=3000)
        except Exception:
            pass
            
    input_elem.fill("")
    input_elem.fill(str(texto))
    page.wait_for_timeout(100)

def seleccionar_opcion_mui(page, selector_combobox, texto_opcion, log_callback, timeout_menu=10000, max_intentos=4):
    """Interactúa con dropdowns y selectores Material-UI (MUI) de React con reintentos y tolerancia a latencia del CRM."""
    combobox = page.locator(selector_combobox).first
    combobox.wait_for(state="visible", timeout=60000)

    # Si el selector está temporalmente deshabilitado por llamadas asíncronas del CRM, esperar
    for _ in range(12):
        try:
            clases = combobox.get_attribute("class") or ""
            aria_dis = combobox.get_attribute("aria-disabled") or ""
            if "Mui-disabled" in clases or aria_dis == "true":
                page.wait_for_timeout(1000)
            else:
                break
        except Exception:
            break

    # Esperar si hay indicadores de carga activos en el CRM
    try:
        spinner = page.locator(".MuiCircularProgress-root, [role='progressbar']").first
        if spinner.is_visible():
            spinner.wait_for(state="hidden", timeout=15000)
    except Exception:
        pass

    menu_abierto = False
    for intento in range(1, max_intentos + 1):
        try:
            combobox.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass

        try:
            combobox.click(timeout=4000)
        except Exception:
            combobox.click(force=True, timeout=4000)

        try:
            page.wait_for_selector(".MuiPopover-root, .MuiMenu-paper, ul[role='listbox']", state="visible", timeout=timeout_menu)
            menu_abierto = True
            break
        except Exception:
            if intento < max_intentos:
                log_callback(f"⏳ [CRM Lento] Desplegando '{texto_opcion}' (Reintento {intento}/{max_intentos})...")
                page.wait_for_timeout(1500 * intento)
            continue

    if not menu_abierto:
        raise Exception(f"El CRM está congestionado o lento: No se pudo desplegar el menú de '{texto_opcion}' tras {max_intentos} intentos.")

    page.wait_for_timeout(600)

    # 1. Coincidencia exacta insensible a mayúsculas
    patron_exacto = re.compile(rf"^\s*{re.escape(texto_opcion.strip())}\s*$", re.IGNORECASE)
    opcion = page.locator(".MuiMenuItem-root, li[role='option']").filter(has=page.get_by_text(patron_exacto)).first

    # 2. Coincidencia de prefijo (ej. '1 Months' en '1 Months - $54...')
    if not opcion.count():
        patron_prefijo = re.compile(rf"^\s*{re.escape(texto_opcion.strip())}(\s*[-–(].*)?$", re.IGNORECASE)
        opcion = page.locator(".MuiMenuItem-root, li[role='option']").filter(has=page.get_by_text(patron_prefijo)).first

    # 3. Fallback a subcadena
    if not opcion.count():
        opcion = page.locator(".MuiMenuItem-root, li[role='option']").filter(has_text=texto_opcion).first

    try:
        opcion.wait_for(state="visible", timeout=12000)
    except Exception:
        opcion = page.locator(".MuiMenuItem-root, li[role='option']").get_by_text(texto_opcion, exact=False).first
        opcion.wait_for(state="visible", timeout=8000)

    try:
        opcion.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    opcion.click(force=True)

    # Esperar que el popover se cierre para no tapar elementos posteriores
    try:
        page.wait_for_selector(".MuiPopover-root, .MuiMenu-paper, ul[role='listbox']", state="hidden", timeout=5000)
    except Exception:
        pass

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)

def hacer_clic_robusto(page, locator_elem, nombre_boton):
    """Ejecuta un clic seguro con auto-scroll, reintento forzado por JS y escape a errores modales."""
    elem = locator_elem.first
    try:
        elem.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    
    for intento in range(4):
        try:
            elem.click(timeout=5000)
        except Exception:
            try:
                elem.click(force=True, timeout=5000)
            except Exception:
                try:
                    elem.evaluate("""node => {
                        node.click();
                        node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    }""")
                except Exception:
                    pass
        
        try:
            error_rojo = page.locator("text=Something went wrong").first
            if error_rojo.is_visible():
                page.keyboard.press("Escape") 
                page.wait_for_timeout(2000)
                continue
            else:
                break
        except Exception:
            break
