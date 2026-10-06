"""
Reemplazo quirúrgico a nivel bytes de las líneas dir_data y rellenar_input
en el paso P3/4 de worker_ftth_ecommerce.py
"""
ARCHIVO = r'c:\Users\KGarcia.Pasante\Music\GIDEON 3.1\GIDEON\automation\worker_ftth_ecommerce.py'

with open(ARCHIVO, 'rb') as f:
    raw = f.read()

# ─ REEMPLAZO 1: Asignaciones dir_data → dir_ott ─────────────────────────────
OLD1 = (
    b'            # Dato base del cat\xc3\x83\xc2\x83\xc3\x82\xc2\xa1logo\r\n'
    b'            estado_val  = dir_data.get("state", "Miranda")\r\n'
    b'            ciudad_val  = dir_data.get("city", "Caracas")\r\n'
    b'            muni_val    = dir_data.get("municipality", "Chacao")\r\n'
    b'            zona_val    = dir_data.get("neighbourhood", "Urb. El Rosal")\r\n'
    b'            cp_val      = dir_data.get("postal_code", "1060")\r\n'
    b'            edificio_val = dir_data.get("building_house", "Torre Directv")\r\n'
)
NEW1 = (
    b'            # Datos del catalogo OTT (campos exactos para selects del contrato)\r\n'
    b'            dir_ott = CATALOGO_DIRECCIONES_OTT.get(ubicacion)\r\n'
    b'            if not dir_ott:\r\n'
    b'                dir_ott = list(CATALOGO_DIRECCIONES_OTT.values())[0]\r\n'
    b'\r\n'
    b'            estado_val   = dir_ott.get("state", "distrito capital")\r\n'
    b'            ciudad_val   = dir_ott.get("city", "caracas")\r\n'
    b'            muni_val     = dir_ott.get("municipality", "libertador")\r\n'
    b'            zona_val     = dir_ott.get("zone", "chacaito")\r\n'
    b'            cp_val       = dir_ott.get("postal_code", "1060")\r\n'
    b'            tipo_calle   = dir_ott.get("street_type", "avenida")\r\n'
    b'            nombre_calle = dir_ott.get("street_name", "Av Venezuela")\r\n'
    b'            edificio_val = dir_ott.get("building_name", "torre directv")\r\n'
    b'            num_casa_val = dir_ott.get("house_number", "533")\r\n'
)

if OLD1 in raw:
    raw = raw.replace(OLD1, NEW1, 1)
    print("OK 1: datos dir_data -> dir_ott")
else:
    print("FAIL 1: no encontrado")

# ─ REEMPLAZO 2: streetType hardcodeado → tipo_calle ─────────────────────────
OLD2 = b'                _react_select(page, "installationAddress.streetType", "Avenida")\r\n'
NEW2 = b'                _react_select(page, "installationAddress.streetType", tipo_calle)\r\n'

if OLD2 in raw:
    raw = raw.replace(OLD2, NEW2, 1)
    print("OK 2: streetType -> tipo_calle")
else:
    print("FAIL 2: streetType no encontrado")

# ─ REEMPLAZO 3: rellenar_input con valores correctos ────────────────────────
OLD3 = (
    b'            rellenar_input(["avenida o calle", "calle", "Avenida"], edificio_val.split(",")[0] if "," in edificio_val else "AVENIDA VENEZUELA")\r\n'
    b'            rellenar_input(["edificio", "casa", "nombre del edificio", "Edificio"], edificio_val)\r\n'
    b'            rellenar_input(["n\xc3\x83\xc2\x83\xc3\x82\xc2\xbamero de casa", "n\xc3\x83\xc2\x82\xc3\x82\xc2\xb0 de casa", "apartamento", "N\xc3\x83\xc2\x82\xc3\x82\xc2\xb0"], "1")\r\n'
)
NEW3 = (
    b'            rellenar_input(["avenida o calle", "calle", "Avenida", "avenida"], nombre_calle)\r\n'
    b'            rellenar_input(["edificio", "casa", "nombre del edificio", "Edificio"], edificio_val)\r\n'
    b'            rellenar_input(["numero de casa", "n de casa", "apartamento"], num_casa_val)\r\n'
)

if OLD3 in raw:
    raw = raw.replace(OLD3, NEW3, 1)
    print("OK 3: rellenar_input -> nombre_calle, num_casa_val")
else:
    print("FAIL 3: rellenar_input no encontrado (verificar bytes)")

with open(ARCHIVO, 'wb') as f:
    f.write(raw)
print("Archivo guardado.")
