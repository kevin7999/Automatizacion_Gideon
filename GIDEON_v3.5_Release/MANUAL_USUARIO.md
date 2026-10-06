# 📖 Manual de Usuario - G.I.D.E.O.N. 3.5

Bienvenido a **G.I.D.E.O.N. 3.5**, la plataforma automatizada con interfaz visual para la creación masiva y multihilo de cuentas de **Simplefibra (FTTH)** y **Streaming (OTT)** en el CRM. Este manual está diseñado para guiarte en su uso paso a paso.

---

## 1. Inicio de la Aplicación
Para iniciar el sistema, simplemente abre tu terminal o consola en la carpeta de GIDEON y ejecuta:
```bash
python main.py
```
Al instante, se abrirá la interfaz visual en modo oscuro con sus respectivas pestañas superiores.

---

## 2. Operativa General (Pestañas)
La aplicación está dividida en pestañas para no mezclar los servicios:
- **Centro de Control:** Exclusivo para generar cuentas de Fibra Óptica (FTTH).
- **Control OTT:** Exclusivo para generar cuentas de los planes de Streaming (OTT).
- **Historial & Reportes:** Tabla unificada con el registro de todas las cuentas (tanto Fibra como OTT).

---

## 3. Centro de Control (Fibra Óptica FTTH)
Aquí es donde armas tu lista de trabajo para las ventas de Fibra:

### A. Preparar la Cola de Cuentas
1. **De forma Manual:** 
   - Selecciona si el cliente es Persona Natural o Jurídica.
   - Selecciona la Ubicación y el Plan de Fibra.
   - Escribe la cantidad y pulsa **"➕ Agregar a la Cola"**.
2. **Usando Presets (Rápido):** 
   - Usa el menú "Seleccionar Preset..." para cargar lotes enteros con un clic.
3. **Guardar/Cargar tu propia lista:** 
   - Pulsa "Guardar JSON" para respaldar una cola y "Cargar JSON" para retomarla luego.

### B. Ejecución Multihilo
- En FTTH puedes ajustar la **Concurrencia**. Si pones "3", Gideon creará 3 cuentas simultáneamente en paralelo.
- Al pulsar **🚀 INICIAR PROCESAMIENTO MASIVO**, las tarjetas indicarán el estado de cada cuenta en tiempo real.

---

## 4. Control OTT (Streaming)
El módulo OTT funciona de manera muy similar, pero con consideraciones especiales por las restricciones del proveedor (evitar bloqueos anti-spam).

### A. Preparar la Cola OTT
1. Selecciona el **Plan OTT** (ej. Oro Prime, Diamante, Lite).
2. Selecciona el tipo de documento y la Ubicación. 
3. Puedes abrir y editar los catálogos de OTT presionando los botones **📦 CSV Planes** y **📍 CSV Ubicaciones**. No olvides darle a **🔄 Actualizar** después de guardar tus cambios en Excel.
4. Agrega a la cola y presiona iniciar.

### B. Proceso y Pago Manual (¡Importante!)
- **Concurrencia Limitada:** El procesamiento OTT está restringido a **1 hilo a la vez**. Esto asegura que las cuentas no sean baneadas por crear muchas simultáneamente.
- **Acción Requerida:** A diferencia de Fibra, las cuentas OTT requieren un pago con tarjeta de crédito real. GIDEON llenará todos los datos, validará el correo OTP en maildrop y **se detendrá en la pasarela de pago**, emitiendo un sonido de alerta (beep).
- En ese momento, **el navegador quedará abierto**. Tú deberás ingresar los datos de la tarjeta, completar el pago y **cerrar el navegador manualmente**. GIDEON detectará que cerraste la ventana y marcará la cuenta como exitosa.

---

## 5. Historial, Reportes y Evidencias 📸
- Si te vas a la pestaña **Historial & Reportes**, verás una tabla con el registro resumido de tus victorias y fallos de ambos servicios.
- **Archivos CSV:** Toda la información (Correos generados, Contraseñas, etc.) se guarda en `cuentas_creadas.csv`.
- **Directorio de Evidencias Fotográficas:**
  - Las capturas de éxito de Fibra se guardan en `Evidencias_QA_Fibra/`.
  - Las capturas de los pasos de OTT se guardan en `Evidencias_QA_OTT/`.
  - Las fotos de errores o caídas del CRM de Fibra van a `logs/screenshots/`.

---

## 6. Recomendaciones de Uso
- No interrumpas la conexión a internet de la máquina mientras las tareas estén activas.
- Si un hilo de Fibra falla, se habilitará el botón **🔁 Reintentar (X)** para volver a encolar las fallidas.
- En OTT, asegúrate de tener la tarjeta de crédito a la mano para cuando suene la alerta de pago.
- Si presionas `Cancelar`, los hilos terminarán lo que estén haciendo (o cerrarán el navegador) de forma ordenada.
