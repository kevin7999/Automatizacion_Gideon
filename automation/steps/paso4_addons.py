import re
from automation.crm_helpers import hacer_clic_robusto

def ejecutar_paso_4_2_addons(page, id_hilo, log_callback):
    """
    Oprime 'Proceed' en la pantalla de Add-Ons adicionales para avanzar al Paso 5.
    Incluye auto-reintento si el primer clic no gatilla la transición.
    """
    log_callback(f"🔌 [Hilo {id_hilo}] Omitiendo Add-Ons adicionales...")
    page.wait_for_timeout(2000)
    
    btn_proceed_addons = page.locator("button:visible").filter(has_text=re.compile(r"^Proceed$", re.I)).last
    btn_proceed_addons.wait_for(state="visible", timeout=35000)
    page.wait_for_timeout(1000)

    hacer_clic_robusto(page, btn_proceed_addons, "Proceed Add-Ons")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Si sigue en la pantalla de Add-ons, hacer reintento de clic
    for _ in range(3):
        if page.locator("button:has-text('Send Contract Via Email')").first.is_visible():
            break
        btn_reintento_addons = page.locator("button:visible").filter(has_text=re.compile(r"^Proceed$", re.I)).last
        if btn_reintento_addons.is_visible():
            hacer_clic_robusto(page, btn_reintento_addons, "Proceed Add-Ons Reintento")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2500)
