# 📖 Manual de Usuario - G.I.D.E.O.N. 3.1

Bienvenido a **G.I.D.E.O.N. 3.1**, la plataforma automatizada con interfaz visual para la creación masiva y multihilo de cuentas de Simplefibra en el CRM. Este manual está diseñado para guiarte en su uso paso a paso.

---

## 1. Inicio de la Aplicación
Para iniciar el sistema, simplemente abre tu terminal o consola en la carpeta `Migracion_GIDEON` y ejecuta:
```bash
python main.py
```
Al instante, se abrirá la interfaz visual en modo oscuro.

---

## 2. Pestaña Principal: Centro de Control
Aquí es donde armas tu lista de trabajo y das la orden de ejecución.

### A. Preparar la Cola de Cuentas
Tienes varias formas de decirle a Gideon qué cuentas debe crear:
1. **De forma Manual:** 
   - En la sección lateral izquierda, selecciona si el cliente es Persona Natural o Jurídica.
   - Selecciona la Ubicación y el Plan (Wifi 5, Wifi 6, Compra, Alquiler, etc).
   - Escribe la cantidad y pulsa **"➕ Agregar a la Cola"**. Verás cómo aparecen en la lista central.
2. **Usando Presets (Rápido):** 
   - Usa el menú "Seleccionar Preset..." para cargar instantáneamente lotes enteros de cuentas mezcladas con solo un clic.
3. **Guardar/Cargar tu propia lista:** 
   - Si armaste una cola de 50 cuentas y quieres repetirla mañana, pulsa "Guardar JSON". Cuando vuelvas, pulsas "Cargar JSON" y ¡listo!

### B. Ajustar la Velocidad (Concurrencia)
- Abajo a la izquierda de la cola verás la opción **Concurrencia**. Esto define cuántos navegadores invisibles trabajarán al mismo tiempo. 
- Si pones "3", Gideon creará 3 cuentas simultáneamente. Ajusta este número según la capacidad de tu internet y PC.

### C. ¡Iniciar y Monitorear! 🚀
Al pulsar **🚀 INICIAR PROCESAMIENTO MASIVO**:
- **Tarjetas de Hilos (NUEVO):** Arriba de la consola de texto, aparecerán pequeñas tarjetas deslizables. Cada tarjeta es una cuenta en tiempo real. 
- **Cronómetro ⏱️:** Verás exactamente en qué paso está el bot (Ej. "Paso 4") y cuántos minutos/segundos lleva de vida esa cuenta.
- **Colores Mágicos:** 
  - 🟠 **Naranja/Gris:** Trabajando a toda máquina.
  - 🟢 **Verde:** ¡Cuenta creada con éxito!
  - 🔴 **Rojo:** Falló (por caída del CRM u otro factor).

- **Consola Pro:** La gran caja negra debajo te relatará como un locutor de radio exactamente qué clics y pasos está haciendo cada hilo por detrás.

### D. Reintentos Automáticos y Manuales
- **Auto-reintento (Anti-Lag):** Si el CRM de la web se pone superlento y no carga la lista de routers, Gideon es lo suficientemente listo para detectarlo. Automáticamente hará un "F5" (Recarga de página) por dentro y volverá a intentar él solo, sin molestarte.
- **Reintento Manual:** Si al finalizar el lote gigante algunas cuentas quedaron en Rojo, verás que el botón naranja se transforma en **🔁 Reintentar (X)**. Púlsalo para que esas cuentas rebeldes vuelvan a la cola y les des un segundo round.

---

## 3. Pestaña: Historial & Reportes
- Si te vas a esta segunda pestaña, verás una tabla con el registro resumido de tus victorias y fallos.
- **¡Tus datos están a salvo!** Toda la información crítica (Correos generados, Contraseñas, Cédulas ficticias, RIFs y Tiempos de ejecución) se guardan en el archivo Excel/CSV llamado `cuentas_creadas.csv` en la carpeta raíz. ¡Allí está todo!

---

## 4. Directorio de Evidencias Fotográficas 📸 (QA)
Por cada cuenta que pase por Gideon, él tomará una fotografía como prueba para QA:
- **Cuentas Exitosas:** Las capturas con el número de orden final se guardan en la carpeta `Evidencias_QA/`.
- **Cuentas Fallidas:** Si algo explotó en el CRM (se cayó la web, no cargó un botón), Gideon le toma una foto al error y la guarda en `logs/screenshots/`. Si ves una cuenta roja, puedes ir a esta carpeta y ver la foto exacta de qué pasaba en el CRM en ese momento.

---

## 5. Recomendaciones de Uso
- No muevas nada en el archivo `catalogo_planes.csv` a menos que sepas que el proveedor cambió oficialmente el nombre de un router o promoción.
- Evita interrumpir la conexión a internet de la máquina mientras las tarjetas naranjas estén activas.
- Si presionas `Cancelar`, los hilos terminarán lo que estén haciendo y luego se detendrán ordenadamente.
