import re
import random
import unicodedata
from faker import Faker

fake = Faker('es_ES')

PREFIJOS_VE = ["0412", "0414", "0424", "0416", "0426"]

NOMBRES_DEFAULT = [
    "Carlos", "Luis", "Jose", "Maria", "Ana", "Pedro", "Juan", "Elena", 
    "Andres", "Carmen", "Sofia", "Daniel", "Patricia", "Manuel", 
    "Alejandro", "Rosa", "Gabriel", "Laura", "Hector", "Diana"
]

APELLIDOS_DEFAULT = [
    "Perez", "Gonzalez", "Rodriguez", "Gomez", "Fernandez", "Lopez", 
    "Diaz", "Martinez", "Sanchez", "Ramirez", "Torres", "Vargas", 
    "Castro", "Rios", "Mendoza", "Morales", "Suarez", "Silva"
]

def limpiar_texto_crm(texto):
    """Elimina acentos, tildes, virgulillas (ñ -> n) y caracteres especiales para compatibilidad estricta con el CRM."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    texto_sin_tildes = "".join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    reemplazos = {
        'ñ': 'n', 'Ñ': 'N',
        'ü': 'u', 'Ü': 'U',
        'ç': 'c', 'Ç': 'C',
    }
    for orig, dest in reemplazos.items():
        texto_sin_tildes = texto_sin_tildes.replace(orig, dest)
    return re.sub(r'[^a-zA-Z0-9\s.,#-]', '', texto_sin_tildes).strip()

def generar_telefono_ve():
    """Genera un número telefónico celular válido con prefijo venezolano."""
    prefijo = random.choice(PREFIJOS_VE)
    primer_digito = str(random.randint(1, 9))
    resto = "".join(str(random.randint(0, 9)) for _ in range(6))
    return f"{prefijo}{primer_digito}{resto}"

def generar_documento_ve(tipo_doc, tipo_persona):
    """Genera número de Cédula o RIF venezolano según el tipo de persona y documento."""
    if tipo_persona == "Persona jurídica":
        # RIF Jurídico de 9 dígitos (100.000.000 a 499.999.999)
        return str(random.randint(100000000, 499999999))
    else:
        if tipo_doc == "Venezuelan":
            # Cédula venezolana realista (12.000.000 a 31.999.999)
            return str(random.randint(12000000, 31999999))
        elif tipo_doc == "Foreigner":
            # Extranjeros residentes (Serie 80 a 84 millones)
            return str(random.randint(80000000, 84999999))
        else:
            # Pasaporte / Otros
            return str(random.randint(10000000, 29999999))

def generar_nombre_humano_limpio():
    """Genera un nombre y apellido limpios sin caracteres conflictivos."""
    nombre = limpiar_texto_crm(fake.first_name())
    apellido = limpiar_texto_crm(fake.last_name())
    if not nombre or len(nombre) < 2 or not nombre.isalpha():
        nombre = random.choice(NOMBRES_DEFAULT)
    if not apellido or len(apellido) < 2 or not apellido.isalpha():
        apellido = random.choice(APELLIDOS_DEFAULT)
    return nombre, apellido
