# 📚 Diccionario de Datos, Esquemas y Catálogos - G.I.D.E.O.N. 4.0 Oficial

Este documento constituye la especificación formal de datos, formatos de almacenamiento y catálogos de soporte para la suite **G.I.D.E.O.N. 4.0**. Diseñado para responder a requerimientos de auditoría de software, aseguramiento de la calidad (QA) e integración continua.

---

## 1. Registro Maestro de Transacciones (`cuentas_creadas.csv`)

Cada ejecución de aprovisionamiento (sea exitosa o fallida) se registra de forma síncrona en el archivo delimitado por comas `cuentas_creadas.csv` ubicado en la raíz del proyecto. El archivo utiliza codificación `UTF-8` con cabecera fija de 13 columnas:

| # | Nombre de Campo | Tipo de Dato | Nullable | Ejemplo | Descripción Técnica |
|---|---|---|---|---|---|
| **1** | `Fecha_Hora` | String (`YYYY-MM-DD HH:MM:SS`) | No | `2026-10-12 13:29:36` | Marca de tiempo del fin de la transacción. |
| **2** | `Servicio` | String (Enum) | No | `FTTH` / `OTT` | Pipeline que originó la cuenta. |
| **3** | `Tipo_Persona` | String | No | `Venezuelan`, `Personal Sign`, `Legal`, `Foreigner` | Clasificación jurídica o de documento en el CRM. |
| **4** | `Documento_RIF` | String | No | `V-18089499`, `J-501234567` | Cédula o RIF generado sintéticamente o asignado. |
| **5** | `Nombre_o_Empresa` | String | No | `Amaya Real`, `Inversiones Alfa C.A.` | Nombre del titular asignado a la cuenta. |
| **6** | `Email` | String (Email RFC 5322) | No | `CAMBIALOT_OTT86@maildrop.cc` | Buzón transaccional único asignado a la cuenta. |
| **7** | `Telefono` | String (`^\d{11}$`) | No | `04164807624` | Teléfono de contacto con prefijo nacional válido. |
| **8** | `Ubicacion` | String | No | `Caracas`, `Maracaibo`, `Valencia` | Identificador de plaza o nodo geográfico. |
| **9** | `Plan` | String | No | `Compra: 400 mbps + Gold Wifi 5`, `Diamante` | Paquete comercial seleccionado. |
| **10** | `Estado` | String | No | `EXITOSO (Cuenta Activada)`, `EXITOSO (Pendiente Pago)`, `Error: [...]` | Resultado de la automatización o traza del fallo. |
| **11** | `Tiempo_Total_Segundos` | String (`^\d+\.\d+s$`) | No | `126.7s` | Latencia acumulada de la cuenta (P1 a PN). |
| **12** | `Desglose_Tiempos` | String (`Key:Value\|...`) | No | `P0:0.0s\|P1:1.2s\|P2:8.6s\|...` | Telemetría granular por paso con fines de auditoría de rendimiento. |
| **13** | `ID_Cliente` | String | Sí | `5832909` o `-` | Número de contrato/cliente devuelto por Evergent. |

---

## 2. Catálogos Dinámicos del Sistema

G.I.D.E.O.N. desacopla los datos comerciales y de cobertura geográfica de la lógica de automatización mediante catálogos CSV editables por el operador o actualizables por TI:

### 2.1. Catálogo de Planes Fibra (`catalogo_planes.csv`)
Define la oferta comercial disponible para el módulo FTTH CRM:

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `Nombre_Plan` | String | Nombre público del plan base | `400 Mbps + Gold` |
| `Sub_Plan` | String | Modalidad de adquisición | `Compra` / `Alquiler` |
| `Velocidad` | String | Ancho de banda de bajada | `400 Mbps` |
| `Tecnologia` | String | Estándar de acceso | `FTTH GPON` |
| `Precio` | Float | Tarifa de referencia en USD | `45.00` |
| `Moneda` | String | Código de moneda | `USD` |
| `Bundle` | String | Paquete de contenido anexo | `Gold Movies` |

### 2.2. Catálogo de Cobertura Fibra (`catalogo_direcciones.csv`)
Gobierna la cascada geográfica en el CRM Evergent para FTTH:

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `Ubicacion` | String | Llave foránea de selección en UI | `Caracas` |
| `Estado` | String | Entidad federal oficial | `Distrito Capital` |
| `Ciudad` | String | Ciudad homologada | `Caracas` |
| `Municipio` | String | Municipio del CRM | `Libertador` |
| `Parroquia` | String | Parroquia censal | `El Recreo` |
| `Codigo_Postal` | String | Código postal postal venezolano | `1050` |
| `Edificio_Casa` | String | Complemento de dirección | `Torre Credicard` |

### 2.3. Catálogo de Planes Streaming OTT (`catalogo_ott.csv`)
Regula los paquetes B2C en la tienda web de SimpleTV:

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `Identificador` | String | Nombre visible en UI de GIDEON | `Diamante`, `Oro Cine (HBO)` |
| `Paquete` | String | Paquete base reconocido por selector | `Diamante`, `Oro`, `Lite` |
| `Variante` | String | Complemento o variante en modal | `Estándar`, `Incluye HBO` |

### 2.4. Catálogo de Direcciones OTT (`catalogo_direcciones_ott.csv`)
Gobierna los menús desplegables de facturación en la tienda web OTT:

| Campo | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `Ubicacion` | String | Nombre de plaza en UI | `Caracas` |
| `Estado` | String | Estado para dropdown web | `Distrito Capital` |
| `Ciudad` | String | Ciudad en dropdown | `Caracas` |
| `Municipio` | String | Municipio en dropdown | `Libertador` |
| `Zona` | String | Sector o zona urbana | `Sabana Grande` |
| `Codigo_Postal` | String | Código postal | `1050` |

---

## 3. Esquema de Configuración del Sistema (`config_gideon.json`)

Archivo de control operativo del motor. No debe incluir secretos de producción sin cifrar:

```json
{
    "agente_id": "Kevin",
    "prefijo_email": "CAMtestO_Fibrastest",
    "prefijo_email_ott": "CAMBIALOT_OTT",
    "usuario_login": "TestSebastian",
    "password_login": "I4FiJJ02aPY0af2",
    "hilos_simultaneos": 2,
    "hilos_simultaneos_ott": 1,
    "modo_headless": false,
    "dominio_email": "maildrop.cc",
    "tema_apariencia": "Dark",
    "modo_ejecucion": "completo",
    "url_google_sheet": "https://docs.google.com/spreadsheets/d/..."
}
```

### Definición de Parámetros:
- `agente_id`: Identificador del operador responsable para auditoría en Google Sheets.
- `prefijo_email` / `prefijo_email_ott`: Prefijos para evitar colisiones de buzón entre operadores.
- `usuario_login` / `password_login`: Credenciales QA del CRM Evergent.
- `hilos_simultaneos`: Workers en paralelo para FTTH (1 a 4).
- `hilos_simultaneos_ott`: Forzado estrictamente a `1` por política anti-bloqueo y pago asistido.
- `modo_headless`: Activa Chromium sin cabecera gráfica (`true`/`false`).
- `dominio_email`: Dominio para recepción de OTP (`maildrop.cc`).
- `tema_apariencia`: Tema de la GUI (`Dark`/`Light`).
- `modo_ejecucion`: `"completo"` (hasta contrato/pago) o `"manual"` (hasta paso 3).
- `url_google_sheet`: Endpoint de la hoja de cálculo centralizada para sincronización Cloud.

---

## 4. Integración Cloud: Google Sheets (`core/sync_sheets.py`)

La sincronización en la nube implementa la tecnología **Smart Scan Anti-Duplicados**:
1. Lee los correos ya persistidos en la columna B de la hoja de cálculo.
2. Compara con los registros locales de `cuentas_creadas.csv`.
3. Sincroniza únicamente las cuentas en estado exitoso que no existan previamente en la nube.
4. Mapeo de columnas en Google Sheets:
   - **Columna A:** Fecha / Hora
   - **Columna B:** Correo Electrónico
   - **Columna C:** Contraseña estándar
   - **Columna D:** Estado / Ciudad
   - **Columna E:** Código Cliente / Contrato Evergent
   - **Columna F:** Documento / RIF
   - **Columna G:** Tasa IVA
   - **Columna H:** Plan Base
   - **Columna I:** Equipo / Addon
   - **Columna J:** Resultado (`Exitoso`)
   - **Columna K:** Agente Responsable (`agente_id`)
