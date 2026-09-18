import os
import re
from automation.crm_helpers import seleccionar_opcion_mui, hacer_clic_robusto

def ejecutar_paso_4_paquetes(page, id_hilo, paquete_nombre, promocion_nombre, tarifa_inst, router_nombre, ruta_evidencia, log_callback):
    """
    Configura el Paquete, Promociones y Equipo Router (Pasos 4 y 4.1):
    - Selecciona Package Type ('Bundle')
    - Selecciona Paquete y Duración ('1 Months')
    - Aplica promociones configuradas
    - Selecciona tarifa de instalación
    - Guarda captura de evidencia QA del plan
    - Avanza a Equipos y marca el Router seleccionado
    - Avanza a Add-Ons
    """
    log_callback(f"📦 [Hilo {id_hilo}] Configurando Paquete: {paquete_nombre}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)

    seleccionar_opcion_mui(page, "//label[contains(text(), 'Package Type')]/following-sibling::div", "Bundle", log_callback, timeout_menu=12000, max_intentos=4)
    
    log_callback(f"⏳ [Hilo {id_hilo}] Sincronizando catálogo de paquetes con el CRM...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)
    
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Packages')]/following-sibling::div", paquete_nombre, log_callback, timeout_menu=15000, max_intentos=4)
    
    log_callback(f"⏳ [Hilo {id_hilo}] Sincronizando duración y promociones...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    
    seleccionar_opcion_mui(page, "//label[contains(text(), 'Duration')]/following-sibling::div", "1 Months", log_callback, timeout_menu=10000, max_intentos=3)
    page.wait_for_timeout(1500)

    sin_promo_keywords = ["", "sin promo", "sin_promo", "ninguna", "ninguno", "n/a", "none", "-"]
    promo_activa = bool(promocion_nombre and promocion_nombre.strip().lower() not in sin_promo_keywords)

    if not promo_activa:
        log_callback(f"ℹ️ [Hilo {id_hilo}] Plan configurado SIN promociones (Tarifa estándar). Omitiendo marcado...")
    else:
        promos = [p.strip() for p in promocion_nombre.split(",") if p.strip()]
        for promo in promos:
            if promo.lower() in sin_promo_keywords:
                continue
            try:
                patron_promo = re.compile(rf"^\s*{re.escape(promo.strip())}\s*$", re.IGNORECASE)
                lbl_promo = page.locator("label").filter(has=page.get_by_text(patron_promo)).first
                
                if not lbl_promo.count() and (promo.endswith("_") or " " in promo):
                    promo_limpia = promo.rstrip("_").strip()
                    patron_limpio = re.compile(rf"^\s*{re.escape(promo_limpia)}\s*$", re.IGNORECASE)
                    lbl_promo = page.locator("label").filter(has=page.get_by_text(patron_limpio)).first

                if not lbl_promo.count():
                    lbl_promo = page.locator("label").filter(has_text=promo).first
                if not lbl_promo.count() and promo.endswith("_"):
                    lbl_promo = page.locator("label").filter(has_text=promo.rstrip("_")).first

                chk_promo = lbl_promo.locator("input[type='checkbox']").first
                chk_promo.scroll_into_view_if_needed()
                if chk_promo.is_visible() and not chk_promo.is_checked():
                    chk_promo.check(force=True)
                    log_callback(f"✅ [Hilo {id_hilo}] Promoción '{promo}' aplicada.")
            except Exception as e:
                log_callback(f"⚠️ [Hilo {id_hilo}] No se pudo marcar la promoción '{promo}': {e}")

    log_callback(f"⏳ [Hilo {id_hilo}] Esperando cálculo de tarifas en el CRM...")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)

    seleccionar_opcion_mui(page, "//label[contains(text(), 'Installation Fees')]/following-sibling::div", tarifa_inst, log_callback, timeout_menu=15000, max_intentos=4)
    page.wait_for_timeout(1500)

    # 📸 Captura QA del Plan
    archivo_plan = os.path.join(ruta_evidencia, f"01_Paso4_{paquete_nombre.replace(' ', '_')}.png")
    page.screenshot(path=archivo_plan, full_page=False)
    log_callback(f"📸 [Hilo {id_hilo}] Evidencia de Plan guardada.")

    btn_next_step4 = page.locator("button:visible").filter(has_text="Next").last
    hacer_clic_robusto(page, btn_next_step4, "Next Step 4")
    page.wait_for_load_state("networkidle")
    
    # ----------------------------------------------------
    # Paso 4.1: Selección de Router
    # ----------------------------------------------------
    log_callback(f"📡 [Hilo {id_hilo}] Seleccionando Equipo: {router_nombre}")
    page.wait_for_selector("text=LIST OF EQUIPMENTS", state="visible", timeout=20000)
    page.wait_for_timeout(1500)

    log_callback(f"🧹 [Hilo {id_hilo}] Limpiando selecciones por defecto...")
    try:
        contenedor_equipos = page.locator("table, .MuiTable-root, [role='table']").first
        if contenedor_equipos.count():
            equipos_checks = contenedor_equipos.locator("input[type='checkbox']")
        else:
            equipos_checks = page.locator("input[type='checkbox']")
        
        for i in range(equipos_checks.count()):
            if equipos_checks.nth(i).is_checked():
                equipos_checks.nth(i).uncheck(force=True)
    except Exception as e:
        log_callback(f"⚠️ [Hilo {id_hilo}] Advertencia limpiando checkboxes: {e}")
    page.wait_for_timeout(500)

    router_marcado = False
    try:
        patron_router = re.compile(rf"^\s*{re.escape(router_nombre.strip())}\s*$", re.IGNORECASE)
        fila_equipo = page.locator("tr").filter(has=page.get_by_text(patron_router)).first
        if not fila_equipo.count():
            fila_equipo = page.locator("div").filter(has=page.get_by_text(patron_router)).first

        if not fila_equipo.count():
            nombre_alt = router_nombre.replace("N ", "").strip() if router_nombre.startswith("N ") else f"N {router_nombre}"
            patron_alt = re.compile(rf"^\s*{re.escape(nombre_alt)}\s*$", re.IGNORECASE)
            fila_equipo = page.locator("tr").filter(has=page.get_by_text(patron_alt)).first

        if not fila_equipo.count():
            fila_equipo = page.locator("tr").filter(has_text=router_nombre).first

        if fila_equipo.count():
            chk_equipo = fila_equipo.locator("input[type='checkbox']").first
            chk_equipo.scroll_into_view_if_needed()
            chk_equipo.check(force=True)
            if chk_equipo.is_checked():
                router_marcado = True
                log_callback(f"✅ [Hilo {id_hilo}] Router '{router_nombre}' seleccionado correctamente.")
    except Exception as e:
        log_callback(f"⚠️ [Hilo {id_hilo}] Error al marcar el router: {e}")

    if not router_marcado:
        try:
            for i in range(equipos_checks.count()):
                if equipos_checks.nth(i).is_checked():
                    router_marcado = True
                    break
        except Exception:
            pass

    if not router_marcado:
        try:
            equipos_visibles = page.locator("table tr td:first-child, .MuiTable-root tr").all_inner_texts()
            equipos_str = ", ".join([e.strip() for e in equipos_visibles if e.strip()][:5])
        except Exception:
            equipos_str = "No detectados"
        raise Exception(f"Timeout - Lista lenta: No se encontró ni pudo marcarse el router '{router_nombre}'. Equipos en CRM: [{equipos_str}].")

    page.wait_for_timeout(1000)
    btn_proceed_equip = page.locator("button:visible").filter(has_text="Proceed").last
    hacer_clic_robusto(page, btn_proceed_equip, "Proceed Equipments")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)
