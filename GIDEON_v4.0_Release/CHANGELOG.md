# Historial de Cambios (Changelog) - G.I.D.E.O.N.

Este documento registra la evolución técnica, arquitectónica y operativa del software G.I.D.E.O.N. (*General Interface for Data Entry & Operations Navigator*).

---

## [v4.0.0 Oficial] - 2026-10-12

### 🚀 Nuevas Funcionalidades y Arquitectura Visual SaaS
- **Rediseño Integral de la Interfaz:** Implementación de arquitectura SaaS moderna con barra lateral colapsable (`Sidebar`), barra de navegación superior (`Top Navbar`) con píldora de estado operativo en tiempo real y banner institucional `v4.0.0 Oficial`.
- **Desacoplamiento Estricto de Monitores Multihilo:** Aislamiento completo de los contenedores de progreso en tiempo real entre los módulos FTTH CRM y eCommerce B2C. Se erradicó la fuga de eventos y el reflejo cruzado de hilos en pestañas inactivas.
- **Sincronización en la Nube con Google Sheets (`core/sync_sheets.py`):**
  - Botón integrado en la esquina inferior derecha de la pestaña Historial (`☁️ Sincronizar a Google Sheets`) para optimización ergonómica del espacio.
  - Algoritmo **Smart Scan**: Lectura preliminar del rango remoto para prevenir registros duplicados contrastando Cédula y Timestamp.
  - Formato homologado de auditoría que exporta tanto cuentas exitosas como fallidas con detalle de error.

### ⚡ Optimización de Rendimiento y Resiliencia en Workers
- **Aceleración Crítica en Worker OTT (`automation/worker_ott.py`):**
  - **Paso P2 (Selección de Plan/Variante):** Reducción de latencia de ~58 segundos a 7-8 segundos mediante el reemplazo de esperas pasivas por selectores resilientes directos (`text=Combo Diamante`, clases jerárquicas y matching difuso insensible a mayúsculas).
  - **Paso P5 (Modal de Contrato y Cédula):** Detección temprana mediante comprobación de visibilidad directa del campo de cédula, reduciendo el timeout de 45s a ~3.8 segundos.
- **Soporte para Combo Diamante:** Incorporación de la variante comercial "Combo Diamante" y homologación de selectores dinámicos ante cambios de interfaz del portal B2C.

### 🛡️ Blindaje de Seguridad y Auditoría Técnica
- **Diccionario de Datos y Catálogos (`docs/DICCIONARIO_DATOS_Y_CATALOGOS.md`):** Especificación formal del esquema de 13 columnas de `cuentas_creadas.csv`, los 4 catálogos CSV maestros, los 12 parámetros de configuración y el mapeo a Google Sheets.
- **Protocolo de Auditoría y Seguridad (`docs/PROTOCOLO_AUDITORIA_Y_SEGURIDAD.md`):** Políticas de Cero Secretos Hardcodeados, generación de identidades sintéticas (PII protegida), protocolo estricto de captura de evidencias fotográficas (`Evidencias_QA_*` y `logs/screenshots/`), protocolo crítico OTP y runbook de recuperación de desastres.
- **Actualización de Diagramas de Flujo (`diagrama_flujo_gideon.md`):** Modelado visual en Mermaid de los 8 pasos reales de OTT (P1 a P8), el ciclo de intercepción Maildrop y la concurrencia multihilo de FTTH.

---

## [v3.5.0] - 2026-09-25

### Nuevas Funcionalidades
- **Módulo eCommerce B2C / OTT:** Incorporación del flujo de contratación de streaming con concurrencia unitaria controlada (1 hilo) y procedimiento de pago asistido.
- **Catálogos Dedicados OTT:** Integración de `catalogo_ott.csv` y `catalogo_direcciones_ott.csv` con interfaz de edición directa y recarga en caliente.
- **Aislamiento de Evidencias:** Separación física de carpetas fotográficas: `Evidencias_QA_Fibra/` para órdenes de red fija y `Evidencias_QA_OTT/` para transacciones de streaming.

---

## [v3.4.2_TEST] - 2026-09-09

### Mejoras y Correcciones
- **Modo Selector de Creación:** Configuración de modo de ejecución: creación de cuenta completa o ejecución parcial controlada hasta el Paso 3.
- **Protección de Concurrencia de Botones:** Bloqueo cruzado de controles en la interfaz gráfica durante la ejecución de tareas para evitar colisiones y dobles clics.
- **Optimización de Lectura OTP (Paso 5 FTTH):** Polling dinámico de hasta 15 segundos sobre la pantalla de código OTP en CRM Evergent, evitando lecturas nulas o fallos tempranos.
- **Retención de Catálogos:** Integración de catálogos vigentes de planes y direcciones homologadas en la entrega de distribución.

---

## [v3.3 - v3.4] - 2026-09-04

### Mejoras Principales
- **Extracción de N° de Cliente:** Captura automática del ID de cliente desde el formulario de confirmación OTP.
- **Historial Avanzado (`ModernCalendar`):** Selector de fechas nativo CustomTkinter en modo oscuro para filtrado de registros.
- **Tabla Estilo Treeview y KPIs:** Implementación de tarjetas métricas (Totales, Éxitos, Tasa, Fallos) y reajuste de ancho de columnas a 1390px con scroll horizontal.
- **Branding Institucional:** Integración del logotipo corporativo oficial (`logo.jpg`) en la barra de tareas y cabecera de ventana.
