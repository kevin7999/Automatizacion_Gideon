# Historial de Cambios (Changelog) - G.I.D.E.O.N.

Este documento registra la evolución del software, documentando las nuevas características y mejoras implementadas a lo largo de su ciclo de vida.

## [v3.4.2_TEST] - 2026-09-09
### Nuevas Funcionalidades y Mejoras
- **Modo Selector de Creación:** Se añadió la opción de configurar el modo de ejecución: creación de cuenta completa o ejecución parcial controlada hasta el Paso 3 (Datos adicionales y contacto).
- **Protección de Concurrencia de Botones:** Bloqueo cruzado de controles en la interfaz gráfica durante la ejecución de tareas para evitar colisiones operativas y dobles clics.
- **Optimización de Lectura OTP (Paso 5):** Implementación de espera activa (polling dinámico) de hasta 15 segundos sobre la pantalla de código OTP en CRM Evergent, evitando lecturas nulas o fallos tempranos (`33333`).
- **Retención de Catálogos:** Integración de los catálogos vigentes de planes y direcciones homologadas en la entrega de distribución limpia.

---

## [v3.4] - 2026-09-04
### Mejoras (Enhancements)
- **Extracción de N° de Cliente:** Se incorporó la captura automática del ID del cliente desde el formulario de confirmación OTP durante el Paso 5 de la automatización.
- **Historial Avanzado (Date Picker Moderno):** Se reemplazó el menú desplegable tradicional de fechas por un **Calendario Nativo CustomTkinter** (`ui/calendario.py`), permitiendo a los operadores seleccionar una fecha de manera visual en una interfaz moderna, robusta y con dark-mode, solucionando los problemas de escalabilidad y los cierres abruptos (bugs de foco).
- **Refactorización de Interfaz (Tabla de Historial):** 
  - Se agregó una nueva columna dedicada "🪪 N° Cliente".
  - Se eliminó la columna "Documento / RIF" para priorizar información más relevante sin saturar la vista.
  - Se reajustaron y optimizaron los anchos de todas las columnas (sumando un total de 1390px), mejorando el espaciado y permitiendo el uso de la barra de desplazamiento horizontal.
- **Lógica de Copiado Inteligente:** Al usar el botón "Copiar Correo(s)" o su atajo en el historial, el sistema ahora da prioridad a copiar el **N° de Cliente**. Para registros antiguos que no tengan este ID, el sistema automáticamente copiará el correo electrónico como respaldo.
- **Compatibilidad con Evidencias:** La apertura de carpetas de evidencias (doble clic) se mantuvo ligada al correo electrónico (mailbox), garantizando que las evidencias guardadas anteriormente (y las futuras) sigan funcionando sin interrupciones.
- **Identidad Visual (Branding):** Se integró el logo oficial de la empresa (`logo.jpg`). Ahora aparece de forma nativa como el icono principal de la ventana (en la barra de tareas y cabecera de G.I.D.E.O.N.) sin bordes blancos.

### Componentes Nuevos
- Se desarrolló desde cero un componente de calendario visual interactivo (`ModernCalendar`) integrado perfectamente con la estética oscura y naranja (CustomTkinter) del proyecto.

---

## [v3.3] - 2026-09-04 (Versión Base de Referencia)
### Mejoras (Enhancements)
- Se consolidó la estructura del "Centro de Reportes" y la tabla estilo Treeview.
- Se implementaron tarjetas KPI superiores con iconos modernos (Totales, Exitosos, Tasa, Errores).
- Se estabilizó la cola de automatización y el guardado de evidencias (`Evidencias_QA`).
