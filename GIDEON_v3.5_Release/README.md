# 🤖 G.I.D.E.O.N. - Simplefibra FTTH & OTT Automation Hub

Esta carpeta contiene la versión de **G.I.D.E.O.N.** equipada para manejar tanto la automatización de cuentas de **Fibra Óptica (FTTH)** como de los planes de Streaming **OTT**. Incluye una interfaz optimizada, gestión de catálogos dinámicos mediante CSV y manejo de evidencias automatizado.

📚 **[Leer el Manual de Usuario para Operadores](MANUAL_USUARIO.md)**

---

## 📁 Estructura del Proyecto

```text
GIDEON/
│
├── core/                               # 📦 CAPA DE NEGOCIO Y DATOS
│   ├── config.py                       # Credenciales CRM, URLs, mutexes
│   ├── generadores.py                  # Generación sintética de Cédulas, RIFs y Nombres VE
│   ├── catalogos.py                    # Carga dinámica de planes y direcciones (FTTH y OTT)
│   └── correlativos.py                 # Manejo del contador de emails y persistencia
│
├── automation/                         # 🤖 CAPA DE PLAYWRIGHT Y CRM
│   ├── crm_helpers.py                  # Utilidades y selectores robustos para React/MUI
│   ├── worker.py                       # Hilo orquestador para flujo FTTH
│   └── worker_ott.py                   # Hilo orquestador exclusivo para flujo OTT
│
├── ui/                                 # 🎨 CAPA VISUAL (CUSTOMTKINTER)
│   ├── theme.py                        # Paleta corporativa (Orange & Dark), fuentes y estilos
│   └── app.py                          # Interfaz principal con pestañas para Fibra y OTT
│
├── main.py                             # 🚀 Punto de entrada principal
├── gui_gideon.py                       # 🔄 Wrapper de compatibilidad directa
├── catalogo_planes.csv                 # Catálogo dinámico de planes Fibra
├── catalogo_direcciones.csv            # Catálogo de cobertura geográfica Fibra
├── catalogo_ott.csv                    # Catálogo dinámico de planes OTT
├── catalogo_direcciones_ott.csv        # Catálogo de cobertura geográfica OTT
└── config_gideon.json                  # Configuración del sistema
```

---

## 🚀 Cómo Ejecutar

Desde esta carpeta, puedes ejecutar cualquiera de los dos comandos:

```bash
python main.py
```
o
```bash
python gui_gideon.py
```

Ambos abrirán la interfaz completa con todas sus funcionalidades para operar los módulos de Fibra y OTT en paralelo o de forma individual.
