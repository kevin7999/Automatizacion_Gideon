from faker import Faker
from core.catalogos import PASSWORD_DEFAULT
from core.generadores import limpiar_texto_crm, generar_documento_ve, generar_nombre_humano_limpio
from automation.crm_helpers import escribir_en_react, seleccionar_opcion_mui, hacer_clic_robusto

fake = Faker('es_ES')

def ejecutar_paso_1_datos_basicos(page, config_cuenta, correlativo, phone_number, email, log_callback):
    """
    Rellena los datos básicos (Paso 1):
    - Tipo de cuenta (Persona natural / Persona jurídica)
    - Nombre, Apellido o Razón Social
    - Documento de identidad / RIF
    - Celular, Email y Contraseña estándar
    Avanza al Paso 2 presionando Proceed.
    """
    tipo_persona = config_cuenta["tipo_persona"]
    company_name = ""
    first_name = ""
    last_name = ""
    last_name_puro = ""
    doc_id = ""

    seleccionar_opcion_mui(page, "#accountType", tipo_persona, log_callback)

    if tipo_persona == "Persona jurídica":
        company_name = limpiar_texto_crm(f"{fake.company()} {correlativo} C.A.")
        doc_id = generar_documento_ve(config_cuenta.get("tipo_rif", "Legal"), tipo_persona)
        escribir_en_react(page, "//input[contains(@aria-label, 'Name of the company') or contains(@name, 'companyName') or contains(@placeholder, 'company')]", company_name)
        seleccionar_opcion_mui(page, "//label[contains(text(), 'RIF')]/following-sibling::div | //*[contains(@id, 'documentType')]", config_cuenta["tipo_rif"], log_callback)
        escribir_en_react(page, "//input[contains(@aria-label, 'Document ID') or contains(@name, 'documentId')]", doc_id)
    else:
        first_name, last_name_puro = generar_nombre_humano_limpio()
        last_name = f"{last_name_puro} {correlativo}".strip()
        doc_id = generar_documento_ve(config_cuenta.get("tipo_doc", "Venezuelan"), tipo_persona)
        escribir_en_react(page, "//input[contains(@aria-label, 'First Name') or contains(@name, 'firstName')]", first_name)
        escribir_en_react(page, "//input[contains(@aria-label, 'Last Name') or contains(@name, 'lastName')]", last_name)
        seleccionar_opcion_mui(page, "#documentType", config_cuenta["tipo_doc"], log_callback)
        escribir_en_react(page, "//input[contains(@aria-label, 'Document ID') or contains(@name, 'documentId')]", doc_id)

    escribir_en_react(page, "//input[contains(@aria-label, 'Cell Phone') or contains(@name, 'cellPhone') or contains(@name, 'phone')]", phone_number)
    escribir_en_react(page, "//input[contains(@aria-label, 'Email') or contains(@name, 'email')]", email)
    escribir_en_react(page, "//input[contains(@aria-label, 'Confirm Email') or contains(@name, 'confirmEmail')]", email)
    escribir_en_react(page, "//input[@type='password' and (contains(@name, 'password') or contains(@aria-label, 'Password'))]", PASSWORD_DEFAULT)

    btn_proceed = page.locator("button:visible").filter(has_text="Proceed").first
    hacer_clic_robusto(page, btn_proceed, "Proceed Step 1")

    return company_name, first_name, last_name, last_name_puro, doc_id
