"""
Inyecta un bloque de diagnóstico ANTES de las asignaciones de dir_ott
para volcar en el log todos los selects e inputs visibles en P3/4.
"""
ARCHIVO = r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py'

with open(ARCHIVO, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# La línea 925 (0-index 924) es el comentario "# Datos del catalogo OTT..."
# Insertamos el bloque de diagnóstico ANTES de esa línea
INSERT_AT = 924  # 0-indexed

BLOQUE_DIAG = [
    '            # Diagnostico: volcar todos los selects e inputs del formulario\n',
    '            try:\n',
    '                dom_info = page.evaluate("""() => {\n',
    '                    const r = { selects: [], inputs: [] };\n',
    '                    document.querySelectorAll("select").forEach(s => {\n',
    '                        if (s.offsetParent !== null) {\n',
    '                            r.selects.push(s.name + "|" + s.id + "|opts:" + Array.from(s.options).slice(0,3).map(o=>o.text).join(","));\n',
    '                        }\n',
    '                    });\n',
    '                    document.querySelectorAll("input").forEach(i => {\n',
    '                        if (i.offsetParent !== null) {\n',
    '                            r.inputs.push(i.name + "|" + i.placeholder);\n',
    '                        }\n',
    '                    });\n',
    '                    return r;\n',
    '                }""")\n',
    '                log_callback(f"[Hilo {id_hilo}] DOM SELECTS: {dom_info[\'selects\']}")\n',
    '                log_callback(f"[Hilo {id_hilo}] DOM INPUTS:  {dom_info[\'inputs\']}")\n',
    '            except Exception as e:\n',
    '                log_callback(f"[Hilo {id_hilo}] DOM inspect error: {e}")\n',
    '\n',
]

nuevas = lines[:INSERT_AT] + BLOQUE_DIAG + lines[INSERT_AT:]

with open(ARCHIVO, 'w', encoding='utf-8') as f:
    f.writelines(nuevas)

print(f"Bloque diagnóstico insertado en línea {INSERT_AT+1}")
