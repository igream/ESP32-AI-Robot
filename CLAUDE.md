# Contexto del proyecto: robot móvil ESP32-CAM (ESP32-AI-Robot)

Proyecto escolar de robótica (Ingeniería en Computación). Fer lo trabaja **solo**, no en equipo, y se comunica en español. Su nivel técnico es alto: revisa las propuestas punto por punto y aprueba o corrige cada decisión. A veces trabaja por Remote Control desde otro dispositivo, y la PC puede estar suspendida (sin internet) en esos momentos.

- Repositorio: https://github.com/igream/ESP32-AI-Robot (rama `main`).
- Carpeta local (PC de escritorio, la principal): `G:\Mi unidad\Escuela\Universidad\07 Septimo Semestre\Robótica\Proyecto\ESP32-AI-Robot` (dentro de Google Drive). En la otra máquina (usuario `Admin`) estaba en `C:\Users\Admin\Desktop\ESP32 CAR`.
- Autor de git configurado solo para este repo: `Fer <ferazuiba@gmail.com>`.

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
- **Pines:**

| Pin | Función |
|---|---|
| GPIO12 | `LEFT_M1`, izquierdo adelante |
| GPIO13 | `LEFT_M0`, izquierdo reversa |
| GPIO14 | `RIGHT_M0`, derecho reversa |
| GPIO15 | `RIGHT_M1`, derecho adelante |
| GPIO4 | LED flash |
| GPIO33 | LED rojo de la placa (activo en bajo) |

  Que GPIO12/13 correspondan físicamente al lado izquierdo no está verificado con el robot en marcha.
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

### Estado de la Tarea 1

- **Firmware** (`firmware/robot_esp32cam/`): compila sin errores ni avisos con el core ESP32 3.3.12 (fqbn `esp32:esp32:esp32cam`; el IDE actualizó el core desde 3.1.0). Usa 33 % de flash y 20 % de RAM. **Subido al robot el 2026-11-02** por COM8: arranca con PSRAM, cámara, AP y servidor web. Para eso, `camera_config_t` se inicializa en ceros y fija `fb_location`/`grab_mode`; antes, con campos sin inicializar, fallaba con `frame buffer malloc failed`. Si la cámara falla, el WiFi y los motores siguen funcionando.
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
- **Borrador del reporte** (`docs/Tarea1/REPORTE.md`): conexiones, diagrama Mermaid, diseño del PWM, código, tablas de las Partes B/C/D por llenar, respuestas de la Parte E con huecos `___` para los datos, y problemas y soluciones.
- **Pendientes y decisiones:** `docs/PENDIENTES.md`.
- **Mediciones pendientes:** L (distancia entre llantas izquierda y derecha), distancia entre ejes, diámetro de llanta, voltaje de la batería, barridos y validación.

### Estado de git

- `main` incluye todo el trabajo de la Tarea 1: el PR igream/ESP32-AI-Robot#1 (rama `tarea1-calibracion`, commit `3918538`) se fusionó el 2026-11-02 con el merge commit `87aa5ce`.
- Antes de eso estaba el commit base `d968dd5`: código del kit, cambio de WiFi, docs y pendientes.
- El firmware estaba originalmente en la raíz como `ESP32_Camera_4WD_Robot_Car_OV3660_V3.ino` y se movió con `git mv`.
- GitHub CLI (`C:/Program Files/GitHub CLI/gh.exe`) está instalado en la máquina `Admin`, con sesión de la cuenta `igream`, y no está en el PATH de Git Bash. En la PC de escritorio no está instalado.
- El repo no tiene CI.
- `build/` contiene el binario original del fabricante y está ignorado.

## Notas del entorno

- **Sistema:** Windows 11, con Git Bash y PowerShell.
- **arduino-cli:**
  - PC de escritorio: `C:/Users/feraz/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe` (versión 1.5.1). El core esp32 3.3.12 está instalado en `%LOCALAPPDATA%\Arduino15`. El ESP32-CAM-MB aparece en COM8 y la subida con reinicio automático funciona sin presionar IO0. Conviene compilar con `--build-path` fuera de Google Drive.
  - Máquina `Admin`: `C:/Program Files/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe`.
- **Driver CH340:** instalado en la PC de escritorio. COM3 y COM4 son Bluetooth, no la placa.
- **Python del sistema:** 3.14. En la PC de escritorio ya tiene numpy, scipy, matplotlib y pyserial. En la máquina `Admin` no tiene scipy y las librerías están en `.venv`.
- **Git Bash:** los heredocs alteran las barras invertidas (`\n`, `\r\n`) en scripts de Python; aplicar parches con el editor de archivos evita ese problema.
- **Finales de línea:** `app_httpd.cpp` usa CRLF; los archivos nuevos usan LF.
- **Mercado Libre:** pide verificación de cuenta para ver búsquedas o fichas en el navegador integrado; los carritos compartidos sí se pueden leer.
