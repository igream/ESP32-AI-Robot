# Plan de implementación: aplicaciones de verificación de la Tarea 1 y la Tarea 2

Versión 1 · 2026-11-06 · Autor: chat con Opus · Ejecutor principal: chat con Sonnet

Este plan describe dos aplicaciones, una por asignación, porque cada asignación lleva su propio reporte. Cada aplicación avanza por **etapas** en orden. Una etapa se habilita solo cuando terminan las etapas de las que depende. Entre etapas hay **puntos de control**: Fer mide, la aplicación guarda los datos y, si hace falta, Fer los comparte en el chat para revisarlos antes de seguir.

## Cómo usar este plan

- Cada paso tiene una etiqueta:
  - **[Sonnet]**: implementación con especificación cerrada.
  - **[Opus]**: revisión o decisión técnica.
  - **[Fer]**: acción física o en una cuenta externa.
- Los pasos se ejecutan en el orden de las secciones. Un paso está terminado solo cuando cumple su **criterio de terminado**.
- 🛑 **Punto de control:** detenerse, informar a Fer qué sigue y esperar sus datos o su confirmación.
- Al terminar cada paso **[Sonnet]**:
  1. Compilar (si hay firmware) con `--build-path` fuera de Google Drive.
  2. Commit con un mensaje que explique el qué y el porqué.
  3. Actualizar la casilla de este archivo y `docs/PENDIENTES.md`.
- Las rutas son relativas a la raíz del repo `ESP32-AI-Robot/`.

## Decisiones ya tomadas (2026-11-06)

| Tema | Decisión |
|---|---|
| Formato | **App Tarea 1:** página web servida por el robot (`/tarea1`), evolución de `/calibrar`. **App Tarea 2:** programa de Python en la PC, que lee el ESP32-CAM por puerto serie y por WiFi. |
| Prioridad | Primero la Tarea 1 completa y después la Tarea 2. |
| Core ESP32 | **Una sola versión para todo:** la más reciente que funcione con Edge Impulse. Primero se prueba la 3.3.12 (la actual). Si Edge Impulse falla, todo pasa a la 3.0.7 (la del video) y se recompila el firmware del robot. Ver el paso T2.5.2. |
| OLED (extra Tarea 2) | No se hace. |
| Captura del dataset | Desde la app de PC, pidiendo fotos al robot por WiFi. No se usa la librería Eloquent. |
| Subida a Edge Impulse | Con Edge Impulse CLI (`edge-impulse-uploader`). Fer inicia sesión él mismo. |
| Material del profesor | El video y los pines son referencia. Lo que importa es cumplir los objetivos de cada tarea. |
| Datos de la Tarea 1 | Se guardan **en el robot** (LittleFS) para que no dependan del navegador del celular. También se exportan a JSON/CSV y se copian al repo. |

---

# Paso 0 – Preparación común

- [x] **0.1 [Sonnet] Guardar el trabajo de `/calibrar` que no tiene commit.**
  - Archivos: `firmware/robot_esp32cam/calibracion_html.h`, cambios en `app_httpd.cpp`, `herramientas/README.md` y `docs/PENDIENTES.md`.
  - Fer ya probó la página y funciona.
  - Commit también de `docs/Asignaciones/Tarea_ESP32CAM_EdgeImpulse.docx`.
  - *Terminado:* `git status` limpio y push a `origin/main`.
- [x] **0.2 [Sonnet] Generalizar `herramientas/reporte_pdf.py`** para que reciba la ruta del Markdown como argumento.
  - Uso: `python herramientas/reporte_pdf.py docs/Tarea2/REPORTE.md`.
  - Sin argumento, debe seguir generando el de la Tarea 1.
  - El HTML temporal se crea junto al `.md` y se borra al final.
  - Agregar `docs/*/_reporte.html` a `.gitignore`.
  - *Terminado:* los dos reportes se generan.

---

# TAREA 1 – App web `/tarea1` en el robot

## Mapa de etapas y dependencias

```
E0 Medidas físicas ─────────────────────────────┐
E1 Parte B (hecha; solo se carga) ──┐           │
                                    ▼           │
                     E2 Parte C: calibrar tiempos
                                    │           │
                     E2b Secuencia para el video│
                                    ▼           ▼
                     E3 Parte D: 3 repeticiones ──► E4 Resultados (Parte E y tablas)
```

- E0 y E1 no dependen de nada. E2 necesita E1. E3 necesita E2. E4 necesita E0 y E3.
- La app muestra cada etapa como **bloqueada**, **disponible** o **completa**, y solo deja entrar a las disponibles. Aun así, desde cualquier etapa debe poderse ver los datos de las anteriores.

## T1.1 Cambios de firmware

- [ ] **T1.1.1 [Sonnet] Tiempo de giro derecho propio.**
  - Hoy `t_giro90` sirve para los dos lados. Como el lado derecho tiene más fricción (Parte B), los giros pueden ser asimétricos.
  - Agregar `t_giro90_der` a `RobotConfig` (clave serie/HTTP `t90d`, valor inicial 500).
  - Usarlo en:
    - `robot_secuencia_tarea()`: el segmento "4 Derecha 90".
    - El comando serie `d` sin argumento.
    - `robot_config_json()`.
    - La lista de claves de `config_handler`.
  - Al cambiar el tamaño de `RobotConfig`, la calibración guardada en NVS vuelve a los valores de fábrica una vez. Es aceptable porque todavía no hay nada calibrado. Mencionarlo en el commit.
  - *Terminado:* `set t90d 520` cambia solo el giro derecho y `cfg` lo muestra.
- [ ] **T1.1.2 [Sonnet] Almacenamiento LittleFS para la Tarea 1.**
  - Verificar que el esquema de particiones del fqbn `esp32:esp32:esp32cam` tenga partición de datos (`arduino-cli board details -b esp32:esp32:esp32cam`). Si hace falta, usar `--board-options PartitionScheme=huge_app` (3 MB de app y 1 MB para datos) y documentarlo en CLAUDE.md, con la opción equivalente en el Arduino IDE.
  - En `robot_setup()` o en un módulo nuevo `datos_t1.h/.cpp`: `LittleFS.begin(true)`.
  - Endpoints:
    - `GET /t1/datos`: devuelve `/t1.json` o `{}` si no existe.
    - `POST /t1/datos`: cuerpo JSON de hasta 32 KB. Copia el archivo actual a `/t1.bak` y escribe el nuevo. Responde `{"ok":true,"bytes":N}`. El cuerpo se lee con `httpd_req_recv` en un ciclo y se rechaza (413) si pasa del límite.
    - `GET /t1/respaldo`: devuelve `/t1.bak`.
  - Subir `max_uri_handlers` si hace falta (hoy 24).
  - *Terminado:* un POST de prueba sobrevive a un reinicio; el GET lo devuelve igual.
- [ ] **T1.1.3 [Sonnet] Registrar `/capture`.**
  - Ya existe `capture_handler` en `app_httpd.cpp`, pero no está registrado. Registrarlo en el servidor del puerto 80.
  - Lo usa la Tarea 2 para el dataset; se hace aquí para no reflashear después.
  - *Terminado:* `http://192.168.4.1/capture` devuelve un JPEG de 320×240 con la misma orientación que el video (vflip = 1).

## T1.2 Página `/tarea1` (nuevo `tarea1_html.h`)

Se construye sobre `calibracion_html.h` (misma estética oscura, móvil primero, mismas funciones `get`, `esperar` y `ejecutar`). `/calibrar` pasa a ser la sección "Prueba libre" dentro de `/tarea1`, y la ruta `/calibrar` redirige ahí. El botón **Calibrar** de la página principal cambia a **Tarea 1**.

### Modelo de datos (`/t1.json`)

```json
{
  "version": 1,
  "fisicas": { "L_cm": [], "ejes_cm": [], "diam_cm": [], "v_reposo": null, "v_carga": null },
  "parteB": { "izq": [65,70,70,70,70,70,70], "der": [85,70,85,70,90,85,70], "sentido_ok": true },
  "calib":  [ { "id": 1, "fecha": "", "mov": "adelante", "ms": 2000, "pwm_l": 140, "pwm_r": 140,
                "ms_real": 2001, "voltaje": 12.1,
                "medido": { "avance_cm": 0, "desviacion_cm": 0, "angulo_deg": 0, "dist_origen_cm": 0 } } ],
  "tiempos": { "t_adelante": null, "t_atras": null, "t90": null, "t90d": null, "t360": null },
  "parteD": [ { "id": 1, "mov": "adelante", "rep": 1, "ms": 0, "ms_real": 0, "voltaje": null, "medido": {} } ],
  "video":  { "grabado": false },
  "estado": { "E0": "disponible", "E1": "completa", "E2": "disponible", "E3": "bloqueada", "E4": "bloqueada" }
}
```

- Los datos de la Parte B ya medidos se precargan.
- `mov` puede ser `adelante`, `atras`, `giro_izq`, `giro_der`, `giro360` o `ida_vuelta`.
- La página guarda el documento completo (`POST /t1/datos`) después de cada cambio. También guarda una copia en `localStorage`.
- Al abrir la página, si el robot y `localStorage` tienen datos distintos, gana el que tenga más registros y se avisa a Fer.

### Etapas de la página

- [ ] **T1.2.1 [Sonnet] Estructura.**
  - Pestañas o acordeón: E0, E1, E2, E2b, E3, E4, "Prueba libre" y "Datos".
  - Encabezado con la línea de estado del robot y un botón PARO siempre visible.
  - Cada etapa muestra su estado y qué falta para completarla.
- [ ] **T1.2.2 [Sonnet] E0 – Medidas físicas.**
  - Campos: L (3 mediciones, cm), distancia entre ejes (3), diámetro de llanta (3), voltaje en reposo y voltaje con motores girando.
  - Para el voltaje con carga, botón "Girar en el aire 3 s" que llama `/move?l=140&r=140&ms=3000`. Fer mide con el multímetro mientras gira.
  - Muestra el promedio y la DE de cada medida.
  - *Completa cuando:* L tiene 3 valores y los dos voltajes están llenos.
- [ ] **T1.2.3 [Sonnet] E1 – Parte B.**
  - Muestra la tabla precargada con media, DE e IC95; los resultados de Welch y Mann-Whitney van como texto fijo, tomado de `REPORTE.md` §6.1.
  - Botones para repetir la rampa (`/pwmmin?lado=I|D` y `/pwmmin_ok`) y agregar valores, por si Fer quiere más repeticiones.
  - Ya está **completa**.
- [ ] **T1.2.4 [Sonnet] E2 – Parte C: calibrar tiempos.**
  - Una tarjeta por movimiento, con su objetivo y su tolerancia:

| Movimiento | Objetivo | Tolerancia | Qué mide Fer | Clave de config |
|---|---|---|---|---|
| Adelante | 100 cm | ±3 cm | avance y desviación lateral | `t_adelante` |
| Atrás | 100 cm (en reversa) | ±3 cm | avance y desviación lateral | `t_atras` |
| Giro izquierda | 90° | ±5° | ángulo | `t90` |
| Giro derecha | 90° | ±5° | ángulo | `t90d` |
| Giro 360° (a la izquierda) | 360° | ±10° | ángulo | `t360` |

  - Flujo de cada tarjeta:
    1. La duración sugerida empieza en el valor actual de la config.
    2. **Ejecutar**: llama `/move` con el PWM de la config y espera a que termine.
    3. Fer captura la medición, que se guarda en `calib`.
    4. La app calcula la **siguiente duración sugerida**:
       - Con 1 punto: `t_nuevo = t · objetivo / medido`.
       - Con 2 o más duraciones distintas: regresión lineal `medido = a·t + b`, y `t_nuevo = (objetivo − b) / a`.
       - Muestra `a`, `b` y R² de la regresión. Redondea a 10 ms.
    5. Repetir hasta que **2 ejecuciones seguidas** con la misma duración caigan dentro de la tolerancia.
    6. Entonces se habilita **Aceptar tiempo**, que guarda el valor en `tiempos` y en el robot (`/config?t_adelante=…`).
  - *Completa cuando:* los 5 tiempos están aceptados.
  - 🛑 **Punto de control:** Fer comparte la tabla de E2 (exportada desde "Datos") si algún movimiento no converge en 6 intentos o si R² < 0.9. En ese caso, **[Opus]** revisa.
- [ ] **T1.2.5 [Sonnet] E2b – Secuencia para el video.**
  - Botón **Ejecutar secuencia** (`/seq`), con los tiempos aceptados.
  - Instrucciones: celular grabando el robot, el piso y el monitor serie de la laptop.
  - Casilla "Video grabado".
  - No bloquea E3; solo cuenta para la lista de entregables en E4.
- [ ] **T1.2.6 [Sonnet] E3 – Parte D: 3 repeticiones.**
  - Usa **solo** los tiempos aceptados en E2. No se pueden editar aquí; para cambiarlos hay que volver a E2, y la app avisa que las repeticiones hechas quedarían obsoletas.
  - Cinco movimientos × 3 repeticiones:

| Movimiento | Ejecución | Qué captura Fer |
|---|---|---|
| Adelante | `t_adelante` | avance (cm) y desviación lateral (cm, + izquierda) |
| Atrás | ida y vuelta: `t_adelante`, pausa de 500 ms, `t_atras` | distancia final al punto de inicio (cm) |
| Izquierda | `t90` | ángulo (°) |
| Derecha | `t90d` | ángulo (°) |
| 360° | `t360` | ángulo (°) |

  - Pide el voltaje de la batería al inicio de cada movimiento (con opción de reutilizar el último).
  - Permite descartar y repetir una repetición.
  - *Completa cuando:* las 15 repeticiones están guardadas.
- [ ] **T1.2.7 [Sonnet] E4 – Resultados.** Se calcula todo en la página:
  - `v = media(avance adelante en E3) / (media(ms_real)/1000)` [cm/s].
  - `ω_izq = media(ángulo izq) / (t90/1000)`, `ω_der` igual con `t90d`, y `ω_360 = media(ángulo 360) / (t360/1000)` [°/s].
  - Tiempo teórico de 90°: `t90_teo = π·L / (4·v)` [s], con L igual a la media de E0.
  - `L_ef = 2·v / ω_rad`, usando `ω_izq` en rad/s. Factor de derrape `= L_ef / L`.
  - Error de cada movimiento: media − objetivo y error relativo %. Para Atrás, el error es la distancia media al origen.
  - Voltaje medio al motor: `PWM/255 · (V_carga − 2)`.
  - Lista de entregables: video (casilla de E2b), fotos y diagrama (casillas manuales) y conclusiones.
  - Botones:
    - **Copiar Markdown**: tablas con el mismo formato de `docs/Tarea1/REPORTE.md` §6.2, §6.3 y los valores de la Parte E.
    - **Descargar JSON** y **Descargar CSV**. El CSV usa las columnas de `herramientas/calibrar.py` para que `calibrar.py analizar` siga sirviendo.
- [ ] **T1.2.8 [Sonnet] Sección "Datos".**
  - Tabla de todos los registros, con opción de borrar uno solo (con confirmación).
  - Descargar e importar el JSON.
  - Ver `/t1/respaldo`.

## T1.3 Utilidades en la PC y reporte

- [ ] **T1.3.1 [Sonnet] `herramientas/tarea1_descargar.py`.**
  - Baja `http://192.168.4.1/t1/datos` a `docs/Tarea1/datos/tarea1.json`.
  - Genera `docs/Tarea1/datos/resultados.md` con las mismas cuentas de E4, para que los resultados queden en el repo y se puedan revisar sin el robot.
  - Solo usa la biblioteca estándar.
- [ ] **T1.3.2 [Fer] Ejecutar E0 → E4 con el robot.**
  - 🛑 **Punto de control** al terminar E3: Fer corre `tarea1_descargar.py` y avisa en el chat.
- [ ] **T1.3.3 [Sonnet] Llenar `docs/Tarea1/REPORTE.md`** con `resultados.md`:
  - Las tablas de §6.2 y §6.3.
  - Los huecos `___` de la §7.
  - L en §3 y §4, y el voltaje.
  - Después, regenerar el PDF.
- [ ] **T1.3.4 [Opus] Revisión final del reporte de la Tarea 1:** coherencia de números, análisis y conclusiones.
- [ ] **T1.3.5 [Fer] Fotos, diagrama dibujado, video, fecha y conclusiones;** entrega.

---

# TAREA 2 – App de PC `herramientas/tarea2/`

## Mapa de etapas y dependencias

```
E0 Preparación ► E1 Condiciones y objetos ► E2 Captura ► E3 Subida y etiquetado
     ► E4 Entrenamiento (corrida 1 ► ajuste ► corrida 2) ► E5 Despliegue
     ► E6 Pruebas (10 + 5 por objeto) ► E7 Resultados ► E8 Reporte y propuesta
```

Es lineal: cada etapa necesita la anterior. La app guarda el avance en `herramientas/tarea2/datos/estado.json` y el comando `estado` dice qué etapa sigue y qué falta.

## Diseño de la app

- `herramientas/tarea2/tarea2.py`: CLI con subcomandos `estado`, `preparar`, `condiciones`, `capturar`, `subir`, `entrenamiento`, `pruebas`, `resultados`.
- Dependencias: `pyserial`, `numpy`, `scipy` y `matplotlib`. Agregarlas a `herramientas/requirements.txt`.
- Datos en `herramientas/tarea2/datos/`:
  - `estado.json`, `condiciones.json`, `entrenamientos.json`.
  - `dataset/<objeto>/*.jpg` y `dataset/capturas.csv`.
  - `pruebas.csv`, `pruebas_crudo.log` y `resultados/`.
- El dataset (imágenes) **sí** va al repo, porque es evidencia; si pasa de 50 MB, se replantea con Fer.

## Etapas

- [ ] **T2.0 [Sonnet] `tarea2.py preparar`.**
  - Verifica:
    - Que Python tenga las dependencias.
    - Que exista `edge-impulse-uploader` en el PATH; si no, muestra `npm install -g edge-impulse-cli`.
    - Que responda `http://192.168.4.1/capture`.
    - Que exista arduino-cli (ruta de CLAUDE.md) y qué core ESP32 tiene instalado.
  - Imprime una lista de verificación con ✓/✗ y cómo resolver cada ✗.
- [ ] **T2.0b [Fer] Instalar Edge Impulse CLI e iniciar sesión.**
  - Crear la cuenta y el proyecto en Edge Impulse.
  - Ejecutar `edge-impulse-uploader --clean` una vez para iniciar sesión y elegir el proyecto.
  - Las credenciales las escribe Fer, no el agente.
- [ ] **T2.1 [Sonnet] `tarea2.py condiciones`.**
  - Pide y guarda en `condiciones.json`:
    - Altura de la cámara (cm) y distancia del punto marcado a la cámara (cm).
    - Descripción del fondo y de la iluminación (por ejemplo, "lámpara LED blanca a 50 cm"), y si se usa el LED flash.
    - Los 3 objetos, con nombre corto sin espacios, e indicación de cuáles dos se parecen y por qué.
  - Valida que los objetos sean distintos del LED, la bornera y el pulsador del video.
  - La cámara es la del robot: el robot queda fijo y su altura es constante; el punto marcado está frente a él.
  - 🛑 **Punto de control:** Fer confirma los objetos antes de capturar.
- [ ] **T2.2 [Sonnet] `tarea2.py capturar --objeto <nombre> [--n 60] [--auto 2]`.**
  - Pide `GET /capture` al robot y guarda `dataset/<objeto>/<objeto>_NNN.jpg`.
  - Modo manual: Enter = foto. Modo `--auto S`: una foto cada S segundos, para que Fer solo gire el objeto.
  - Muestra el conteo y la resolución, y avisa si una foto llegó vacía o con otra resolución.
  - Registra en `capturas.csv`: archivo, objeto, fecha, tamaño, resolución.
  - Meta: **60 por objeto**, 10 más del mínimo de 50, por si se descartan algunas.
  - Antes de capturar, recuerda las condiciones de `condiciones.json`.
  - *Terminado:* 3 objetos con 50 fotos o más cada uno.
- [ ] **T2.3 [Sonnet] `tarea2.py subir`.**
  - Para cada objeto ejecuta `edge-impulse-uploader --category split --label <objeto> dataset/<objeto>/*.jpg` (reparto automático 80/20) y guarda la salida en el log.
  - Después muestra las instrucciones de etiquetado:
    - Edge Impulse Studio → Labeling queue.
    - Cuadros ajustados al objeto; se puede usar el etiquetado asistido.
- [ ] **T2.3b [Fer] Etiquetar todas las imágenes** con cuadros delimitadores en Edge Impulse.
- [ ] **T2.4 [Sonnet] `tarea2.py entrenamiento --corrida 1|2`.**
  - Pide y guarda en `entrenamientos.json`:
    - Configuración: resolución del impulse (96×96), modo de color (escala de grises), modelo (FOMO MobileNetV2 0.35), ciclos, tasa de aprendizaje y aumento de datos.
    - Resultados: F1 de validación por clase y total, la matriz de confusión (filas y columnas que Fer copia de la pantalla), y el rendimiento estimado en el dispositivo (inferencia en ms, RAM y flash).
    - En la corrida 2: el **único parámetro** que cambió y por qué.
  - Ruta de las capturas de pantalla: `docs/Tarea2/img/entrenamiento_<n>.png`.
  - Guía para Fer:
    - Corrida 1 con los valores por defecto.
    - Corrida 2 cambiando un solo parámetro según la confusión observada. Ejemplos: bajar la tasa de aprendizaje a 0.01 como en el video, subir los ciclos o agregar fotos del objeto confundido.
  - 🛑 **Punto de control:** Fer comparte `entrenamientos.json`; **[Opus]** revisa si la corrida 2 mejoró y si conviene otra antes de desplegar.
- [ ] **T2.5 Despliegue (`firmware/deteccion_ei/`).**
  - **T2.5.1 [Fer]** Exportar la librería de Arduino desde Edge Impulse (Deployment → Arduino library, versión cuantizada int8) y guardar el ZIP en `firmware/deteccion_ei/lib/`.
  - **T2.5.2 [Sonnet] Decisión del core.**
    1. Instalar el ZIP con `arduino-cli lib install --zip-path …` (habilitar `library.enable_unsafe_install` si hace falta).
    2. Compilar el ejemplo `esp32_camera` de la librería con el core actual **3.3.12**, subirlo y verificar en el monitor serie que haya inferencias sin `cam_hal: DMA overflow` y sin reinicios.
    3. Si funciona, el proyecto se queda en 3.3.12.
    4. Si falla al compilar o al correr, instalar `esp32:esp32@3.0.7` (la versión del video), repetir, y **recompilar y volver a probar el firmware del robot** (`/tarea1`, `seq`, `/capture`) con 3.0.7.
    5. Registrar el resultado en CLAUDE.md (sección del core) y en el reporte.
    - 🛑 **Punto de control** si 3.0.7 también falla: **[Opus]** depura (el respaldo es la 2.0.4, la que Edge Impulse documenta como probada).
  - **T2.5.3 [Sonnet] Sketch propio `firmware/deteccion_ei/deteccion_ei.ino`,** basado en el ejemplo:
    - Modelo de cámara AI Thinker y `vflip = 1`, igual que el firmware del robot, para que las imágenes de inferencia tengan la misma orientación que las del dataset.
    - **GPIO 12–15 como `OUTPUT` en `LOW` al arrancar**, para que el L298N no mueva los motores con pines flotantes.
    - Una línea por cada cuadro, fácil de leer por la máquina:
      - Con detecciones: `DET;<t_ms>;<dsp_ms>;<clasif_ms>;<etiqueta>;<prob>;<cx>;<cy>;<w>;<h>`, una línea por detección. `cx = x + w/2` y `cy = y + h/2`, en píxeles de la entrada del modelo (96×96).
      - Sin detecciones: `NONE;<t_ms>;<dsp_ms>;<clasif_ms>`.
    - Al arrancar imprime `INFO;modelo=<nombre>;entrada=96x96;umbral=<x>;core=<versión>`.
    - Comentarios en español en todo el sketch (es entregable).
    - *Terminado:* con el robot fijo y un objeto en el punto marcado, el monitor serie muestra líneas `DET` con la etiqueta correcta.
  - **T2.5.4 [Fer]** Prueba autónoma con power bank, sin computadora: foto o video corto de máximo 1 minuto. Como no hay OLED, la evidencia es el LED flash: el sketch lo enciende 200 ms cuando detecta cualquier objeto con probabilidad ≥ umbral. **[Sonnet]** agrega ese comportamiento al sketch.
- [ ] **T2.6 [Sonnet] `tarea2.py pruebas --puerto COM8`.**
  - Abre el puerto a 115200 baudios y escribe todo lo que llega en `pruebas_crudo.log`.
  - Plan de pruebas: por objeto, 10 en la **posición de entrenamiento** (`cond=entrenamiento`) y 5 en **otra posición u otra luz** (`cond=posicion` o `cond=luz`, a elegir por prueba). Total: 45 pruebas.
  - Flujo de cada prueba:
    1. La app indica el objeto, la condición y el número de prueba.
    2. Fer coloca el objeto y presiona Enter.
    3. La app lee 3 segundos de líneas `DET`/`NONE` y elige la detección **de mayor probabilidad** en esa ventana. Si solo hubo `NONE`, la etiqueta es `sin_deteccion`.
    4. Muestra el resultado y propone acierto = (etiqueta == objeto). Fer puede corregirlo.
    5. Guarda en `pruebas.csv`: objeto, condición, prueba, etiqueta detectada, probabilidad, x, y, acierto, número de cuadros en la ventana, tiempo de inferencia medio de la ventana y nota.
  - Permite pausar y reanudar: sigue desde la última prueba guardada.
- [ ] **T2.7 [Sonnet] `tarea2.py resultados`.** Genera `herramientas/tarea2/datos/resultados/resultados.md` y gráficas PNG:
  - **Tabla de resultados** del entregable: objeto, prueba, etiqueta detectada, probabilidad, (x, y), acierto (sí/no).
  - Exactitud por objeto y por condición, con IC95 de Wilson.
  - **Matriz de confusión de las pruebas reales**, incluida la columna `sin_deteccion`, también como PNG.
  - Comparación entrenamiento vs posición/luz: prueba exacta de Fisher (2×2 de aciertos y errores), por objeto y global.
  - Probabilidad media en aciertos vs errores.
  - Estabilidad de las coordenadas en la posición de entrenamiento: media y DE de (x, y) por objeto.
  - Tiempo de inferencia (DSP + clasificación): media y DE, y FPS = 1000 / tiempo total medio.
  - Tabla de entrenamiento, corrida 1 vs corrida 2: F1 total y por clase, más las dos matrices de confusión, tomadas de `entrenamientos.json`.
- [ ] **T2.8 Reporte (`docs/Tarea2/REPORTE.md` → PDF de 4 a 6 páginas).**
  - **[Sonnet]** Estructura:
    - Portada; introducción (TinyML, FOMO); metodología con capturas (condiciones, captura, etiquetado, impulse, entrenamiento y despliegue); resultados (tablas de T2.7).
    - Análisis: las 6 preguntas de la asignación, respondidas con los datos propios. Conclusiones. Referencias en formato IEEE.
    - Incluir el enlace al proyecto de Edge Impulse (público) y al repositorio.
  - **[Sonnet]** Propuesta de integración en el robot diferencial (1 página), con diagrama de bloques en Mermaid, coherente con la arquitectura decidida en CLAUDE.md:
    - **Sensor:** la cámara del ESP32-CAM corre FOMO.
    - **Control:** el error de dirección `e = cx − 48` (centro de la imagen de 96 px) ajusta la diferencia de PWM entre ruedas, con un control P o PI. El robot se acerca hasta que el tamaño del cuadro (w·h) supera un umbral.
    - **Acciones:** buscar (girar en su lugar) cuando no hay detección; centrar y acercarse cuando la hay; detenerse y encender el LED al llegar.
    - **Evolución:** reparto de carga con el ESP32-WROOM-32D por UART, y la Raspberry Pi 5 para modelos más grandes.
  - Referencias: las de la asignación con datos completos, más **dos artículos arbitrados propios**. **[Opus]** los propone y verifica.
  - **[Opus]** Revisión final del reporte. **[Fer]** Entrega.

---

## Riesgos conocidos

| Riesgo | Mitigación |
|---|---|
| Edge Impulse no corre con el core 3.3.12 | Regla de T2.5.2: probar 3.0.7 y, si falla, 2.0.4, con una sola versión para todo el proyecto |
| `localStorage` del celular se borra | Los datos de la Tarea 1 viven en LittleFS del robot, con respaldo `/t1.bak` y descarga al repo |
| Pines 12–15 flotantes con el sketch de Edge Impulse | Se fijan en `LOW` al arrancar (T2.5.3) |
| Dataset con otra orientación o resolución que la inferencia | Mismo `vflip` y resolución base (QVGA); Edge Impulse redimensiona a 96×96 |
| Google Drive sincroniza `.git` entre las dos PC | Un solo chat y una sola PC hacen commits a la vez; antes de empezar, `git pull` |
| La batería cambia los tiempos calibrados | Registrar el voltaje en E2 y E3; si cae más de 0.5 V entre E2 y E3, avisar y recalibrar |
