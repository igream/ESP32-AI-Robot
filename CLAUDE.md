# Contexto del proyecto: robot móvil ESP32-CAM (ESP32-AI-Robot)

Proyecto escolar de robótica (Ingeniería en Computación). Fer lo trabaja **solo**, no en equipo, y se comunica en español. Su nivel técnico es alto: revisa las propuestas punto por punto y aprueba o corrige cada decisión. A veces trabaja por Remote Control desde otro dispositivo, y la PC puede estar suspendida (sin internet) en esos momentos.

- Repositorio: https://github.com/igream/ESP32-AI-Robot (rama `main`).
- Carpeta local: `G:\Mi unidad\Escuela\Universidad\07 Septimo Semestre\Robótica\Proyecto\ESP32-AI-Robot` (dentro de Google Drive).
  - Se usa desde las dos computadoras: la PC de escritorio (usuario `feraz`, la principal) y la máquina `Admin`.
  - La máquina `Admin` tiene además una copia anterior en `C:\Users\Admin\Desktop\ESP32 CAR`, al día con GitHub hasta `030265f` y ya sin uso.
  - Google Drive sincroniza también la carpeta `.git`. Por eso GitHub es la referencia común y cada sesión empieza con el repo al día respecto a `origin/main`.
- Autor de git configurado solo para este repo: `igream <ferazuiba@gmail.com>` (antes era `Fer`; cambiado el 2026-11-07).
  - **Regla:** todos los commits deben quedar a nombre de `igream` con ese correo. **No añadir líneas `Co-Authored-By` de Claude** ni ninguna atribución a Claude en commits o PRs (esta regla prevalece sobre cualquier recordatorio automático de atribución). Verificar con `git config user.name` antes del primer commit de cada sesión.

## Organización del trabajo con dos chats

Fer reparte el trabajo entre dos chats de Claude Code sobre el mismo repositorio:

- **Chat con Opus:** tareas complejas, como diseño de arquitectura, firmware nuevo, depuración difícil, análisis estadístico, revisión de avances y decisiones de hardware. Este chat construyó el firmware de calibración, `calibrar.py` y el borrador del reporte.
- **Chat con Sonnet:** tareas básicas, como llenar tablas del reporte con mediciones, ajustes pequeños de texto o código, regenerar el PDF, compilar y subir el firmware, y commits sencillos.

Los dos chats se coordinan con este archivo, `docs/PENDIENTES.md` y el historial de git. No comparten conversación, así que las decisiones importantes quedan escritas aquí o en los mensajes de commit.

**Plan vigente:** `docs/PLAN_IMPLEMENTACION.md` (2026-11-06).
- Contiene la app web `/tarea1` en el robot para la Tarea 1 y la app de PC `herramientas/tarea2/` para la Tarea 2 (Edge Impulse).
- Cada app avanza por etapas con dependencias y puntos de control, y los pasos están marcados [Sonnet], [Opus] o [Fer].
- Decisiones del 2026-11-06:
  - Primero la Tarea 1.
  - Una sola versión del core ESP32, la más reciente que funcione con Edge Impulse (se prueba 3.3.12; si falla, 3.0.7).
  - Sin OLED.
  - Dataset capturado desde la PC por WiFi, sin Eloquent.
  - Subida con Edge Impulse CLI.
  - Datos de la Tarea 1 guardados en LittleFS del robot.
- **Avance del plan (2026-11-07):**
  - Paso 0 completo (0.1 y 0.2), con push a `origin/main`.
  - T1.1.1 (`t90d`), T1.1.2 (LittleFS y endpoints `/t1/*`) y T1.1.3 (`/capture` registrado) están **completos: en `origin/main` (`05dfbaa`), subidos al robot por COM8 y probados el 2026-11-07** (`set t90d` cambia solo el giro derecho; POST a `/t1/datos` sobrevive a un reinicio y devuelve 413 sobre 32 KB; `/capture` da JPEG de 320×240).
  - **T1.3.1 y app de la Tarea 2 (2026-11-07):** `herramientas/tarea1_descargar.py` y `herramientas/tarea2/tarea2.py` (T2.0–T2.4, T2.6, T2.7) están escritos y probados solo con datos simulados (`pruebas --simular`, `resultados`) y con `capturar` real contra el robot. Sin probar con Edge Impulse (`subir` necesita el CLI y la sesión de Fer), ni `condiciones`/`entrenamiento` de forma interactiva. Observación: `/capture` dio 500 una vez tras un reinicio del robot y se recuperó al reiniciar de nuevo; vigilarlo.
  - **T2.5.3 (2026-11-07):** `firmware/deteccion_ei/deteccion_ei.ino` escrito (formato `INFO`/`DET`/`NONE`, GPIO12–15 en LOW, flash 200 ms al detectar, mismo vflip que el robot). Compila contra una librería de prueba, **no** contra la de Edge Impulse; falta instalar la librería real (T2.5.1, Fer) y cambiar el nombre en `modelo_ei.h`.
  - **T1.2 (2026-11-07):** página `/tarea1` (`tarea1_html.h`) escrita, compilada (36 % de flash), subida al robot por COM8 y revisada en el navegador con datos simulados (render de las 8 secciones, regresión de E2, resultados de E4, Markdown y CSV). **Nunca se ejecutó un movimiento desde la página**: lo primero que hay que probar con el robot en el piso es E2 (Ejecutar → medir → Aceptar tiempo). `/calibrar` redirige a `/tarea1#libre`. Sigue T1.3.1 (`herramientas/tarea1_descargar.py`).

## Objetivos del curso (en orden)

1. Movimientos definidos por coordenadas: saber de forma precisa cuánto se mueve el robot (calibración). **Etapa actual.**
2. Probar el movimiento desde una interfaz de usuario.
3. Dataset con la cámara del robot de diferentes colores (primer ejercicio de visión).
4. Dataset y detección de objetos con la cámara del robot.
5. Lenguaje natural por voz. Por ejemplo, el usuario dice "Buscar", el robot entiende y espera la siguiente instrucción, y confirma con LEDs (rojo/azul = entendido o no).
6. Requisito del profesor: **toda la inferencia es local**, en el hardware del robot, sin nube.

## Hardware actual (kit LaFvin ESP32 Camera 4WD Robot Car V3)

- **Placa:** ESP32-CAM AI-Thinker con cámara OV3660, programada con la ESP32-CAM-MB (CH340).
- **Motores:** driver L298N con 4 motores TT amarillos. Los 2 motores de cada lado van en paralelo, así que el robot se comporta como diferencial aunque gire derrapando (skid-steer).
- **Alimentación:** 3 × 18650 (9–12.6 V). El regulador del L298N da 5 V al ESP32-CAM.
  - Con las baterías bajas, al quitar el USB la ESP32-CAM se reinicia en bucle (brownout) y al final se apaga. El LED rojo (GPIO33) lo enciende el firmware una sola vez al terminar de arrancar y no parpadea; si parpadea, son reinicios.
  - Por ahora las pruebas usan una **fuente externa conectada al portapilas** (máximo 12.6 V). Anotar su voltaje en cada prueba: los tiempos calibrados solo valen para ese voltaje. Recargar las baterías cuando se pueda.
- **Pines:**

| Pin | Función |
|---|---|
| GPIO12 | `LEFT_M1`, izquierdo adelante |
| GPIO13 | `LEFT_M0`, izquierdo reversa |
| GPIO14 | `RIGHT_M0`, derecho reversa |
| GPIO15 | `RIGHT_M1`, derecho adelante |
| GPIO4 | LED flash |
| GPIO33 | LED rojo de la placa (activo en bajo) |

  Verificado con `mot` el 2026-11-02: GPIO12/13 mueven el lado izquierdo y GPIO14/15 el derecho, en el sentido correcto.
- **Pines libres:** el ESP32-CAM prácticamente no tiene. GPIO2 es de arranque y de la SD; GPIO16 lo usa la PSRAM; GPIO12 es de arranque (strapping), aunque el robot arranca bien con el L298N conectado.
- **PWM:** los jumpers ENA/ENB están puestos. Decisión aprobada para la Tarea 1: la velocidad se regula con PWM en los pines IN (un IN con PWM y el otro en 0). Usar ENA/ENB queda para cuando exista el coprocesador. LEDC a 2 kHz y 8 bits, canales 4–7 con el timer 1 (la cámara usa canal 0 / timer 0).
- **Voltaje de los motores:** desconocido; el manual no lo dice y el motor no tiene etiqueta. Se asume TT de 3–6 V.
  - Con 12.6 V − ~2 V de caída en el L298N, el límite es `pwm_max = 145/255` (~6 V promedio).
  - El código del fabricante usaba 150, lo que es consistente con esa estimación.
- **Diámetro de llanta:** sin medir.

## Arquitectura futura (decidida)

- **Raspberry Pi 5 de 4 GB:** "cerebro" para visión y voz, montada en el carro. Se conecta al WiFi del robot y procesa el video MJPEG del ESP32-CAM (`http://192.168.4.1:81/stream`) con OpenCV. La cámara del kit se mantiene; el dataset y la inferencia usan la misma cámara. Una Camera Module 3 o un AI HAT+ solo si después hace falta.
- **ESP32-WROOM-32D** (Fer ya lo tiene; lo llamó "3D"): controlador de motores, LEDs y sensores, conectado por UART a la Pi. Libera pines para ENA/ENB, IMU, ultrasónico y lectura de batería. No sirve para visión, y sin PSRAM no corre ESP-SR.
- **Micrófono USB** en la Pi para voz. Se descartó el del celular porque el robot no "escucharía" y el navegador pide HTTPS.
- Encoders LM393 descartados por ahora.

## Compras (carritos revisados el 2026-11-02, todo compatible; pendientes de comprar)

| Tienda | Artículo | Precio |
|---|---|---|
| Mercado Libre | Raspberry Pi 5 de 4 GB | $3,201 |
| Mercado Libre | Convertidor JELELECRONICA MDC-DC12-24A5V5A (entrada 9–36 V, salida 5 V 5 A / 30 W, USB) | $78 |
| Mercado Libre | MPU6050 (GY-521), 5 piezas | $215 |
| Amazon | microSD SanDisk Extreme PRO 64 GB (vendida por Amazon México) | $499 |
| Amazon | 2 cables Fasgear USB-A → USB-C de 30 cm, 3 A | $240 |
| Amazon | Sensor ultrasónico HC-SR04P (versión 3–5 V, sin divisor a 3.3 V) | $66 |
| Amazon | Active Cooler para Pi 5 | $235 |
| Amazon | Micrófono USB SunFounder | $191 |

- Fer ya tiene LEDs rojo/azul, resistencias de 220 Ω y cables Dupont.
- El convertidor no negocia corriente por USB-C. Al instalar la Pi hace falta `PSU_MAX_CURRENT=5000` en la EEPROM.

## Asignación actual: Tarea 1

Enunciado: `docs/Asignaciones/Tarea_Robot_Movil_Diferencial.docx`.

| Parte | Contenido |
|---|---|
| A | Ensamble y diagrama de conexiones |
| B | Sentido de cada motor y PWM mínimo |
| C | Funciones `adelante/atras/izquierda/derecha/detener/girar360` y secuencia con 1 s de pausa |
| D | Calibración: 1 m recto, regreso al origen, 90°, 90° y 360°, con 3 repeticiones |
| E | Preguntas de análisis y cinemática: v = (vR+vL)/2, ω = (vR−vL)/L |

- Entregable: reporte PDF, video con el monitor serie mostrando las etiquetas, fotos y enlace a GitHub.
- Rúbrica: +10 puntos extra por el giro de 360°.
- Siguiente asignación: `docs/Asignaciones/Tarea_ESP32CAM_EdgeImpulse.docx` apareció en la carpeta el 2026-11-03, todavía sin commit y sin revisar. Por el nombre, trata de visión con Edge Impulse en el ESP32-CAM.

### Estado de la Tarea 1

- **Firmware** (`firmware/robot_esp32cam/`): compila sin errores ni avisos con el core ESP32 3.3.12 (fqbn `esp32:esp32:esp32cam`; el IDE actualizó el core desde 3.1.0). Usa 33 % de flash y 20 % de RAM. **Subido al robot el 2026-11-02** por COM8: arranca con PSRAM, cámara, AP y servidor web. Para eso, `camera_config_t` se inicializa en ceros y fija `fb_location`/`grab_mode`; antes, con campos sin inicializar, fallaba con `frame buffer malloc failed`. Si la cámara falla, el WiFi y los motores siguen funcionando.
- **Cambios posteriores (2026-11-06 y 2026-11-07):**
  - **Página `/calibrar`** (`calibracion_html.h`, ya en `main`, subida al robot por COM7 y probada por Fer): ejecuta un movimiento, pide la medición y la guarda en `localStorage` con las columnas de `calibrar.py`; resumen n/media/DE y exportación a CSV. Tipos: adelante, atrás, giro izquierda, giro derecha e ida y vuelta (el 360° es giro izquierda con ≈ `t360`). El botón **Calibrar** de la página principal la abre. Será la sección "Prueba libre" de `/tarea1`.
  - **Sin commit todavía (compila, 35 % de flash):**
    - `t90d`: tiempo de giro derecho propio (`t_giro90_der` en `RobotConfig`, clave serie/HTTP `t90d`, valor inicial 500). Lo usan la secuencia (segmento 4), el comando serie `d` y `/config`. Como cambia el tamaño de `RobotConfig`, la calibración guardada en NVS vuelve una vez a los valores de fábrica.
    - `datos_t1.h/.cpp`: LittleFS con `/t1.json` y respaldo `/t1.bak` (escritura segura vía `/t1.new`). Endpoints `GET/POST /t1/datos` (máx. 32 KB, 413 si se pasa) y `GET /t1/respaldo`. El esquema de particiones por defecto del fqbn `esp32cam` ya es `huge_app` (3 MB de app y 1 MB para datos), así que no hace falta cambiar opciones.
    - `/capture` registrado (QVGA 320×240, `vflip = 1`, igual que el video).
    - `max_uri_handlers = 32` (antes 24).
  - `herramientas/reporte_pdf.py` acepta la ruta de otro `.md` como argumento (sin argumento genera el de la Tarea 1). Probado con el reporte de la Tarea 1 y con un `.md` de prueba; el de la Tarea 2 aún no existe.
- **Parte B hecha (2026-11-02):**
  - `mot` confirma que GPIO12/13 son el lado izquierdo y que los cuatro sentidos son correctos.
  - PWM mínimo con el criterio "giran las dos llantas": izquierdo 69.3 ± 1.9, derecho 79.3 ± 8.9 (n = 7 por lado; Welch p = 0.024). El lado derecho tiene más fricción estática (valores de 70 u 85–90, arranque brusco). Los resultados ya están en `REPORTE.md` §6.1.
  - `robot_esp32cam.ino`:
    - Cámara.
    - WiFi en modo punto de acceso: SSID `ESP32Car_Fer`, contraseña `Fer12345.`, IP `192.168.4.1`.
    - `loop()` llama a `robot_loop()`.
  - `robot_motion.h/.cpp`:
    - Funciones básicas y una cola FreeRTOS de comandos no bloqueante, basada en `millis()`, con segmentos y pausas.
    - Corrección `trim_i`/`trim_d`, `pwm_max`, pose estimada por tiempo y `ir_a(x, y)` (gira hacia el punto y luego avanza).
    - Rampa de PWM mínimo (+5 cada 400 ms; se marca con `ok`).
    - Configuración guardada en NVS (`Preferences`, namespace `robot`).
    - Comandos serie a 115200 baudios: `a r i d g m seq mot min ok cm gr ir origen s cfg estado set reset_cfg ayuda`.
  - `app_httpd.cpp`:
    - Video y página con botones (incluye Secuencia, Giro 360, Prueba motores y una línea de estado).
    - Endpoints JSON: `/move?l=&r=&ms=`, `/seq`, `/mot`, `/pwmmin?lado=I|D`, `/pwmmin_ok`, `/g360`, `/cm?d=`, `/grados?a=`, `/ir?x=&y=`, `/origen`, `/estado`, `/config?clave=valor`.
    - `max_uri_handlers = 24`. El log de cada cuadro de video está apagado (`LOG_STREAM 0`).
  - Marco de coordenadas: x hacia el frente, y a la izquierda, ángulo positivo = izquierda.
  - Calibración por defecto: pwm 140, pwm_giro 140, t90 500 ms, t360 1800 ms; `v` y `w` en 0 (sin calibrar).
- **Script de PC** (`herramientas/calibrar.py`, guía en `herramientas/README.md`):
  - Subcomandos `prueba`, `barrido` (orden aleatorio), `analizar`, `aplicar` y `validar`; `--simular` sirve para probar sin robot.
  - Guarda en `herramientas/datos/pruebas.csv`; el análisis queda en `herramientas/datos/analisis/` (`resumen.md`, gráficas PNG, `sugerencias.json`).
  - Estadística: descriptiva con IC95 t, Shapiro-Wilk, atípicos IQR, tamaño de muestra, t de una muestra de la desviación normalizada a 1 m (recorridos de 30 cm o más), regresión tiempo → distancia/ángulo, L efectiva y factor de derrape, t de Welch, Pearson voltaje–residuo y ANOVA por superficie.
  - Probado de punta a punta solo con datos simulados.
  - En la máquina `Admin` usa el entorno `.venv` (numpy 2.5, scipy 1.18, matplotlib 3.11), que está en `.gitignore`. En la PC de escritorio corre con el Python del sistema; se probó con `--simular` el 2026-11-02.
- **Reporte** (`docs/Tarea1/REPORTE.md`, exportado a `REPORTE.pdf` con `python herramientas/reporte_pdf.py [ruta.md]`):
  - Ya incluye conexiones, diagrama Mermaid, diseño del PWM, código, la Parte B llena y problemas y soluciones.
  - Por llenar: tiempos calibrados de la Parte C, la tabla de la Parte D (3 repeticiones), los huecos `___` de la Parte E, fecha, fotos y conclusiones.
  - Se eligió la ruta mínima: la Parte D con 3 repeticiones, sin la sección de análisis estadístico extra de `calibrar.py`.
- **Pendientes y decisiones:** `docs/PENDIENTES.md`.
- **Mediciones pendientes:** L (distancia entre llantas izquierda y derecha), distancia entre ejes, diámetro de llanta, voltaje de la fuente o batería (en reposo y con motores girando), barridos y validación. Se harán con la app `/tarea1` (T1.2).

### Estado de git

- **2026-11-06:** `e5cd415` (página `/calibrar` y enunciado de la Tarea 2) y `dc73e0f` (`reporte_pdf.py` con argumento), ambos en `origin/main`. Después, `05dfbaa` (T1.1: `t90d`, `datos_t1.*`, `/capture`) también está en `origin/main`.
- Después del PR, Fer subió desde la PC de escritorio el arreglo de la cámara, la Parte B, la exportación a PDF y la actualización de CLAUDE.md (commits `d19a491` a `7cecd02`).
- `030265f` (2026-11-03): corrección de la normalidad en la Parte B, `reporte_pdf.py` también usa Chrome (la máquina `Admin` no tiene Edge), y CLAUDE.md al día.
- `main` incluye todo el trabajo de la Tarea 1: el PR igream/ESP32-AI-Robot#1 (rama `tarea1-calibracion`, commit `3918538`) se fusionó el 2026-11-02 con el merge commit `87aa5ce`.
- Antes de eso estaba el commit base `d968dd5`: código del kit, cambio de WiFi, docs y pendientes.
- El firmware estaba originalmente en la raíz como `ESP32_Camera_4WD_Robot_Car_OV3660_V3.ino` y se movió con `git mv`.
- GitHub CLI (`C:/Program Files/GitHub CLI/gh.exe`) está instalado en la máquina `Admin`, con sesión de la cuenta `igream`, y no está en el PATH de Git Bash. En la PC de escritorio no está instalado. La máquina `Admin` tiene Google Chrome pero no Edge.
- El repo no tiene CI.
- `build/` contiene el binario original del fabricante y está ignorado.

## Notas del entorno

- **Sistema:** Windows 11, con Git Bash y PowerShell.
- **arduino-cli:**
  - PC de escritorio: `C:/Users/feraz/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe` (versión 1.5.1). El core esp32 3.3.12 está instalado en `%LOCALAPPDATA%\Arduino15`. El ESP32-CAM-MB aparece en COM8 y la subida con reinicio automático funciona sin presionar IO0. Conviene compilar con `--build-path` fuera de Google Drive.
  - Máquina `Admin`: `C:/Program Files/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe`. Aquí el core instalado es el **3.1.0** (no el 3.3.12), y compila igual. El robot aparece en **COM7**. Compilar con `--build-path "$TEMP/build_robot"`; subir con `upload -p COM7 --input-dir "$TEMP/build_robot"`. La compilación tarda varios minutos y alguna vez falla sin mensaje (`exit status 1`); repetirla suele bastar.
- **Edge Impulse (Tarea 2):** proyecto público https://studio.edgeimpulse.com/public/1159326/live (creado por Fer el 2026-11-07). El CLI se instaló en la PC de escritorio con `npm install -g edge-impulse-cli --ignore-scripts`: con Node 26 el build normal falla (`@serialport/bindings` necesita Visual Studio) y el uploader no usa serialport. Falta que Fer inicie sesión con `edge-impulse-uploader --clean`.
- **Driver CH340:** instalado en la PC de escritorio. COM3 y COM4 son Bluetooth, no la placa.
- **Python del sistema:** 3.14. En la PC de escritorio ya tiene numpy, scipy, matplotlib y pyserial. En la máquina `Admin` no tiene scipy y las librerías están en `.venv`.
- **Git Bash:** los heredocs alteran las barras invertidas (`\n`, `\r\n`) en scripts de Python; aplicar parches con el editor de archivos evita ese problema.
- **Finales de línea:** `app_httpd.cpp` usa CRLF; los archivos nuevos usan LF.
- **Mercado Libre:** pide verificación de cuenta para ver búsquedas o fichas en el navegador integrado; los carritos compartidos sí se pueden leer.
