import os
import re
from core.config import lock_login
from automation.crm_helpers import escribir_en_react, hacer_clic_robusto

def ejecutar_paso_0_login(browser, id_hilo, url_login, url_create, usuario_login, password_login, log_callback, check_cancel, auth_file="auth_state.json"):
    """
    Ejecuta el Paso 0 (Login en CRM) utilizando sincronización mutex 'lock_login'
    y reutilización de tokens/cookies mediante 'auth_state.json'.
    Retorna la tupla (context, page) autenticada y posicionada en el Paso 1.
    """
    max_intentos_login = 3
    login_exitoso = False
    context = None
    page = None

    with lock_login:
        if os.path.exists(auth_file):
            try:
                context = browser.new_context(no_viewport=True, storage_state=auth_file)
            except Exception:
                context = browser.new_context(no_viewport=True)
        else:
            context = browser.new_context(no_viewport=True)

        page = context.new_page()

        # Comprobación rápida: intentar reutilizar la sesión guardada
        try:
            page.goto(url_create, timeout=40000)
            page.wait_for_load_state("networkidle")
            if page.locator("#accountType").first.is_visible(timeout=5000):
                log_callback(f"✅ [Hilo {id_hilo}] Sesión recuperada de auth_state.json. Saltando login.")
                login_exitoso = True
        except Exception:
            pass

        if not login_exitoso:
            for intento_login in range(1, max_intentos_login + 1):
                check_cancel()
                log_callback(f"🔑 [Hilo {id_hilo}] (Intento {intento_login}/{max_intentos_login}) Iniciando sesión en CRM...")
                try:
                    page.goto(url_login, timeout=60000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(3000)
                    
                    input_usuario = page.locator("input[type='text']").first
                    input_usuario.wait_for(state="visible", timeout=30000)
                    
                    escribir_en_react(page, "input[type='text']", usuario_login)
                    page.wait_for_timeout(300)
                    escribir_en_react(page, "input[type='password']", password_login)
                    page.wait_for_timeout(500)
                    
                    btn_login = page.locator("button:visible").filter(has_text=re.compile(r"Login|Iniciar|Sign in|Ingresar", re.I)).first
                    if btn_login.is_visible():
                        hacer_clic_robusto(page, btn_login, "Boton Login CRM")
                    else:
                        page.locator("input[type='password']").first.press("Enter")
                    
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(4000)

                    check_cancel()

                    # Comprobar alertas de error devueltas por el CRM
                    alerta_err = page.locator(".MuiAlert-message, .Toastify__toast-body, div[role='alert']").first
                    if alerta_err.is_visible():
                        msg_crm = alerta_err.inner_text().strip()
                        log_callback(f"⚠️ [Hilo {id_hilo}] El CRM reportó alerta en login: {msg_crm}")
                        page.wait_for_timeout(2000)
                        if intento_login < max_intentos_login:
                            page.reload(timeout=45000)
                            page.wait_for_load_state("networkidle")
                            page.wait_for_timeout(3000)
                            continue

                    # Navegar al formulario de creación (Paso 1)
                    log_callback(f"➡️ [Hilo {id_hilo}] Navegando a creación de cuenta...")
                    page.goto(url_create, timeout=60000)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(3000)

                    try:
                        page.wait_for_selector("#accountType", state="visible", timeout=35000)
                        login_exitoso = True
                        log_callback(f"✅ [Hilo {id_hilo}] Sesión iniciada y Paso 1 cargado correctamente.")
                        context.storage_state(path=auth_file)
                        break
                    except Exception:
                        log_callback(f"⚠️ [Hilo {id_hilo}] Demora al abrir formulario. Refrescando página...")
                        page.reload(timeout=45000)
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(3000)
                        page.wait_for_selector("#accountType", state="visible", timeout=35000)
                        login_exitoso = True
                        log_callback(f"✅ [Hilo {id_hilo}] Paso 1 cargado tras refrescar.")
                        context.storage_state(path=auth_file)
                        break

                except Exception as e_login:
                    log_callback(f"⚠️ [Hilo {id_hilo}] Incidencia en intento {intento_login} de login: {e_login}")
                    if intento_login < max_intentos_login:
                        log_callback(f"🔄 [Hilo {id_hilo}] Reintentando login completo en 4 segundos...")
                        page.wait_for_timeout(4000)
                    else:
                        raise Exception(f"Fallo al iniciar sesión en el CRM tras {max_intentos_login} intentos completos.")

    if not login_exitoso:
        raise Exception(f"No fue posible acceder al formulario de creación tras {max_intentos_login} intentos de login.")

    return context, page
