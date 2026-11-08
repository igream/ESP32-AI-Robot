# ESP32-AI-Robot

Robot móvil de 4 ruedas con **ESP32-CAM** para el curso de Robótica (UAEMéx). Tiene dos partes independientes:

- **Movimiento:** firmware del robot con calibración de giros y avance, y una página web para medirlos (Tarea 4).
- **Visión:** detector de objetos (FOMO de Edge Impulse) que corre completo en el ESP32-CAM, sin internet, y hace un gesto al detectar (Tarea 5).

## Contenido

| Carpeta | Qué hay |
|---|---|
| `firmware/robot_esp32cam/` | Firmware del robot: WiFi propio, video, movimientos y página `/tarea1` |
| `firmware/deteccion_ei/` | Detector de objetos con gestos (necesita tu librería de Edge Impulse) |
| `herramientas/` | Scripts de PC: `calibrar.py`, `tarea1_descargar.py`, `reporte_pdf.py` |
| `herramientas/tarea2/` | App de PC de la detección: captura, subida, pruebas y resultados |
| `docs/` | Enunciados, planes y reportes |

## Material

Kit LaFvin ESP32 Camera 4WD Robot Car V3 (ESP32-CAM AI-Thinker con cámara OV3660, driver L298N, 4 motores TT, 3 baterías 18650), placa de programación ESP32-CAM-MB (CH340) y un power bank.

## Requisitos

- Arduino IDE o `arduino-cli` con el core **esp32 3.3.12** (placa `esp32:esp32:esp32cam`).
- Python 3 con `pyserial`, `numpy`, `scipy` y `matplotlib` (`pip install -r herramientas/requirements.txt`).
- Para la visión: Node.js, Edge Impulse CLI (`npm install -g edge-impulse-cli`) y una cuenta gratuita de Edge Impulse.

## Cómo usarlo

**Probar el robot**
1. Compila y sube `firmware/robot_esp32cam/` a la placa.
2. Conéctate al WiFi del robot (nombre y contraseña en `robot_esp32cam.ino`) y abre `http://192.168.4.1/tarea1`.

**Hacer tu propio detector**
1. Sube `robot_esp32cam` y arma un montaje fijo (cámara a altura constante, fondo y luz iguales, sin flash).
2. `python herramientas/tarea2/tarea2.py condiciones` define tus objetos y `... servir` abre una página para tomar al menos 50 fotos por objeto desde el celular.
3. `... subir` las manda a Edge Impulse (primero `edge-impulse-uploader --clean` para iniciar sesión). En el Studio etiqueta con cuadros, crea el impulse (96×96) con el bloque FOMO, entrena y exporta la **librería de Arduino**.
4. Instala el ZIP, pon el nombre de su `.h` en `firmware/deteccion_ei/modelo_ei.h`, compila y sube `firmware/deteccion_ei/`.
5. `... pruebas --web --puerto COMx` guarda las 45 pruebas desde el celular y `... resultados` genera tablas y gráficas.

Cada subcomando tiene ayuda con `--help`, y `tarea2.py estado` dice qué etapa sigue.

## Avisos

- Los motores TT son de unos 6 V: el firmware limita el PWM. No uses encendido total con 12 V.
- Conecta las baterías al final, con el ESP32 ya alimentado, para evitar picos de voltaje.
- `deteccion_ei` reemplaza al firmware del robot: para volver a moverlo o capturar fotos, sube otra vez `robot_esp32cam`.
- Si el robot detecta, hace gestos con los motores; `USAR_GESTOS 0` en el sketch los desactiva.

Más detalle del proyecto, decisiones y estado en `CLAUDE.md` y `docs/`.
