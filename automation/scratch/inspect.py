f = open(r'c:/Users/KGarcia.Pasante/Music/GIDEON 3.1/GIDEON/automation/worker_ftth_ecommerce.py', 'rb')
raw = f.read()
f.close()
# Buscar ocurrencias de rellenar_input
import re
for m in re.finditer(rb'rellenar_input\(\[', raw):
    print(f"pos {m.start()}: {repr(raw[m.start():m.start()+160])}")
    print()
