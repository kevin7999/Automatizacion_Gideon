# 🏗️ Arquitectura de Flujos de G.I.D.E.O.N. 4.0 Oficial

El sistema orquesta el aprovisionamiento automatizado mediante procesos independientes ejecutados en instancias aisladas de Chromium gestionadas por **Playwright** (`sync_playwright`). El núcleo operativo soporta tres pipelines: **FTTH CRM (Evergent)**, **eCommerce B2C (OTT Streaming)** y **Sincronización Cloud (Google Sheets)**.

---

## 1. Diagrama Macro de Arquitectura y Orquestación

```mermaid
graph TD
    %% Núcleo UI
    UI[🖥️ G.I.D.E.O.N. 4.0 GUI - CustomTkinter] -->|Encola Lotes| Router{Módulo Operativo}

    %% Pipeline FTTH CRM
    Router -->|Multihilo Concurrente: 1-4 Workers| FTTH_Engine[⚡ Worker FTTH CRM]
    subgraph FTTH [Pipeline FTTH CRM - Evergent]
        F0[P0: Autenticación CRM] --> F1[P1: Datos Básicos e Identidad]
        F1 --> F2[P2: Dirección y Cobertura Geográfica]
        F2 --> F3[P3: Validación / Contacto Adicional]
        F3 --> F4[P4: Selección de Paquete Fibra]
        F4 --> F4_2[P4.2: Addons & Equipos]
        F4_2 --> F5[P5: Interceptación y Confirmación OTP]
        F5 --> F_Eval{¿OTP Válido?}
    end
    FTTH_Engine --> F0
    F_Eval -->|Fallo / Timeout 60s| F_Error[Fallo: Registro en CSV & Reintento]
    F_Eval -->|Éxito| F_OK[Cuenta FTTH Creada con Éxito]

    %% Pipeline OTT Streaming
    Router -->|Mono-hilo Estricto: 1 Worker| OTT_Engine[🎬 Worker eCommerce OTT]
    subgraph OTT [Pipeline eCommerce B2C - Tienda SimpleTV Streaming]
        O1[P1: Iniciar Navegador & Sesión] --> O2[P2: Selección de Plan OTT / Combo Diamante]
        O2 --> O3[P3: Registro Simpletv+ - Datos Básicos]
        O3 --> O4[P4: Validar OTP - Maildrop Polling]
        O4 --> O_OTP{¿Código 6 Dígitos?}
        O_OTP -->|No / Timeout 90s| O_Error[Fallo: Debug Screenshot & Error]
        O_OTP -->|Sí| O5[P5: Carrito y Contrato - Cédula & Checkbox Idempotente]
        O5 --> O6[P6: Dirección de Facturación]
        O6 --> O7[P7: Datos Adicionales]
        O7 --> O8[P8: Aceptación de Documentos]
        O8 --> O_Wait((🔔 Alerta Sonora: Espera Pago TDC))
        O_Wait -.->|Operador realiza Pago y cierra Navegador| O_OK[Cuenta OTT Creada con Éxito]
    end
    OTT_Engine --> O1

    %% Persistencia y Nube
    F_OK --> Storage[(📂 Persistencia Local: CSV & JSON)]
    O_OK --> Storage
    F_OK --> Evidencias[📸 Evidencias QA Fotográficas]
    O_OK --> Evidencias

    %% Sincronización Google Sheets
    UI -->|Botón Inferior Derecho| CloudSync[☁️ Smart Scan Sync - Google Sheets]
    Storage --> CloudSync
    CloudSync --> GSheets[(📊 Hoja de Cálculo Centralizada Google)]
```

---

## 2. Detalle Exhaustivo del Pipeline OTT (Streaming B2C: P1 a P8)

A diferencia de los flujos de prueba simplificados, el worker en producción de OTT ([`automation/worker_ott.py`](file:///c:/Users/KGarcia.Pasante/Music/GIDEON%203.1/GIDEON/automation/worker_ott.py)) ejecuta **8 pasos rigurosos y cronometrados**:

```mermaid
sequenceDiagram
    autonumber
    actor Operador
    participant GUI as GIDEON UI (eCommerce B2C)
    participant Worker as Worker OTT (Playwright)
    participant Tienda as Tienda SimpleTV (React/Next)
    participant Mail as Buzón Maildrop (Asíncrono)
    participant Banco as Pasarela de Pago TDC

    GUI->>Worker: Despacha tarea (1 hilo)
    Worker->>Tienda: P1: Navega a catálogo streaming
    Worker->>Tienda: P2: Localiza y clica botón de plan (Regex Combo Diamante/Oro/Lite)
    Worker->>Tienda: P3: Modal Datos Básicos (Nombre, Apellido, Teléfono, Submit OTP)
    Worker->>Mail: P4: Polling de bandeja (15 intentos x 4s)
    Mail-->>Worker: Retorna código numérico 6 dígitos
    Worker->>Tienda: P4: Inyecta dígitos en otp.0 - otp.5 y valida formulario
    Worker->>Tienda: P5: Clica Continuar en Carrito -> Despliega modal 'Datos básicos'
    Worker->>Tienda: P5: Inyecta Cédula en DOM, omite clientType disabled, asegura checkbox idempotente
    Worker->>Tienda: P6: Llena Estado, Ciudad, Municipio y Zona en cascada
    Worker->>Tienda: P7: Llena teléfono secundario y campos demográficos
    Worker->>Tienda: P8: Marca aceptación de documentos de forma idempotente
    Worker->>Tienda: P8: Clica Aceptar -> Transiciona a Pasarela Bancaria
    Worker->>Operador: 🔔 Emite beep continuo y mantiene ventana abierta
    Operador->>Banco: Ingresa TDC y confirma el pago
    Operador->>Worker: Cierra la ventana del navegador
    Worker->>GUI: Certifica Éxito (Pendiente Pago) y registra en CSV maestro
```

---

## 3. Detalle del Ciclo de Interceptación OTP (Maildrop Engine)

La validación por OTP en [`automation/crm_helpers.py`](file:///c:/Users/KGarcia.Pasante/Music/GIDEON%203.1/GIDEON/automation/crm_helpers.py) y [`automation/worker_ott.py`](file:///c:/Users/KGarcia.Pasante/Music/GIDEON%203.1/GIDEON/automation/worker_ott.py) opera con un bucle de tolerancia asíncrona:

```mermaid
flowchart TD
    O1[Apertura de Contexto Maildrop Aislado] --> O2{Carga de Página Buzón}
    O2 -->|Timeout 30s| Falla1[Error de Red: Maildrop Inaccesible]
    O2 -->|Éxito| O3[Inicia Bucle de Polling: Máximo 15 Reintentos]
    O3 --> O4[Verificación de Cancelación: ¿cancel_event activo?]
    O4 -- Sí --> FallaCancel[Aborto Inmediato por el Operador]
    O4 -- No --> O5{¿Llegó Correo Transaccional?}
    O5 -- Sí --> O6[Abre Mensaje y Extrae Texto HTML / Iframes]
    O5 -- No --> O7[Pausa de 4s con Recarga de Buzón]
    O7 --> O8{¿Reintentos < 15?}
    O8 -- Sí --> O4
    O8 -- No --> FallaTimeout[Timeout: OTP No Entregado tras 90s]
    O6 --> O9[Aplica Regex Contextual: Código 6 Dígitos]
    O9 --> O10{¿Match Numérico Válido?}
    O10 -- Sí --> O11[Retorna OTP y Cierra Pestaña Maildrop]
    O10 -- No --> O7
```

---

## 4. Arquitectura de Sincronización Cloud (Smart Scan Google Sheets)

Para evitar duplicaciones y colisiones al sincronizar desde múltiples computadoras de operadores hacia una misma hoja de cálculo:

```mermaid
flowchart LR
    CSV[(cuentas_creadas.csv)] --> Scanner[Smart Scan Engine]
    GSheet[(Google Sheets Central)] -->|Descarga Columna B: Correos Previos| Scanner
    Scanner --> Filter{¿Correo ya existe en Columna B?}
    Filter -- Sí --> Skip[Ignora Registro: Anti-Duplicado]
    Filter -- No --> Validate{¿Estado es Exitoso?}
    Validate -- Sí --> Append[Añade Fila con Mapeo A-K e ID Agente]
    Validate -- No --> Skip
    Append --> GSheet
```

---

## 5. Decisiones Técnicas y Justificación de Arquitectura

1. **Aislamiento Multihilo de la GUI:** Todo proceso de Playwright se ejecuta dentro de un hilo secundario (`threading.Thread` o `ThreadPoolExecutor`). La interfaz de CustomTkinter **únicamente** recibe eventos a través de `self.after(0, callback)` para evitar el congelamiento de la ventana principal.
2. **Desacoplamiento de Monitores de Progreso:** A partir de la versión 4.0, FTTH CRM y eCommerce OTT poseen paneles gráficos y estructuras de datos de cronómetro completamente independientes (`frame_monitor_hilos` vs `frame_monitor_hilos_ott`).
3. **Idempotencia en Checkboxes:** Todos los checkboxes en formularios React se validan con la función [`asegurar_checkbox`](file:///c:/Users/KGarcia.Pasante/Music/GIDEON%203.1/GIDEON/automation/worker_ott.py), la cual evalúa `is_checked()` antes de interactuar, erradicando el error de "doble toggle" que desmarcaba la declaración de datos.
4. **Resiliencia ante Elementos Deshabilitados:** Los selectores con atributo `disabled` (como el tipo de cliente predeterminado en la tienda online) son detectados preventivamente con `is_enabled()`, omitiendo los timeouts de 45 segundos de Playwright.
