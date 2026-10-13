# 🤖 G.I.D.E.O.N. 4.0 Oficial - Simplefibra FTTH & OTT Automation Hub

**G.I.D.E.O.N.** (*Global Intelligent Deployment & Evergent Order Network*) es una plataforma de automatización de procesos mediante software (RPA) equipada con una interfaz gráfica moderna SaaS desarrollada en CustomTkinter. Diseñada para la creación, aprovisionamiento y gestión masiva de cuentas de telecomunicaciones para **Simplefibra (FTTH)** en el CRM Evergent y planes de streaming **OTT (Simpletv+)** en la tienda en línea.

---

## 📚 Documentación Técnica y de Auditoría

- 📖 **[Manual de Usuario para Operadores](MANUAL_USUARIO.md)** - Guía operativa paso a paso de la interfaz y procesos.
- 🏗️ **[Arquitectura y Diagramas de Flujo](diagrama_flujo_gideon.md)** - Diagramas de secuencia Mermaid, pipeline OTT (P1 a P8) y motor de OTP.
- 📊 **[Diccionario de Datos y Catálogos](docs/DICCIONARIO_DATOS_Y_CATALOGOS.md)** - Especificación técnica de los 13 campos del CSV maestro, catálogos y esquemas.
- 🛡️ **[Protocolo de Seguridad y Auditoría QA](docs/PROTOCOLO_AUDITORIA_Y_SEGURIDAD.md)** - Políticas de evidencias fotográficas, resiliencia OTP y cero secretos.
- 📜 **[Historial de Cambios (Changelog)](CHANGELOG.md)** - Evolución del software hasta la versión **4.0 Oficial**.

---

## 📁 Estructura del Proyecto

```text
GIDEON/
│
├── core/                               # 📦 CAPA DE NEGOCIO Y DATOS
│   ├── config.py                       # Carga de config_gideon.json, mutexes y credenciales
│   ├── generadores.py                  # Generación sintética determinística de Cédulas, RIFs y Nombres VE
│   ├── catalogos.py                    # Carga dinámica de planes y coberturas geográficas desde CSV
│   ├── correlativos.py                 # Persistencia en cuentas_creadas.csv y contadores
│   └── sync_sheets.py                  # Motor Smart Scan para sincronización con Google Sheets
│
├── automation/                         # 🤖 CAPA DE AUTOMATIZACIÓN (PLAYWRIGHT)
│   ├── crm_helpers.py                  # Utilidades y selectores robustos para React y polling de OTP
│   ├── worker.py                       # Orquestador multihilo para el flujo FTTH CRM (Evergent)
│   ├── worker_ott.py                   # Orquestador optimizado P1-P8 para planes streaming OTT
│   └── worker_ftth_ecommerce.py        # Orquestador para el flujo de compra FTTH en tienda web
│
├── ui/                                 # 🎨 CAPA VISUAL (CUSTOMTKINTER MODERNO)
│   ├── app.py                          # Controlador principal de la ventana y eventos
│   ├── theme.py                        # Paleta cromática corporativa, fuentes y estilos
│   ├── calendario.py                   # Date picker visual para filtrado interactivo de fechas
│   └── components/                     # Componentes modulares reutilizables
│       ├── sidebar.py                  # Barra lateral de navegación colapsable
│       ├── console_log.py              # Terminal de log interactiva con scroll elástico
│       └── stepper.py                  # Indicador visual de progreso de pasos
│
├── docs/                               # 📋 DOCUMENTACIÓN TÉCNICA FORMAL
│   ├── DICCIONARIO_DATOS_Y_CATALOGOS.md # Diccionario formal de datos y catálogos
│   └── PROTOCOLO_AUDITORIA_Y_SEGURIDAD.md # Runbook de auditoría, evidencias y seguridad
│
├── main.py                             # 🚀 Punto de entrada oficial de la aplicación
├── catalogo_planes.csv                 # Catálogo dinámico de planes Fibra FTTH
├── catalogo_direcciones.csv            # Catálogo de cobertura geográfica Fibra FTTH
├── catalogo_ott.csv                    # Catálogo dinámico de planes Streaming OTT
├── catalogo_direcciones_ott.csv        # Catálogo de cobertura geográfica OTT
├── config_gideon.json                  # Archivo de configuración operativa del sistema
└── requirements.txt                    # Dependencias y librerías del proyecto
```

---

## 🚀 Requisitos e Instalación

### Requisitos Previos:
- Python 3.10 o superior (compatible con Windows 10/11).
- Navegador Chromium (gestionado por Playwright).

### Instalación de Dependencias:
```bash
# 1. Instalar librerías de Python
pip install -r requirements.txt

# 2. Descargar los navegadores de Playwright
playwright install chromium
```

### Ejecución:
```bash
python main.py
```

---

## 🌟 Módulos Principales de la Suite

1. **FTTH CRM:** Creación masiva y concurrente de cuentas de Fibra Óptica directamente sobre el CRM Evergent con soporte de 1 a 4 hilos en paralelo.
2. **eCommerce B2C:** Creación de cuentas en la tienda en línea de SimpleTV para planes de Streaming OTT (Combo Diamante, Oro, Platino, Lite) y compras FTTH. Opera estrictamente a 1 hilo con control asistido en la pasarela de pago.
3. **Historial Operativo:** Tabla unificada con filtro interactivo por búsqueda global, servicio, estado y calendario. Incluye botón inferior derecho para **Sincronización a Google Sheets** con algoritmo anti-duplicados.
4. **Configuración:** Administración centralizada de credenciales QA, ID de agente para reportes y parámetros de concurrencia.
