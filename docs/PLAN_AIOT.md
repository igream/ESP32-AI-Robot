# Plan de implementación: Robot AIoT de seguimiento de objetivo

Versión 1 · 2026-11-10 · Autor: chat con Opus · **Entrega: 19 de noviembre de 2026**

Enunciado: `docs/Asignaciones/Tarea_Robot_AIoT_ESP32CAM_EdgeImpulse.docx`, **opción 8**. El robot detecta un objetivo, lo sigue o lo evita según su posición en la imagen, y publica la telemetría de su trayectoria en un dashboard. Toda la inferencia ocurre en el ESP32-CAM; al dashboard solo llegan metadatos.

Convenciones de la versión anterior (`docs/PLAN_IMPLEMENTACION.md`):
- Etiquetas: **[Sonnet]** para implementación con especificación cerrada, **[Opus]** para diseño, revisión o depuración difícil, y **[Fer]** para acciones físicas o en cuentas externas.
- 🛑 **Punto de control:** detenerse y esperar los datos o la confirmación de Fer.
- Al terminar un paso: compilar fuera de Google Drive, hacer commit a nombre de `igream` **sin líneas de atribución**, y marcar la casilla aquí y en `docs/PENDIENTES.md`.

---

## 1. Qué pide el enunciado y de dónde sale cada cosa

| Entregable (rúbrica) | Qué se reutiliza | Qué es nuevo |
|---|---|---|
| Dataset de 100–150 imágenes por clase, con variación de luz, fondo y distancia, más clase de fondo y división entrenamiento/prueba (**20 pts**) | `tarea2.py servir` (captura desde el celular), `subir`, `entrenamiento`, `condiciones.json` y `/capture` en `robot_esp32cam` | Objetos nuevos, 5 fondos, 3 distancias, 2–3 luces, imágenes negativas y un **conjunto de prueba con fondos que el modelo no vio** |
| Proyecto de Edge Impulse: impulse, matriz de confusión y F1 | El mismo flujo de la Tarea 5 (FOMO MobileNetV2 0.35) | Un proyecto nuevo y **dos modelos** para el bonus |
| Modelo en el ESP32-CAM (**20 pts**) | `deteccion_ei`: cámara, recorte de 240×240, corrección de RGB, inferencia, `DET;…`, página web y LEDC de los motores | Firmware `seguimiento_ei` |
| Acción coherente con la detección, umbral ≥ 0.8 (**20 pts**) | Confirmación 2 de 3 cuadros, `mover()`, ω ≈ 192 °/s y v ≈ 72.6 cm/s calibrados en la Tarea 4, y la pose estimada de `robot_motion` | Máquina de estados: buscar → centrar → avanzar → llegó / evitar |
| IoT y dashboard con al menos clase y confianza (**15 pts**) | Nada | Modo WiFi AP+STA, MQTT y dashboard con trayectoria |
| Diagrama de flujo y de arquitectura; firmware documentado (**10 pts**) | Diagramas Mermaid de los reportes anteriores y el README del firmware | Diagramas nuevos |
| Reporte de 4–6 páginas: latencia, memoria, iluminación y falsos positivos | `formato_word.py` y la estructura de `reporte_tarea2.py` | `herramientas/aiot/reporte_aiot.py` |
| Video de 2–3 min (**5 pts**) | Experiencia con los videos de las Tareas 4 y 5 | Guion nuevo |
| **Bonus +10:** comparar dos modelos en latencia y precisión | Registro de entrenamientos de `tarea2.py` | 96×96 contra 64×64 |

---

## 2. Decisiones propuestas (🛑 Fer aprueba o corrige cada una)

| # | Tema | Propuesta | Razón | Alternativa |
|---|---|---|---|---|
| D1 | Objetos | **Dos clases:** `pelota` (objetivo: el robot la sigue) y `cono` (obstáculo: el robot lo evita). Además, imágenes **sin objeto** como negativos. Objetos opacos, de color saturado y distintos entre sí: por ejemplo, una pelota verde o amarilla de 7–10 cm y un cono naranja. | Cumple "sigue **o** evita" con dos acciones distintas, lo que vale más en la rúbrica de acción e innovación. Los objetos opacos evitan el problema que tuvieron los vasos transparentes con el fondo. | Solo `pelota`: menos fotos, pero una sola acción. |
| D2 | Clase de fondo | En FOMO, `background` es implícita. Para cumplir la "clase de fondo" se suben **≥ 100 imágenes sin objetos y sin etiquetas**, y en el reporte aparecen como clase *fondo*. | Así funciona FOMO, y esas imágenes son las que reducen los falsos positivos. | — |
| D3 | IoT | **MQTT → Node-RED con Dashboard 2.0 en la PC.** El broker es **Aedes**, que corre como nodo dentro de Node-RED, así que no hay que instalar Mosquitto. Node 26 ya está instalado. | MQTT es ligero en el ESP32 (`PubSubClient`), aguanta una publicación por cuadro (~1 Hz) y Node-RED dibuja la trayectoria como gráfica XY. | ThingSpeak (nube): sin instalación, pero con un mínimo de 15 s entre envíos, lo que deja una trayectoria muy pobre. |
| D4 | Red | El robot en **AP+STA**: como estación se une a la red de la casa para MQTT, y como punto de acceso conserva `ESP32Det_Fer` para la página del celular. Si no se encuentra la red de la casa, sigue funcionando sin publicar. | La demo no depende de que la red de la casa funcione. | Solo STA: más simple, pero la página del celular necesitaría la red de la casa. |
| D5 | Firmware | Un sketch nuevo, **`firmware/seguimiento_ei`**, copia de `deteccion_ei`. Conserva la cámara, la inferencia, la página y los motores. Se le agregan la máquina de estados, la pose por cálculo muerto y MQTT. `deteccion_ei` queda congelado como entrega de la Tarea 5. | Las tareas quedan separadas y no se arriesga lo que ya funciona. | Modificar `deteccion_ei`. |
| D6 | Control | **A pasos**, por la latencia (~0.8 s por cuadro): capturar, inferir, mover entre 150 y 400 ms con el robot detenido durante la siguiente captura, y repetir. El ángulo de giro es proporcional al error horizontal del centroide. La distancia se estima con la **altura del centroide en la imagen**: con la cámara a 10 cm del piso, un objeto más cercano aparece más abajo. | FOMO no da el tamaño real de la caja, pero sí un centroide confiable. Mover el robot mientras captura borronea la imagen. | Usar el ancho de la caja FOMO (es menos estable). |
| D7 | Bonus | Comparar **dos modelos int8: 96×96 contra 64×64**, con el mismo dataset y la misma división. Se miden la latencia en el ESP32, el F1 de prueba y la memoria. Si sobra tiempo, también **int8 contra float32** del modelo de 96. | El de 64×64 debería acercarse a ~300 ms y mejorar el seguimiento, así que el bonus además sirve para el robot. | Solo int8 contra float32: no hay que reentrenar, pero el resultado es menos útil para el robot. |
| D8 | Alimentación | Para las pruebas, los motores con la **fuente externa en el portapilas** y el ESP32 con el power bank, como en la Tarea 4. Las baterías solo para el video final, conectándolas al final. Se anota el voltaje en cada prueba. | Una batería ya se dañó y los tiempos calibrados dependen del voltaje. | — |
| D9 | Reporte | Word con el formato institucional (`formato_word.py`), de **6 páginas como máximo**, más un anexo con las tablas largas. | Es el mismo flujo que ya funcionó en las Tareas 4 y 5. | — |

---

## 3. Calendario (9 días)

| Fecha | Etapa | Responsable principal |
|---|---|---|
| Lun 10 | Cerrar la **Tarea 5** (prueba autónoma, entrega hoy). Aprobar las decisiones D1–D9. Conseguir los objetos. | Fer |
| Mar 11 | **A1** IoT mínimo con el modelo actual y **A2** el dashboard | Sonnet + Fer |
| Mar 11 – Jue 13 | **B1** captura del dataset v4 (en paralelo con A3) | Fer |
| Mié 12 – Jue 13 | **A3** máquina de estados de seguimiento, probada con el **vaso rojo** del modelo actual | Opus |
| Vie 14 | **B2** subida, etiquetado y entrenamiento de los dos modelos; **B3** despliegue | Fer + Sonnet |
| Sáb 15 – Dom 16 | **C** ajuste del seguimiento con el modelo nuevo y pruebas medidas | Fer + Opus |
| Lun 17 | **D1** diagramas y **D2** borrador del reporte | Sonnet + Opus |
| Mar 18 | **D3** video y reporte final | Fer + Sonnet |
| Mié 19 | Entrega (holgura) | — |

La clave del calendario: **A3 no espera al dataset.** La lógica de seguimiento se desarrolla con el modelo de la Tarea 5, usando el vaso rojo como objetivo. Al cambiar de modelo solo se cambian los nombres de las clases.

---

## 4. Etapa A – Firmware e IoT

### A0. Preparación
- [ ] **A0.1 [Sonnet]** Crear `firmware/seguimiento_ei/` como copia de `deteccion_ei` (sketch, `modelo_ei.h` y README).
  - Cambiar el SSID a `ESP32Seg_Fer` (clave `Seg12345.`).
  - Agregar `secretos.h` (en `.gitignore`) con el SSID y la clave de la red de la casa y la IP del broker, más un `secretos_ejemplo.h` que sí se sube al repo.
  - *Terminado:* compila con la librería de la Tarea 5.
- [ ] **A0.2 [Fer]** Dar la IP fija de la PC en la red de la casa, o reservarla en el router.

### A1. Telemetría MQTT
- [ ] **A1.1 [Sonnet]** Modo WiFi AP+STA y la librería `PubSubClient` (instalarla con `arduino-cli lib install PubSubClient`).
  - La reconexión **no debe bloquear**: un intento cada 5 s.
  - Se publica **una vez por cuadro** en el tema `robot/aiot/telemetria`, con este JSON:
    ```json
    {"t":123456,"n":42,"clase":"pelota","conf":0.93,"cx":51,"cy":70,
     "estado":"AVANZAR","x":35.2,"y":-4.1,"th":-12.0,
     "ms_dsp":26,"ms_clasif":772,"heap":61234,"psram":3912345,"v_bat":null}
    ```
  - Sin detección se publica `clase:"ninguna"` y `conf:0`.
  - Los eventos (cambio de estado, llegada, evasión) se publican en `robot/aiot/evento`.
  - Se mantiene la línea serie `DET;…`/`NONE;…`, para que `tarea2.py pruebas` siga funcionando.
- [ ] **A1.2 [Sonnet]** Medir cuánto cambia el tiempo por cuadro con MQTT activo, comparado con los 806 ms de la Tarea 5.
  - *Terminado:* tabla en el README del firmware.

### A2. Dashboard (Node-RED)
- [ ] **A2.1 [Sonnet]** `herramientas/aiot/nodered/`: instrucciones de instalación (`npm install -g node-red`, más los nodos `node-red-contrib-aedes` y `@flowfuse/node-red-dashboard`) y `flujo.json` para importar.
- [ ] **A2.2 [Sonnet]** El dashboard debe mostrar:
  - **Clase detectada** (texto con color) y **confianza** (indicador de 0 a 1, con el umbral de 0.8 marcado).
  - **Trayectoria** XY en cm, con el robot, el rumbo y las detecciones marcadas en el punto donde ocurrieron.
  - Latencia por cuadro (serie de tiempo), estado de la máquina, contador de seguimientos y evasiones, y la tabla de eventos.
  - Un botón **Reiniciar origen**, que publica en `robot/aiot/cmd`, y un interruptor para activar o desactivar los movimientos.
- [ ] **A2.3 [Sonnet]** Node-RED guarda cada mensaje en `herramientas/aiot/datos/telemetria_<fecha>.csv`. Esos datos alimentan el reporte.
- [ ] **A2.4 [Fer]** Prueba de punta a punta con el modelo actual, sin mover el robot. 🛑 Captura del dashboard con detecciones reales.

### A3. Seguimiento (máquina de estados) [Opus]
- [ ] **A3.1** Estados y transiciones (también serán el diagrama de flujo del reporte):
  - **BUSCAR:** sin objetivo confirmado. Gira unos 30° (~155 ms) y espera a que se estabilice la imagen. Después de 12 pasos (una vuelta) se detiene y publica `perdido`.
  - **CENTRAR:** objetivo confirmado (2 de 3 cuadros con conf ≥ 0.8) y |cx − 48| > tolerancia. Gira θ = k · (cx − 48) · (FOV_h / 96), con la duración calculada desde ω calibrado, y un giro mínimo de 80 ms por la fricción estática del lado derecho.
  - **AVANZAR:** objetivo centrado y lejos (cy < umbral). Avanza un paso de ~15 cm (~200 ms).
  - **LLEGÓ:** objetivo centrado y cerca (cy ≥ umbral). Se detiene, enciende el LED y publica el evento. Si el objetivo se aleja, vuelve a CENTRAR.
  - **EVITAR:** se confirma un `cono` en el tercio central de la imagen. Retrocede un paso, gira 60° hacia el lado contrario al cono, avanza dos pasos y vuelve a BUSCAR.
- [ ] **A3.2** Pose por cálculo muerto: cada movimiento suma su Δx, Δy y Δθ con v, ω y `t90`/`t90d` de la Tarea 4. Se reutilizan las fórmulas de `robot_motion.cpp`.
- [ ] **A3.3** Medir FOV_h y la tabla cy → distancia: objetivo a 20, 40, 60 y 80 cm, al centro y a ±20 cm. Con eso se fijan el umbral de LLEGÓ y la constante k. **[Fer]** mide, **[Opus]** ajusta.
- [ ] **A3.4 [Fer]** Prueba en el piso con el vaso rojo. 🛑 Video corto y CSV de telemetría para revisarlos.

---

## 5. Etapa B – Dataset y modelos

### B1. Captura (dataset v4) [Fer]
- [ ] **B1.1** Subir `robot_esp32cam` (tiene `/capture`) y usar `tarea2.py servir` con una carpeta nueva:
  - `--datos herramientas/aiot/datos/dataset_v4`.
  - Agregar a `condiciones.json` los campos *fondo*, *luz* y *distancia* por foto. **[Sonnet]** adapta `servir` para que se elijan con botones.
- [ ] **B1.2** Matriz de captura por clase (`pelota`, `cono`):

  | Variable | Niveles |
  |---|---|
  | Fondo | 5: piso de la casa, mesa blanca, alfombra o tapete, pared de color y cuarto con muebles |
  | Distancia | 3: ~25, ~50 y ~80 cm |
  | Luz | 2–3: foco de noche, luz natural de día y lámpara lateral |
  | Posición en el cuadro | izquierda, centro y derecha |

  - Meta: **≥ 130 fotos por clase** (5 fondos × 3 distancias × ~9 fotos), más **≥ 100 negativos** con los mismos fondos y sin objetos.
  - Se recomiendan unas 20 fotos con los dos objetos juntos.
- [ ] **B1.3** **Conjunto de prueba fuera de distribución:** un **6.º fondo** que no se usa para entrenar, con 20 fotos por clase y 20 negativos.
- [ ] **B1.4 [Opus]** Probar si fijar la exposición y el balance de blancos de la OV3660 en `/capture` y en el firmware del detector reduce la dependencia de la luz. Decidirlo **antes** de capturar.

### B2. Entrenamiento [Fer + Sonnet]
- [ ] **B2.1 [Fer]** Proyecto nuevo en Edge Impulse ("AIoT Seguimiento"). `tarea2.py subir` con la división 80/20 y el 6.º fondo forzado a *test*.
- [ ] **B2.2** **Modelo A:** FOMO MobileNetV2 0.35, 96×96, RGB e int8. **Modelo B:** igual pero en 64×64.
  - Se registra todo con `tarea2.py entrenamiento`: F1 por clase, matriz de confusión, latencia y RAM estimadas, y capturas del impulse.
- [ ] **B2.3 [Sonnet]** Desplegar los dos modelos en el ESP32 y medir 50 cuadros de cada uno (latencia de DSP y de clasificación, y heap). El que gane se queda en `seguimiento_ei`.

---

## 6. Etapa C – Pruebas medidas (para el reporte)

| Prueba | Procedimiento | Métrica |
|---|---|---|
| C1 Latencia y memoria | 100 cuadros por modelo | Media ± DE de DSP y clasificación, fps, flash y RAM al compilar, heap y PSRAM libres en ejecución |
| C2 Precisión | Conjunto de prueba de Edge Impulse más el 6.º fondo en vivo (20 cuadros por clase) | F1 y matriz de confusión por modelo |
| C3 Iluminación | Mismo montaje con 3 luces, 20 cuadros por luz y objeto | Tasa de detección y confianza media por luz |
| C4 Falsos positivos | 5 min por fondo sin objetos (3 fondos), contando las detecciones ≥ 0.8 y las confirmadas 2 de 3 | Falsos positivos por minuto, antes y después de confirmar |
| C5 Seguimiento | 10 recorridos: la pelota a 1 m, en un ángulo aleatorio de ±45° | Éxito si llega a ≤ 20 cm en ≤ 60 s; tiempo y número de pasos; trayectoria del dashboard |
| C6 Evasión | 5 recorridos con el cono en el camino | Evasiones correctas y choques |

- [ ] **C0 [Sonnet]** `herramientas/aiot/pruebas_aiot.py` lee los CSV de telemetría y produce las tablas y gráficas de C1–C6 (reutilizando el estilo de `tarea2.py resultados`).

---

## 7. Etapa D – Documentación y entrega

- [ ] **D1 [Sonnet]** Diagramas en Mermaid, exportados a PNG:
  - **Arquitectura:** cámara → FOMO → máquina de estados → L298N/motores, y por otro lado WiFi STA → MQTT (Aedes) → Node-RED → dashboard y CSV, con el AP para el celular.
  - **Flujo:** la máquina de estados de A3.1.
  - **Conexiones:** el de la Tarea 4 más el power bank.
- [ ] **D2 [Sonnet + Opus]** `herramientas/aiot/reporte_aiot.py` genera `docs/AIoT/REPORTE_AIoT.docx/.pdf` de 6 páginas como máximo:
  1. Introducción y aplicación
  2. Arquitectura
  3. Dataset
  4. Modelo y comparación (bonus)
  5. Lógica de control
  6. IoT
  7. Resultados C1–C6
  8. Discusión de latencia, memoria, iluminación y falsos positivos
  9. Conclusiones y referencias

  Va acompañado de un anexo con las tablas completas.
- [ ] **D3 [Fer]** Video de 2–3 min, siguiendo este guion:
  1. Presentación y arquitectura (15 s)
  2. Dataset y Edge Impulse (20 s)
  3. Seguimiento de la pelota, con el dashboard en pantalla dividida (60 s)
  4. Evasión del cono (30 s)
  5. Robustez: otro fondo y otra luz (20 s)
  6. Comparación de modelos (15 s)
- [ ] **D4 [Sonnet]** README de `seguimiento_ei` y de `herramientas/aiot/`, enlaces en el README principal, y CLAUDE.md y PENDIENTES actualizados.

---

## 8. Riesgos y planes B

| Riesgo | Señal | Plan B |
|---|---|---|
| El modelo nuevo falla fuera del montaje | F1 < 0.8 en el 6.º fondo | Más negativos y fotos del fondo problemático; fijar la exposición (B1.4); o bajar la exigencia a 2 fondos para la demo y reportar el límite |
| Memoria con WiFi STA, MQTT, web y modelo | Reinicios o `malloc` fallido | Apagar `/foto` durante el seguimiento, reducir `JPG_MAX` o usar el modelo de 64×64 |
| La red de la casa no está disponible en la demo | Sin MQTT | Hotspot del celular como red STA, con la PC conectada al mismo hotspot |
| El seguimiento oscila | Gira de un lado a otro | Bajar k, aumentar la tolerancia o usar el promedio de 2 cuadros |
| Batería o brownout con motores y WiFi | LED rojo parpadea | Fuente externa en el portapilas, como en la Tarea 4 |
| Falta de tiempo | Retraso de más de 1 día en B | Recortar la evasión del cono a "detenerse y alertar" y quitar el float32 del bonus |
