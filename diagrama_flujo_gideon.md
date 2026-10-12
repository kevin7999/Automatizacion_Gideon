## Arquitectura de Flujos de G.I.D.E.O.N.

El sistema orquesta la creación masiva de cuentas mediante procesos aislados inyectados en navegadores Chromium (`playwright`). Existen dos pipelines principales: **FTTH (Fibra)** y **OTT (Streaming)**.

### Diagrama de Secuencia y Estados

```mermaid
graph TD
    %% Inicialización
    A[Inicio: Orquestador UI] -->|Encola Tareas| B{Módulo Seleccionado}

    %% FLUJO FTTH
    B -->|Multihilo| C[Worker FTTH]
    subgraph FTTH [Flujo Automatizado FTTH]
        C1[Paso 0: Login CRM] --> C2[Paso 1: Datos Básicos e Identidad]
        C2 --> C3[Paso 2: Dirección y Cobertura]
        C3 --> C4[Paso 3: Validación / Adicional]
        C4 --> C5[Paso 4: Selección de Paquete Fibra]
        C5 --> C6[Paso 4.2: Addons]
        C6 --> C7[Paso 5: Recepción OTP / Confirmación]
        C7 -->|Polling a Maildrop| C8{Validación OTP}
    end
    C --> C1
    C8 -->|Timeout / Falla| C9[Fallo: Regreso a Cola]
    C8 -->|Éxito| C10[Cuenta Creada Exitosamente]

    %% FLUJO OTT
    B -->|Mono-hilo| D[Worker OTT]
    subgraph OTT [Flujo Semi-Asistido OTT]
        D1[Paso 0: Login CRM] --> D2[Paso 1: Datos y Plan OTT]
        D2 --> D3[Paso 2: Dirección OTT]
        D3 --> D4[Paso 3: Validación OTP]
        D4 -->|Polling a Maildrop| D5{Código Válido?}
        D5 -->|Éxito| D6[Paso 4: Transición a Pasarela de Pago]
        D6 --> D7((Alerta Sonora / Espera))
        D7 -.->|Acción Manual Requerida| D8[Pago TDC Ingresado por Operador]
    end
    D --> D1
    D5 -->|Timeout / Falla| C9
    D8 -->|Cierre de Navegador| C10

    %% Cierre y Persistencia
    C10 --> E[(Historial CSV / JSON / Google Sheets)]
    C10 --> F[Captura de Evidencia Fotográfica QA]

### Detalle de Ciclo de Interceptación OTP (Maildrop)
```mermaid
flowchart TD
    O1[Apertura Buzón Maildrop] --> O2{Carga de Bandeja}
    O2 -->|Timeout 60s| Falla[Fallo de Conexión]
    O2 -->|Éxito| O3[Inicia Polling: Máximo 15 Reintentos]
    O3 --> O4[Evaluación de Ciclo: intento < 15]
    O4 -->|Sí| O5[Detecta Correo 'Bienvenido a Simplefibra' / Mensajes Nuevos]
    O4 -->|No| Falla2[Timeout: OTP No Recibido en ~60-90s]
    
    O5 -->|Correo Encontrado| O6[Abre Correo y Espera 2s]
    O5 -->|Bandeja Vacía| O7[Espera 4s y Recarga Página]
    
    O7 --> O4
    
    O6 --> O8[Extrae Texto Visible HTML/Iframes]
    O8 --> O9{Regex Match: Código 6 Dígitos}
    O9 -->|Sí| O10[Retorna Código OTP]
    O9 -->|No| O7
```
```

## Explicación Táctica
1. **Concurrencia vs Bloqueos:** El pipeline FTTH ejecuta **multihilo total**, creando múltiples cuentas al mismo tiempo. El pipeline OTT es **mono-hilo estricto** para evitar mecanismos anti-spam del proveedor y debido a la necesidad de interacción manual al final.
2. **Generación de Identidades:** Los nodos de *Datos Básicos* consumen `core.generadores` (Cédulas, RIF, Teléfonos de VZLA) en tiempo de ejecución, evitando la colisión de datos en hilos paralelos.
3. **Manejo del Cuello de Botella (OTP):** Ambos flujos utilizan sincronización asíncrona mediante un bucle de polling progresivo sobre buzones de `maildrop.cc`. El sistema ejecuta un ciclo de **hasta 15 intentos**, esperando **4 segundos entre cada recarga** (aprox. 60 a 90 segundos de tolerancia global). Para extraer el código, utiliza 2 capas de RegEx (`PATRON_CONTEXTUAL` y fallback a 6 dígitos consecutivos) escaneando el body principal y los iFrames del correo.
4. **Fricción por Pago (Control Dual OTT):** En el flujo de Streaming, el bot realiza el 90% del trabajo pesado y se detiene tácticamente en la pasarela de pago. Se emite una alerta auditiva (`\a`) y delega el control exacto en el momento del pago con tarjeta.

## Open Questions
¿Requiere el usuario final o tu equipo que se documente el sub-flujo de rescate/reintentos cuando un worker falla por "Timeout de Selector", o con la vista macro de este plan es suficiente para su reporte?

## User Review Required
Este diagrama resume el comportamiento lógico implementado en el sistema real. Puedes utilizar el botón "Proceed" si das por aprobada esta documentación técnica y no necesitas adaptarla a otros formatos.
