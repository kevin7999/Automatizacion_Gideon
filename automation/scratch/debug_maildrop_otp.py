"""
Captura el HTML completo de Maildrop para un buzón con email real.
Usar para identificar qué números de 6 dígitos aparecen ANTES del OTP.
"""
from playwright.sync_api import sync_playwright
import re
import os

MAILBOX = "CAMBIALOT_OTT276"  # Cambiar por un buzón real con email recibido

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()
    
    url = f"https://maildrop.cc/inbox/?mailbox={MAILBOX}"
    print(f"Navegando a: {url}")
    page.goto(url, timeout=60000)
    page.wait_for_timeout(3000)
    
    # Captura 1: inbox vacío / con email
    page.screenshot(path="scratch/maildrop_inbox.png")
    print("Screenshot 1 tomado (inbox)")
    
    # Intentar click en primer correo
    try:
        primer = page.locator("a[href*='/message/'], div[class*='Message'], li[class*='message'], div[class*='message'], a[class*='message']").first
        if primer.is_visible():
            print("Email encontrado - haciendo click...")
            primer.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="scratch/maildrop_email_abierto.png")
            print("Screenshot 2 tomado (email abierto)")
    except Exception as e:
        print(f"No se pudo abrir email: {e}")
    
    # Extraer texto y buscar todos los 6-digit matches
    texto = ""
    try:
        texto += page.inner_text("body")
    except:
        pass
    try:
        texto += " " + page.content()
    except:
        pass
        
    print("\n=== TODOS LOS 6-DIGIT ENCONTRADOS (en orden de aparición) ===")
    todos = list(re.finditer(r'(?<!\d)(\d{6})(?!\d)', texto))
    for i, m in enumerate(todos[:20]):
        contexto = texto[max(0, m.start()-30):m.end()+30].replace("\n", " ")
        print(f"  [{i+1}] {m.group(1)} | Contexto: ...{contexto}...")
    
    print(f"\nTotal encontrados: {len(todos)}")
    print("\nGuarda el HTML completo en scratch/maildrop_content.html")
    
    with open("scratch/maildrop_content.html", "w", encoding="utf-8", errors="replace") as f:
        f.write(page.content())
    
    input("\nPresiona Enter para cerrar el navegador...")
    browser.close()
