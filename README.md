# 🤖 G.I.D.E.O.N. 3.4 - Simplefibre FTTH Automation Hub

Esta carpeta contiene la versión **G.I.D.E.O.N. 3.4** con interfaz optimizada, tarjetas KPI ejecutivas con logos gráficos dedicados y cola de automatización limpia.

📚 **[Leer el Manual de Usuario para Operadores](MANUAL_USUARIO.md)**

---

## 📁 Estructura del Proyecto

```text
GIDEON_v3.3/
│
├── core/                               # 📦 CAPA DE NEGOCIO Y DATOS
│   ├── config.py                       # Credenciales CRM, URLs, mutexes (lock_login, etc.)
│   ├── generadores.py                  # Generación sintética de Cédulas, RIFs y Nombres VE
│   ├── catalogos.py                    # Carga y parsing de catalogo_planes.csv y direcciones
│   └── correlativos.py                 # Manejo del contador de emails y persistencia CSV/JSON
│
├── automation/                         # 🤖 CAPA DE PLAYWRIGHT Y CRM
│   ├── crm_helpers.py                  # escribir_en_react, seleccionar_opcion_mui, hacer_clic_robusto
│   ├── worker.py                       # Orquestador del flujo por hilo: crear_cuenta_individual()
│   └── steps/                          # Pasos individuales del CRM desacoplados
│       ├── paso0_login.py              # Login seguro con reuso de cookies (auth_state.json)
│       ├── paso1_datos.py              # Paso 1: Datos Básicos (Persona natural / jurídica)
│       ├── paso2_direccion.py          # Paso 2: Dirección y geolocalización en mapa
│       ├── paso3_adicional.py          # Paso 3: Contacto, vivienda y validación
│       ├── paso4_paquetes.py           # Paso 4 y 4.1: Configuración de Plan y Router
│       ├── paso4_addons.py             # Paso 4.2: Omitir Add-Ons
│       └── paso5_otp.py                # Paso 5: Maildrop, consentimiento y validación OTP
│
├── ui/                                 # 🎨 CAPA VISUAL (CUSTOMTKINTER)
│   ├── theme.py                        # Paleta corporativa (Orange & Dark), fuentes y estilos
│   └── app.py                          # Ventana AppGideon, pestañas, KPIs y despachador de hilos
│
├── main.py                             # 🚀 Punto de entrada principal
├── gui_gideon.py                       # 🔄 Wrapper de compatibilidad directa
├── catalogo_planes.csv                 # Catálogo dinámico de planes Simplefibra
├── catalogo_direcciones.csv            # Catálogo de cobertura geográfica
└── config_gideon.json                  # Configuración del sistema
```

---

## 🚀 Cómo Ejecutar

Desde esta carpeta (`Migracion_GIDEON`), puedes ejecutar cualquiera de los dos comandos:

```bash
python main.py
```
o
```bash
python gui_gideon.py
```

Ambos abrirán la interfaz completa con todas sus funcionalidades, pero respaldada por módulos independientes de entre 50 y 150 líneas cada uno.
