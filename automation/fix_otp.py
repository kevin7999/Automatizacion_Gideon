import re
with open(r'worker_ftth_ecommerce.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('primer_correo = page_mail.locator("div[class*=\'truncate\']").first', 'primer_correo = page_mail.locator("div[class*=\'truncate\'], a[href*=\'/inbox/\'], li[class*=\'message\']").first')

text = text.replace('texto += page_mail.inner_text("body")', 'texto += page_mail.inner_text("body")\n                texto += " " + page_mail.content()')

text = text.replace('texto += " " + frame.inner_text("body")', 'texto += " " + frame.inner_text("body")\n                    texto += " " + frame.content()')

text = text.replace(r"match = re.search(r'\b(\d{6})\b', texto)", r"match = re.search(r'(?<!\d)(\d{6})(?!\d)', texto)")

with open(r'worker_ftth_ecommerce.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Replacement done')
