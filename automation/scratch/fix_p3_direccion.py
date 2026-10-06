"""
Reemplaza líneas 940-993 (bloque selects P3/4) por la versión con wait_for_selector + logs.
Opera directamente sobre las líneas del archivo.
"""
ARCHIVO = r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py'

with open(ARCHIVO, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Líneas a reemplazar: 940-993 (1-indexed) → índices 939-992
L_INICIO = 939  # índice 0-based
L_FIN    = 993  # índice 0-based, exclusivo

NUEVO = [
    '            log_callback(f"[Hilo {id_hilo}] Datos: {estado_val} / {ciudad_val} / {muni_val} / {zona_val}")\n',
    '\n',
    '            # Helper local con wait + log para cada select\n',
    '            def _sel(nombre_campo, valor, descripcion):\n',
    '                try:\n',
    "                    page.wait_for_selector(f\"select[name='{nombre_campo}']\", timeout=8000)\n",
    '                    page.evaluate("""([name, text]) => {\n',
    '                        const select = document.querySelector(`select[name=\'${name}\']`);\n',
    '                        if (!select) return;\n',
    '                        const target = Array.from(select.options).find(o => o.text.toLowerCase().includes(text.toLowerCase()));\n',
    '                        if (!target) return;\n',
    "                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;\n",
    '                        nativeSetter.call(select, target.value);\n',
    "                        select.dispatchEvent(new Event('change', { bubbles: true }));\n",
    '                    }""", [nombre_campo, valor])\n',
    '                    log_callback(f"[Hilo {id_hilo}] OK {descripcion}: \'{valor}\'")\n',
    '                except Exception as e:\n',
    '                    log_callback(f"[Hilo {id_hilo}] WARN {descripcion} (\'{nombre_campo}\'): {e}")\n',
    '\n',
    '            _sel("installationAddress.state",        estado_val,    "Estado")\n',
    '            page.wait_for_timeout(3000)\n',
    '            _sel("installationAddress.city",         ciudad_val,    "Ciudad")\n',
    '            page.wait_for_timeout(3000)\n',
    '            _sel("installationAddress.municipality", muni_val,      "Municipio")\n',
    '            page.wait_for_timeout(3000)\n',
    '            _sel("installationAddress.zone",         zona_val,      "Zona")\n',
    '            page.wait_for_timeout(3000)\n',
    '            _sel("installationAddress.postalCode",   cp_val,        "Codigo Postal")\n',
    '            page.wait_for_timeout(2000)\n',
    '            _sel("installationAddress.propertyArea", "70",          "Area Inmueble")\n',
    '            page.wait_for_timeout(1000)\n',
    '            _sel("installationAddress.streetType",   tipo_calle,    "Tipo Calle")\n',
    '            page.wait_for_timeout(1000)\n',
    '            _sel("installationAddress.buildingType", "residencial", "Tipo Edificio")\n',
    '            page.wait_for_timeout(1000)\n',
    '\n',
    '            # Inputs de texto con placeholders exactos del CRM\n',
    '            try:\n',
    "                page.locator(\"input[placeholder*='avenida o calle']\").first.fill(nombre_calle, force=True)\n",
    '                log_callback(f"[Hilo {id_hilo}] OK Avenida/Calle: {nombre_calle}")\n',
    '            except Exception as e:\n',
    '                log_callback(f"[Hilo {id_hilo}] WARN Avenida/Calle: {e}")\n',
    '\n',
    '            try:\n',
    "                page.locator(\"input[placeholder*='nombre del edificio']\").first.fill(edificio_val, force=True)\n",
    '                log_callback(f"[Hilo {id_hilo}] OK Edificio: {edificio_val}")\n',
    '            except Exception as e:\n',
    '                log_callback(f"[Hilo {id_hilo}] WARN Edificio: {e}")\n',
    '\n',
    '            try:\n',
    "                page.locator(\"input[placeholder*='n\u00famero de casa']\").first.fill(num_casa_val, force=True)\n",
    '                log_callback(f"[Hilo {id_hilo}] OK N Casa: {num_casa_val}")\n',
    '            except Exception as e:\n',
    '                log_callback(f"[Hilo {id_hilo}] WARN N Casa: {e}")\n',
    '\n',
    '            page.wait_for_timeout(1000)\n',
    '            guardar_evidencia(timer.current_step)\n',
    '\n',
    '            page.get_by_role("button", name="Continuar").last.click(force=True)\n',
    '            page.wait_for_timeout(3000)\n',
    '            timer.stop_step()\n',
]

nuevas_lineas = lines[:L_INICIO] + NUEVO + lines[L_FIN:]

with open(ARCHIVO, 'w', encoding='utf-8') as f:
    f.writelines(nuevas_lineas)

print(f"OK: reemplazadas lineas {L_INICIO+1}-{L_FIN} ({L_FIN-L_INICIO} lineas originales -> {len(NUEVO)} lineas nuevas)")
