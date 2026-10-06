"""
Script de diagnóstico: abre el CRM en el paso P3/4 y extrae los name/id/placeholder
de todos los selects e inputs presentes en el modal de dirección.
Ejecutar MANUALMENTE cuando el CRM esté en la pantalla de dirección de instalación.
"""
from playwright.sync_api import sync_playwright
import json

URL = "https://tiendatesting.simple.com.ve/carrito"

with sync_playwright() as p:
    # Conectar al navegador existente si hay uno, o abrir uno nuevo
    browser = p.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context()
    page = context.new_page()

    page.goto(URL, timeout=60000)
    page.wait_for_timeout(3000)

    print("Navega manualmente hasta la pantalla 'Dirección de instalación' (Paso 3 de 4).")
    input("Cuando estés en esa pantalla, presiona ENTER aquí...")

    # Extraer info de todos los select e inputs
    info = page.evaluate("""() => {
        const result = { selects: [], inputs: [] };

        // Selects
        document.querySelectorAll('select').forEach(s => {
            result.selects.push({
                name: s.name,
                id: s.id,
                placeholder: s.getAttribute('placeholder'),
                options: Array.from(s.options).slice(0, 5).map(o => ({text: o.text, value: o.value})),
                visible: s.offsetParent !== null
            });
        });

        // Inputs
        document.querySelectorAll('input').forEach(i => {
            result.inputs.push({
                name: i.name,
                id: i.id,
                type: i.type,
                placeholder: i.placeholder,
                visible: i.offsetParent !== null
            });
        });

        return result;
    }""")

    print("\n=== SELECTS ENCONTRADOS ===")
    for s in info['selects']:
        if s['visible']:
            print(f"  name='{s['name']}' id='{s['id']}' | opciones: {[o['text'] for o in s['options']]}")

    print("\n=== INPUTS ENCONTRADOS ===")
    for i in info['inputs']:
        if i['visible']:
            print(f"  name='{i['name']}' type='{i['type']}' placeholder='{i['placeholder']}'")

    # Guardar resultado completo
    with open("scratch/dom_direccion.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print("\nResultado completo guardado en scratch/dom_direccion.json")

    input("Presiona ENTER para cerrar...")
    browser.close()
