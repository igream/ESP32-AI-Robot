#!/usr/bin/env python3
"""
calibrar.py - Calibracion estadistica del robot ESP32-CAM (Tarea 1)

La PC se conecta al WiFi del robot (ESP32Car_Fer) y este script:
  1. Manda un movimiento al robot (/move).
  2. Te pide lo que mediste con la cinta (distancia, desviacion, angulo...).
  3. Lo guarda en un CSV y repite.
  4. Analiza los datos: estadistica descriptiva, intervalos de confianza,
     pruebas de hipotesis, regresion tiempo -> distancia/angulo y graficas.

Uso rapido (ver README en esta carpeta):
  python calibrar.py prueba  --tipo adelante --ms 2000 -n 10
  python calibrar.py barrido --tipo adelante --ms 500 1000 1500 2000 2500 -n 5
  python calibrar.py analizar --L 13.5
  python calibrar.py aplicar
  python calibrar.py validar --puntos "50,0 50,50 0,50 0,0"

Agrega --simular a prueba/barrido/validar para probar sin robot (datos ficticios).
"""
import argparse
import csv
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
CSV_PRUEBAS = os.path.join(AQUI, "datos", "pruebas.csv")

COLUMNAS = ["fecha", "sesion", "tipo", "pwm_izq", "pwm_der", "ms", "ms_real",
            "trim_i", "trim_d", "avance_cm", "desviacion_cm", "angulo_deg",
            "dist_origen_cm", "voltaje", "superficie", "nota"]
COLUMNAS_VAL = ["fecha", "sesion", "punto", "x_obj", "y_obj", "x_med", "y_med",
                "error_cm", "voltaje", "superficie", "nota"]

# Que se mide en cada tipo de prueba:
#   (pwm izq, pwm der) en funcion del pwm elegido, y campos a capturar.
TIPOS = {
    "adelante":   {"lados": (1, 1),   "campos": ["avance_cm", "desviacion_cm"]},
    "atras":      {"lados": (-1, -1), "campos": ["avance_cm", "desviacion_cm"]},
    "giro_izq":   {"lados": (-1, 1),  "campos": ["angulo_deg"]},
    "giro_der":   {"lados": (1, -1),  "campos": ["angulo_deg"]},
    "pivote_izq": {"lados": (0, 1),   "campos": ["angulo_deg"]},   # izq detenido
    "pivote_der": {"lados": (1, 0),   "campos": ["angulo_deg"]},   # der detenido
    "ida_vuelta": {"lados": (1, 1),   "campos": ["dist_origen_cm"]},  # adelante y luego atras
}

AYUDA_CAMPOS = {
    "avance_cm":      "Distancia recorrida hacia el frente del movimiento (cm)",
    "desviacion_cm":  "Desviacion lateral al final (cm, + izquierda / - derecha)",
    "angulo_deg":     "Angulo girado (grados, siempre positivo)",
    "dist_origen_cm": "Distancia del punto final al punto de inicio (cm)",
}


# ======================================================================
# Comunicacion con el robot
# ======================================================================
class Robot:
    def __init__(self, ip, simular=False):
        self.base = f"http://{ip}"
        self.simular = simular
        self.sim = Simulador() if simular else None

    def get(self, ruta, timeout=4.0):
        if self.simular:
            return self.sim.get(ruta)
        url = self.base + ruta
        for intento in range(3):
            try:
                with urllib.request.urlopen(url, timeout=timeout) as r:
                    texto = r.read().decode("utf-8", "replace")
                    return json.loads(texto) if texto.strip().startswith("{") else {"texto": texto}
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if intento == 2:
                    raise SystemExit(f"\nNo pude conectar con el robot en {url}: {e}\n"
                                     "Revisa que la PC este conectada al WiFi 'ESP32Car_Fer'.")
                time.sleep(0.5)

    def config(self):
        return self.get("/config")

    def esperar(self, max_s=60):
        """Espera a que el robot termine el movimiento y regresa su estado."""
        t0 = time.time()
        time.sleep(0.15)
        while time.time() - t0 < max_s:
            e = self.get("/estado")
            if not e.get("ocupado", False):
                return e
            time.sleep(0.15)
        self.get("/stop")
        raise SystemExit("El robot no termino a tiempo; se mando PARO.")

    def mover(self, izq, der, ms):
        r = self.get(f"/move?l={int(izq)}&r={int(der)}&ms={int(ms)}")
        if not r.get("ok", False):
            raise SystemExit(f"El robot rechazo el movimiento: {r}")
        return self.esperar(max_s=ms / 1000 + 15)


class Simulador:
    """Robot ficticio para probar el script sin hardware."""
    def __init__(self):
        self.cfg = {"pwm": 140, "pwm_giro": 140, "pwm_max": 145, "trim_i": 1.0, "trim_d": 1.0,
                    "t_adelante": 2000, "t_atras": 2000, "t90": 500, "t360": 1800,
                    "v": 0, "b": 0, "w": 0, "bg": 0, "pwm_hz": 2000}
        self.ultimo = {"izq": 0, "der": 0, "ms": 0}

    def get(self, ruta):
        if ruta.startswith("/config"):
            return dict(self.cfg)
        if ruta.startswith("/move"):
            q = dict(p.split("=") for p in ruta.split("?")[1].split("&"))
            self.ultimo = {"izq": int(q["l"]), "der": int(q["r"]), "ms": int(q["ms"])}
            return {"ok": True}
        if ruta.startswith("/estado"):
            return {"ocupado": False, "ultimo_ms_real": self.ultimo["ms"] + random.choice([0, 1, 1, 2])}
        return {"ok": True}

    # "Mediciones" ficticias con ruido, para la prueba del script
    def medir(self, tipo, ms, voltaje):
        t = ms / 1000
        k = voltaje / 11.5                       # mas bateria -> mas rapido
        if tipo in ("adelante", "atras"):
            avance = max(0, (24.0 * t - 3.0) * k + random.gauss(0, 1.2))
            desv = (3.5 if tipo == "adelante" else -2.0) * (avance / 100) ** 2 * 4 + random.gauss(0, 1.0)
            return {"avance_cm": round(avance, 1), "desviacion_cm": round(desv, 1)}
        if tipo == "ida_vuelta":
            return {"dist_origen_cm": round(abs(random.gauss(4, 2)), 1)}
        base = {"giro_izq": 190, "giro_der": 182, "pivote_izq": 85, "pivote_der": 80}[tipo]
        ang = max(0, (base * t - 8) * k + random.gauss(0, 3.5))
        return {"angulo_deg": round(ang, 1)}


# ======================================================================
# Utilidades de captura y CSV
# ======================================================================
def leer_numero(mensaje, permitir_vacio=False, defecto=None):
    """Pide un numero. Acepta coma decimal. 'r' = repetir, 'q' = terminar."""
    while True:
        extra = f" [{defecto}]" if defecto is not None else ""
        txt = input(f"   {mensaje}{extra}: ").strip().replace(",", ".")
        if txt.lower() in ("q", "r"):
            return txt.lower()
        if txt == "":
            if defecto is not None:
                return defecto
            if permitir_vacio:
                return ""
            continue
        try:
            return float(txt)
        except ValueError:
            print("   Escribe un numero (o 'r' para repetir la prueba, 'q' para terminar).")


def anexar_csv(ruta, columnas, fila):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        if nuevo:
            w.writeheader()
        w.writerow({c: fila.get(c, "") for c in columnas})


def leer_csv(ruta):
    if not os.path.exists(ruta):
        raise SystemExit(f"No existe {ruta}. Primero captura datos con 'prueba' o 'barrido'.")
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


# ======================================================================
# Captura de pruebas
# ======================================================================
def ejecutar_pruebas(args, plan):
    """plan = lista de duraciones (ms), una por repeticion, ya en orden."""
    robot = Robot(args.ip, args.simular)
    cfg = robot.config()
    tipo = args.tipo
    pwm = args.pwm if args.pwm is not None else (cfg["pwm"] if tipo in ("adelante", "atras", "ida_vuelta") else cfg["pwm_giro"])
    si, sd = TIPOS[tipo]["lados"]
    izq, der = si * pwm, sd * pwm
    if args.l is not None and args.r is not None:
        izq, der = args.l, args.r
    campos = TIPOS[tipo]["campos"]
    sesion = datetime.now().strftime("%Y%m%d-%H%M%S")
    voltaje = args.voltaje

    print(f"\nTipo: {tipo} | PWM izq={izq} der={der} | trims: izq={cfg['trim_i']} der={cfg['trim_d']}")
    print(f"Repeticiones: {len(plan)} | Superficie: {args.superficie} | CSV: {args.csv}")
    print("Por cada prueba: coloca el robot en la marca, presiona Enter y luego captura lo medido.")
    print("En cualquier dato: 'r' = descartar y repetir esa prueba, 'q' = terminar.\n")
    for c in campos:
        print(f"  - {c}: {AYUDA_CAMPOS[c]}")

    i = 0
    while i < len(plan):
        ms = plan[i]
        if args.simular:
            print(f"\n[{i + 1}/{len(plan)}] {ms} ms (simulado)")
        else:
            txt = input(f"\n[{i + 1}/{len(plan)}] {ms} ms -> robot en la marca y Enter (q = terminar): ").strip().lower()
            if txt == "q":
                break
        estado = robot.mover(izq, der, ms)
        if tipo == "ida_vuelta":
            time.sleep(0.5)
            estado = robot.mover(-izq, -der, ms)
        fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "sesion": sesion, "tipo": tipo,
                "pwm_izq": izq, "pwm_der": der, "ms": ms, "ms_real": estado.get("ultimo_ms_real", ""),
                "trim_i": cfg["trim_i"], "trim_d": cfg["trim_d"], "superficie": args.superficie,
                "nota": args.nota}

        if args.simular:
            voltaje = voltaje or round(random.uniform(10.8, 12.4), 2)
            fila.update(robot.sim.medir(tipo, ms, voltaje))
            fila["voltaje"] = voltaje
        else:
            repetir = terminar = False
            for c in campos:
                v = leer_numero(c)
                if v in ("r", "q"):
                    repetir, terminar = v == "r", v == "q"
                    break
                fila[c] = v
            if terminar:
                break
            if repetir:
                print("   Prueba descartada; se repite.")
                continue
            v = leer_numero("voltaje de bateria (V, Enter = mismo, vacio = no medido)",
                            permitir_vacio=True, defecto=voltaje)
            if v in ("r", "q"):
                if v == "q":
                    break
                continue
            voltaje = v if v != "" else voltaje
            fila["voltaje"] = voltaje if voltaje is not None else ""
        anexar_csv(args.csv, COLUMNAS, fila)
        print("   Guardado:", {c: fila.get(c) for c in campos}, f"ms_real={fila['ms_real']}")
        i += 1
    print(f"\nListo. Datos en {args.csv}. Ahora: python calibrar.py analizar")


def cmd_prueba(args):
    ejecutar_pruebas(args, [args.ms] * args.n)


def cmd_barrido(args):
    plan = [ms for ms in args.ms for _ in range(args.n)]
    random.shuffle(plan)     # orden aleatorio: evita que la bateria sesgue una sola duracion
    ejecutar_pruebas(args, plan)


# ======================================================================
# Analisis estadistico
# ======================================================================
def importar_ciencia():
    try:
        import numpy as np
        from scipy import stats
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return np, stats, plt
    except ImportError:
        raise SystemExit("Faltan librerias. Instala con:  pip install -r requirements.txt")


def descriptiva(np, stats, x):
    x = np.asarray([v for v in x if not math.isnan(v)])
    n = len(x)
    r = {"n": n}
    if n == 0:
        return r
    r["media"] = float(np.mean(x))
    r["min"], r["max"] = float(np.min(x)), float(np.max(x))
    if n >= 2:
        r["de"] = float(np.std(x, ddof=1))
        r["cv"] = r["de"] / abs(r["media"]) * 100 if r["media"] else math.nan
        t = stats.t.ppf(0.975, n - 1)
        r["ic95"] = (r["media"] - t * r["de"] / math.sqrt(n), r["media"] + t * r["de"] / math.sqrt(n))
        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        r["atipicos"] = [float(v) for v in x if v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr]
    if n >= 3:
        r["shapiro_p"] = float(stats.shapiro(x).pvalue) if np.ptp(x) > 0 else math.nan
    return r


def fmt(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{v:.{d}f}"


def tamano_muestra(stats, de, error, n_actual):
    """n necesario para que el IC95 tenga +/- error (iterando con t de Student)."""
    if not de or not error:
        return None
    n = max(n_actual, 3)
    for _ in range(50):
        nuevo = math.ceil((stats.t.ppf(0.975, n - 1) * de / error) ** 2)
        if nuevo == n:
            break
        n = max(nuevo, 2)
    return n


def dir_analisis(args):
    """Las graficas y el resumen se guardan junto al CSV, en analisis/."""
    return os.path.join(os.path.dirname(os.path.abspath(args.csv)), "analisis")


def csv_validacion(args):
    return os.path.join(os.path.dirname(os.path.abspath(args.csv)), "validacion.csv")


def cmd_analizar(args):
    np, stats, plt = importar_ciencia()
    DIR_ANALISIS = dir_analisis(args)
    filas = leer_csv(args.csv)
    os.makedirs(DIR_ANALISIS, exist_ok=True)
    md = []   # resumen en Markdown para el reporte
    md.append(f"# Resultados de calibracion\n\nGenerado: {datetime.now():%Y-%m-%d %H:%M}  \n"
              f"Datos: `{os.path.basename(args.csv)}` ({len(filas)} pruebas)\n")
    sugerencias = {}

    def p(linea=""):
        print(linea)
        md.append(linea)

    # ---------- 1. Descriptiva por condicion ----------
    p("## 1. Estadistica descriptiva por condicion\n")
    p("Condicion = tipo + PWM + duracion + factores de correccion. IC95 con t de Student; "
      "normalidad con Shapiro-Wilk (p > 0.05 = no se rechaza normalidad); atipicos por regla IQR.\n")
    p("| Tipo | PWM izq/der | ms | trim i/d | Variable | n | Media | DE | CV % | IC95 | Shapiro p | Atipicos | n para +/-E |")
    p("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    grupos = {}
    for f in filas:
        clave = (f["tipo"], f["pwm_izq"], f["pwm_der"], int(num(f["ms"])), f["trim_i"], f["trim_d"])
        grupos.setdefault(clave, []).append(f)
    for clave in sorted(grupos, key=lambda k: (k[0], k[3])):
        tipo = clave[0]
        for campo in TIPOS.get(tipo, {"campos": []})["campos"]:
            x = [num(f[campo]) for f in grupos[clave]]
            d = descriptiva(np, stats, x)
            if d["n"] == 0:
                continue
            error = args.error_cm if campo.endswith("cm") else args.error_deg
            nreq = tamano_muestra(stats, d.get("de"), error, d["n"])
            ic = f"[{fmt(d['ic95'][0], 1)}, {fmt(d['ic95'][1], 1)}]" if "ic95" in d else "-"
            p(f"| {tipo} | {clave[1]}/{clave[2]} | {clave[3]} | {clave[4]}/{clave[5]} | {campo} | {d['n']} | "
              f"{fmt(d['media'])} | {fmt(d.get('de'))} | {fmt(d.get('cv'), 1)} | {ic} | "
              f"{fmt(d.get('shapiro_p'), 3)} | {len(d.get('atipicos', []))} | {nreq or '-'} |")
    p(f"\n*n para +/-E*: repeticiones necesarias para un IC95 de +/-{args.error_cm} cm o +/-{args.error_deg} grados.\n")

    # ---------- 2. Desviacion en linea recta ----------
    p("## 2. Desviacion en linea recta (prueba t de una muestra, H0: media = 0)\n")
    p("Se usan las pruebas de 30 cm o mas, normalizadas a 1 m con desviacion / (avance/100)^2 "
      "(una curvatura constante hace crecer la desviacion con el cuadrado de la distancia).\n")
    for tipo in ("adelante", "atras"):
        sub = [f for f in filas if f["tipo"] == tipo]
        if len(sub) < 3:
            continue
        # Se normaliza a 1 m: desviacion / (avance/100)^2 (la curvatura constante crece con D^2)
        desv = np.array([num(f["desviacion_cm"]) for f in sub])
        av = np.array([num(f["avance_cm"]) for f in sub])
        ok = ~np.isnan(desv) & ~np.isnan(av) & (av >= 30)   # en recorridos cortos domina el ruido
        if ok.sum() < 3:
            continue
        desv_1m = desv[ok] / (av[ok] / 100) ** 2
        t = stats.ttest_1samp(desv_1m, 0)
        lado = "izquierda" if desv_1m.mean() > 0 else "derecha"
        p(f"- **{tipo}**: desviacion equivalente a 1 m = {fmt(desv_1m.mean(), 1)} +/- {fmt(desv_1m.std(ddof=1), 1)} cm "
          f"(n={ok.sum()}), t={fmt(t.statistic)}, p={fmt(t.pvalue, 4)}.")
        if t.pvalue < 0.05:
            p(f"  - Se desvia de forma **sistematica** hacia la {lado}: conviene ajustar el factor de correccion.")
            if tipo == "adelante":
                trims = (num(sub[-1]["trim_i"]), num(sub[-1]["trim_d"]))
                # curvatura k = 2y/D^2 ; (vD - vI)/v = k*L  (modelo diferencial)
                k = 2 * desv_1m.mean() / 100 ** 2
                if args.L:
                    rel = abs(k * args.L)
                    msg = f"diferencia relativa de velocidad = {rel * 100:.1f} %"
                else:
                    rel = 0.02
                    msg = "sin L medido se sugiere un paso de 2 %; repite la prueba y ajusta"
                if desv_1m.mean() > 0:   # se va a la izquierda: el lado derecho es mas rapido
                    sugerencias["trim_d"] = round(trims[1] * (1 - rel), 3)
                    p(f"  - Lado derecho mas rapido ({msg}). Sugerencia: trim_d = {sugerencias['trim_d']}")
                else:
                    sugerencias["trim_i"] = round(trims[0] * (1 - rel), 3)
                    p(f"  - Lado izquierdo mas rapido ({msg}). Sugerencia: trim_i = {sugerencias['trim_i']}")
        else:
            p("  - No hay evidencia de desviacion sistematica (p >= 0.05): la desviacion es ruido aleatorio.")
    p("")

    # ---------- 3. Regresion tiempo -> distancia / angulo ----------
    p("## 3. Regresion lineal: magnitud = pendiente * t + ordenada\n")
    p("La pendiente es la velocidad real; la ordenada (normalmente negativa) es lo que se pierde al arrancar y frenar.\n")
    p("| Tipo | PWM | Variable | n | Duraciones | Pendiente | IC95 pendiente | Ordenada | R2 | p |")
    p("|---|---|---|---|---|---|---|---|---|---|")
    regresiones = {}
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.5))
    for tipo, campo, eje in (("adelante", "avance_cm", 0), ("atras", "avance_cm", 0),
                             ("giro_izq", "angulo_deg", 1), ("giro_der", "angulo_deg", 1),
                             ("pivote_izq", "angulo_deg", 1), ("pivote_der", "angulo_deg", 1)):
        por_pwm = {}
        for f in filas:
            if f["tipo"] == tipo:
                por_pwm.setdefault(abs(int(num(f["pwm_izq"]) or num(f["pwm_der"]))), []).append(f)
        for pwm, sub in por_pwm.items():
            t = np.array([num(f["ms_real"]) if not math.isnan(num(f["ms_real"])) else num(f["ms"]) for f in sub]) / 1000
            y = np.array([num(f[campo]) for f in sub])
            ok = ~np.isnan(t) & ~np.isnan(y)
            t, y = t[ok], y[ok]
            if len(set(np.round(t, 2))) < 3 or len(t) < 4:
                continue
            r = stats.linregress(t, y)
            tc = stats.t.ppf(0.975, len(t) - 2)
            regresiones[(tipo, pwm)] = r
            p(f"| {tipo} | {pwm} | {campo} | {len(t)} | {len(set(np.round(t, 2)))} | {fmt(r.slope)} | "
              f"[{fmt(r.slope - tc * r.stderr)}, {fmt(r.slope + tc * r.stderr)}] | {fmt(r.intercept)} | "
              f"{fmt(r.rvalue ** 2, 4)} | {fmt(r.pvalue, 4)} |")
            ax = ejes[eje]
            ax.scatter(t, y, s=18, alpha=0.7, label=f"{tipo} (PWM {pwm})")
            xs = np.linspace(0, t.max() * 1.05, 50)
            ax.plot(xs, r.slope * xs + r.intercept, lw=1.5)
    for ax, ylab in zip(ejes, ("Distancia (cm)", "Angulo (grados)")):
        ax.set_xlabel("Tiempo con motores encendidos (s)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.3)
        if ax.has_data():
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DIR_ANALISIS, "regresion.png"), dpi=130)
    plt.close(fig)
    if not regresiones:
        p("| (se necesitan al menos 3 duraciones distintas por tipo: usa `barrido`) |||||||||| ")
    p("\n![Regresion](regresion.png)\n")

    # Residuos de la regresion principal
    r_ade = next((regresiones[k] for k in regresiones if k[0] == "adelante"), None)
    r_giro = next((regresiones[k] for k in regresiones if k[0] == "giro_izq"), None)
    if r_ade is not None:
        sugerencias["v"] = round(r_ade.slope, 3)
        sugerencias["b"] = round(r_ade.intercept, 3)
    if r_giro is not None:
        sugerencias["w"] = round(r_giro.slope, 3)
        sugerencias["bg"] = round(r_giro.intercept, 3)

    # ---------- 4. Tiempos calibrados y modelo cinematico ----------
    p("## 4. Tiempos calibrados y comparacion con el modelo cinematico\n")
    if r_ade is not None:
        t1m = (args.objetivo_cm - r_ade.intercept) / r_ade.slope
        p(f"- Velocidad lineal medida v = {fmt(r_ade.slope)} cm/s. Tiempo para {args.objetivo_cm:g} cm: **{t1m * 1000:.0f} ms**.")
    if r_giro is not None:
        t90 = (90 - r_giro.intercept) / r_giro.slope
        t360 = (360 - r_giro.intercept) / r_giro.slope
        sugerencias["t90"] = round(t90 * 1000)
        sugerencias["t360"] = round(t360 * 1000)
        p(f"- Velocidad angular medida w = {fmt(r_giro.slope)} grados/s. Tiempo para 90 grados: **{t90 * 1000:.0f} ms**; "
          f"para 360 grados: **{t360 * 1000:.0f} ms**.")
    if r_ade is not None and r_giro is not None:
        w_rad = math.radians(r_giro.slope)
        L_ef = 2 * r_ade.slope / w_rad      # giro sobre su eje: vR = v, vL = -v  ->  w = 2v/L
        p(f"- Modelo diferencial: v = (vR + vL)/2, w = (vR - vL)/L. En giro sobre su eje vR = -vL = v, asi que w = 2v/L.")
        p(f"- **L efectiva** (la que explica el giro medido) = 2v/w = {fmt(L_ef)} cm.")
        if args.L:
            w_teo = 2 * r_ade.slope / args.L
            t90_teo = (math.pi / 2) / w_teo
            p(f"- Con L medida = {args.L} cm: w teorica = {fmt(math.degrees(w_teo))} grados/s, "
              f"t90 teorico = **{t90_teo * 1000:.0f} ms** vs medido {((90 - r_giro.intercept) / r_giro.slope) * 1000:.0f} ms.")
            p(f"- Factor de derrape L_efectiva / L = {fmt(L_ef / args.L)}: el robot 4WD gira mas lento que el modelo "
              f"porque las llantas delanteras y traseras se arrastran de lado.")
        else:
            p("- Para comparar con el tiempo teorico, vuelve a correr con `--L <cm>` (distancia entre llantas).")
    p("")

    # ---------- 5. Comparaciones entre grupos ----------
    p("## 5. Comparaciones entre grupos (t de Welch)\n")

    def welch(nombre, a, b, etiqueta_a, etiqueta_b):
        a = np.array([v for v in a if not math.isnan(v)])
        b = np.array([v for v in b if not math.isnan(v)])
        if len(a) >= 3 and len(b) >= 3:
            t = stats.ttest_ind(a, b, equal_var=False)
            veredicto = "diferencia significativa" if t.pvalue < 0.05 else "sin diferencia significativa"
            p(f"- {nombre}: {etiqueta_a} = {fmt(a.mean())} vs {etiqueta_b} = {fmt(b.mean())}, "
              f"t = {fmt(t.statistic)}, p = {fmt(t.pvalue, 4)} -> {veredicto}.")

    # Misma duracion para que sea comparable
    def por_tipo_ms(tipo, campo):
        out = {}
        for f in filas:
            if f["tipo"] == tipo:
                out.setdefault(int(num(f["ms"])), []).append(num(f[campo]))
        return out
    gi, gd = por_tipo_ms("giro_izq", "angulo_deg"), por_tipo_ms("giro_der", "angulo_deg")
    for ms in sorted(set(gi) & set(gd)):
        welch(f"Simetria de giro ({ms} ms)", gi[ms], gd[ms], "izquierda", "derecha")
    ad, at = por_tipo_ms("adelante", "avance_cm"), por_tipo_ms("atras", "avance_cm")
    for ms in sorted(set(ad) & set(at)):
        welch(f"Adelante vs atras ({ms} ms)", ad[ms], at[ms], "adelante", "atras")
    gz, pz = por_tipo_ms("giro_izq", "angulo_deg"), por_tipo_ms("pivote_izq", "angulo_deg")
    for ms in sorted(set(gz) & set(pz)):
        welch(f"Giro sobre su eje vs un motor detenido ({ms} ms)", gz[ms], pz[ms], "eje", "pivote")
    # Antes/despues del ajuste de correccion (adelante, mismas ms, distinto trim)
    ad_trim = {}
    for f in filas:
        if f["tipo"] == "adelante" and not math.isnan(num(f["avance_cm"])) and num(f["avance_cm"]) >= 30:
            d1m = num(f["desviacion_cm"]) / (num(f["avance_cm"]) / 100) ** 2
            ad_trim.setdefault((f["trim_i"], f["trim_d"]), []).append(abs(d1m))
    claves = list(ad_trim)
    if len(claves) >= 2:
        welch("|Desviacion a 1 m| antes vs despues del ajuste", ad_trim[claves[0]], ad_trim[claves[-1]],
              f"trim {claves[0][0]}/{claves[0][1]}", f"trim {claves[-1][0]}/{claves[-1][1]}")
    p("")

    # ---------- 6. Efecto de la bateria y superficie ----------
    p("## 6. Efecto del voltaje de bateria y de la superficie\n")
    # Se correlaciona el voltaje con el residuo de la regresion de "adelante"
    # (cuanto avanzo de mas o de menos para su duracion), asi no influye el tiempo.
    resid, volt = [], []
    k_ade = next((k for k in regresiones if k[0] == "adelante"), None)
    if k_ade is not None:
        for f in filas:
            if f["tipo"] == "adelante" and abs(num(f["pwm_izq"])) == k_ade[1]:
                v, a = num(f["voltaje"]), num(f["avance_cm"])
                t = (num(f["ms_real"]) if not math.isnan(num(f["ms_real"])) else num(f["ms"])) / 1000
                if not math.isnan(v) and not math.isnan(a):
                    resid.append(a - (r_ade.slope * t + r_ade.intercept))
                    volt.append(v)
    if len(set(volt)) >= 3:
        r = stats.pearsonr(volt, resid)
        p(f"- Correlacion de Pearson entre voltaje y residuo de avance (cm de mas o de menos para su duracion): "
          f"r = {fmt(r.statistic, 3)}, p = {fmt(r.pvalue, 4)} (n = {len(resid)}). "
          f"{'Hay' if r.pvalue < 0.05 else 'No hay'} evidencia de que la bateria cambie la velocidad.")
        fig, ax = plt.subplots(figsize=(5.5, 4))
        ax.scatter(volt, resid, s=18)
        ax.set_xlabel("Voltaje de bateria (V)")
        ax.set_ylabel("Residuo de avance (cm)")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(DIR_ANALISIS, "bateria.png"), dpi=130)
        plt.close(fig)
        p("\n![Bateria](bateria.png)\n")
    else:
        p("- Se necesitan al menos 3 voltajes distintos para analizar la bateria (anota el voltaje en cada prueba).")
    sup = {}
    for f in filas:
        if f["tipo"] == "adelante" and f.get("superficie"):
            a = num(f["avance_cm"])
            if not math.isnan(a):
                sup.setdefault(f["superficie"], []).append(a / (num(f["ms"]) / 1000))
    if len(sup) >= 2 and all(len(v) >= 3 for v in sup.values()):
        r = stats.f_oneway(*sup.values())
        p(f"- ANOVA de una via, velocidad por superficie ({', '.join(sup)}): F = {fmt(r.statistic)}, p = {fmt(r.pvalue, 4)}.")
    p("")

    # ---------- 7. Graficas por condicion ----------
    cajas, etiquetas = [], []
    for clave in sorted(grupos, key=lambda k: (k[0], k[3])):
        campo = TIPOS.get(clave[0], {"campos": [None]})["campos"][0]
        if campo:
            x = [num(f[campo]) for f in grupos[clave] if not math.isnan(num(f[campo]))]
            if len(x) >= 2:
                cajas.append(x)
                etiquetas.append(f"{clave[0]}\n{clave[3]} ms")
    if cajas:
        fig, ax = plt.subplots(figsize=(max(6, len(cajas) * 1.1), 4.5))
        ax.boxplot(cajas)
        ax.set_xticks(range(1, len(etiquetas) + 1), etiquetas, fontsize=7)
        ax.set_ylabel("cm (rectas) / grados (giros)")
        ax.set_title("Dispersion por condicion")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(DIR_ANALISIS, "cajas.png"), dpi=130)
        plt.close(fig)
        p("![Cajas](cajas.png)\n")

    # ---------- Sugerencias ----------
    p("## 7. Parametros sugeridos para el robot\n")
    if sugerencias:
        p("| Parametro | Valor |\n|---|---|")
        for k, v in sugerencias.items():
            p(f"| {k} | {v} |")
        p("\nAplicalos con: `python calibrar.py aplicar`")
    else:
        p("Aun no hay datos suficientes para sugerir parametros.")
    with open(os.path.join(DIR_ANALISIS, "sugerencias.json"), "w", encoding="utf-8") as f:
        json.dump(sugerencias, f, indent=2)
    ruta_md = os.path.join(DIR_ANALISIS, "resumen.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"\nResumen: {ruta_md}\nGraficas en: {DIR_ANALISIS}")


def cmd_aplicar(args):
    ruta = os.path.join(dir_analisis(args), "sugerencias.json")
    if not os.path.exists(ruta):
        raise SystemExit("Primero corre: python calibrar.py analizar")
    sug = json.load(open(ruta, encoding="utf-8"))
    if args.solo:
        sug = {k: v for k, v in sug.items() if k in args.solo}
    if not sug:
        raise SystemExit("No hay parametros para aplicar.")
    print("Se enviaran al robot:", sug)
    if input("Confirmar (s/n): ").strip().lower() != "s":
        return
    robot = Robot(args.ip, args.simular)
    q = "&".join(f"{k}={v}" for k, v in sug.items())
    print("Configuracion del robot:", robot.get("/config?" + q))


# ======================================================================
# Validacion: ir a coordenadas y medir el error de posicion
# ======================================================================
def cmd_validar(args):
    robot = Robot(args.ip, args.simular)
    cfg = robot.config()
    if not args.simular and (cfg.get("v", 0) <= 0 or cfg.get("w", 0) <= 0):
        raise SystemExit("El robot no tiene v y w calibrados. Corre 'analizar' y 'aplicar' primero.")
    puntos = [tuple(float(c) for c in p.split(",")) for p in args.puntos.split()]
    sesion = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("Marco: origen = posicion inicial, x hacia el frente del robot, y hacia su izquierda (cm).")
    for vuelta in range(args.n):
        if not args.simular:
            input(f"\nVuelta {vuelta + 1}/{args.n}: robot en el origen viendo hacia +x y Enter...")
        robot.get("/origen")
        for k, (x, y) in enumerate(puntos, 1):
            r = robot.get(f"/ir?x={x}&y={y}")
            if not r.get("ok", False):
                raise SystemExit(f"El robot rechazo /ir: {r}")
            robot.esperar()
            if args.simular:
                xm, ym = x + random.gauss(0, 3), y + random.gauss(0, 3)
            else:
                print(f"  Punto {k}: objetivo ({x}, {y}) cm")
                xm = leer_numero("x medida (cm)")
                ym = leer_numero("y medida (cm)")
                if "q" in (xm, ym):
                    return
                if "r" in (xm, ym):
                    continue
            err = math.hypot(xm - x, ym - y)
            anexar_csv(csv_validacion(args), COLUMNAS_VAL, {
                "fecha": datetime.now().isoformat(timespec="seconds"), "sesion": sesion, "punto": k,
                "x_obj": x, "y_obj": y, "x_med": xm, "y_med": ym, "error_cm": round(err, 2),
                "voltaje": args.voltaje or "", "superficie": args.superficie, "nota": args.nota})
            print(f"  Error de posicion: {err:.1f} cm")
    filas = leer_csv(csv_validacion(args))
    errs = [num(f["error_cm"]) for f in filas if f["sesion"] == sesion]
    if errs:
        rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
        print(f"\nValidacion ({len(errs)} puntos): error medio = {sum(errs) / len(errs):.1f} cm, "
              f"RMSE = {rmse:.1f} cm, maximo = {max(errs):.1f} cm. Datos en {csv_validacion(args)}")


# ======================================================================
def main():
    ap = argparse.ArgumentParser(description="Calibracion estadistica del robot ESP32-CAM")
    ap.add_argument("--ip", default="192.168.4.1", help="IP del robot (por defecto 192.168.4.1)")
    ap.add_argument("--csv", default=CSV_PRUEBAS, help="archivo CSV de pruebas")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comunes(s):
        s.add_argument("--tipo", choices=list(TIPOS), required=True)
        s.add_argument("--pwm", type=int, help="PWM (por defecto el configurado en el robot)")
        s.add_argument("--l", type=int, help="PWM izquierdo manual (con --r ignora --tipo para los motores)")
        s.add_argument("--r", type=int, help="PWM derecho manual")
        s.add_argument("--voltaje", type=float, help="voltaje inicial de bateria (V)")
        s.add_argument("--superficie", default="piso", help="tipo de piso (para comparar superficies)")
        s.add_argument("--nota", default="")
        s.add_argument("--simular", action="store_true", help="probar sin robot, con datos ficticios")

    s = sub.add_parser("prueba", help="repite el mismo movimiento N veces")
    comunes(s)
    s.add_argument("--ms", type=int, required=True)
    s.add_argument("-n", type=int, default=10)
    s.set_defaults(func=cmd_prueba)

    s = sub.add_parser("barrido", help="varias duraciones x N repeticiones, en orden aleatorio")
    comunes(s)
    s.add_argument("--ms", type=int, nargs="+", required=True)
    s.add_argument("-n", type=int, default=5)
    s.set_defaults(func=cmd_barrido)

    s = sub.add_parser("analizar", help="estadistica, regresion y graficas")
    s.add_argument("--L", type=float, help="distancia entre llantas izq y der (cm)")
    s.add_argument("--objetivo-cm", type=float, default=100, help="distancia objetivo para el tiempo calibrado")
    s.add_argument("--error-cm", type=float, default=1.0, help="error aceptable para el tamano de muestra (cm)")
    s.add_argument("--error-deg", type=float, default=2.0, help="error aceptable para el tamano de muestra (grados)")
    s.set_defaults(func=cmd_analizar)

    s = sub.add_parser("aplicar", help="envia al robot los parametros sugeridos")
    s.add_argument("--solo", nargs="+", help="aplicar solo estas claves (ej. v b w bg)")
    s.add_argument("--simular", action="store_true")
    s.set_defaults(func=cmd_aplicar)

    s = sub.add_parser("validar", help="ir a coordenadas y medir el error de posicion")
    s.add_argument("--puntos", default="50,0 50,50 0,50 0,0", help='lista "x,y x,y ..." en cm')
    s.add_argument("-n", type=int, default=3, help="vueltas")
    s.add_argument("--voltaje", type=float)
    s.add_argument("--superficie", default="piso")
    s.add_argument("--nota", default="")
    s.add_argument("--simular", action="store_true")
    s.set_defaults(func=cmd_validar)

    args = ap.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrumpido. Mandando PARO al robot...")
        if not getattr(args, "simular", False):
            try:
                Robot(args.ip).get("/stop", timeout=2)
            except SystemExit:
                pass


if __name__ == "__main__":
    main()
