#!/usr/bin/env python3
"""Genera el reporte de la Tarea 4 del curso (en el repo, "Tarea 1": robot móvil diferencial) en docx + PDF,
con el formato institucional de la skill de Ciencia de Datos (como el de la Tarea 5) y la estructura que pide el
enunciado: portada e integrantes, objetivo, materiales y diagrama de conexión, código comentado, resultados
(tablas y fotos), respuestas del análisis, problemas y soluciones, conclusiones.

Cumple además: índice vinculado (estilos Título 1/2), ecuaciones nativas de Word, video en línea con miniatura,
enlaces visibles y consultables, todo el texto en negro y encabezados de tabla grises.

Datos: último docs/Tarea1/tarea1_*.json exportado desde la página /tarea1 (Parte B, mediciones, corridas de E2 y E3).
Salida: docs/Tarea1/REPORTE_Tarea4.docx y .pdf (si Word está instalado) y docs/Tarea1/img/*.png

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
from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "tarea2"))
sys.path.insert(0, str(AQUI))
import formato_word as fw  # noqa: E402
import reporte_tarea2 as rt  # noqa: E402  (solo para cargar la skill y reutilizar crear_tabla)
from builder_documento_base import cargar_plantilla_base, insertar_imagen  # noqa: E402
from generador_graficos_base import configurar_estilo_uaemex, guardar_grafico  # noqa: E402
from formato_word import M  # noqa: E402

RAIZ = AQUI.parent
SALIDA = RAIZ / "docs" / "Tarea1"
REC = SALIDA / "Recursos"
IMG = SALIDA / "img"
FECHA = "Toluca, Estado de México, 10 de noviembre de 2026"
URL_REPO = "https://github.com/igream/ESP32-AI-Robot"
URL_VIDEO = "https://youtu.be/V50d3I37h6I"
URL_EMBED = "https://www.youtube.com/embed/V50d3I37h6I?feature=oembed"

# ids del JSON con dato mal capturado o atípico descartado por el autor (23: 500°, 26: 240°, 32: 2050°, 64: 310°)
ERRORES_CAPTURA = {23, 26, 32, 64}
CORRECCION = {35: 100.0}                   # id 35: se escribió 1000 y era 100 cm
OBJETIVO = {"adelante": 100, "atras": 100, "giro_izq": 90, "giro_der": 90, "giro360": 360}
TOL = {"adelante": 3, "atras": 3, "giro_izq": 5, "giro_der": 5, "giro360": 10}
TIEMPO_FINAL = {"adelante": 1340, "atras": 1490, "giro_izq": 480, "giro_der": 520, "giro360": 1740}
NOMBRE = {"adelante": "Adelante", "atras": "Atrás", "giro_izq": "Izquierda", "giro_der": "Derecha", "giro360": "360°"}
NOMBRE_SALIDA = "REPORTE_Tarea4.docx"          # --salida=OTRO.docx si el archivo está abierto en Word
FIG = {k: i + 1 for i, k in enumerate(["video", "fotos", "diagrama", "cod1", "cod2", "serie", "pagina", "conv"])}


def _tabla(doc, enc, filas, **kw):
    """crear_tabla de reporte_tarea2 (no se parte entre páginas) sin marcas de Markdown y con encabezado gris."""
    limpia = lambda x: x.replace("`", "").replace("**", "") if isinstance(x, str) else x  # noqa: E731
    t = rt.crear_tabla(doc, [limpia(e) for e in enc], [[limpia(c) for c in f] for f in filas], **kw)
    fw.tabla_gris(t)
    return t


def cargar():
    ruta = sorted((SALIDA / "datos").glob("tarea1_*.json"))[-1]
    d = json.loads(ruta.read_text(encoding="utf-8"))
    corr = {k: [] for k in OBJETIVO}
    for c in d["calib"]:
        k = c["mov"]
        if c["id"] in ERRORES_CAPTURA or k not in corr:
            continue
        m = c["medido"]
        v = CORRECCION.get(c["id"], m.get("avance_cm", m.get("angulo_deg")))
        corr[k].append((c["ms"], v, m.get("desviacion_cm")))
    return d, corr, ruta.name


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
        ax.axhspan(ob - tl, ob + tl, color="#D9D9D9", alpha=0.8)
        ax.axhline(ob, color="black", lw=0.8)
        sc = ax.scatter(x, y, c=ms, cmap="viridis", s=14, zorder=3)
        ax.plot(x, y, color="#64748B", lw=0.5, zorder=2)
        ax.set_title(NOMBRE[k] + (" (cm)" if k in ("adelante", "atras") else " (°)"), fontsize=8)
        ax.set_xlabel("Corrida")
        ax.set_ylim(min(y.min(), ob - tl) - 0.06 * ob, min(y.max(), ob * 1.45) + 0.06 * ob)
        cb = fig.colorbar(sc, ax=ax, pad=0.01)
        cb.set_label("ms", fontsize=7)
        cb.ax.tick_params(labelsize=6)
    ejes[-1].axis("off")
    ejes[-1].text(0.0, 0.5, "Banda gris: tolerancia del enunciado.\nColor: duración usada en la corrida.\n"
                  "Se excluyeron 3 datos mal capturados\ny 1 atípico de 360° (310°).", fontsize=7.5, va="center")
    fig.tight_layout()
    ruta = IMG / "fig_t4_convergencia.png"
    guardar_grafico(fig, str(ruta), dpi=300)
    return ruta


def figura_fotos():
    """Robot armado y medición del voltaje, recortados al área útil."""
    configurar_estilo_uaemex(font_size=8.0)
    a = mi.imread(str(REC / "RobotArmado.jpeg"))[300:1330, :]
    b = mi.imread(str(REC / "T1 Medición Voltaje.jpeg"))[330:980, :]
    fig = plt.figure(figsize=(7.4, 3.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[a.shape[1] / a.shape[0], b.shape[1] / b.shape[0]], wspace=0.04)
    for i, (im, t) in enumerate([(a, "a) Robot armado"), (b, "b) Voltaje de las baterías en reposo: 12.11 V")]):
        ax = fig.add_subplot(gs[i])
        ax.imshow(im)
        ax.axis("off")
        ax.set_title(t, fontsize=8, loc="left")
    ruta = IMG / "fig_t4_fotos.png"
    guardar_grafico(fig, str(ruta), dpi=300)
    return ruta


def recorte_pagina():
    """Captura del celular recortada (barra de estado hasta la tarjeta de 'Adelante')."""
    im = Image.open(REC / "T1 Registro Tiempos.jpeg")
    ruta = IMG / "fig_t4_pagina.png"
    im.crop((0, 95, im.width, 1135)).save(ruta)
    return ruta


def miniatura_con_play():
    im = Image.open(IMG / "video_miniatura.jpg").convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy, r = im.width // 2, im.height // 2, 46
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0, 0, 0, 170))
    d.polygon([(cx - 14, cy - 24), (cx - 14, cy + 24), (cx + 26, cy)], fill=(255, 255, 255, 255))
    ruta = IMG / "video_miniatura_play.png"
    im.save(ruta)
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


def resumen(vals):
    a = np.array(vals, float)
    return a.mean(), (a.std(ddof=1) if len(a) > 1 else 0.0)


# ------------------------------------------------------------------ documento
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


def P(doc, texto, **kw):
    return fw.parrafo(doc, texto, **kw)


def pie_fig(clave, texto):
    return f"Figura {FIG[clave]}. {texto}"


def referencias(doc, refs):
    """Referencias IEEE con *cursiva* para el título de la obra y enlaces clicables."""
    fw.titulo(doc, "REFERENCIAS", 1)
    for i, (texto, url, acceso) in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = 3
        p.paragraph_format.space_after = fw.Pt(1.5)
        p.paragraph_format.line_spacing = 1.0
        fw._fmt_run(p.add_run(f"[{i}] "), 8.5, negrita=True)
        for j, trozo in enumerate(texto.split("*")):
            if trozo:
                fw._fmt_run(p.add_run(trozo), 8.5, cursiva=(j % 2 == 1))
        if url:
            fw.hipervinculo(p, url, url, tam=8.5)
        fw._fmt_run(p.add_run(f". {acceso}." if acceso else "."), 8.5)


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

    # Parte D (E3): 3 repeticiones por movimiento, como las registró la página. El 360° nº 1 (967°) es un error de captura.
    PD = d["parteD"]
    EXCL_D = {92}

    def rep(mov, campo):
        return [(r["ms"], r["medido"][campo], r["medido"].get("desviacion_cm"), r["id"]) for r in PD if r["mov"] == mov]
    D = {"adelante": rep("adelante", "avance_cm"), "atras": rep("ida_vuelta", "dist_origen_cm"), "giro_izq": rep("giro_izq", "angulo_deg"),
         "giro_der": rep("giro_der", "angulo_deg"), "giro360": rep("giro360", "angulo_deg")}
    val = {k: [v for _, v, _, i in D[k] if i not in EXCL_D] for k in D}
    ms_real = np.mean([r["ms_real"] for r in PD if r["mov"] == "adelante"])
    v = np.mean(val["adelante"]) / (ms_real / 1000)                       # cm/s, como la etapa E4 de la página
    w_izq = np.radians(np.mean(val["giro_izq"])) / (TIEMPO_FINAL["giro_izq"] / 1000)
    w_der = np.radians(np.mean(val["giro_der"])) / (TIEMPO_FINAL["giro_der"] / 1000)
    w_360 = np.radians(np.mean(val["giro360"])) / (TIEMPO_FINAL["giro360"] / 1000)
    Lef = 2 * v / w_izq
    t90_teo = np.pi * L / (4 * v) * 1000
    t90_med = TIEMPO_FINAL["giro_izq"]
    desv_ade = [x for _, _, x, _ in D["adelante"]]
    desv_atr = [x for _, _, x in corr["atras"] if x is not None]
    desv_ade_e2 = [x for _, _, x in corr["adelante"] if x is not None]

    f_conv, f_fot, f_pag = figura_convergencia(corr), figura_fotos(), recorte_pagina()
    f_min = miniatura_con_play()
    c1 = captura_codigo("firmware/robot_esp32cam/robot_motion.cpp", 106, 129, "cod_t4_motores.png")
    c2 = captura_codigo("firmware/robot_esp32cam/robot_motion.cpp", 443, 459, "cod_t4_secuencia.png")

    doc = cargar_plantilla_base()
    portada(doc)
    T = fw.titulo
    V, TX, F, S = M.var, M.txt, M.frac, M.sub
    E = lambda *a: "".join(a)  # noqa: E731
    vR, vL = S(V("v"), V("R")), S(V("v"), V("L"))

    # ---------------- Índice y enlaces
    fw.indice(doc)
    fw.parrafo(doc, "**ENLACES DEL PROYECTO**", espacio_antes=8, alineacion=0)
    t = doc.add_table(rows=3, cols=2)
    t.style = "Table Grid" if "Table Grid" in [s.name for s in doc.styles] else None
    t.autofit = False
    filas = [("Repositorio en GitHub (código, datos y reportes)", URL_REPO),
             ("Video de la secuencia con el monitor serie (YouTube)", URL_VIDEO),
             ("Datos crudos exportados de la página /tarea1", f"{URL_REPO}/blob/main/docs/Tarea1/datos/{nombre_json}")]
    for fila, (etq, url) in zip(t.rows, filas):
        fila.cells[0].width, fila.cells[1].width = fw.Inches(2.6), fw.Inches(3.5)
        fw.agregar_texto(fila.cells[0].paragraphs[0], f"**{etq}**", 9)
        fw.hipervinculo(fila.cells[1].paragraphs[0], url, url, tam=9)
        for c in fila.cells:
            c.paragraphs[0].paragraph_format.space_before = c.paragraphs[0].paragraph_format.space_after = fw.Pt(2)
    fw.parrafo(doc, "", espacio_antes=2)
    fw.video_en_linea(doc, URL_VIDEO, URL_EMBED, f_min, ancho_pulgadas=3.1,
                      descripcion="Video de la secuencia completa de la Tarea 4 con el monitor serie")
    cap = doc.add_paragraph()
    cap.alignment = 1
    fw.agregar_texto(cap, f"**Figura {FIG['video']}.** Video en línea de la secuencia completa (Parte C): robot, marca del piso y monitor serie. "
                          "Se reproduce desde Word o desde el enlace: ", 8)
    fw.hipervinculo(cap, URL_VIDEO, URL_VIDEO, tam=8)

    # ---------------- 1. Objetivo
    T(doc, "1. OBJETIVO", 1, salto_antes=True)
    P(doc, "Armar y verificar un robot móvil de ruedas con arquitectura diferencial (**kit LaFvin ESP32 Camera 4WD**, driver **L298N**, cuatro "
           "motores TT y baterías 18650) y programar rutinas reutilizables de movimiento (adelante, atrás, giro a la izquierda, giro a la derecha y "
           "vuelta de 360° sobre su eje). Después, **calibrar el tiempo de cada rutina** midiendo el movimiento real en el piso para saber con "
           "precisión cuánto se mueve el robot, y contrastar lo medido con el modelo cinemático diferencial [1].")

    # ---------------- 2. Materiales y diagrama
    T(doc, "2. MATERIALES Y DIAGRAMA DE CONEXIÓN", 1)
    P(doc, "Se usó el kit completo con una **ESP32-CAM AI-Thinker** (cámara OV3660) programada por una placa **ESP32-CAM-MB** (CH340), el driver "
           "L298N [2], tres baterías 18650 (12.1 V cargadas), cinta métrica, cinta de color, multímetro y un celular para controlar y grabar. Se programó con "
           "arduino-cli y el core ESP32 3.3.12. Los dos motores de cada lado van en paralelo, por lo que el robot se comporta como diferencial y gira "
           f"derrapando. La Tabla 1 muestra las conexiones; la Figura {FIG['fotos']} muestra el robot armado y la medición de voltaje, y la "
           f"Figura {FIG['diagrama']}, el diagrama de conexiones.")
    _tabla(doc, ["ESP32-CAM", "L298N", "Función"],
           [["GPIO12", "IN1", "Lado izquierdo, adelante (LEFT_M1)"],
            ["GPIO13", "IN2", "Lado izquierdo, reversa (LEFT_M0)"],
            ["GPIO14", "IN3", "Lado derecho, reversa (RIGHT_M0)"],
            ["GPIO15", "IN4", "Lado derecho, adelante (RIGHT_M1)"],
            ["5V / GND", "+5V / GND", "Alimentación del ESP32 desde el regulador del L298N; tierra común"],
            ["Batería + / −", "+12V / GND", "Alimentación de motores (3×18650, por el interruptor)"],
            ["—", "ENA, ENB", "Jumpers puestos; la velocidad se regula con PWM en los pines IN"]],
           anchos_columnas=[1.1, 1.0, 4.2], pie_tabla="Tabla 1. Tabla de pines (GPIO12–15 son los pines propuestos por el enunciado).")
    insertar_imagen(doc, str(f_fot), ancho_pulgadas=5.8, pie_figura=pie_fig("fotos", "Robot armado y medición del voltaje de las baterías con el multímetro."))
    insertar_imagen(doc, str(REC / "DiagramaConexiones.png"), ancho_pulgadas=5.6,
                    pie_figura=pie_fig("diagrama", "Diagrama de conexiones del kit (M1–M4 son los cuatro motores; el ESP32-CAM se conecta a IN1–IN4 del L298N)."))
    P(doc, "GPIO12 es un pin de arranque (strapping): si está en alto al encender, el ESP32 no arranca [3]; con el L298N conectado arranca sin problema "
           "porque las entradas no lo jalan a alto, lo que se comprobó al energizar. Antes de mover el robot se verificó la polaridad y las tierras comunes, "
           "y se hicieron las primeras pruebas con el robot en el aire, como pide el enunciado.")

    # ---------------- 3. Código
    T(doc, "3. CÓDIGO COMENTADO", 1)
    P(doc, "El firmware está en firmware/robot_esp32cam/ del repositorio [4]. robot_motion.cpp contiene las funciones "
           "**adelante(), atras(), izquierda(), derecha(), detener() y girar360()**, una cola de movimientos no bloqueante basada en millis() "
           "(el video y la página web siguen respondiendo mientras el robot se mueve), la secuencia de la Parte C, la prueba de PWM mínimo, la calibración "
           "guardada en flash (NVS) y los comandos por monitor serie, que imprime cada etiqueta con su marca de tiempo y la duración real medida "
           f"(Figura {FIG['serie']}). **La velocidad se regula con PWM en los pines IN** (2 kHz, 8 bits, canales LEDC 4–7): como los jumpers ENA/ENB están puestos, "
           "basta enviar PWM a la entrada del sentido deseado y 0 a la otra, y el ESP32-CAM no tiene pines libres para ENA/ENB. El PWM se limita a pwm_max = 145 "
           "(≈ 6 V promedio) porque los motores TT son de unos 6 V.")
    insertar_imagen(doc, str(c1), ancho_pulgadas=4.9, pie_figura=pie_fig("cod1", "Control de bajo nivel y funciones de movimiento (robot_motion.cpp)."))
    insertar_imagen(doc, str(c2), ancho_pulgadas=4.9, pie_figura=pie_fig("cod2", "Giro de 360° y secuencia de la Parte C con pausas de 1 s (robot_motion.cpp)."))
    insertar_imagen(doc, str(IMG / "MonitorSerie.png"), ancho_pulgadas=4.9,
                    pie_figura=pie_fig("serie", "Monitor serie (115200 baudios) durante la secuencia: etiqueta, PWM izquierdo/derecho y duración de cada movimiento."))

    # ---------------- 4. Resultados
    T(doc, "4. RESULTADOS", 1)
    T(doc, "4.1 Medidas físicas y alimentación", 2)
    P(doc, f"Se midieron tres veces las dimensiones del robot: distancia entre las llantas izquierdas y derechas **L = {L:.1f} cm**, distancia entre ejes "
           f"**{ejes:.1f} cm** y diámetro de llanta **{diam:.1f} cm**. El voltaje de las baterías fue **{f['v_reposo']:.2f} V en reposo** y "
           f"**{f['v_carga']:.2f} V con los motores girando** (caída de {f['v_reposo'] - f['v_carga']:.2f} V). Durante la calibración el voltaje bajó de "
           "12.35 V a 11.83 V, así que los tiempos calibrados valen para ese intervalo.")

    T(doc, "4.2 Parte B – Prueba individual de motores", 2)
    P(doc, "Con las llantas en el aire se probó cada lado en ambos sentidos (los sentidos son correctos sin invertir cables) y se midió el PWM mínimo con una "
           "rampa de 5 en 5 cada 0.4 s, marcando cuando **giran las dos llantas del lado**. Se alternaron lados, con 7 repeticiones por lado.")
    _tabla(doc, ["Motor", "PWM mínimo (7 repeticiones)", "Media ± DE", "Sentido correcto", "Observaciones"],
           [["Izquierdo (GPIO12/13)", " / ".join(str(x) for x in pb["izq"]), f"{ib[0]:.1f} ± {ib[1]:.1f}", "Sí", "Arranque consistente"],
            ["Derecho (GPIO15/14)", " / ".join(str(x) for x in pb["der"]), f"{db[0]:.1f} ± {db[1]:.1f}", "Sí", "Arranca brusco; valores en dos grupos (70 u 85–90)"]],
           anchos_columnas=[1.2, 1.9, 0.9, 0.7, 1.7], pie_tabla="Tabla 2. PWM mínimo por lado (0–255).")
    P(doc, "El lado derecho necesita más PWM (Welch: t = 2.92, p = 0.024; Mann-Whitney: p = 0.025), lo que indica **más fricción estática**: según la "
           "posición en que se detiene el engranaje del motor TT basta 70 u hacen falta 85–90. Con el PWM de operación (140) ambos lados quedan muy "
           "por encima de su umbral.", espacio_antes=3)

    T(doc, "4.3 Parte C – Rutinas de movimiento", 2)
    P(doc, "La secuencia se ejecuta con el comando seq o con el botón de la página, con 3 s de espera inicial y **1 s de pausa** entre movimientos "
           f"(Figura {FIG['cod2']}); su ejecución completa se ve en el video de la Figura {FIG['video']}. La duración inicial del enunciado se calibró como "
           f"muestra la Tabla 3; la página /tarea1 del robot guía la calibración (Figura {FIG['pagina']}).")
    _tabla(doc, ["#", "Movimiento", "PWM izq. / der.", "Inicial", "Calibrada"],
           [["1", "Adelante", "+140 / +140", "2000 ms", f"{TIEMPO_FINAL['adelante']} ms"],
            ["2", "Atrás", "−140 / −140", "2000 ms", f"{TIEMPO_FINAL['atras']} ms"],
            ["3", "Giro izquierda", "−140 / +140", "500 ms", f"{TIEMPO_FINAL['giro_izq']} ms"],
            ["4", "Giro derecha", "+140 / −140", "500 ms", f"{TIEMPO_FINAL['giro_der']} ms"],
            ["5", "Giro 360° (opcional)", "−140 / +140", "1800 ms", f"{TIEMPO_FINAL['giro360']} ms"]],
           anchos_columnas=[0.3, 1.6, 1.3, 0.9, 0.9], pie_tabla="Tabla 3. Duraciones de la secuencia, antes y después de calibrar.")
    insertar_imagen(doc, str(f_pag), ancho_pulgadas=3.3, pie_figura=pie_fig("pagina", "Página /tarea1 del robot (celular): E2, calibración de tiempos."))

    T(doc, "4.4 Parte D – Calibración y medición", 2)
    P(doc, "En el piso se marcó con cinta una línea de 1 m y una cruz de ángulos. Cada duración se ajustó por regresión del tiempo contra la distancia o el "
           f"ángulo medidos y se repitió hasta que dos corridas seguidas cayeran en la tolerancia (etapa E2, 78 corridas en total; la Figura {FIG['conv']} muestra cómo "
           "convergió cada movimiento). Las primeras corridas del 360° dispersaban mucho (240° a 426°) porque el robot estaba frío y la rampa de arranque "
           "pierde ángulo; después de unos giros de calentamiento la repetibilidad fue de ±1 a ±5°. Con los tiempos finales se hicieron las **3 repeticiones "
           "de la Parte D** (etapa E3, Tabla 4); en el regreso al origen se anota la distancia entre el punto de inicio y el de llegada tras ir adelante y atrás.")
    filas = []
    for k in OBJETIVO:
        todos = D[k]
        vals = [x for _, x, _, i in todos if i not in EXCL_D]
        ob = OBJETIVO[k] if k != "atras" else 0
        unidad = " cm" if k in ("adelante", "atras") else "°"
        mu = np.mean(vals)
        ms = sorted({str(m) for m, *_ in todos})
        celda = " / ".join((f"{x:g}*" if i in EXCL_D else f"{x:g}") for _, x, _, i in todos) + unidad
        if k == "adelante":
            celda += "\nDesv. lateral: " + " / ".join(f"{x:+.1f}" for x in desv_ade) + " cm"
        if k == "atras":
            celda += f"\n(ida {TIEMPO_FINAL['adelante']} ms + vuelta {TIEMPO_FINAL['atras']} ms)"
        esp = {"adelante": "Línea recta de 1 m", "atras": "Regreso al origen (0 cm)"}.get(k, f"{ob}°")
        filas.append([NOMBRE[k], "/".join(ms), esp, celda, f"{mu:.1f}{unidad}", f"{mu - ob:+.1f}{unidad}"])
    _tabla(doc, ["Movimiento", "Tiempo (ms)", "Esperado", "Medido (rep. 1 / 2 / 3)", "Promedio", "Error"], filas,
           anchos_columnas=[0.9, 0.8, 1.1, 2.4, 0.7, 0.6],
           pie_tabla="Tabla 4. Parte D (E3), con los tiempos finales de la Tabla 3 y 11.94 V. *El primer 360° (967°) es un error de captura y se "
                     "excluyó del promedio.")
    insertar_imagen(doc, str(f_conv), ancho_pulgadas=5.0,
                    pie_figura=pie_fig("conv", "Convergencia de la calibración (valor medido contra número de corrida)."))
    P(doc, "En la Parte D el avance y los giros quedaron cerca de lo esperado (errores de −2.7 cm, +2.0° a la izquierda y −0.5° en el 360°), pero "
           "el **giro a la derecha dio 95.7°** (+5.7°, apenas fuera de ±5°) y el **regreso al origen terminó a 11–13.5 cm del inicio**. La diferencia en el "
           "derecho se debe, con probabilidad, a su mayor fricción estática y al estado de los motores en esa serie: en la calibración, a 520 ms dio de 89° "
           "a 91° con 11.89 V. El 360° tuvo una repetición con 967° que corresponde a un error de captura (probablemente 367°).", espacio_antes=3)

    # ---------------- 5. Análisis
    T(doc, "5. RESPUESTAS DEL ANÁLISIS", 1)
    P(doc, "**1. ¿Por qué se desvía en línea recta si ambos motores reciben la misma señal?** El control es de lazo abierto: el mismo PWM no garantiza "
           "la misma velocidad. Influyen las tolerancias de los motores TT y sus reductoras (fricción y holgura), pequeñas diferencias de diámetro "
           "de llanta, la distribución del peso y que cada lado arranca con un PWM mínimo distinto (Tabla 2: 69 contra 79). Una diferencia de pocos por "
           "ciento produce una curvatura constante y la desviación lateral crece con la distancia. En el avance de 1 m la desviación lateral fue pequeña "
           f"({np.mean(desv_ade):+.1f} cm en las tres repeticiones de la Parte D y de {min(desv_ade_e2):+.1f} a {max(desv_ade_e2):+.1f} cm en la calibración), pero al "
           f"retroceder llegó a {min(desv_atr):+.1f} y {max(desv_atr):+.1f} cm, y tras ir y volver el robot terminó a **11–13.5 cm del origen**: el desvío cambia con "
           "el sentido y con la fricción de cada serie, y no es una constante que se pueda compensar con un solo factor.")
    fw.parrafo_mixto(doc, [
        "**2. ¿Diferencia entre girar con un motor detenido y con motores en sentidos opuestos?** Con un motor detenido, el centro de giro es la "
        "rueda detenida, ", fw.en_linea(E(V("ω"), V("="), F(V("v"), V("L")))), " y el robot describe un arco de radio ", fw.en_linea(F(V("L"), V("2"))),
        "; con motores opuestos, el centro es el punto medio entre ruedas, ", fw.en_linea(E(V("ω"), V("="), F(E(V("2"), V("v")), V("L")))),
        " (el doble) y el robot gira en su lugar. Este programa usa giros sobre su eje, que cambian la orientación sin desplazarse. En un 4WD ambos "
        "giros arrastran las llantas de lado, por lo que el giro real es más lento que el teórico."])
    P(doc, "**3. ¿Cómo afectan la caída de voltaje del L298N y la batería?** El L298N (transistores bipolares) pierde unos 2 V [2], de modo que el "
           "voltaje promedio que recibe el motor con PWM es aproximadamente:")
    fw.ecuacion(doc, E(S(V("V"), TX("motor")), V("≈"), F(TX("PWM"), V("255")), V("⋅"), M.par(E(S(V("V"), TX("bat")), V("−"), V("2"), TX(" V")))), 1)
    P(doc, "Con 12.1 V y PWM 140 son ≈ 5.5 V; con la batería baja el mismo PWM da menos velocidad, y la calibración lo mostró: con 12.1 V el avance de "
           "1390 ms midió 104.7 cm y con 12.0 V el de 1325 ms midió 97.7 cm, y el voltaje bajó de 12.35 a 11.83 V durante los giros, lo que obligó a dejar el "
           "tiempo de 360° un poco largo. Los tiempos calibrados solo valen para ese intervalo de voltaje, y se mitiga midiendo la batería y compensando el "
           "PWM, con un driver MOSFET o cerrando el lazo con sensores.", espacio_antes=2)
    P(doc, "**4. Ecuaciones cinemáticas y tiempo teórico de 90°.** La velocidad lineal y la velocidad angular del robot diferencial son [1]:")
    fw.ecuacion(doc, E(V("v"), V("="), F(E(vR, V("+"), vL), V("2"))), 2)
    fw.ecuacion(doc, E(V("ω"), V("="), F(E(vR, V("−"), vL), V("L"))), 3)
    fw.parrafo_mixto(doc, ["Al girar sobre su eje, ", fw.en_linea(E(vR, V("="), V("v"))), " y ", fw.en_linea(E(vL, V("="), V("−"), V("v"))),
                           ", así que ", fw.en_linea(E(V("ω"), V("="), F(E(V("2"), V("v")), V("L")))),
                           " y el tiempo teórico de un giro de 90° (π/2 rad) es:"], espacio_antes=2)
    fw.ecuacion(doc, E(S(V("t"), TX("90")), V("="), F(E(V("π"), V("/"), V("2")), V("ω")), V("="), F(E(V("π"), V("L")), E(V("4"), V("v")))), 4)
    fw.parrafo_mixto(doc, ["Con ", fw.en_linea(E(V("L"), V("="), TX(f"{L:.1f} cm"))), " y ", fw.en_linea(E(V("v"), V("="), TX(f"{v:.1f} cm/s"))),
                           " (avance medio entre tiempo real en la Parte D), el tiempo teórico es ", fw.en_linea(E(S(V("t"), TX("90")), V("="), TX(f"{t90_teo:.0f} ms"))),
                           f", contra **{t90_med:.0f} ms medidos** (izquierda). La diferencia se explica con la **longitud efectiva** del eje, que se obtiene de la "
                           f"velocidad angular medida (ω = {np.degrees(w_izq):.0f} °/s):"], espacio_antes=2)
    fw.ecuacion(doc, E(S(V("L"), TX("ef")), V("="), F(E(V("2"), V("v")), V("ω")), V("="), TX(f"{Lef:.0f} cm")), 5)
    fw.parrafo_mixto(doc, ["lo que da un factor de derrape ", fw.en_linea(E(F(S(V("L"), TX("ef")), V("L")), V("="), TX(f"{Lef / L:.1f}"))),
                           f". En un 4WD con dirección por derrape las cuatro llantas se arrastran de lado, así que el giro es mucho más lento que el del modelo ideal; "
                           "la rampa de arranque y la fricción estática (más alta en el lado derecho, y por eso t90d es 40 ms mayor que t90) contribuyen. "
                           f"Con la Parte D, ω vale {np.degrees(w_izq):.0f} °/s a la izquierda, {np.degrees(w_der):.0f} °/s a la derecha y {np.degrees(w_360):.0f} °/s en el 360°."],
                      espacio_antes=2)
    P(doc, "**5. Mejora propuesta.** Agregar una **IMU MPU6050** para medir el ángulo real y cerrar el lazo del giro con un PID sobre la orientación "
           "(hoy el error de un giro depende del voltaje y del estado de los motores); leer el voltaje de la batería para compensar el PWM; y usar un coprocesador ESP32-WROOM-32D "
           "dedicado a motores y sensores, que libera pines para ENA/ENB, encoders y un sensor ultrasónico. La cámara del ESP32-CAM ya permite el control "
           "por WiFi con video.")

    # ---------------- 6. Problemas
    T(doc, "6. PROBLEMAS ENCONTRADOS Y SOLUCIONES", 1)
    _tabla(doc, ["Problema", "Solución"],
           [["Velocidad fija (speed = 150) y sin regulación en el código original", "Funciones con PWM configurable, factor de corrección por lado y límite pwm_max"],
            ["Los movimientos con delay() bloqueaban el servidor web y la cámara", "Cola de movimientos no bloqueante con millis()"],
            ["El servidor web admite pocas rutas por defecto", "config.max_uri_handlers subido a 32"],
            ["Con el core 3.3.12 la cámara no iniciaba (frame buffer malloc failed) y se detenía el arranque", "camera_config_t inicializada en ceros con fb_location (PSRAM) y grab_mode; si la cámara falla, el WiFi y los motores siguen"],
            ["El PWM mínimo variaba según se contara una o dos llantas del lado", "Criterio fijo: se marca cuando giran las dos llantas"],
            ["Calibración perdida al reiniciar", "Parámetros guardados en flash (NVS); los datos de la página en LittleFS"],
            ["Una batería se dañó por el pico de voltaje al conectarla con el ESP32 apagado", "Conectar las baterías al final, con el ESP32 ya alimentado por USB"],
            ["El 360° dispersaba mucho al inicio (240° a 426° con 2145 ms)", "Calentar el robot con unos giros antes de medir, excluir el atípico y recalcular la tasa de giro"],
            ["Datos mal capturados en la página (ángulos de 500°, 2050° y 1000 cm)", "Se excluyeron o corrigieron y se documentaron"]],
           anchos_columnas=[3.0, 3.3], pie_tabla="Tabla 5. Problemas y soluciones.")

    # ---------------- 7. Conclusiones
    T(doc, "7. CONCLUSIONES", 1)
    P(doc, "Se armó el robot, se verificaron sus motores y se calibraron sus cinco rutinas con una calibración **medida y no supuesta**: "
           f"avance de 100 cm en {TIEMPO_FINAL['adelante']} ms, retroceso en {TIEMPO_FINAL['atras']} ms, giros de 90° en {TIEMPO_FINAL['giro_izq']} ms "
           f"(izquierda) y {TIEMPO_FINAL['giro_der']} ms (derecha) y una vuelta de 360° en {TIEMPO_FINAL['giro360']} ms. En la validación de la Parte D el "
           "avance (97.3 cm), el giro a la izquierda (92°) y el 360° (359.5°) quedaron dentro de la tolerancia; el giro a la derecha (95.7°) la "
           "rebasó por 0.7° y el regreso al origen terminó a 11–13.5 cm del inicio. "
           "El resultado principal es que **un robot de lazo abierto es repetible dentro de una sesión, pero no entre sesiones**: dependen del "
           "voltaje, de la fricción de cada lado y de si los motores están calientes, y por eso los tiempos solo valen para esas condiciones. "
           "El modelo cinemático ideal subestima mucho el tiempo de giro de un 4WD por derrape (L efectiva unas 3.5 veces L). Una IMU cerraría "
           "el lazo y haría innecesaria esta calibración.")
    p = fw.parrafo(doc, "**Enlaces y evidencias.** Repositorio (código, datos y reportes): ", espacio_antes=2, alineacion=0)
    fw.hipervinculo(p, URL_REPO, URL_REPO)
    fw.agregar_texto(p, " · Video de la secuencia: ")
    fw.hipervinculo(p, URL_VIDEO, URL_VIDEO)
    fw.agregar_texto(p, f". Evidencias incluidas: fotos del robot y diagrama (Figuras {FIG['fotos']} y {FIG['diagrama']}), capturas del código y del monitor serie "
                        f"(Figuras {FIG['cod1']} a {FIG['serie']}), tablas de calibración (Tablas 2–4) y datos crudos en docs/Tarea1/datos/{nombre_json}.")

    referencias(doc, [
        ("R. Siegwart, I. R. Nourbakhsh, and D. Scaramuzza, *Introduction to Autonomous Mobile Robots*, 2nd ed. Cambridge, MA, USA: MIT Press, 2011. "
         "[Online]. Available: ", "https://mitpress.mit.edu/9780262015356/introduction-to-autonomous-mobile-robots/", None),
        ("STMicroelectronics, “L298: Dual full-bridge driver,” Datasheet, Geneva, Switzerland. [Online]. Available: ",
         "https://www.st.com/resource/en/datasheet/l298.pdf", None),
        ("Espressif Systems, *ESP32 Series Datasheet*, Version 5.3, Shanghai, China. [Online]. Available: ",
         "https://documentation.espressif.com/esp32_datasheet_en.pdf", "Accessed: Nov. 10, 2026"),
        ("F. Azuara Ibarra, *ESP32-AI-Robot* (código, datos y reportes de las Tareas 4 y 5), GitHub repository, 2026. [Online]. Available: ", URL_REPO, "Accessed: Nov. 10, 2026"),
        ("F. Azuara Ibarra, “Tarea 4 Robot móvil diferencial,” YouTube, 10 nov. 2026. [Online Video]. Available: ", URL_VIDEO, "Accessed: Nov. 10, 2026"),
    ])

    fw.todo_negro(doc)
    ruta = SALIDA / NOMBRE_SALIDA
    doc.save(str(ruta))
    print("Guardado", ruta)
    return ruta


if __name__ == "__main__":
    for a in sys.argv[1:]:
        if a.startswith("--salida="):
            NOMBRE_SALIDA = a.split("=", 1)[1]
    r = construir()
    if "--sin-pdf" not in sys.argv:
        print("PDF:", fw.exportar(str(r)))
