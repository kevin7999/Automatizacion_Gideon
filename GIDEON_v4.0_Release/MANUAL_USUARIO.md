# 📖 Manual de Usuario - G.I.D.E.O.N. 4.0 Oficial

Bienvenido a **G.I.D.E.O.N. 4.0 Oficial** (*General Interface for Data Entry & Operations Navigator*), la plataforma corporativa de automatización RPA con interfaz SaaS moderna para la emisión masiva y multihilo de órdenes y cuentas de **Simplefibra (FTTH CRM)** y **Streaming (eCommerce B2C / OTT)**.

Este manual detalla paso a paso la operación visual, los controles de seguridad, el procedimiento de pago asistido y la sincronización a la nube auditada.

---

## 1. Arquitectura Visual y Arranque del Sistema

### 1.1 Ejecución
Para iniciar el entorno, abra una consola de comandos en el directorio del proyecto y ejecute:
```bash
python main.py
```

### 1.2 Estructura de la Interfaz SaaS
G.I.D.E.O.N. 4.0 implementa un diseño inspirado en paneles corporativos SaaS:
- **Barra Lateral Izquierda (Sidebar):** Muestra el logotipo corporativo, el indicador de estado global y los botones de navegación entre módulos:
  - `🌐 FTTH CRM`
  - `🛒 eCommerce B2C`
  - `📊 Historial`
  - `⚙️ Configuración`
  Incluye además un botón de colapso rápido para optimizar el espacio horizontal en pantallas estándar.
- **Barra Superior (Top Navbar):** Presenta el título del módulo activo, el badge de versión (**v4.0.0 Oficial**) y la píldora de estado operativo en tiempo real (`En Espera`, `Ejecutando`, `Pausado`).
- **Área de Trabajo Central:** Paneles dinámicos desacoplados con telemetría visual, tablas de datos y consolas de registro dedicadas.

---

## 2. Módulo FTTH CRM (Fibra Óptica Masiva)

Diseñado para el aprovisionamiento masivo de servicios de fibra sobre la plataforma CRM Evergent/Salesforce con soporte multihilo.

### 2.1 Preparación de la Cola de Emisión
1. **Configuración de Datos del Servicio:**
   - **Tipo de Documento / Cliente:** Seleccione *Natural (V/E)* o *Jurídico (J/G)*.
   - **Ubicación Técnica:** Seleccione la ciudad/zona homologada del catálogo oficial.
   - **Plan de Fibra:** Seleccione la velocidad/paquete contratado.
   - **Cantidad:** Ingrese el volumen de cuentas a emitir en el lote.
2. **Carga y Guardado de Colas:**
   - Botón **"➕ Agregar a la Cola"**: Encola los elementos configurados.
   - **Presets Rápidos:** Despliegue de plantillas preconfiguradas para pruebas o lotes recurrentes.
   - **"💾 Guardar JSON" / "📂 Cargar JSON"**: Permite pausar turnos operativos exportando la cola de trabajo pendiente e importarla posteriormente sin pérdida de estado.
3. **Mantenimiento de Catálogos:**
   - Botones **"📦 CSV Planes"** y **"📍 CSV Ubicaciones"** abren los archivos locales para incorporar nuevos nodos o tarifas.
   - Botón **"🔄 Actualizar"**: Recarga los catálogos en memoria sin reiniciar la aplicación.

### 2.2 Concurrencia y Procesamiento Multihilo
- **Selector de Concurrencia:** Configure la cantidad de hilos paralelos deseados (recomendado: 1 a 4 según hardware y capacidad de red).
- **Control de Ejecución:**
  - Presione **"🚀 INICIAR PROCESAMIENTO MASIVO"**.
  - Cada hilo levantará una tarjeta de monitoreo independiente que refleja el paso actual de navegación, el tiempo transcurrido y la captura de depuración si se produce un fallo.
  - Botón **"⛔ Cancelar"**: Emite la señal de parada segura (`cancel_event`). Los navegadores activos completan o abortan limpiamente sin corromper el CSV maestro.
  - Botón **"🔁 Reintentar (X)"**: Reencola automáticamente sólo aquellas cuentas que hayan fallado por timeout o saturación de red.

---

## 3. Módulo eCommerce B2C (Streaming OTT / Combos)

Diseñado para la contratación de planes de streaming y combos sobre el portal B2C. Por restricciones de pasarelas de pago y políticas anti-spam, este módulo opera estrictamente en **concurrencia unitaria (1 solo hilo secuencial)**.

### 3.1 Flujo Operativo Automatizado (Pasos P1 a P7)
1. **Selección del Plan:** Escoja el plan en el menú desplegable (Lite, Estándar, Oro Prime, **Combo Diamante**, etc.).
2. **Configuración de Identidad:** Tipo de cliente, prefijo y ubicación técnica.
3. **Inicio de Tarea:** Presione **"🚀 Iniciar OTT"**.
4. **Ciclo Autónomo de Navegación:**
   - **P1:** Ingreso a la plataforma y apertura del catálogo.
   - **P2:** Detección y selección resiliente de variante y plan.
   - **P3:** Generación sintética y llenado del formulario de identidad y dirección.
   - **P4:** Intercepción de buzón Maildrop, extracción de código OTP (6 dígitos) y validación en portal.
   - **P5:** Confirmación de carrito y modal de contrato legal.
   - **P6:** Selección de método de pago (Tarjeta de Crédito / Débito).
   - **P7:** Aceptación obligatoria de términos y condiciones.

### 3.2 Procedimiento de Pago Asistido (Paso P8 - Obligatorio para el Operador)
A diferencia de FTTH, la emisión de OTT involucra cobros financieros reales:
1. Al llegar a la pasarela de pago, el worker entra en modo de **espera pasiva**, genera un registro en el log y emite una señal sonora (**beep**).
2. **La ventana del navegador permanecerá abierta y visible.**
3. **Acción del Operador:**
   - Introduzca el número de tarjeta, fecha de expiración y CVV directamente en la interfaz segura bancaria.
   - Complete la autenticación bancaria adicional (si aplica) y confirme el pago.
4. **Cierre y Finalización:**
   - Una vez procesado el pago exitosamente, **cierre la ventana del navegador**.
   - G.I.D.E.O.N. detectará automáticamente el evento de cierre (`page.is_closed()`), registrará la cuenta como **Éxito** en `cuentas_creadas.csv` y notificará el fin del ciclo.

---

## 4. Módulo Historial, Reportes y Auditoría

La pestaña **Historial & Reportes** consolida todas las transacciones generadas en la estación de trabajo.

### 4.1 Métricas KPI Superiores
- **Total Procesadas:** Suma histórica de órdenes registradas.
- **Exitosas:** Volumen de cuentas con alta confirmada.
- **Tasa de Éxito:** Porcentaje de efectividad del lote.
- **Fallidas:** Volumen de intentos abortados o rechazados.

### 4.2 Tabla Central y Filtros
- **Filtro de Fecha con Calendario Nativo (`ModernCalendar`):** Permite aislar emisiones por día operativo sin problemas de foco.
- **Columnas Registradas:** N° de Cliente, Fecha/Hora, Servicio (FTTH/OTT), Cédula, Nombre, Correo, Plan, Estado, Detalle.
- **Acciones Rápidas:**
  - **Copiar Correo / ID:** Copia el identificador seleccionado al portapapeles.
  - **Abrir Evidencias (Doble Clic):** Abre el explorador de Windows directamente en la carpeta con las capturas de pantalla de la cuenta seleccionada.

### 4.3 Sincronización en la Nube (Google Sheets)
- Ubicación: **Botón inferior derecho en la vista de Historial** (`☁️ Sincronizar a Google Sheets`).
- **Funcionamiento:**
  - Lee el archivo maestro local `cuentas_creadas.csv`.
  - Conecta mediante la API de Google Sheets (`credentials.json`).
  - Aplica el algoritmo **Smart Scan** para evitar duplicados en la hoja remota.
  - Publica los registros exitosos y fallidos con su respectivo ID y timestamp auditado.

---

## 5. Módulo de Configuración y Seguridad

Permite ajustar los parámetros operativos contenidos en `config_gideon.json`:
- **Credenciales CRM:** Usuario y contraseña institucional (cifrados / manejados localmente).
- **Timeouts de Red:** Margen de espera para respuestas del portal y entrega de correos OTP.
- **Modo Headless (Segundo Plano):** Habilita o deshabilita la visualización gráfica de los navegadores durante FTTH. *(Nota: En OTT el navegador siempre se muestra para permitir el pago asistido)*.
- **Switches de Notificaciones:** Habilitación de alertas audibles y logs detallados de depuración.

---

## 6. Manejo de Evidencias y Troubleshooting

| Tipo de Evidencia | Ubicación en Disco | Propósito de Auditoría |
| :--- | :--- | :--- |
| **Éxitos Fibra Óptica** | `Evidencias_QA_Fibra/<timestamp>_<email>/` | Comprobante de contrato y confirmación CRM. |
| **Éxitos / Pasos Streaming** | `Evidencias_QA_OTT/<timestamp>_<email>/` | Secuencia de pasos P1 a P7 y comprobante final. |
| **Fallos de Automatización** | `logs/screenshots/` | Capturas instantáneas con traceback del error. |

### Reglas de Operación Segura
- **No forzar el cierre de la terminal:** Si desea interrumpir una corrida masiva, utilice siempre el botón **"⛔ Cancelar"** de la interfaz gráfica.
- **Verificación de Conectividad:** Compruebe acceso a Maildrop y a las pasarelas corporativas antes de lanzar lotes de alta densidad.
- **Documentación Técnica de Referencia:**
  - Especificación de esquemas: [DICCIONARIO_DATOS_Y_CATALOGOS.md](file:///docs/DICCIONARIO_DATOS_Y_CATALOGOS.md)
  - Políticas de seguridad y PII: [PROTOCOLO_AUDITORIA_Y_SEGURIDAD.md](file:///docs/PROTOCOLO_AUDITORIA_Y_SEGURIDAD.md)
