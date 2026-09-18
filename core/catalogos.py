import os
import csv

ARCHIVO_DIRECCIONES = "catalogo_direcciones.csv"
ARCHIVO_PLANES = "catalogo_planes.csv"
ARCHIVO_OTT = "catalogo_ott.csv"
PASSWORD_DEFAULT = "Ingreso-1"

def cargar_catalogo_direcciones(ruta_archivo=ARCHIVO_DIRECCIONES):
    catalogo_dir = {}
    if not os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Ubicacion", "Estado", "Ciudad", "Municipio", "Parroquia", "Codigo_Postal", "Edificio_Casa"])
                writer.writerow(["Caracas", "Distrito capital", "Caracas", "Libertador", "URB. CHACAITO", "1050", "Torre Directv"])
                writer.writerow(["Miranda", "Miranda", "Caracas", "Chacao", "Urb. el rosal", "1060", "Simple centro de transmisiones"])
                writer.writerow(["Nueva Esparta", "Nueva esparta", "La asuncion", "Arismendi", "La asuncion", "6311", "Centro estetico la asuncion"])
        except Exception as e:
            print(f"Error creando plantilla de direcciones CSV: {e}")

    try:
        with open(ruta_archivo, "r", encoding="utf-8-sig", errors="replace") as f:
            muestra = f.read(2048)
            f.seek(0)
            delimitador = ";" if ";" in muestra and muestra.count(";") > muestra.count(",") else ","
            reader = csv.DictReader(f, delimiter=delimitador)
            for row in reader:
                clean_row = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None and v is not None}
                ubicacion = clean_row.get("Ubicacion")
                if ubicacion:
                    catalogo_dir[ubicacion] = {
                        "state": clean_row.get("Estado", "Distrito capital"),
                        "city": clean_row.get("Ciudad", "Caracas"),
                        "municipality": clean_row.get("Municipio", "Libertador"),
                        "neighbourhood": clean_row.get("Parroquia", "URB. CHACAITO"),
                        "postal_code": clean_row.get("Codigo_Postal", "1050"),
                        "building_house": clean_row.get("Edificio_Casa", "Torre Directv")
                    }
    except Exception as e:
        print(f"Error al leer el catálogo de direcciones: {e}")

    if not catalogo_dir:
        catalogo_dir["Caracas"] = {
            "state": "Distrito capital", "city": "Caracas", "municipality": "Libertador",
            "neighbourhood": "URB. CHACAITO", "postal_code": "1050", "building_house": "Torre Directv"
        }
    return catalogo_dir

def cargar_catalogo_planes(ruta_archivo=ARCHIVO_PLANES):
    catalogo = {}
    if not os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Identificador", "Paquete", "Promocion", "Tarifa", "Router"])
                writer.writerow(["Compra: 400 mbps + Gold", "400 mbps + Gold", "INTERNET100%OFF", "$0", "Nokia G-1426G-A"])
                writer.writerow(["Alquiler: 400 mbps + Gold", "400 mbps + Gold", "Gold_400Mbps_Alquiler", "$0", "N NokiaG1426GA1Month"])
                writer.writerow(["Compra: 500 mbps + Gold", "500 mbps + Gold", "INTERNET100%OFF", "$0", "Nokia G-1426G-A"])
                writer.writerow(["Alquiler: 500 mbps + Gold", "500 mbps + Gold", "Gold_500Mbps_Alquiler", "$0", "N NokiaG1426GA1Month"])
        except Exception as e:
            print(f"Error creando plantilla CSV de planes: {e}")

    try:
        with open(ruta_archivo, "r", encoding="utf-8-sig", errors="replace") as f:
            muestra = f.read(2048)
            f.seek(0)
            delimitador = ";" if ";" in muestra and muestra.count(";") > muestra.count(",") else ","
            reader = csv.DictReader(f, delimiter=delimitador)
            for row in reader:
                clean_row = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None and v is not None}
                nombre_id = clean_row.get("Identificador")
                if nombre_id:
                    paquete = clean_row.get("Paquete", "")
                    promocion = clean_row.get("Promocion", "")
                    tarifa = clean_row.get("Tarifa", "$0")
                    router = clean_row.get("Router", "")

                    velocidad = "Otro"
                    for vel in ["1000", "600", "500", "400"]:
                        if vel in nombre_id or vel in paquete:
                            velocidad = f"{vel} Mbps"
                            break

                    modalidad = "Alquiler" if "alquiler" in nombre_id.lower() else "Compra"

                    familia = "Otros"
                    if "diamond" in paquete.lower() or "diamante" in paquete.lower():
                        familia = "Diamante"
                    elif "platino" in paquete.lower():
                        familia = "Platino"
                    elif "gold" in paquete.lower():
                        familia = "Gold"

                    catalogo[nombre_id] = {
                        "paquete": paquete,
                        "promocion": promocion,
                        "tarifa": tarifa,
                        "router": router,
                        "velocidad": velocidad,
                        "modalidad": modalidad,
                        "familia": familia
                    }
    except PermissionError:
        print(f"⚠️ [AVISO] El archivo '{ruta_archivo}' está bloqueado (posiblemente abierto en Excel).")
    except Exception as e:
        print(f"Error al leer el catálogo de planes: {e}")

    if not catalogo:
        catalogo["Compra: 400 mbps + Gold"] = {
            "paquete": "400 mbps + Gold",
            "promocion": "INTERNET100%OFF",
            "tarifa": "$0",
            "router": "Nokia G-1426G-A",
            "velocidad": "400 Mbps",
            "modalidad": "Compra",
            "familia": "Gold"
        }

    return catalogo

def cargar_catalogo_ott(ruta_archivo=ARCHIVO_OTT):
    catalogo = {}
    if not os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Identificador", "Paquete"])
                writer.writerow(["Litesports", "Litesports"])
                writer.writerow(["Gold", "Gold"])
                writer.writerow(["Platino", "Platino"])
                writer.writerow(["Diamante", "Diamante"])
        except Exception as e:
            print(f"Error creando plantilla CSV de planes OTT: {e}")

    try:
        with open(ruta_archivo, "r", encoding="utf-8-sig", errors="replace") as f:
            muestra = f.read(2048)
            f.seek(0)
            delimitador = ";" if ";" in muestra and muestra.count(";") > muestra.count(",") else ","
            reader = csv.DictReader(f, delimiter=delimitador)
            for row in reader:
                clean_row = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None and v is not None}
                nombre_id = clean_row.get("Identificador")
                if nombre_id:
                    catalogo[nombre_id] = {
                        "paquete": clean_row.get("Paquete", nombre_id)
                    }
    except PermissionError:
        print(f"⚠️ [AVISO] El archivo '{ruta_archivo}' está bloqueado (posiblemente abierto en Excel).")
    except Exception as e:
        print(f"Error al leer el catálogo de planes OTT: {e}")

    if not catalogo:
        catalogo["Gold"] = {"paquete": "Gold"}

    return catalogo
