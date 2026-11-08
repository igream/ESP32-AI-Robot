# deteccion_ei (Tarea 2)

Sketch de detección con FOMO. Para compilarlo hace falta la librería de Arduino exportada de Edge Impulse (T2.5.1):

1. Guarda el ZIP en `firmware/deteccion_ei/lib/` e instálalo (`arduino-cli lib install --zip-path <zip>`; si lo rechaza, `arduino-cli config set library.enable_unsafe_install true`).
2. En `modelo_ei.h` cambia `NOMBRE_DEL_PROYECTO_inferencing.h` por el nombre real de la librería.
3. Compila con `--fqbn esp32:esp32:esp32cam --build-path <fuera de Drive>` y sube por COM8.

Salida serie (115200): `INFO;…`, `DET;t;dsp;clasif;etiqueta;prob;cx;cy;w;h` y `NONE;t;dsp;clasif`. El LED flash destella 200 ms con cada detección ≥ umbral.
Este sketch reemplaza al firmware del robot; para volver a moverlo, sube de nuevo `firmware/robot_esp32cam`.

Estado (2026-11-07): compila contra una librería de prueba (stub), no contra la de Edge Impulse; sin probar en el robot.
