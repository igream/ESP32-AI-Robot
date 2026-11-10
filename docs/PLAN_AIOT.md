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

## 2. Decisiones (revisadas por Fer el 2026-11-10)

Las que tienen ✅ ya están aprobadas. D2, D5 y D9 no recibieron comentarios y se toman como aprobadas.

| # | Tema | Propuesta | Razón | Alternativa |
|---|---|---|---|---|
| D1 ✅ | Objetos | **Aprobado con cambio (Fer, 2026-11-10).** Dos clases: **`jabonzote`** (objetivo: el robot lo sigue), que es una barra de jabón Zote con su envoltura, y **`vasoalreves`** (obstáculo tipo cono: el robot lo evita), que son los vasos de la Tarea 5 boca abajo y **con cinta**, para que dejen de ser transparentes. Además, imágenes **sin objeto** como negativos. | Cumple "sigue **o** evita" con dos acciones distintas. La cinta le da al vaso un aspecto que no cambia con el fondo, que fue la causa de los fallos de la Tarea 5. | — |
| D2 | Clase de fondo | En FOMO, `background` es implícita. Para cumplir la "clase de fondo" se suben **≥ 100 imágenes sin objetos y sin etiquetas**, y en el reporte aparecen como clase *fondo*. | Así funciona FOMO, y esas imágenes son las que reducen los falsos positivos. | — |
| D3 ✅ | IoT | **MQTT → Node-RED con Dashboard 2.0 en la PC.** El broker es **Aedes**, que corre como nodo dentro de Node-RED, así que no hay que instalar Mosquitto. Node 26 ya está instalado. | MQTT es ligero en el ESP32 (`PubSubClient`), aguanta una publicación por cuadro (~1 Hz) y Node-RED dibuja la trayectoria como gráfica XY. | ThingSpeak (nube): sin instalación, pero con un mínimo de 15 s entre envíos, lo que deja una trayectoria muy pobre. |
| D4 ✅ | Red | El robot en **AP+STA**: como estación se une a la red de la casa para MQTT, y como punto de acceso conserva `ESP32Det_Fer` para la página del celular. Si no se encuentra la red de la casa, sigue funcionando sin publicar. | La demo no depende de que la red de la casa funcione. | Solo STA: más simple, pero la página del celular necesitaría la red de la casa. |
| D5 | Firmware | Un sketch nuevo, **`firmware/seguimiento_ei`**, copia de `deteccion_ei`. Conserva la cámara, la inferencia, la página y los motores. Se le agregan la máquina de estados, la pose por cálculo muerto y MQTT. `deteccion_ei` queda congelado como entrega de la Tarea 5. | Las tareas quedan separadas y no se arriesga lo que ya funciona. | Modificar `deteccion_ei`. |
| D6 ✅ | Control | **Aprobado con cambio (Fer, 2026-11-10).** El control es **a pasos**, por la latencia (~0.8 s por cuadro): capturar, inferir, mover con el robot detenido durante la siguiente captura, y repetir. **Cómo se calcula cada movimiento no se fija de antemano:** se comparan varios métodos para estimar el ángulo y la distancia (paso A3.3) y se usa el que dé menos error. | FOMO solo da un centroide y una caja de celdas, así que hay que medir qué estimación funciona mejor con esta cámara. | — |
| D7 ✅ | Bonus | Comparar **dos modelos int8: 96×96 contra 64×64**, con el mismo dataset y la misma división. Se miden la latencia en el ESP32, el F1 de prueba y la memoria. Si sobra tiempo, también **int8 contra float32** del modelo de 96. | El de 64×64 debería acercarse a ~300 ms y mejorar el seguimiento, así que el bonus además sirve para el robot. | Solo int8 contra float32: no hay que reentrenar, pero el resultado es menos útil para el robot. |
| D8 ✅ | Alimentación | **Corregido por Fer (2026-11-10): todas las pruebas con movimiento se hacen con las pilas 18650**, no con la fuente externa, porque con el robot en movimiento la fuente se puede desconectar y hacer un corto. El **voltaje que llega al driver** (bornes +12V/GND del L298N) se mide con el multímetro al inicio de cada sesión y cada ~10 recorridos, se escribe en el dashboard y queda en la telemetría. Antes de conectar las pilas se revisan su voltaje y su polaridad. Opcional: compensar la duración de los movimientos con t = t_cal · V_cal / V_medido (V_cal ≈ 12 V, de la Tarea 4). | Es la alimentación real del robot, y los tiempos calibrados dependen del voltaje. | — |
| D9 | Reporte | Word con el formato institucional (`formato_word.py`), de **6 páginas como máximo**, más un anexo con las tablas largas. | Es el mismo flujo que ya funcionó en las Tareas 4 y 5. | — |

---

## 3. Calendario (9 días)

| Fecha | Etapa | Responsable principal |
|---|---|---|
| Lun 10 | Cerrar la **Tarea 5** (prueba autónoma, entrega hoy). Decisiones D1–D9 revisadas. Ponerle cinta a los vasos y tener a la mano el jabón Zote. | Fer |
| Mar 11 | **A1** IoT mínimo con el modelo actual y **A2** el dashboard | Sonnet + Fer |
| Mar 11 – Jue 13 | **B1** captura del dataset v4 (en paralelo con A3) | Fer |
| Mié 12 – Jue 13 | **A3** máquina de estados de seguimiento, probada con el **vaso rojo** del modelo actual | Opus |
| Vie 14 | **B2** subida, etiquetado y entrenamiento de los dos modelos; **B3** despliegue | Fer + Sonnet |
| Sáb 15 – Dom 16 | **C** ajuste del seguimiento con el modelo nuevo y pruebas medidas | Fer + Opus |
| Lun 17 | **D1** diagramas y **D2** borrador del reporte | Sonnet + Opus |
| Mar 18 | **D3** video y reporte final | Fer + Sonnet |
| Mié 19 | Entrega (holgura) | — |

La clave del calendario: **A3 no espera al dataset.** La lógica de seguimiento se desarrolla con el modelo de la Tarea 5, usando `vasorojo` como objetivo y `jarraroja` como obstáculo. Al cambiar de modelo solo se cambian los nombres de las clases (`jabonzote` y `vasoalreves`).

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
    {"t":123456,"n":42,"clase":"jabonzote","conf":0.93,"cx":51,"cy":70,
     "estado":"AVANZAR","x":35.2,"y":-4.1,"th":-12.0,
     "ms_dsp":26,"ms_clasif":772,"heap":61234,"psram":3912345,"v_driver":11.9}
    ```
  - Sin detección se publica `clase:"ninguna"` y `conf:0`.
  - `v_driver` es el último voltaje medido en el driver que Fer escribió en el dashboard (llega por `robot/aiot/cmd`).
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
  - Un campo **Voltaje en el driver (V)** que Fer llena con la medición del multímetro. Se manda al robot por `robot/aiot/cmd`, queda en la telemetría y, si se activa la compensación de D8, ajusta la duración de los movimientos.
- [ ] **A2.3 [Sonnet]** Node-RED guarda cada mensaje en `herramientas/aiot/datos/telemetria_<fecha>.csv`. Esos datos alimentan el reporte.
- [ ] **A2.4 [Fer]** Prueba de punta a punta con el modelo actual, sin mover el robot. 🛑 Captura del dashboard con detecciones reales.

### A3. Seguimiento (máquina de estados) [Opus]
- [ ] **A3.1** Estados y transiciones (también serán el diagrama de flujo del reporte):
  - **BUSCAR:** sin objetivo confirmado. Gira unos 30° (~155 ms) y espera a que se estabilice la imagen. Después de 12 pasos (una vuelta) se detiene y publica `perdido`.
  - **CENTRAR:** objetivo confirmado (2 de 3 cuadros con conf ≥ 0.8) y su ángulo estimado está fuera de la tolerancia. Gira el ángulo estimado con el método elegido en A3.3. La duración sale de ω calibrado (con `t90` a la izquierda y `t90d` a la derecha), con un giro mínimo de 80 ms por la fricción estática del lado derecho.
  - **AVANZAR:** objetivo centrado y con distancia estimada mayor a la de llegada. Avanza lo que falte, con un máximo de ~15 cm por paso.
  - **LLEGÓ:** objetivo centrado y a la distancia de llegada (~20 cm) o menos. Se detiene, enciende el LED y publica el evento. Si el objetivo se aleja, vuelve a CENTRAR.
  - **EVITAR:** se confirma un `vasoalreves` en el tercio central de la imagen. Retrocede un paso, gira 60° hacia el lado contrario al vaso, avanza dos pasos y vuelve a BUSCAR.
- [ ] **A3.2** Pose por cálculo muerto: cada movimiento suma su Δx, Δy y Δθ con v, ω y `t90`/`t90d` de la Tarea 4. Se reutilizan las fórmulas de `robot_motion.cpp`.
- [ ] **A3.3 Comparación de métodos para calcular el movimiento (decisión D6).** FOMO entrega el centroide (cx, cy) y una caja (w, h) en una cuadrícula de 12×12 celdas de 8 px con el modelo de 96×96 (8×8 con el de 64×64). De ahí hay que estimar **cuánto girar** y **cuánto avanzar**.

  **Métodos candidatos para el ángulo** (desde cx):

  | Clave | Método | Fórmula o idea |
  |---|---|---|
  | θ1 | Lineal con el campo de visión | θ = (cx − 48) · FOV_h / 96 |
  | θ2 | Cámara estenopeica | θ = atan((cx − 48) / f_px), con f_px = 48 / tan(FOV_h / 2) |
  | θ3 | Regresión sobre los datos | Polinomio de grado 1 o 2, cx → θ medido |
  | θ4 | Por zonas (referencia) | Tres zonas: izquierda, centro y derecha, con un giro fijo de ~15° |

  **Métodos candidatos para la distancia:**

  | Clave | Método | Fórmula o idea |
  |---|---|---|
  | d1 | Geometría del piso | Cámara a h ≈ 10 cm con inclinación α: d = h / tan(α + (cy − cy₀) / f_px). Se ajustan α y cy₀. |
  | d2 | Tamaño de la caja | d = a / w + b (también se prueba con el área w·h) |
  | d3 | Regresión combinada | 1/d = c₀ + c₁·cy + c₂·w |
  | d4 | Tabla interpolada | cy → d, interpolación lineal entre puntos medidos |

  **Conversión a tiempo de motor**, que también se compara:
  - (m1) Usar directamente ω y v calibrados en la Tarea 4.
  - (m2) Incluir la ordenada al origen de la regresión tiempo → ángulo/distancia (pérdida al arrancar y frenar).
  - En los dos casos se puede aplicar la compensación por voltaje de D8.

  **Procedimiento:**
  1. **[Fer] Datos de calibración:** se coloca el objetivo en una cuadrícula medida con cinta y transportador:
     - Distancias: 20, 30, 45, 60, 80 y 100 cm.
     - Ángulos: −25°, −15°, 0°, +15° y +25°.
     - Se toman 3 cuadros por punto, unos 90 en total, y se repite con los dos objetos.
     - **[Sonnet]** escribe `herramientas/aiot/estimacion.py captura --d 45 --ang 15 --puerto COMx`, que lee las líneas `DET;…` (ya traen cx, cy, w y h) y las guarda en `herramientas/aiot/datos/estimacion.csv`.
  2. **[Sonnet] Evaluación fuera de línea:** `estimacion.py comparar` ajusta cada método con validación cruzada (se deja fuera una distancia o un ángulo a la vez).
     - Reporta el **RMSE** y el **MAE** del ángulo (°) y de la distancia (cm), y el porcentaje de estimaciones dentro de ±5° y ±5 cm.
     - Genera las gráficas de valor estimado contra valor real.
     - Se repite con el modelo de 64×64 cuando exista (alimenta el bonus).
  3. **[Opus] Preselección:** se quedan los **2 mejores métodos** de ángulo y de distancia. Si dos métodos difieren menos de ~10 % en RMSE, se prefiere el más simple.
  4. **[Fer] Evaluación en lazo cerrado:** el firmware deja **elegir el método con un comando** (`metodo θ2 d1 m2` por serie o MQTT), así que no hay que recompilar. Se hacen 5 recorridos por combinación preseleccionada (un C5 reducido). Se mide el número de pasos, el tiempo para llegar y el error final.
  5. **Elección:** la combinación con menor error final y menos pasos queda fija en el firmware.
  6. La tabla comparativa y las gráficas van al reporte: justifican la decisión y aportan al análisis.
  - Nota: la cuadrícula de 8 px limita la resolución a unos 4–5° por celda. Promediar el centroide de los 2–3 cuadros de la confirmación lo mejora, y eso también se mide.
- [ ] **A3.4 [Fer]** Prueba en el piso con el vaso rojo (objetivo) y la jarra (obstáculo), con las pilas y el voltaje anotado. 🛑 Video corto y CSV de telemetría para revisarlos.

---

## 5. Etapa B – Dataset y modelos

### B1. Captura (dataset v4) [Fer]
- [ ] **B1.1** Subir `robot_esp32cam` (tiene `/capture`) y usar `tarea2.py servir` con una carpeta nueva:
  - `--datos herramientas/aiot/datos/dataset_v4`.
  - Agregar a `condiciones.json` los campos *fondo*, *luz* y *distancia* por foto. **[Sonnet]** adapta `servir` para que se elijan con botones.
- [ ] **B1.2** Matriz de captura por clase (`jabonzote`, `vasoalreves`):

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
| C5 Seguimiento | 10 recorridos: el jabón a 1 m, en un ángulo aleatorio de ±45° | Éxito si llega a ≤ 20 cm en ≤ 60 s; tiempo y número de pasos; trayectoria del dashboard |
| C6 Evasión | 5 recorridos con el vaso al revés en el camino | Evasiones correctas y choques |

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
  3. Seguimiento del jabón, con el dashboard en pantalla dividida (60 s)
  4. Evasión del vaso al revés (30 s)
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
| Batería baja o brownout con motores y WiFi | El LED rojo parpadea o el voltaje en el driver baja de ~11 V | Recargar las pilas antes de cada sesión, medir el voltaje en el driver y activar la compensación de D8. No usar la fuente externa con el robot en movimiento (riesgo de corto) |
| Los vasos con cinta se confunden entre sí o con el jabón | Confusión en la matriz de Edge Impulse | Cinta de un color distinto al envoltorio del Zote; más fotos con los dos objetos juntos |
| Falta de tiempo | Retraso de más de 1 día en B | Recortar la evasión del vaso a "detenerse y alertar" y quitar el float32 del bonus |
