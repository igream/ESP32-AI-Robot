#!/usr/bin/env python3
"""Genera el reporte de la Tarea 4 del curso (en el repo, "Tarea 1": robot móvil diferencial) en docx + PDF,
con el formato institucional de la skill de Ciencia de Datos (igual que el de la Tarea 5) y la estructura que pide
el enunciado: portada e integrantes, objetivo, materiales y diagrama de conexión, código comentado, resultados
(tablas y fotos), respuestas del análisis, problemas y soluciones, conclusiones.

Datos: último docs/Tarea1/tarea1_*.json exportado desde la página /tarea1 (Parte B, mediciones físicas y corridas
de E2/E3) más las corridas de validación de la sesión final (SESION2, anotadas a mano de la página).
Salida: docs/Tarea1/REPORTE_Tarea4.docx (+ .pdf si Word está instalado) y docs/Tarea1/img/*.png

Uso:  python herramientas/reporte_tarea1.py [--sin-pdf]
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mi
import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "tarea2"))
import reporte_tarea2 as rt  # noqa: E402  (reutiliza P, crear_tabla y el estilo de la skill)

from builder_documento_base import (cargar_plantilla_base, agregar_titulo_seccion, insertar_imagen,  # noqa: E402
                                    agregar_referencias_ieee, exportar_pdf_word, agregar_parrafo)
from generador_graficos_base import configurar_estilo_uaemex, guardar_grafico  # noqa: E402

RAIZ = AQUI.parent
SALIDA = RAIZ / "docs" / "Tarea1"
REC = SALIDA / "Recursos"
IMG = SALIDA / "img"
P = rt.P
_tabla = rt.crear_tabla


def _limpia(x):
    return x.replace("`", "").replace("**", "") if isinstance(x, str) else x


def crear_tabla(doc, enc, filas, **kw):
    """Igual que la de reporte_tarea2, pero sin marcas de Markdown en las celdas."""
    return _tabla(doc, [_limpia(e) for e in enc], [[_limpia(c) for c in f] for f in filas], **kw)
FECHA = "Toluca, Estado de México, noviembre de 2026"

# Corridas de validación con el robot caliente (sesión final), (ms, valor, desviación lateral cm o None).
# Se anotaron desde la página /tarea1; la corrida de 360° a 1765 ms que dio 310° se excluyó por atípica.
SESION2 = {
    "adelante": [(1390, 104.5, 4.5), (1390, 104.5, 4.5), (1390, 105.0, 5.0), (1390, 105.0, 5.0), (1390, 104.5, 4.5),
                 (1325, 98.0, -2.0), (1325, 98.0, -2.0), (1325, 97.0, -3.0)],
    "giro_izq": [(480, 90, None), (480, 90, None), (480, 88, None), (480, 88, None), (480, 87, None)],
    "giro_der": [(520, 91, None), (520, 89, None), (520, 91, None), (520, 91, None), (520, 90, None)],
    "giro360": [(2145, 342, None), (2145, 392, None), (2145, 380, None), (2145, 393, None), (2145, 420, None),
                (2145, 418, None), (2145, 426, None), (2145, 415, None), (2145, 423, None), (2145, 413, None),
                (1842, 380, None), (1842, 369, None), (1842, 378, None), (1842, 376, None), (1842, 378, None),
                (1842, 374, None), (1765, 370, None), (1765, 370, None), (1765, 369, None), (1765, 367, None),
                (1765, 367, None), (1765, 368, None), (1765, 367, None)],
}
ERRORES_CAPTURA = {23, 26, 32}            # ids del JSON con ángulo mal escrito o dato descartado por el autor
CORRECCION = {35: 100.0}                   # id 35: se escribió 1000 y era 100 cm
OBJETIVO = {"adelante": 100, "atras": 100, "giro_izq": 90, "giro_der": 90, "giro360": 360}
TOL = {"adelante": 3, "atras": 3, "giro_izq": 5, "giro_der": 5, "giro360": 10}
TIEMPO_FINAL = {"adelante": 1340, "atras": 1490, "giro_izq": 480, "giro_der": 520, "giro360": 1740}
NOMBRE = {"adelante": "Adelante", "atras": "Atrás", "giro_izq": "Izquierda", "giro_der": "Derecha", "giro360": "360°"}


def cargar():
    ruta = sorted((SALIDA).glob("tarea1_*.json"))[-1]
    d = json.loads(ruta.read_text(encoding="utf-8"))
    corr = {k: [] for k in OBJETIVO}
    for c in d["calib"]:
        k = "giro360" if c["mov"] == "giro360" else c["mov"]
        if c["id"] in ERRORES_CAPTURA or k not in corr:
            continue
        m = c["medido"]
        v = m.get("avance_cm", m.get("angulo_deg"))
        v = CORRECCION.get(c["id"], v)
        corr[k].append((c["ms"], v, m.get("desviacion_cm")))
    # El 360° de la sesión inicial (a mano, 2000-2250 ms) queda como primeras corridas
    for k, lista in SESION2.items():
        corr[k].extend(lista)
    return d, corr, ruta.name


def ultimas(corr, k, n=3):
    t = TIEMPO_FINAL[k]
    return corr[k][-n:]


# ------------------------------------------------------------------ figuras
def figura_convergencia(corr):
    configurar_estilo_uaemex(font_size=7.5)
    fig, axs = plt.subplots(2, 3, figsize=(8, 4.4))
    ejes = axs.ravel()
    for ax, k in zip(ejes, OBJETIVO):
        datos = corr[k]
        x = np.arange(1, len(datos) + 1)
        y = np.array([v for _, v, _ in datos])
        ms = np.array([m for m, _, _ in datos])
        ob, tl = OBJETIVO[k], TOL[k]
        ax.axhspan(ob - tl, ob + tl, color="#BFD7EA", alpha=0.7, label=f"{ob} ± {tl}")
        ax.axhline(ob, color="#0F172A", lw=0.8)
        sc = ax.scatter(x, y, c=ms, cmap="viridis", s=14, zorder=3)
        ax.plot(x, y, color="#64748B", lw=0.5, zorder=2)
        ax.set_title(NOMBRE[k] + (" (cm)" if k in ("adelante", "atras") else " (°)"), fontsize=8)
        ax.set_xlabel("Corrida")
        ax.set_ylim(min(y.min(), ob - tl) - 0.06 * ob, min(y.max(), ob * 1.45) + 0.06 * ob)
        cb = fig.colorbar(sc, ax=ax, pad=0.01)
        cb.set_label("ms", fontsize=7)
        cb.ax.tick_params(labelsize=6)
    ejes[-1].axis("off")
    ejes[-1].text(0.0, 0.5, "Banda azul: tolerancia del enunciado.\nColor: duración usada en la corrida.\n"
                  "Se excluyeron 3 datos mal capturados\ny 1 atípico de 360° (310°).", fontsize=7.5, va="center")
    fig.tight_layout()
    ruta = IMG / "fig_t4_convergencia.png"
    guardar_grafico(fig, str(ruta), dpi=300)
    return ruta


def figura_fotos():
    """Robot armado, diagrama de conexiones y medición de voltaje."""
    configurar_estilo_uaemex(font_size=8.0)
    fig = plt.figure(figsize=(8, 3.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.5, 1.45, 0.5], wspace=0.05)
    for i, (n, t) in enumerate([("RobotArmado.jpeg", "a) Robot armado"), ("DiagramaConexiones.png", "b) Diagrama de conexiones (kit)"),
                                ("T1 Medición Voltaje.jpeg", "c) Voltaje en reposo: 12.11 V")]):
        ax = fig.add_subplot(gs[i])
        ax.imshow(mi.imread(str(REC / n)))
        ax.axis("off")
        ax.set_title(t, fontsize=7.5, loc="left")
    ruta = IMG / "fig_t4_fotos.png"
    guardar_grafico(fig, str(ruta), dpi=300)
    return ruta


def figura_pagina():
    configurar_estilo_uaemex(font_size=8.0)
    fig = plt.figure(figsize=(3.0, 5.2))
    ax = fig.add_subplot(111)
    ax.imshow(mi.imread(str(REC / "T1 Registro Tiempos.jpeg")))
    ax.axis("off")
    ruta = IMG / "fig_t4_pagina.png"
    guardar_grafico(fig, str(ruta), dpi=200)
    return ruta


def captura_codigo(archivo, ini, fin, nombre):
    """Imagen del código con resaltado de sintaxis (equivale a una captura del editor)."""
    from pygments import highlight
    from pygments.formatters import ImageFormatter
    from pygments.lexers import CppLexer
    lineas = (RAIZ / archivo).read_text(encoding="utf-8").splitlines()[ini - 1:fin]
    fmt = ImageFormatter(font_name="Consolas", font_size=20, line_numbers=True, line_number_start=ini,
                         style="friendly", image_pad=12, line_pad=4)
    ruta = IMG / nombre
    ruta.write_bytes(highlight("\n".join(lineas) + "\n", CppLexer(), fmt))
    return ruta


# ------------------------------------------------------------------ cálculos
def resumen(vals):
    a = np.array(vals, float)
    return a.mean(), (a.std(ddof=1) if len(a) > 1 else 0.0)


def portada(doc):
    ps = doc.paragraphs

    def poner(p, texto):
        runs = p.runs
        runs[0].text = texto
        for r in runs[1:]:
            r.text = ""
    poner(ps[7], "Robótica")
    poner(ps[9], "Tarea 4")
    ps[10].runs[1].text = "PRUEBA DE FUNCIONALIDAD DE UN ROBOT MÓVIL DIFERENCIAL"
    ps[15]._element.getparent().remove(ps[15]._element)
    for p in doc.paragraphs:
        if p.text.strip() == "O1":
            poner(p, rt.GRUPO)
        elif "LEDEZMA" in p.text:
            poner(p, "\t" + rt.DOCENTE)
        elif p.text.startswith("Toluca"):
            poner(p, FECHA)
    doc.add_page_break()


def construir():
    SALIDA.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    d, corr, nombre_json = cargar()
    f = d["fisicas"]
    L = np.mean(f["L_cm"])
    ejes = np.mean(f["ejes_cm"])
    diam = np.mean(f["diam_cm"])
    pb = d["parteB"]
    ib, db = resumen(pb["izq"]), resumen(pb["der"])

    # Parte D: últimas 3 corridas de cada movimiento con el tiempo cercano al final
    D = {k: ultimas(corr, k) for k in OBJETIVO}
    # Estimaciones cinemáticas con las corridas finales
    v_ade = np.mean([v / (ms / 1000) for ms, v, _ in D["adelante"]])
    v_atr = np.mean([v / (ms / 1000) for ms, v, _ in D["atras"]])
    v = (v_ade + v_atr) / 2
    w_izq = np.mean([np.radians(a) / (ms / 1000) for ms, a, _ in D["giro_izq"]])
    w_der = np.mean([np.radians(a) / (ms / 1000) for ms, a, _ in D["giro_der"]])
    w_360 = np.mean([np.radians(a) / (ms / 1000) for ms, a, _ in D["giro360"]])
    w = np.mean([w_izq, w_der, w_360])
    Lef = 2 * v / w
    t90_teo = np.pi * L / (4 * v) * 1000
    t90_med = np.mean([TIEMPO_FINAL["giro_izq"], TIEMPO_FINAL["giro_der"]])
    desv_ade = [x for _, _, x in D["adelante"]]
    desv_atr = [x for _, _, x in corr["atras"] if x is not None]

    f_conv = figura_convergencia(corr)
    f_fot = figura_fotos()
    f_pag = figura_pagina()
    c1 = captura_codigo("firmware/robot_esp32cam/robot_motion.cpp", 106, 129, "cod_t4_motores.png")
    c2 = captura_codigo("firmware/robot_esp32cam/robot_motion.cpp", 443, 459, "cod_t4_secuencia.png")

    doc = cargar_plantilla_base()
    portada(doc)

    # ---------------- 1. Objetivo
    agregar_titulo_seccion(doc, "1. OBJETIVO")
    P(doc, "Armar y verificar un robot móvil de ruedas con arquitectura diferencial (**kit LaFvin ESP32 Camera 4WD**, driver **L298N**, cuatro "
           "motores TT y baterías 18650) y programar rutinas reutilizables de movimiento (adelante, atrás, giro a la izquierda, giro a la derecha y "
           "vuelta de 360° sobre su eje). Después, **calibrar el tiempo de cada rutina** midiendo el movimiento real en el piso para saber con "
           "precisión cuánto se mueve el robot, y contrastar lo medido con el modelo cinemático diferencial.")

    # ---------------- 2. Materiales y diagrama
    agregar_titulo_seccion(doc, "2. MATERIALES Y DIAGRAMA DE CONEXIÓN")
    P(doc, "Se usó el kit completo con una **ESP32-CAM AI-Thinker** (cámara OV3660) programada por una placa **ESP32-CAM-MB** (CH340), el driver "
           "L298N, tres baterías 18650 (12.1 V cargadas), cinta métrica, cinta de color, multímetro y un celular para controlar y grabar. Se programó con "
           "`arduino-cli` y el core ESP32 3.3.12. Los dos motores de cada lado van en paralelo, por lo que el robot se comporta como diferencial y gira "
           "derrapando. La Tabla 1 muestra las conexiones y la Figura 1 las fotos del robot armado, el diagrama y la medición del voltaje.")
    crear_tabla(doc, ["ESP32-CAM", "L298N", "Función"],
                [["GPIO12", "IN1", "Lado izquierdo, adelante (`LEFT_M1`)"],
                 ["GPIO13", "IN2", "Lado izquierdo, reversa (`LEFT_M0`)"],
                 ["GPIO14", "IN3", "Lado derecho, reversa (`RIGHT_M0`)"],
                 ["GPIO15", "IN4", "Lado derecho, adelante (`RIGHT_M1`)"],
                 ["5V / GND", "+5V / GND", "Alimentación del ESP32 desde el regulador del L298N; tierra común"],
                 ["Batería + / −", "+12V / GND", "Alimentación de motores (3×18650, por el interruptor)"],
                 ["—", "ENA, ENB", "Jumpers puestos; la velocidad se regula con PWM en los pines IN"]],
                anchos_columnas=[1.1, 1.0, 4.2], pie_tabla="Tabla 1. Tabla de pines (GPIO12–15 son los pines propuestos por el enunciado).")
    insertar_imagen(doc, str(f_fot), ancho_pulgadas=5.7,
                    pie_figura="Figura 1. a) Robot armado; b) diagrama de conexiones del kit (M1–M4 son los cuatro motores); c) medición del voltaje de las baterías.")
    P(doc, "GPIO12 es un pin de arranque (strapping): si está en alto al encender, el ESP32 no arranca; con el L298N conectado arranca sin problema "
           "porque las entradas no lo jalan a alto, lo que se comprobó al energizar. Antes de mover el robot se verificó la polaridad y las tierras comunes, "
           "y se hicieron las primeras pruebas con el robot en el aire, como pide el enunciado.")

    # ---------------- 3. Código
    agregar_titulo_seccion(doc, "3. CÓDIGO COMENTADO")
    P(doc, "El firmware está en `firmware/robot_esp32cam/` (repositorio de GitHub, enlace en las conclusiones). `robot_motion.cpp` contiene las funciones "
           "**`adelante()`, `atras()`, `izquierda()`, `derecha()`, `detener()` y `girar360()`**, una cola de movimientos no bloqueante basada en `millis()` "
           "(el video y la página web siguen respondiendo mientras el robot se mueve), la secuencia de la Parte C, la prueba de PWM mínimo, la calibración "
           "guardada en flash (NVS) y los comandos por monitor serie, que imprime cada etiqueta con su marca de tiempo y la duración real medida. "
           "**La velocidad se regula con PWM en los pines IN** (2 kHz, 8 bits, canales LEDC 4–7): como los jumpers ENA/ENB están puestos, basta enviar PWM "
           "a la entrada del sentido deseado y 0 a la otra, y el ESP32-CAM no tiene pines libres para ENA/ENB. El PWM se limita a `pwm_max = 145` "
           "(≈ 6 V promedio) porque los motores TT son de unos 6 V.")
    insertar_imagen(doc, str(c1), ancho_pulgadas=5.6, pie_figura="Figura 2. Control de bajo nivel y funciones de movimiento (`robot_motion.cpp`).")
    insertar_imagen(doc, str(c2), ancho_pulgadas=5.6, pie_figura="Figura 3. Giro de 360° y secuencia de la Parte C con pausas de 1 s (`robot_motion.cpp`).")
    P(doc, "**[Pendiente: captura del monitor serie con las etiquetas de la secuencia (se toma durante el video).]**")

    # ---------------- 4. Resultados
    agregar_titulo_seccion(doc, "4. RESULTADOS")
    agregar_titulo_seccion(doc, "4.1 Medidas físicas y alimentación", nivel=2)
    P(doc, f"Se midieron tres veces las dimensiones del robot: distancia entre las llantas izquierdas y derechas **L = {L:.1f} cm**, distancia entre ejes "
           f"**{ejes:.1f} cm** y diámetro de llanta **{diam:.1f} cm**. El voltaje de las baterías fue **{f['v_reposo']:.2f} V en reposo** y "
           f"**{f['v_carga']:.2f} V con los motores girando** (caída de {f['v_reposo'] - f['v_carga']:.2f} V). Durante la calibración el voltaje bajó de "
           "12.35 V a 11.83 V, así que los tiempos calibrados valen para ese intervalo.")

    agregar_titulo_seccion(doc, "4.2 Parte B – Prueba individual de motores", nivel=2)
    P(doc, "Con las llantas en el aire se probó cada lado en ambos sentidos (los sentidos son correctos sin invertir cables) y se midió el PWM mínimo con una "
           "rampa de 5 en 5 cada 0.4 s, marcando cuando **giran las dos llantas del lado**. Se alternaron lados, con 7 repeticiones por lado.")
    crear_tabla(doc, ["Motor", "PWM mínimo (7 repeticiones)", "Media ± DE", "Sentido correcto", "Observaciones"],
                [["Izquierdo (GPIO12/13)", " / ".join(str(x) for x in pb["izq"]), f"{ib[0]:.1f} ± {ib[1]:.1f}", "Sí", "Arranque consistente"],
                 ["Derecho (GPIO15/14)", " / ".join(str(x) for x in pb["der"]), f"{db[0]:.1f} ± {db[1]:.1f}", "Sí", "Arranca brusco; valores en dos grupos (70 u 85–90)"]],
                anchos_columnas=[1.2, 1.9, 0.9, 0.7, 1.7], pie_tabla="Tabla 2. PWM mínimo por lado (0–255).")
    P(doc, "El lado derecho necesita más PWM (Welch: t = 2.92, p = 0.024; Mann-Whitney: p = 0.025), lo que indica **más fricción estática**: según la "
           "posición en que se detiene el engranaje del motor TT basta 70 u hacen falta 85–90. Con el PWM de operación (140) ambos lados quedan muy "
           "por encima de su umbral.", espacio_antes=3)

    agregar_titulo_seccion(doc, "4.3 Parte C – Rutinas de movimiento", nivel=2)
    P(doc, "La secuencia se ejecuta con el comando `seq` o con el botón de la página, con 3 s de espera inicial y **1 s de pausa** entre movimientos "
           "(Figura 3). La duración inicial del enunciado se calibró como muestra la Tabla 3; la página `/tarea1` guía la calibración (Figura 4).")
    crear_tabla(doc, ["#", "Movimiento", "PWM izq. / der.", "Inicial", "Calibrada"],
                [["1", "Adelante", "+140 / +140", "2000 ms", f"{TIEMPO_FINAL['adelante']} ms"],
                 ["2", "Atrás", "−140 / −140", "2000 ms", f"{TIEMPO_FINAL['atras']} ms"],
                 ["3", "Giro izquierda", "−140 / +140", "500 ms", f"{TIEMPO_FINAL['giro_izq']} ms"],
                 ["4", "Giro derecha", "+140 / −140", "500 ms", f"{TIEMPO_FINAL['giro_der']} ms"],
                 ["5", "Giro 360° (opcional)", "−140 / +140", "1800 ms", f"{TIEMPO_FINAL['giro360']} ms"]],
                anchos_columnas=[0.3, 1.6, 1.3, 0.9, 0.9], pie_tabla="Tabla 3. Duraciones de la secuencia, antes y después de calibrar.")
    insertar_imagen(doc, str(f_pag), ancho_pulgadas=1.9, pie_figura="Figura 4. Página /tarea1 del robot: E2, calibración de tiempos.")

    agregar_titulo_seccion(doc, "4.4 Parte D – Calibración y medición", nivel=2)
    P(doc, "En el piso se marcó con cinta una línea de 1 m y una cruz de ángulos. Cada duración se ajustó por regresión del tiempo contra la distancia o el "
           "ángulo medidos y se repitió hasta que dos corridas seguidas cayeran en la tolerancia. La Figura 5 muestra cómo convergió cada movimiento. "
           "Las primeras corridas del 360° dispersaban mucho porque el robot estaba frío y la primera arrancada con la rampa pierde ángulo; después de "
           "unos giros de calentamiento la repetibilidad fue de ±1 a ±5°. La Tabla 4 reúne las **últimas tres corridas** de cada movimiento.")
    filas = []
    for k in OBJETIVO:
        vals = [v for _, v, _ in D[k]]
        ms = [m for m, _, _ in D[k]]
        mu, _ = resumen(vals)
        ob = OBJETIVO[k]
        unidad = " cm" if k in ("adelante", "atras") else "°"
        error = mu - ob
        extra = ""
        if k == "adelante":
            extra = f"\nDesv. lateral: {' / '.join(f'{x:+.1f}' for x in desv_ade)} cm"
        if k == "atras":
            ult = [x for _, _, x in corr["atras"][-3:]]
            extra = f"\nDistancia al origen (desv.): {' / '.join(f'{x:+.1f}' for x in ult)} cm"
        filas.append([NOMBRE[k], "/".join(sorted({str(m) for m in ms})), {"adelante": "Línea recta de 1 m", "atras": "Regreso al inicio"}.get(k, f"{ob}°"),
                      " / ".join(f"{x:g}" for x in vals) + unidad + extra, f"{mu:.1f}{unidad}", f"{error:+.1f}{unidad}"])
    crear_tabla(doc, ["Movimiento", "Tiempo (ms)", "Esperado", "Medido (rep. 1 / 2 / 3)", "Promedio", "Error"], filas,
                anchos_columnas=[0.9, 0.8, 1.0, 2.5, 0.7, 0.6],
                pie_tabla="Tabla 4. Parte D: últimas tres repeticiones. El tiempo cargado al final (Tabla 3) es el ajuste posterior a la última serie "
                          "de adelante (1325→1340 ms) y de 360° (1765→1740 ms).")
    insertar_imagen(doc, str(f_conv), ancho_pulgadas=5.7, pie_figura="Figura 5. Convergencia de la calibración (valor medido contra número de corrida).")
    P(doc, "**[Pendiente: validación con 15 repeticiones por movimiento (etapa E3) con los tiempos finales, y enlace del video de la secuencia.]**")

    # ---------------- 5. Análisis
    agregar_titulo_seccion(doc, "5. RESPUESTAS DEL ANÁLISIS")
    P(doc, "**1. ¿Por qué se desvía en línea recta si ambos motores reciben la misma señal?** El control es de lazo abierto: el mismo PWM no garantiza "
           "la misma velocidad. Influyen las tolerancias de los motores TT y sus reductoras (fricción y holgura), pequeñas diferencias de diámetro "
           "de llanta, la distribución del peso y que cada lado arranca con un PWM mínimo distinto (Tabla 2: 69 contra 79). Una diferencia de pocos por "
           f"ciento produce una curvatura constante y la desviación lateral crece con la distancia. En las pruebas finales de avance de 1 m la desviación "
           f"fue de {np.mean(desv_ade):+.1f} cm (con 1390 ms, antes del ajuste, llegó a +4.5 y +5 cm) y al ir en reversa llegó a "
           f"±{max(abs(x) for x in desv_atr):.1f} cm, lo que confirma que el desvío cambia con la fricción de cada serie y no es una constante.")
    P(doc, "**2. ¿Diferencia entre girar con un motor detenido y con motores en sentidos opuestos?** Con un motor detenido, el centro de giro es la "
           "rueda detenida, ω = v/L y el robot describe un arco de radio L/2; con motores opuestos, el centro es el punto medio entre ruedas, ω = 2v/L "
           "(el doble) y el robot gira en su lugar. Este programa usa giros sobre su eje, que cambian la orientación sin desplazarse. En un 4WD ambos "
           "giros arrastran las llantas de lado, por lo que el giro real es más lento que el teórico.")
    P(doc, "**3. ¿Cómo afectan la caída de voltaje del L298N y la batería?** El L298N (transistores bipolares) pierde unos 2 V; el voltaje promedio "
           "del motor es ≈ PWM/255·(V_bat − 2 V). Con 12.1 V y PWM 140 son ≈ 5.5 V; con la batería baja el mismo PWM da menos velocidad, y la "
           f"calibración lo mostró: con {f['v_reposo']:.1f} V el avance de 1390 ms midió 104.7 cm y con 12.0 V el de 1325 ms midió 97.7 cm, y el voltaje "
           "bajó de 12.35 a 11.83 V durante los giros, lo que obligó a dejar el tiempo de 360° un poco largo. Los tiempos calibrados solo valen para ese "
           "intervalo de voltaje, y se mitiga midiendo la batería y compensando el PWM, con un driver MOSFET o cerrando el lazo con sensores.")
    P(doc, "**4. Ecuaciones cinemáticas y tiempo teórico de 90°.** v = (v_R + v_L)/2 y ω = (v_R − v_L)/L. Girando sobre su eje (v_R = v, v_L = −v), "
           f"ω = 2v/L y t₉₀ = π/(2ω) = πL/(4v). Con L = {L:.1f} cm y v = {v:.0f} cm/s (distancia entre tiempo de las corridas de avance y retroceso), "
           f"el tiempo teórico es **t₉₀ = {t90_teo:.0f} ms**, contra **{t90_med:.0f} ms medidos**. La diferencia se explica con la **L efectiva**: con "
           f"ω medida de {w:.2f} rad/s, L_ef = 2v/ω = **{Lef:.0f} cm**, un factor de derrape L_ef/L = **{Lef / L:.1f}**. En un 4WD con dirección por derrape las "
           "cuatro llantas se arrastran de lado, así que el giro es mucho más lento que el del modelo ideal; la rampa de arranque y la fricción estática "
           "(más alta en el lado derecho, y por eso `t90d` es 40 ms mayor que `t90`) contribuyen. Los valores son estimaciones con las últimas tres "
           "corridas; la etapa E4 los recalcula con todos los datos.")
    P(doc, "**5. Mejora propuesta.** Agregar una **IMU MPU6050** para medir el ángulo real y cerrar el lazo del giro con un PID sobre la orientación "
           "(hoy el error de un giro depende del voltaje y del estado de los motores); leer el voltaje de la batería para compensar el PWM; y usar un coprocesador ESP32-WROOM-32D "
           "dedicado a motores y sensores, que libera pines para ENA/ENB, encoders y un sensor ultrasónico. La cámara del ESP32-CAM ya permite el control "
           "por WiFi con video.")

    # ---------------- 6. Problemas
    agregar_titulo_seccion(doc, "6. PROBLEMAS ENCONTRADOS Y SOLUCIONES")
    crear_tabla(doc, ["Problema", "Solución"],
                [["Velocidad fija (`speed = 150`) y sin regulación en el código original", "Funciones con PWM configurable, factor de corrección por lado y límite `pwm_max`"],
                 ["Los movimientos con `delay()` bloqueaban el servidor web y la cámara", "Cola de movimientos no bloqueante con `millis()`"],
                 ["El servidor web admite pocas rutas por defecto", "`config.max_uri_handlers` subido a 32"],
                 ["Con el core 3.3.12 la cámara no iniciaba (`frame buffer malloc failed`) y se detenía el arranque", "`camera_config_t` inicializada en ceros con `fb_location` (PSRAM) y `grab_mode`; si la cámara falla, el WiFi y los motores siguen"],
                 ["El PWM mínimo variaba según se contara una o dos llantas del lado", "Criterio fijo: se marca cuando giran las dos llantas"],
                 ["Calibración perdida al reiniciar", "Parámetros guardados en flash (NVS); los datos de la página en LittleFS"],
                 ["Una batería se dañó por el pico de voltaje al conectarla con el ESP32 apagado", "Conectar las baterías **al final**, con el ESP32 ya alimentado por USB"],
                 ["El 360° dispersaba mucho al inicio (240° a 426° con 2145 ms)", "Calentar el robot con unos giros antes de medir, excluir el atípico y recalcular la tasa de giro"],
                 ["Datos mal capturados en la página (ángulos de 500°, 2050° y 1000 cm)", "Se excluyeron o corrigieron y se documentaron"]],
                anchos_columnas=[3.0, 3.3], pie_tabla="Tabla 5. Problemas y soluciones.")

    # ---------------- 7. Conclusiones
    agregar_titulo_seccion(doc, "7. CONCLUSIONES")
    P(doc, "Se armó el robot, se verificaron sus motores y se calibraron sus cinco rutinas con una calibración **medida y no supuesta**: "
           f"avance de 100 cm en {TIEMPO_FINAL['adelante']} ms, retroceso en {TIEMPO_FINAL['atras']} ms, giros de 90° en {TIEMPO_FINAL['giro_izq']} ms "
           f"(izquierda) y {TIEMPO_FINAL['giro_der']} ms (derecha) y una vuelta de 360° en {TIEMPO_FINAL['giro360']} ms. Los dos giros de 90° quedaron "
           "dentro de ±5° con una desviación de 1–2° y el 360° a ±10° con una desviación de 1–4° una vez que el robot se calienta. "
           "El resultado principal es que **un robot de lazo abierto es repetible dentro de una sesión, pero no entre sesiones**: dependen del "
           "voltaje, de la fricción de cada lado y de si los motores están calientes, y por eso los tiempos solo valen para esas condiciones. "
           "El modelo cinemático ideal subestima mucho el tiempo de giro de un 4WD por derrape (L efectiva unas 3.4 veces L). Una IMU cerraría "
           "el lazo y haría innecesaria esta calibración. **[Conclusión individual: revisar y ajustar.]**")
    P(doc, "**Enlaces y evidencias.** Repositorio (código, datos y videos): https://github.com/igream/ESP32-AI-Robot · Video de la secuencia: "
           "**[pendiente]**. Evidencias incluidas: foto del robot armado y del diagrama (Figura 1), capturas del código (Figuras 2 y 3), tablas de calibración "
           "(Tablas 2–4) y datos crudos en `docs/Tarea1/" + nombre_json + "`.", espacio_antes=2)

    agregar_referencias_ieee(doc, [
        "STMicroelectronics, “L298: Dual full-bridge driver,” hoja de datos.",
        "Espressif Systems, “ESP32 Series Datasheet.”",
        "Curso de Robótica, UAEMéx, “Tarea: Prueba de funcionalidad de un robot móvil diferencial,” enunciado, 2026.",
    ])
    ruta = SALIDA / "REPORTE_Tarea4.docx"
    doc.save(str(ruta))
    print("Guardado", ruta)
    return ruta


if __name__ == "__main__":
    r = construir()
    if "--sin-pdf" not in sys.argv:
        print("PDF:", exportar_pdf_word(str(r)))
