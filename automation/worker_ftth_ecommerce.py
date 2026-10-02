import os
import time
import random
import re
from playwright.sync_api import sync_playwright

from core.correlativos import (
    obtener_siguiente_correlativo, formatear_error_amigable, registrar_cuenta_creada
)
from core.generadores import generar_telefono_ve, generar_nombre_humano_limpio
from core.catalogos import cargar_catalogo_direcciones, cargar_catalogo_planes
from automation.worker import StepTimer

# Catálogos cargados al inicio (thread-safe, solo lectura)
CATALOGO_DIRECCIONES_ECOM = cargar_catalogo_direcciones()
CATALOGO_PLANES_ECOM = cargar_catalogo_planes()

URL_TIENDA_ECOMMERCE = "https://tiendatesting.simple.com.ve/tienda"

def _detectar_captcha(page, solo_fullpage=False) -> bool:
    """
    Detecta si hay un captcha bloqueando el flujo y que AUN NO HA SIDO RESUELTO.
    Cubre: Cloudflare Challenge page, Cloudflare Turnstile embebido (sin cambio de URL),
    reCAPTCHA v2 visible, hCaptcha.
    """
    try:
        # 1. Cloudflare Challenge de pagina completa (con y sin cambio de URL)
        if "/cdn-cgi/challenge-platform" in page.url or "__cf_chl" in page.url:
            return True

        for sel in ("#challenge-stage", "#challenge-form", "#cf-challenge-running"):
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible(timeout=200):
                    return True
            except:
                pass

        # 2. Cloudflare Turnstile EMBEBIDO (moderno — no cambia URL)
        # Turnstile resuelto inyecta un valor en el input oculto; si está vacío, no fue resuelto.
        try:
            turnstile_input = page.locator("input[name='cf-turnstile-response']")
            if turnstile_input.count() > 0:
                # El iframe del widget debe estar visible Y el token debe estar vacío
                iframe_ts = page.locator(
                    "iframe[src*='challenges.cloudflare.com'], "
                    "iframe[src*='turnstile'], "
                    ".cf-turnstile iframe"
                ).first
                try:
                    ts_visible = iframe_ts.is_visible(timeout=300)
                except Exception:
                    ts_visible = False
                if ts_visible and not turnstile_input.first.input_value(timeout=300).strip():
                    return True
        except Exception:
            pass

        if solo_fullpage:
            return False

        # 3. reCAPTCHA v2 visible (checkbox sin resolver)
        try:
            recaptcha_textarea = page.locator("textarea[name='g-recaptcha-response']")
            if recaptcha_textarea.count() > 0:
                iframe_rc = page.locator("iframe[src*='recaptcha']").first
                try:
                    rc_visible = iframe_rc.is_visible(timeout=300)
                except Exception:
                    rc_visible = False
                if rc_visible and not recaptcha_textarea.first.input_value(timeout=300).strip():
                    return True
        except Exception:
            pass

        # 4. hCaptcha
        try:
            hcaptcha_textarea = page.locator("textarea[name='h-captcha-response']")
            if hcaptcha_textarea.count() > 0:
                iframe_hc = page.locator("iframe[src*='hcaptcha']").first
                try:
                    hc_visible = iframe_hc.is_visible(timeout=300)
                except Exception:
                    hc_visible = False
                if hc_visible and not hcaptcha_textarea.first.input_value(timeout=300).strip():
                    return True
        except Exception:
            pass

    except Exception:
        pass

    return False


def _esperar_captcha_si_presente(page, id_hilo, contexto, log_callback, cancel_event=None, solo_fullpage=False):
    """
    Si hay un captcha visible, pausa y espera hasta que el operador lo resuelva.
    Ventana maxima: 5 minutos. Propaga CancelException correctamente.
    Si no hay captcha retorna inmediatamente (fast-path sin costo).
    """
    if not _detectar_captcha(page, solo_fullpage):
        return  # Fast-path: sin captcha

    log_callback(
        f"[Hilo {id_hilo}] 🛡️ [{contexto}] CAPTCHA detectado. "
        f"Resuélvelo manualmente en el navegador (ventana: 5 min)..."
    )

    for segundo in range(300):
        if cancel_event and cancel_event.is_set():
            raise Exception("Ejecución cancelada por el usuario durante la espera de Captcha.")

        if not _detectar_captcha(page, solo_fullpage):
            log_callback(f"[Hilo {id_hilo}] ✅ [{contexto}] Captcha superado tras {segundo}s.")
            page.wait_for_timeout(1500)
            return

        page.wait_for_timeout(1000)

    raise Exception(
        f"Tiempo agotado ({contexto}): el Captcha no fue resuelto en 5 minutos. "
        "Cancela o reintenta la cuenta."
    )


def _esperar_selector_o_captcha(
    page, selector, id_hilo, contexto, log_callback,
    cancel_event=None, timeout_total=60, intervalo=2, solo_fullpage=False
):
    """
    Primitiva de espera resiliente: espera a que `selector` sea visible.

    Ciclo de decisión en cada tick:
      1. Si la página está navegando (post-redirect de CF) → espera domcontentloaded.
      2. Si el selector ya está visible → retorna True.
      3. Si hay CAPTCHA activo → notifica, NO cuenta el tiempo, sigue esperando.
      4. Si se agota timeout_total sin captcha → lanza excepción con diagnóstico.

    FIX CRÍTICO: Cuando Cloudflare resuelve el captcha, hace un HTTP redirect de vuelta
    a la URL original. En ese momento Playwright entra en estado de navegación activa
    y TODAS las queries del DOM lanzan excepciones. El código anterior las capturaba con
    `except: pass` quedando en un bloqueo silencioso eterno. Esta versión detecta ese
    estado y espera a que la navegación termine antes de continuar.
    """
    transcurrido = 0
    captcha_activo = False
    url_objetivo = page.url  # URL en el momento de llamar (puede ser la de CF o la real)

    while transcurrido < timeout_total:
        if cancel_event and cancel_event.is_set():
            raise Exception(f"[{contexto}] Ejecucion cancelada por el usuario.")

        # ── 1. Detectar si la página está en medio de una navegación ──────────
        # Esto ocurre justo después de que CF redirige a la URL real.
        # Las queries DOM en este estado fallan con "Execution context was destroyed".
        navegando = False
        try:
            # Si la URL cambió hacia algo diferente a la challenge de CF, CF ya redirigió.
            url_actual = page.url
            if ("/cdn-cgi/" in url_objetivo or "__cf_chl" in url_objetivo):
                # Estabamos en la challenge page. Si la URL ya no tiene eso, CF redirigió.
                if "/cdn-cgi/" not in url_actual and "__cf_chl" not in url_actual:
                    log_callback(
                        f"[Hilo {id_hilo}] ↩️  [{contexto}] CF redirigió a: {url_actual[:60]}..."
                        f" Esperando carga de pagina..."
                    )
                    url_objetivo = url_actual  # actualizar referencia
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    page.wait_for_timeout(1500)
                    if captcha_activo:
                        captcha_activo = False
                        log_callback(f"[Hilo {id_hilo}] ✅ [{contexto}] Captcha resuelto. Pagina cargada. Continuando...")
                    continue  # Re-evaluar desde arriba con la nueva página

        except Exception:
            # page.url puede fallar si la página está navegando activamente
            navegando = True
            page.wait_for_timeout(1000)
            # NO incrementar transcurrido: estamos en navegación, no en timeout real
            continue

        # ── 2. Verificar si el selector ya está disponible ────────────────────
        if not navegando:
            try:
                loc = page.locator(selector)
                if loc.count() > 0 and loc.first.is_visible(timeout=500):
                    if captcha_activo:
                        log_callback(f"[Hilo {id_hilo}] ✅ [{contexto}] Captcha resuelto. Elemento encontrado.")
                    return True
            except Exception:
                # Puede ocurrir si la página está cargando. No contar como timeout.
                page.wait_for_timeout(800)
                continue

        # ── 3. Verificar si hay CAPTCHA bloqueando ────────────────────────────
        try:
            hay_captcha = _detectar_captcha(page, solo_fullpage)
        except Exception:
            hay_captcha = False

        if hay_captcha:
            if not captcha_activo:
                log_callback(
                    f"[Hilo {id_hilo}] 🛡️  [{contexto}] CAPTCHA detectado. "
                    f"Resuelvelo en el navegador y el bot continuara automaticamente..."
                )
                captcha_activo = True
                # Actualizar url_objetivo a la URL de la challenge para detectar el redirect
                try:
                    url_objetivo = page.url
                except Exception:
                    pass
            # No contar el tiempo de captcha contra el timeout
            page.wait_for_timeout(intervalo * 1000)
            continue
        else:
            if captcha_activo:
                # El captcha desapareció pero aún no hubo redirect detectado.
                # Dar margen para que CF procese y redirija.
                captcha_activo = False
                log_callback(f"[Hilo {id_hilo}] ⏳ [{contexto}] Captcha resuelto. Esperando redirect de CF...")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                continue  # Re-evaluar sin contar timeout

        page.wait_for_timeout(intervalo * 1000)
        transcurrido += intervalo

    # ── 4. Timeout agotado: captura de diagnóstico ───────────────────────────
    raise Exception(
        f"[{contexto}] Timeout ({timeout_total}s): el selector '{selector}' "
        f"no aparecio. URL actual: {page.url}. "
        f"Posible cambio en la UI del CRM o bloqueo no detectado."
    )


def _safe_fill_obligatorio(page, selector_list, valor, campo_nombre, id_hilo, log_callback):
    """
    Llena un campo OBLIGATORIO del formulario. A diferencia de safe_fill, NO falla
    en silencio: intenta múltiples selectores y lanza advertencia táctica si ninguno
    recibe el valor correctamente. Reintenta hasta 3 veces.
    """
    for intento in range(3):
        for selector in selector_list:
            try:
                loc = page.locator(selector).first
                if loc.count() == 0:
                    loc = page.get_by_placeholder(re.compile(selector, re.IGNORECASE)).first
                loc.wait_for(state="visible", timeout=5000)
                loc.click(force=True)
                loc.fill("", force=True)   # Limpiar primero
                loc.fill(valor, force=True)
                loc.blur()
                page.wait_for_timeout(300)
                # Verificar que el valor quedó escrito
                val_actual = loc.input_value(timeout=1000).strip()
                if val_actual and valor.strip() in val_actual:
                    return True
            except Exception:
                continue
        page.wait_for_timeout(500)

    log_callback(
        f"[Hilo {id_hilo}] ⚠️ Campo obligatorio '{campo_nombre}' no pudo ser llenado "
        f"con valor '{valor}'. Verifique el DOM del formulario."
    )
    return False


# HELPER: Lectura OTP desde Maildrop (mismo protocolo blindado que OTT)
# ────────────────────────────────────────────────────────────────────────────────
def _obtener_otp_maildrop_ecom(email_base, correlativo, p_context, id_hilo, log_callback, cancel_event=None):
    """
    Abre una pestana de Maildrop y extrae el OTP de 6 digitos.
    Estrategia de extraccion en 2 fases:
      1. Contextual: busca el numero cerca de palabras clave (codigo, OTP, verificacion).
      2. Fallback: primer 6-digit en inner_text del email abierto (nunca en HTML crudo).
    Mantiene la pestana abierta y refresca en cada reintento.
    """
    # Patron contextual: OTP rodeado de palabras clave del email del CRM
    PATRON_CONTEXTUAL = re.compile(
        r'(?:c[o\u00f3]digo|code|verificaci[o\u00f3]n|verification|otp|token|clave|pin)'
        r'.{0,120}(\d{6})'
        r'|'
        r'(\d{6})'
        r'.{0,120}(?:c[o\u00f3]digo|code|verificaci[o\u00f3]n|verification|otp|token|clave|pin)',
        re.IGNORECASE | re.DOTALL
    )

    mailbox_name = f"{email_base}{correlativo}"
    url_mailbox = f"https://maildrop.cc/inbox/?mailbox={mailbox_name}"
    log_callback(f"[Hilo {id_hilo}] Abriendo Maildrop: {url_mailbox}")

    page_mail = p_context.new_page()
    codigo = None
    try:
        page_mail.goto(url_mailbox, timeout=60000)
        try:
            page_mail.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        for intento in range(15):
            if cancel_event and cancel_event.is_set():
                log_callback(f"[Hilo {id_hilo}] OTP cancelado.")
                break

            log_callback(f"[Hilo {id_hilo}] Maildrop - intento {intento + 1}/15 en '{mailbox_name}'...")

            # ── PASO 1: Intentar abrir el primer correo ───────────────────────────
            email_abierto = False
            try:
                primer_correo = page_mail.locator(
                    "a[href*='/message/'], div[class*='Message'], li[class*='message'], "
                    "div[class*='message'], a[class*='message'], article, [role='listitem']"
                ).first
                if primer_correo.is_visible():
                    log_callback(f"[Hilo {id_hilo}] Email detectado - abriendo...")
                    primer_correo.click()
                    page_mail.wait_for_timeout(2000)
                    email_abierto = True
            except Exception:
                pass

            # ── PASO 2: Raspar SOLO inner_text (nunca HTML crudo) ─────────────────
            texto_visible = ""
            try:
                texto_visible = page_mail.inner_text("body")
            except Exception:
                pass
            for frame in page_mail.frames:
                try:
                    texto_visible += " " + frame.inner_text("body")
                except Exception:
                    pass

            # ── PASO 3: Busqueda contextual (alta precision, sin falsos positivos) ─
            match_ctx = PATRON_CONTEXTUAL.search(texto_visible)
            if match_ctx:
                codigo = match_ctx.group(1) or match_ctx.group(2)
                log_callback(f"[Hilo {id_hilo}] OTP (contextual): {codigo} (intento {intento + 1})")
                break

            # ── PASO 4: Fallback — solo si el email esta abierto ─────────────────
            if email_abierto:
                match_fb = re.search(r'(?<!\d)(\d{6})(?!\d)', texto_visible)
                if match_fb:
                    codigo = match_fb.group(1)
                    log_callback(f"[Hilo {id_hilo}] OTP (fallback): {codigo} (intento {intento + 1})")
                    break

            # Diagnostico: que hay en el inbox
            extracto = texto_visible[:200].replace("\n", " ").replace("\r", "").strip()
            log_callback(f"[Hilo {id_hilo}] Sin OTP. Texto: '{extracto[:120]}'")

            page_mail.wait_for_timeout(5000)
            try:
                page_mail.reload()
                page_mail.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

    except Exception as e:
        log_callback(f"[Hilo {id_hilo}] Error accediendo a Maildrop: {e}")
    finally:
        try:
            page_mail.close()
        except Exception:
            pass

    return codigo

def _react_select(page, select_name, text_match):
    """
    Selecciona una opción en un <select> de React comparando texto parcial
    e inyectando el evento 'change' nativo para que React actualice su estado.
    """
    page.evaluate("""([name, text]) => {
        const select = document.querySelector(`select[name='${name}']`);
        if (!select) return;
        const options = Array.from(select.options);
        const target = options.find(o => o.text.toLowerCase().includes(text.toLowerCase()));
        if (!target) return;
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
        nativeSetter.call(select, target.value);
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }""", [select_name, text_match])


# ────────────────────────────────────────────────────────────────────────────────
# WORKER PRINCIPAL: FTTH eCOMMERCE
# ────────────────────────────────────────────────────────────────────────────────
def ejecutar_worker_ftth_ecommerce(
    id_hilo,
    datos_cuenta,
    sys_config,
    log_callback,
    update_kpi_callback,
    cancel_event=None,
    update_thread_status_callback=None
):
    """
    Worker de automatización para la tienda eCommerce B2C de Simpletv Fibra.

    Flujo de 5 fases:
      Fase 1 — Validación de cobertura (Google Maps)
      Fase 2 — Vitrina y selección de plan / equipo ONT
      Fase 3 — Generación de contrato (4 sub-pasos)
      Fase 4 — Aceptación de documentos legales
      Fase 5 — Handoff al operador (pantalla Pagar ahora)
    """
    timer = StepTimer(id_hilo, log_callback, update_thread_status_callback)

    # ── Parámetros de entrada ──
    plan_id    = datos_cuenta.get("plan_seleccionado", "")
    ubicacion  = datos_cuenta.get("ubicacion", "Caracas")

    # ── P0: Preparación de identidad sintética ──
    timer.start_step("P0: Preparación")
    email_generado = ""
    tipo_cliente_str = "Natural"
    try:
        nuevo_corr      = obtener_siguiente_correlativo("contador_email_ecommerce.txt")
        telefono_full   = generar_telefono_ve()
        prefijo_tel     = telefono_full[:4]
        numero_tel      = telefono_full[4:]
        prefijo_ced     = "V"
        cedula          = str(random.randint(10_000_000, 30_000_000))
        nombre, apellido = generar_nombre_humano_limpio()

        # Correo Maildrop
        email_base = sys_config.get("prefijo_email_ott", "testecommerce")
        if "@" in email_base:
            email_base = email_base.split("@")[0]
        mailbox_name   = f"{email_base}{nuevo_corr}"
        email_generado = f"{mailbox_name}@maildrop.cc"

        # Dirección base del catálogo (con cobertura garantizada)
        dir_data = CATALOGO_DIRECCIONES_ECOM.get(ubicacion)
        if not dir_data:
            dir_data = list(CATALOGO_DIRECCIONES_ECOM.values())[0]

        # String de búsqueda para Google Places (ej: "Torre Directv, Urb. El Rosal, Caracas, Miranda, Venezuela")
        dir_google = (
            f"{dir_data['building_house']}, {dir_data['neighbourhood']}, "
            f"{dir_data['city']}, {dir_data['state']}, Venezuela"
        )

        fecha_hoy         = time.strftime("%Y-%m-%d")
        carpeta_evidencias = os.path.join(os.getcwd(), "Evidencias_QA_eCommerce", fecha_hoy, mailbox_name)

        log_callback(f"[Hilo {id_hilo}] 📝 eCommerce FTTH: {nombre} {apellido} | {cedula} | {email_generado}")
        log_callback(f"[Hilo {id_hilo}] 📍 Dirección: {dir_google}")
        timer.stop_step()

    except Exception as e:
        timer.stop_step("Error")
        err_msg = formatear_error_amigable("preparando datos eCommerce", e)
        log_callback(f"[Hilo {id_hilo}] ❌ {err_msg}")
        update_kpi_callback(fallo=1)
        return {"exito": False, "error": err_msg, "email": ""}

    # ── Inicio de sesión de Playwright ──
    with sync_playwright() as p:
        browser = None
        page    = None
        try:
            timer.start_step("P1: Iniciar Navegador")
            browser = p.chromium.launch(headless=False, slow_mo=50, args=["--start-maximized"])
            context = browser.new_context(no_viewport=True)
            page    = context.new_page()
            page.set_default_timeout(45000)

            def guardar_evidencia(nombre_paso):
                try:
                    paso_limpio = re.sub(r'[:\s/\\]', '_', nombre_paso)
                    os.makedirs(carpeta_evidencias, exist_ok=True)
                    ruta = os.path.join(carpeta_evidencias, f"H{id_hilo}_{paso_limpio}.png")
                    if page and not page.is_closed():
                        page.screenshot(path=ruta, full_page=True, timeout=3000)
                except Exception:
                    pass

            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 1 — VALIDACIÓN DE COBERTURA
            # ────────────────────────────────────────────────────────────────────────────────
            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 1 - VALIDACION DE COBERTURA
            # Arquitectura: cada wait critico usa _esperar_selector_o_captcha.
            # Si Cloudflare/Turnstile aparece durante la carga, el proceso PAUSA y espera
            # al operador sin morir. Una vez resuelto, continua desde el punto exacto.
            # ────────────────────────────────────────────────────────────────────────────────
            timer.start_step("F1: Cobertura P1/2 Datos")
            page.goto(URL_TIENDA_ECOMMERCE)
            log_callback(f"[Hilo {id_hilo}] \U0001f310 Cargando tienda eCommerce... (URL: {URL_TIENDA_ECOMMERCE})")

            # ── ESPERA POST-GOTO: CF puede interceptar la carga ──────────────────────────
            # solo_fullpage=False para detectar también Turnstile embebido en la página
            # Solo usamos selectores CSS puros (sin text='...' que rompe el locator compound)
            _esperar_selector_o_captcha(
                page,
                "input[name*='name'], input[placeholder*='Nombre'], button:has-text('Avanzar')",
                id_hilo, "Carga tienda inicial", log_callback,
                cancel_event, timeout_total=360, solo_fullpage=False
            )

            log_callback(f"[Hilo {id_hilo}] \u2705 Tienda cargada. Verificando modal de cobertura...")
            page.wait_for_timeout(1500)  # Dar tiempo a React para renderizar

            # ── VERIFICAR / ABRIR MODAL DE COBERTURA ────────────────────────────────────
            # Estrategia: intentar varios indicadores del modal antes de buscarlo con clic
            modal_abierto = False

            # Intento 1: el modal se abrió automáticamente (texto visible)
            try:
                if page.get_by_text("Validaci", exact=False).first.is_visible(timeout=3000):
                    modal_abierto = True
                    log_callback(f"[Hilo {id_hilo}] \U0001f4cb Modal de cobertura detectado (auto-open).")
            except Exception:
                pass

            # Intento 2: buscar por input del formulario (nombre, apellido, teléfono)
            if not modal_abierto:
                try:
                    if page.locator("input[name*='name'], input[name='firstName']").first.is_visible(timeout=2000):
                        modal_abierto = True
                        log_callback(f"[Hilo {id_hilo}] \U0001f4cb Formulario de contacto detectado en la página.")
                except Exception:
                    pass

            # Intento 3: buscar disparador del modal y hacer clic
            if not modal_abierto:
                log_callback(f"[Hilo {id_hilo}] \U0001f50d Buscando disparador del modal de cobertura...")
                try:
                    btn_cobertura = page.locator(
                        "button:visible, a:visible, [role='button']:visible"
                    ).filter(has_text=re.compile(r"cobertura|consulta|zona|disponibilidad|verificar", re.I)).first
                    if btn_cobertura.is_visible(timeout=5000):
                        log_callback(f"[Hilo {id_hilo}] \U0001f44d Haciendo clic en disparador de cobertura...")
                        btn_cobertura.click(force=True)
                        page.wait_for_timeout(2000)
                        modal_abierto = True
                except Exception:
                    pass

            if not modal_abierto:
                # Último recurso: esperar que cualquier input del form aparezca
                log_callback(f"[Hilo {id_hilo}] \u23f3 Esperando formulario de cobertura...")
                try:
                    page.wait_for_selector(
                        "input[name='firstName'], input[name*='name'], input[placeholder*='Nombre']",
                        timeout=15000
                    )
                    modal_abierto = True
                except Exception:
                    log_callback(f"[Hilo {id_hilo}] \u26a0\ufe0f  No se pudo detectar el modal. Continuando de todas formas...")

            log_callback(f"[Hilo {id_hilo}] \U0001f4dd Llenando datos de contacto...")

            # ── CAMPOS OBLIGATORIOS ─────────────────────────────────────────────────────
            page.wait_for_timeout(500)

            _safe_fill_obligatorio(
                page,
                ["input[name='firstName']", "input[name*='name']:not([name*='last'])",
                 "nombre", "Nombre"],
                nombre, "Nombre", id_hilo, log_callback
            )

            _safe_fill_obligatorio(
                page,
                ["input[name='lastName']", "input[name*='last']",
                 "apellido", "Apellido"],
                apellido, "Apellido", id_hilo, log_callback
            )

            try:
                _react_select(page, "phone.prefix", prefijo_tel)
                page.wait_for_timeout(500)
            except Exception:
                pass

            _safe_fill_obligatorio(
                page,
                ["input[name='phone.number']", "input[name*='phone']:not([name*='prefix'])"],
                numero_tel, "Telefono", id_hilo, log_callback
            )

            _safe_fill_obligatorio(
                page,
                ["input[name*='email']", "input[type='email']"],
                email_generado, "Email", id_hilo, log_callback
            )

            guardar_evidencia(timer.current_step)
            log_callback(f"[Hilo {id_hilo}] \U0001f4dd Formulario llenado. Buscando botón Avanzar...")

            # ── AVANZAR (con espera resiliente por si hay Turnstile aquí también) ────────
            _esperar_selector_o_captcha(
                page, "button:has-text('Avanzar')",
                id_hilo, "Boton Avanzar cobertura", log_callback,
                cancel_event, timeout_total=360, solo_fullpage=False
            )
            log_callback(f"[Hilo {id_hilo}] \U0001f449 Haciendo clic en Avanzar...")
            page.get_by_role("button", name="Avanzar").click(force=True)
            timer.stop_step()

            # ── Paso 2/2 Cobertura: Google Places / Maps ────────────────────────────────
            timer.start_step("F1: Cobertura P2/2 Mapa")
            log_callback(f"[Hilo {id_hilo}] 🗺️ Esperando formulario de direcci\u00f3n...")

            # Espera resiliente: puede haber un Turnstile en la transicion de paso
            _esperar_selector_o_captcha(
                page,
                "input[placeholder*='direcci\u00f3n'], input[placeholder*='Direcci\u00f3n'], "
                "input[placeholder*='Ingresa tu direcci\u00f3n']",
                id_hilo, "Formulario de direccion", log_callback,
                cancel_event, timeout_total=60
            )

            input_direccion = page.locator(
                "input[placeholder*='direcci\u00f3n'], input[placeholder*='Direcci\u00f3n'], "
                "input[placeholder*='Ingresa tu direcci\u00f3n']"
            ).first
            input_direccion.wait_for(state="visible", timeout=10000)
            log_callback(f"[Hilo {id_hilo}] \U0001f4cd Ingresando direcci\u00f3n: {dir_google}")

            # Pegar la dirección directamente
            input_direccion.click()
            input_direccion.fill(dir_google, force=True)
            log_callback(f"[Hilo {id_hilo}] \U0001f4cd Dirección pegada. Esperando sugerencia del sistema...")
            
            page.wait_for_timeout(1000)

            # El CRM renderiza un dropdown custom de Tailwind, NO el .pac-item de Google
            # El contenedor tiene clases como 'absolute z-10 top-full' y contiene botones
            dropdown_selector = "div.absolute.z-10 button"
            
            try:
                page.wait_for_selector(dropdown_selector, state="visible", timeout=8000)
                page.locator(dropdown_selector).first.click(force=True)
                log_callback(f"[Hilo {id_hilo}] \U0001f4cc Sugerencia clickeada en el dropdown.")
            except Exception:
                log_callback(f"[Hilo {id_hilo}] \u26a0\ufe0f Dropdown no detectado. Intentando forzar con Enter...")
                input_direccion.press("Enter")

            page.wait_for_timeout(2500)

            # Verificar que el pin naranja aparece y el boton se habilito
            log_callback(f"[Hilo {id_hilo}] \U0001f50d Verificando habilitacion del boton 'Ver disponibilidad'...")
            _esperar_selector_o_captcha(
                page, "button:has-text('Ver disponibilidad')",
                id_hilo, "Pin en mapa", log_callback,
                cancel_event, timeout_total=30
            )
            btn_disponibilidad = page.locator("button:visible").filter(has_text="Ver disponibilidad").first

            guardar_evidencia(timer.current_step)
            log_callback(f"[Hilo {id_hilo}] \u2705 Pin colocado. Verificando cobertura...")
            btn_disponibilidad.click(force=True)

            # Espera resiliente al modal de exito de cobertura
            _esperar_selector_o_captcha(
                page, "text=/cobertura en tu zona/i",
                id_hilo, "Confirmacion cobertura", log_callback,
                cancel_event, timeout_total=45
            )
            guardar_evidencia("F1_cobertura_exitosa")
            log_callback(f"[Hilo {id_hilo}] \U0001f389 \u00a1Cobertura confirmada! Accediendo a planes...")

            page.locator("a:visible, button:visible").filter(has_text=re.compile(r"Ver planes", re.I)).first.click(force=True)

            # Ya no esperamos a que cargue la vitrina visualmente porque haremos un bypass directo por URL.
            # Solo damos un pequeño respiro para que el backend procese el clic y guarde la sesión.
            page.wait_for_timeout(2000)
            
            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 2 - VITRINA: SELECCION DE PAQUETE
            # ────────────────────────────────────────────────────────────────────────────────
            timer.start_step("F2: Seleccion de Plan")

            # Obtener datos del plan del catalogo
            datos_plan = CATALOGO_PLANES_ECOM.get(plan_id, {})
            velocidad  = datos_plan.get("velocidad", "")

            log_callback(f"[Hilo {id_hilo}] 🚀 Aplicando bypass de URL para el plan: {velocidad}")

            enlaces_directos = {
                "400": "https://tiendatesting.simple.com.ve/planes/f6c96f3e-2826-4845-9afb-b738a724c3bd"
            }

            velocidad_num = re.search(r'\d+', velocidad).group() if re.search(r'\d+', velocidad) else "400"
            url_plan = enlaces_directos.get(velocidad_num, enlaces_directos["400"])

            try:
                log_callback(f"[Hilo {id_hilo}] 🔗 Navegando directo a la configuración del plan {velocidad_num}...")
                page.goto(url_plan, wait_until="commit")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] ⚠️ Falló el bypass por URL: {e}")

            # ── SELECCION DE BUNDLE (TV) Y ROUTER ──
            paquete = datos_plan.get("paquete", plan_id)
            modalidad = datos_plan.get("modalidad", "Compra")

            # Extraer palabra clave principal del paquete de TV (ej: "Sports", "Cine")
            # Si el paquete base ya está incluido, quizás no haya tarjeta que hacer clic
            keyword_tv = paquete.split("+")[-1].strip() if "+" in paquete else paquete
            log_callback(f"[Hilo {id_hilo}] 📺 Buscando Bundle TV con keyword: '{keyword_tv}'")
            try:
                # Buscamos un div clickeable que contenga la palabra clave del paquete
                card_paquete = page.locator("div").filter(has_text=re.compile(keyword_tv, re.I)).locator("div").first
                # Como puede coincidir con mucho texto, usamos un timeout corto
                card_paquete.wait_for(state="visible", timeout=5000)
                card_paquete.click(force=True)
                page.wait_for_timeout(1000)
                log_callback(f"[Hilo {id_hilo}] ✅ Bundle TV seleccionado.")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] ℹ️ No se seleccionó paquete TV extra (o ya viene incluido).")

            wifi_ver = "WiFi6" if "6" in datos_plan.get("router", "WiFi6") else "WiFi5"
            log_callback(f"[Hilo {id_hilo}] 🛜 Buscando Router: {wifi_ver} + {modalidad}")
            try:
                # El texto puede variar ("ONT - Router" o "ONT / Router"), filtramos por las palabras clave
                # Buscamos un div que contenga el texto de wifi y la modalidad
                card_ont = page.locator("div").filter(has_text=re.compile(wifi_ver, re.I)).filter(has_text=re.compile(modalidad, re.I)).first
                card_ont.wait_for(state="visible", timeout=8000)
                card_ont.click(force=True)
                page.wait_for_timeout(1000)
                log_callback(f"[Hilo {id_hilo}] ✅ Router seleccionado.")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] ⚠️ No se pudo seleccionar el ONT '{wifi_ver} {modalidad}': {e}")

            guardar_evidencia(timer.current_step)
            
            # Punto 3/5: Antes de continuar al carrito
            # Usamos solo_fullpage=True para ignorar falsos positivos de widgets Turnstile pasivos
            _esperar_captcha_si_presente(page, id_hilo, "Configuracion plan", log_callback, cancel_event, solo_fullpage=True)
            
            # Hacer clic en el botón Continuar final de la configuración del plan
            try:
                page.locator("button:visible").filter(has_text=re.compile(r"Continuar", re.I)).first.click(force=True)
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
                        # Pantalla del Carrito
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
                # Esperamos específicamente por las cajas del OTP
                page.locator("input[placeholder='0'], input[name='otp.0'], input[name='otp0']").first.wait_for(
                    state="visible", timeout=60000
                )
            except Exception:
                os.makedirs(carpeta_evidencias, exist_ok=True)
                page.screenshot(
                    path=os.path.join(carpeta_evidencias, f"debug_H{id_hilo}_timeout_otp_ecom.png")
                )
                raise Exception("El formulario de OTP no apareció a tiempo.")

            log_callback(f"[Hilo {id_hilo}] ⏳ Esperando OTP en {email_generado}...")
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
                # Localizar inputs de OTP de forma más estricta (excluyendo hidden/disabled si es posible)
                # O intentamos la inyección directa sugerida en la guía táctica.
                for i, digito in enumerate(codigo_otp):
                    # Escribimos explícitamente en otp.0, otp.1, otp.2 o su equivalente react
                    caja = page.locator(f"input[name='otp.{i}'], input[name='otp{i}'], input[aria-label*='{i+1}']").first
                    if i == 0:
                        caja.wait_for(state="visible", timeout=5000)
                    caja.fill("", force=True)
                    caja.press_sequentially(digito, delay=50)
                
                # Desenfocar la última caja
                caja_final = page.locator("input[name='otp.5'], input[name='otp5'], input[aria-label*='6']").first
                caja_final.blur()
            except Exception:
                # Fallback modal genérico
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

            # -- CONTRATO PASO 3/4: Direccion de instalacion --
            timer.start_step("F3: Contrato P3/4 Direccion")
            page.wait_for_timeout(2000)
            log_callback(f"[Hilo {id_hilo}] Llenando direccion de instalacion...")

            # Datos del catalogo Ecommerce
            dir_ott = CATALOGO_DIRECCIONES_ECOM.get(ubicacion)
            if not dir_ott:
                dir_ott = list(CATALOGO_DIRECCIONES_ECOM.values())[0]

            estado_val   = dir_ott.get("state",         "distrito capital")
            ciudad_val   = dir_ott.get("city",          "caracas")
            muni_val     = dir_ott.get("municipality",  "libertador")
            zona_val     = dir_ott.get("zone",          "chacaito")
            cp_val       = dir_ott.get("postal_code",   "1060")
            tipo_calle   = dir_ott.get("street_type",   "avenida")
            nombre_calle = dir_ott.get("street_name",   "Av Venezuela")
            edificio_val = dir_ott.get("building_name", "torre directv")
            num_casa_val = dir_ott.get("house_number",  "533")

            log_callback(f"[Hilo {id_hilo}] Datos: {estado_val} / {ciudad_val} / {muni_val} / {zona_val}")

            # Helper nativo estilo OTT para inyectar en <select> de Tailwind/React
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

            try:
                # La captura del DOM reveló que los atributos name usan el prefijo "address."
                
                # Estado
                react_select_by_text(page, 'address.state', estado_val)
                page.wait_for_timeout(3000)
                
                # Ciudad
                react_select_by_text(page, 'address.city', ciudad_val)
                page.wait_for_timeout(3000)
                
                # Municipio
                react_select_by_text(page, 'address.municipality', muni_val)
                page.wait_for_timeout(3000)
                
                # Zona
                react_select_by_text(page, 'address.zone', zona_val)
                page.wait_for_timeout(3000)
                
                # Código postal
                try:
                    react_select_by_text(page, 'address.postalCode', cp_val)
                except:
                    pass
                page.wait_for_timeout(2000)
                
                # Area inmueble
                try:
                    react_select_by_text(page, 'address.area', '70')
                except:
                    pass
                page.wait_for_timeout(2000)
                
                # Tipo de calle
                react_select_by_text(page, 'address.streetType', tipo_calle)
                page.wait_for_timeout(2000)
                
                # Tipo de edificio (En la imagen es "Torre", el fallback a residencial puede fallar si no existe)
                try:
                    react_select_by_text(page, 'address.buildingType', 'torre')
                except:
                    try:
                        react_select_by_text(page, 'address.buildingType', 'residencial')
                    except:
                        pass
                page.wait_for_timeout(2000)

                # Entradas de texto (Desambiguación estricta por jerarquía DOM: Label -> Input)
                
                try:
                    # 1. Avenida / Calle
                    loc_calle = page.locator("label").filter(has_text=re.compile(r"Avenida \/ Calle", re.IGNORECASE)).locator("input").first
                    if not loc_calle.is_visible(timeout=500):
                        loc_calle = page.locator("input[placeholder*='avenida' i]").first
                    loc_calle.fill(nombre_calle, force=True)
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] WARN Avenida/Calle: {e}")

                try:
                    # 2. Edificio / Casa / Apartamento
                    loc_edif = page.locator("label").filter(has_text=re.compile(r"Edificio \/ Casa", re.IGNORECASE)).locator("input").first
                    if not loc_edif.is_visible(timeout=500):
                        loc_edif = page.locator("input[placeholder*='edificio' i]").first
                    loc_edif.fill(edificio_val, force=True)
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] WARN Edificio: {e}")

                try:
                    # 3. N° de Casa o Apartamento
                    # Usamos regex tolerante a caracteres especiales (N°, Nro, N.)
                    loc_casa = page.locator("label").filter(has_text=re.compile(r"N.* de Casa", re.IGNORECASE)).locator("input").first
                    if not loc_casa.is_visible(timeout=500):
                        # Fallback extremo: de todos los inputs con "casa" o "apartamento", tomar el ÚLTIMO
                        loc_casa = page.locator("input[placeholder*='casa' i], input[placeholder*='apartamento' i]").last
                    loc_casa.fill(num_casa_val, force=True)
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] WARN N Casa: {e}")
                
                log_callback(f"[Hilo {id_hilo}] OK Dirección llenada (Selectores Estructurales por Label)")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] WARN Error fatal llenando dropdowns de dirección: {e}")

            page.wait_for_timeout(1000)
            guardar_evidencia(timer.current_step)

            page.get_by_role("button", name="Continuar").last.click(force=True)
            page.wait_for_timeout(3000)
            timer.stop_step()

            # ── CONTRATO PASO 4/4: Datos adicionales ──
            timer.start_step("F3: Contrato P4/4 Datos Adicionales")
            page.wait_for_selector("text='Datos adicionales'", timeout=20000)
            log_callback(f"[Hilo {id_hilo}] 📋 Llenando datos adicionales...")

            # Sexo
            page.evaluate("""() => {
                const selects = Array.from(document.querySelectorAll('select'));
                const select = selects.find(s =>
                    s.name && s.name.toLowerCase().includes('gender') ||
                    (s.closest('label') && s.closest('label').textContent.toLowerCase().includes('sexo'))
                ) || selects.find(s =>
                    Array.from(s.options).some(o => o.text.toLowerCase().includes('masculino'))
                );
                if (select) {
                    const target = Array.from(select.options).find(o => o.text.toLowerCase().includes('masculino'));
                    if (target) {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                        setter.call(select, target.value);
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            }""")
            page.wait_for_timeout(500)

            # Fecha de nacimiento (mayor de edad de prueba)
            try:
                page.locator("input[name='birthDate'], input[type='date']").first.fill("2000-09-30", force=True)
            except Exception:
                try:
                    page.locator("input[name='birthDate']").fill("30/09/2000", force=True)
                except Exception:
                    pass

            # Pago móvil (mismo teléfono)
            try:
                _react_select(page, "mobilePayment.prefix", prefijo_tel)
                page.locator("input[name='mobilePayment.number'], input[placeholder*='pago']").first.fill(numero_tel, force=True)
            except Exception:
                pass  # No obligatorio

            # ISP actual (primer elemento del dropdown o fallback textual)
            try:
                isp_select = page.locator("select").filter(
                    has=page.locator("option")
                ).filter(
                    has_text=re.compile(r"Inter|CANTV|Chircal|Telcel|proveedor", re.I)
                ).first
                if isp_select.is_visible():
                    primera_opcion = isp_select.locator("option").nth(1)
                    val = primera_opcion.get_attribute("value") or ""
                    if val:
                        isp_select.select_option(value=val)
            except Exception:
                pass  # No crítico

            guardar_evidencia(timer.current_step)

            page.get_by_role("button", name="Continuar").last.click(force=True)
            page.wait_for_timeout(4000)
            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 4 — ACEPTACIÓN DE DOCUMENTOS LEGALES
            # ────────────────────────────────────────────────────────────────────────────────
            timer.start_step("F4: Aceptación de Documentos")
            page.wait_for_selector("text=/Aceptación/i", timeout=20000)
            log_callback(f"[Hilo {id_hilo}] 📜 Aceptando documentos legales...")

            # Marcar el checkbox de aceptación (forzado para evadir estilos custom)
            page.locator("input[type='checkbox']").first.check(force=True)
            page.wait_for_timeout(1000)

            guardar_evidencia(timer.current_step)

            # ── Punto 5/5: Antes de la aceptación legal final ──
            _esperar_captcha_si_presente(page, id_hilo, "Aceptación legal", log_callback, cancel_event, solo_fullpage=True)

            page.locator("button:visible").filter(
                has_text=re.compile(r"Continuar|Aceptar", re.IGNORECASE)
            ).last.click(force=True)

            # Esperar pantalla de carrito final con el botón "Pagar ahora"
            page.wait_for_selector("button:has-text('Pagar ahora')", timeout=25000)
            timer.stop_step()

            # ────────────────────────────────────────────────────────────────────────────────
            # FASE 5 — HANDOFF AL OPERADOR
            # ────────────────────────────────────────────────────────────────────────────────
            timer.start_step("F5: Handoff Operador")
            guardar_evidencia("F5_pantalla_pagar_ahora")
            log_callback(f"[Hilo {id_hilo}] 🏁 ¡FLUJO COMPLETADO! Pantalla de pago lista.")
            log_callback(f"[Hilo {id_hilo}] 🛑 El navegador quedará abierto para que el operador realice el pago.")

            # Notificación sonora
            try:
                import winsound
                winsound.Beep(1000, 300)
                winsound.Beep(1500, 400)
            except Exception:
                pass

            tiempo_total, desglose_str = timer.print_benchmark(email_generado)
            update_kpi_callback(exito=1)

            # Registrar cuenta en el historial CSV
            registrar_cuenta_creada({
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "eCommerce FTTH",
                "Tipo_Persona": tipo_cliente_str,
                "Documento_RIF": f"{prefijo_ced}-{cedula}",
                "Nombre_o_Empresa": f"{nombre} {apellido}",
                "Email": email_generado,
                "Telefono": telefono_full,
                "Ubicacion": ubicacion,
                "Plan": plan_id,
                "Estado": "EXITOSO (Pendiente Pago Operador)",
                "Tiempo_Total_Segundos": f"{tiempo_total}s",
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": ""
            })
            timer.stop_step("Exito")

            # Mantener el navegador vivo hasta que el operador lo cierre manualmente
            while True:
                if cancel_event and cancel_event.is_set():
                    log_callback(f"[Hilo {id_hilo}] 🚫 Cancelación manual. Cerrando navegador.")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    break
                try:
                    if not browser.is_connected() or (page and page.is_closed()):
                        log_callback(f"[Hilo {id_hilo}] ℹ️ Navegador cerrado por el operador. Liberando hilo.")
                        break
                    page.wait_for_timeout(1000)
                except Exception:
                    log_callback(f"[Hilo {id_hilo}] ℹ️ Navegador desconectado. Liberando hilo.")
                    break

            return {"exito": True, "error": None, "email": email_generado}

        except Exception as e:
            if timer.current_step:
                timer.stop_step("Error")
            err_msg = formatear_error_amigable(timer.current_step or "Flujo eCommerce FTTH", e)
            log_callback(f"[Hilo {id_hilo}] ❌ Error en {timer.current_step}: {err_msg}")

            # Captura de debug
            if page and not page.is_closed():
                try:
                    os.makedirs(os.path.join(os.getcwd(), "logs", "screenshots"), exist_ok=True)
                    path_err = os.path.join(
                        os.getcwd(), "logs", "screenshots",
                        f"ecom_crash_H{id_hilo}_{int(time.time())}.png"
                    )
                    page.screenshot(path=path_err, timeout=3000)
                    log_callback(f"[Hilo {id_hilo}] 📸 Evidencia de crash: {path_err}")
                except Exception:
                    pass

            update_kpi_callback(fallo=1)

            tiempo_total, desglose_str = timer.print_benchmark(email_generado)
            registrar_cuenta_creada({
                "Fecha_Hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Servicio": "eCommerce FTTH",
                "Tipo_Persona": tipo_cliente_str,
                "Documento_RIF": f"{prefijo_ced}-{cedula}",
                "Nombre_o_Empresa": f"{nombre} {apellido}",
                "Email": email_generado,
                "Telefono": telefono_full,
                "Ubicacion": ubicacion,
                "Plan": plan_id,
                "Estado": f"Error: {err_msg}",
                "Tiempo_Total_Segundos": f"{tiempo_total}s",
                "Desglose_Tiempos": desglose_str,
                "ID_Cliente": ""
            })

            return {"exito": False, "error": err_msg, "email": email_generado}

        finally:
            # Solo cerramos si fue cancelación; en éxito el operador cierra manualmente
            if browser and cancel_event and cancel_event.is_set():
                try:
                    browser.close()
                except Exception:
                    pass
