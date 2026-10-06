"""
Reemplaza _obtener_otp_maildrop_ecom con una version que:
1. Primero intenta abrir el correo
2. Busca el OTP SOLO en inner_text (no en HTML crudo) del email abierto
3. Prioriza codigos cerca de palabras clave (codigo, code, verificacion, OTP)
4. Como fallback, busca en todo el inner_text pero excluyendo falsos positivos conocidos
"""

ARCHIVO = r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py'

with open(ARCHIVO, 'r', encoding='utf-8', errors='replace') as f:
    contenido = f.read()

INICIO_MARKER = "def _obtener_otp_maildrop_ecom("

import re

idx_inicio = contenido.find(INICIO_MARKER)
if idx_inicio == -1:
    print("ERROR: No se encontro la funcion")
    exit(1)

# Buscar la siguiente funcion de nivel modulo
patron = re.compile(r'\r?\ndef [a-z_]', re.MULTILINE)
coincidencias = list(patron.finditer(contenido, idx_inicio + 50))
idx_fin = coincidencias[0].start()

print(f"Reemplazando bloque [{idx_inicio}:{idx_fin}]")

NUEVA_FUNCION = r'''def _obtener_otp_maildrop_ecom(email_base, correlativo, p_context, id_hilo, log_callback, cancel_event=None):
    """
    Abre una pestana de Maildrop, espera el correo del CRM y extrae el OTP de 6 digitos.
    Estrategia de extraccion en 2 fases:
      1. Busca el OTP cerca de palabras clave (codigo, verificacion, OTP) - alta precision.
      2. Fallback: primer 6-digit en el inner_text del correo abierto (no en HTML crudo).
    Mantiene la pestana abierta y refresca en cada reintento.
    """
    mailbox_name = f"{email_base}{correlativo}"
    url_mailbox = f"https://maildrop.cc/inbox/?mailbox={mailbox_name}"
    log_callback(f"[Hilo {id_hilo}] Abriendo Maildrop: {url_mailbox}")

    # Palabras clave que deben aparecer CERCA del OTP real en el email
    PATRON_CONTEXTUAL = re.compile(
        r'(?:c[oó]digo|code|verificaci[oó]n|verification|otp|token|clave|pin)'  # keyword
        r'.{0,80}'       # hasta 80 chars de distancia
        r'(\d{6})'       # el codigo de 6 digitos
        r'|'             # O al reves: numero primero, keyword despues
        r'(\d{6})'
        r'.{0,80}'
        r'(?:c[oó]digo|code|verificaci[oó]n|verification|otp|token|clave|pin)',
        re.IGNORECASE | re.DOTALL
    )

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

            # ── FASE 1: Intentar abrir el primer correo ──────────────────────────────
            email_abierto = False
            try:
                primer_correo = page_mail.locator(
                    "a[href*='/message/'], div[class*='Message'], li[class*='message'], "
                    "div[class*='message'], a[class*='message'], "
                    "article, [role='listitem']"
                ).first
                if primer_correo.is_visible():
                    log_callback(f"[Hilo {id_hilo}] Email detectado en inbox - abriendo...")
                    primer_correo.click()
                    page_mail.wait_for_timeout(2000)
                    email_abierto = True
            except Exception:
                pass

            # ── FASE 2: Extraer SOLO el texto visible (sin HTML crudo) ────────────
            texto_email = ""
            try:
                texto_email = page_mail.inner_text("body")
            except Exception:
                pass

            # Tambien extraer de frames (Maildrop incrusta el contenido en iframes)
            for frame in page_mail.frames:
                try:
                    texto_email += " " + frame.inner_text("body")
                except Exception:
                    pass

            # ── FASE 3: Busqueda con contexto (maxima precision) ─────────────────
            match_ctx = PATRON_CONTEXTUAL.search(texto_email)
            if match_ctx:
                # Puede estar en grupo 1 o grupo 2 segun el orden
                codigo = match_ctx.group(1) or match_ctx.group(2)
                log_callback(f"[Hilo {id_hilo}] OTP (contextual) encontrado: {codigo} (intento {intento + 1})")
                break

            # ── FASE 4: Fallback — primer 6-digit en texto del correo (sin HTML) ─
            if email_abierto:
                match_fb = re.search(r'(?<!\d)(\d{6})(?!\d)', texto_email)
                if match_fb:
                    codigo = match_fb.group(1)
                    log_callback(f"[Hilo {id_hilo}] OTP (fallback) encontrado: {codigo} (intento {intento + 1})")
                    break

            # Diagnostico: mostrar extracto del texto para ver que hay
            extracto = texto_email[:200].replace("\n", " ").replace("\r", "").strip()
            log_callback(f"[Hilo {id_hilo}] Sin OTP. Texto inbox: '{extracto[:120]}'")

            # Esperar y refrescar para la siguiente iteracion
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
'''

nuevo_contenido = contenido[:idx_inicio] + NUEVA_FUNCION + contenido[idx_fin:]

with open(ARCHIVO, 'wb') as f:
    f.write(nuevo_contenido.encode('utf-8'))

print("ARCHIVO ACTUALIZADO CON EXITO")
