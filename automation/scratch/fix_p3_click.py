"""
Reemplaza el bloque P3/4 (bytes 55071-60253) con estrategia click-based 
para dropdowns custom React/Ant Design.
Opera en binario puro, sin tocar el encoding del resto del archivo.
"""
ARCHIVO = r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py'

IDX_INI = 55071
IDX_FIN = 60253  # exclusivo (el \r\n\r\n antes de P4/4 se mantiene)

NUEVO_BLOQUE = b'''            # -- CONTRATO PASO 3/4: Direccion de instalacion --
            timer.start_step("F3: Contrato P3/4 Direccion")
            page.wait_for_timeout(2000)
            log_callback(f"[Hilo {id_hilo}] Llenando direccion de instalacion...")

            # Datos del catalogo OTT
            dir_ott = CATALOGO_DIRECCIONES_OTT.get(ubicacion)
            if not dir_ott:
                dir_ott = list(CATALOGO_DIRECCIONES_OTT.values())[0]

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

            # Helper: abre un dropdown custom (React/Ant) por su placeholder actual
            # y selecciona la opcion que coincida con 'valor'.
            def _ddown(placeholder_actual, valor, desc):
                ABRE = [
                    f"[title='{placeholder_actual}']",
                    f"[placeholder='{placeholder_actual}']",
                    f"span.ant-select-selection-placeholder:text-is('{placeholder_actual}')",
                    f"span:text-is('{placeholder_actual}')",
                    f"div:text-is('{placeholder_actual}')",
                ]
                OPCIONES = [
                    f"[role='option']:has-text('{valor}')",
                    f"li[role='option']:has-text('{valor}')",
                    f".ant-select-item:has-text('{valor}')",
                    f".select__option:has-text('{valor}')",
                    f"div.rc-virtual-list-holder-inner div:has-text('{valor}')",
                    f"li:has-text('{valor}')",
                ]
                try:
                    for sel in ABRE:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible():
                                el.click(force=True)
                                page.wait_for_timeout(800)
                                # Verificar que se abrio la lista
                                for sel_op in OPCIONES:
                                    try:
                                        op = page.locator(sel_op).first
                                        op.wait_for(state="visible", timeout=3000)
                                        op.click(force=True)
                                        page.wait_for_timeout(300)
                                        log_callback(f"[Hilo {id_hilo}] OK {desc}: {valor}")
                                        return True
                                    except Exception:
                                        continue
                                # Si no encontro la opcion, cerrar con Escape
                                page.keyboard.press("Escape")
                        except Exception:
                            continue
                    log_callback(f"[Hilo {id_hilo}] WARN {desc}: dropdown '{placeholder_actual}' no abierto")
                    return False
                except Exception as e:
                    log_callback(f"[Hilo {id_hilo}] WARN {desc}: {e}")
                    return False

            _ddown("Selecciona un estado",          estado_val,  "Estado")
            page.wait_for_timeout(3000)
            _ddown("Selecciona tu ciudad",          ciudad_val,  "Ciudad")
            page.wait_for_timeout(3000)
            _ddown("Selecciona un municipio",       muni_val,    "Municipio")
            page.wait_for_timeout(3000)
            _ddown("Selecciona tu zona",            zona_val,    "Zona")
            page.wait_for_timeout(3000)
            _ddown("Selecciona tu codigo postal",   cp_val,      "Codigo Postal")
            page.wait_for_timeout(2000)
            _ddown("Selecciona el area",            "70",        "Area Inmueble")
            page.wait_for_timeout(1000)
            _ddown("Selecciona un tipo de calle",   tipo_calle,  "Tipo Calle")
            page.wait_for_timeout(1000)
            _ddown("Selecciona un tipo de edificio","residencial","Tipo Edificio")
            page.wait_for_timeout(1000)

            # Inputs de texto (placeholders exactos del CRM)
            try:
                page.locator("input[placeholder*='avenida o calle']").first.fill(nombre_calle, force=True)
                log_callback(f"[Hilo {id_hilo}] OK Avenida/Calle: {nombre_calle}")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] WARN Avenida/Calle: {e}")
            try:
                page.locator("input[placeholder*='nombre del edificio']").first.fill(edificio_val, force=True)
                log_callback(f"[Hilo {id_hilo}] OK Edificio: {edificio_val}")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] WARN Edificio: {e}")
            try:
                page.locator("input[placeholder*='mero de casa']").first.fill(num_casa_val, force=True)
                log_callback(f"[Hilo {id_hilo}] OK N Casa: {num_casa_val}")
            except Exception as e:
                log_callback(f"[Hilo {id_hilo}] WARN N Casa: {e}")

            page.wait_for_timeout(1000)
            guardar_evidencia(timer.current_step)

            page.get_by_role("button", name="Continuar").last.click(force=True)
            page.wait_for_timeout(3000)
            timer.stop_step()

'''

with open(ARCHIVO, 'rb') as f:
    raw = f.read()

nuevo_raw = raw[:IDX_INI] + NUEVO_BLOQUE + raw[IDX_FIN:]

with open(ARCHIVO, 'wb') as f:
    f.write(nuevo_raw)

print(f"OK: {IDX_FIN - IDX_INI} bytes -> {len(NUEVO_BLOQUE)} bytes")
