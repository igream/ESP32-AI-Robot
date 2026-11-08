# deteccion_ei (Tarea 2)

Sketch de detección con FOMO. Para compilarlo hace falta la librería de Arduino exportada de Edge Impulse (T2.5.1):

1. Guarda el ZIP en `firmware/deteccion_ei/lib/` e instálalo (`arduino-cli lib install --zip-path <zip>`; si lo rechaza, `arduino-cli config set library.enable_unsafe_install true`).
2. En `modelo_ei.h` cambia `NOMBRE_DEL_PROYECTO_inferencing.h` por el nombre real de la librería.
3. Compila con `--fqbn esp32:esp32:esp32cam --build-path <fuera de Drive>` y sube por COM8.

Salida serie (115200): `INFO;…`, `DET;t;dsp;clasif;etiqueta;prob;cx;cy;w;h` y `NONE;t;dsp;clasif`. El LED flash destella 200 ms con cada detección ≥ umbral.
Este sketch reemplaza al firmware del robot; para volver a moverlo, sube de nuevo `firmware/robot_esp32cam`.

Estado (2026-11-08): compilado con la librería real (`Tarea2_Objetos_inferencing`, core 3.3.12, 14 % de flash) y probado en el robot por COM9: 772 ms de clasificación + 26 ms de procesado (~1 cuadro/s). Con el vaso rojo a 55 cm detecta `vasorojo` con prob. ~0.996 en 36 de 36 cuadros.

Importante: en este core `fmt2rgb888` entrega los bytes en orden R,G,B (no B,G,R como en el ejemplo de Edge Impulse). Con el orden del ejemplo el vaso rojo se veía azul y no se detectaba nada.

Depuración: enviar `i` por el serie vuelca la imagen de 96×96 que ve el modelo (`IMG;96;96;<hex RGB>`).

## Gestos (2026-11-08)

Al detectar una clase en 2 de 3 cuadros seguidos, el robot hace un gesto corto con los motores (PWM 140): vasorojo asiente, jarraroja niega y laptop gira una vuelta (tiempo fijo, sin calibrar). Tras el gesto hay una pausa de 3 s. Salida serie: `GESTO;t;clase`. El comando serie `g` activa o desactiva los gestos (conviene apagarlos en las 45 pruebas si hay baterías conectadas). `USAR_GESTOS 0` en el sketch deja solo la detección. Con las baterías desconectadas los motores no se mueven (solo se probó por serie).
