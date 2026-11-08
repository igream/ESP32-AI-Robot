#!/usr/bin/env python3
"""App de PC de la Tarea 2 (deteccion de objetos con Edge Impulse en el ESP32-CAM).

Subcomandos (una etapa cada uno, ver docs/PLAN_IMPLEMENTACION.md):
    estado          que etapa sigue y que falta
    preparar        verifica dependencias, Edge Impulse CLI, el robot y arduino-cli   (T2.0)
    condiciones     guarda las condiciones del experimento y los 3 objetos            (T2.1)
    capturar        toma fotos del robot por WiFi (GET /capture) para el dataset      (T2.2)
    servir          pagina para el celular: vista previa y boton de foto              (T2.2)
    subir           sube el dataset con edge-impulse-uploader                          (T2.3)
    entrenamiento   registra la corrida 1 o 2 de Edge Impulse                         (T2.4)
    marcar          marca a mano una etapa hecha fuera de la app (etiquetado, despliegue)
    pruebas         45 pruebas leyendo las lineas DET/NONE por puerto serie           (T2.6)
    resultados      tablas, estadistica y graficas                                     (T2.7)

Todos los datos quedan en herramientas/tarea2/datos/ (o en --datos).
Requiere: pyserial, numpy, scipy, matplotlib.
"""
import argparse
import csv
import json
import math
import random
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8")
    except Exception:
        pass

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
DATOS = AQUI / "datos"
ROBOT = "http://192.168.4.1"
ARDUINO_CLI = "C:/Users/feraz/AppData/Local/Programs/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe"
PROHIBIDOS = {"led", "bornera", "pulsador"}      # objetos del video de referencia
MIN_FOTOS, META_FOTOS = 50, 60
PRUEBAS_ENT, PRUEBAS_OTRA = 10, 5
VENTANA_S = 3.0
COLS_PRUEBAS = ["objeto", "condicion", "prueba", "etiqueta", "prob", "x", "y", "acierto", "cuadros", "t_inf_ms", "nota"]


# ---------------------------------------------------------------- utilidades
def ruta(nombre):
    return DATOS / nombre


def leer_json(nombre, defecto=None):
    p = ruta(nombre)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return defecto


def guardar_json(nombre, obj):
    DATOS.mkdir(parents=True, exist_ok=True)
    ruta(nombre).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def preguntar(texto, defecto=None, tipo=str):
    while True:
        suf = f" [{defecto}]" if defecto not in (None, "") else ""
        r = input(f"{texto}{suf}: ").strip()
        if not r and defecto not in (None, ""):
            return defecto
        if not r:
            continue
        try:
            return tipo(r.replace(",", ".")) if tipo is float else tipo(r)
        except ValueError:
            print("  Valor no valido.")


def si_no(texto, defecto=True):
    r = input(f"{texto} [{'S/n' if defecto else 's/N'}]: ").strip().lower()
    return defecto if not r else r.startswith("s")


def pedir_jpeg(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def resolucion_jpeg(d):
    """(ancho, alto) leyendo el marcador SOF del JPEG; None si no es un JPEG valido."""
    if len(d) < 4 or d[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(d):
        if d[i] != 0xFF:
            return None
        m = d[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(d[i + 2:i + 4], "big")
    return None


def objetos():
    c = leer_json("condiciones.json")
    return [o["nombre"] for o in c["objetos"]] if c else []


def contar_fotos(obj):
    d = ruta("dataset") / obj
    return len(list(d.glob("*.jpg"))) if d.exists() else 0


def contar_pruebas():
    p = ruta("pruebas.csv")
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


# ---------------------------------------------------------------- estado
def etapas():
    est = leer_json("estado.json", {})
    objs = objetos()
    ent = leer_json("entrenamientos.json", {})
    total_pruebas = 3 * (PRUEBAS_ENT + PRUEBAS_OTRA)
    return [
        ("T2.0 preparar", bool(est.get("preparar")), "python tarea2.py preparar"),
        ("T2.1 condiciones y objetos", bool(objs), "python tarea2.py condiciones"),
        ("T2.2 captura (>= 50 fotos por objeto)", bool(objs) and all(contar_fotos(o) >= MIN_FOTOS for o in objs),
         "python tarea2.py capturar --objeto <nombre> --n 60 --auto 2"),
        ("T2.3 subida a Edge Impulse", bool(est.get("subido")), "python tarea2.py subir"),
        ("T2.3b etiquetado en Edge Impulse", bool(est.get("etiquetado")), "etiqueta en el Studio y luego: python tarea2.py marcar etiquetado"),
        ("T2.4 entrenamiento (corridas 1 y 2)", "1" in ent and "2" in ent, "python tarea2.py entrenamiento --corrida 1|2"),
        ("T2.5 despliegue (sketch en el robot)", bool(est.get("desplegado")), "ver plan T2.5; luego: python tarea2.py marcar desplegado"),
        (f"T2.6 pruebas ({total_pruebas})", contar_pruebas() >= total_pruebas, "python tarea2.py pruebas --puerto COM8"),
        ("T2.7 resultados", ruta("resultados/resultados.md").exists(), "python tarea2.py resultados"),
        ("T2.8 reporte", (RAIZ / "docs/Tarea2/REPORTE.md").exists(), "escribir docs/Tarea2/REPORTE.md"),
    ]


def cmd_estado(a):
    print(f"Datos: {DATOS}\n")
    siguiente = None
    for n, ok, como in etapas():
        marca = "✓" if ok else ("→" if siguiente is None else "·")
        if not ok and siguiente is None:
            siguiente = (n, como)
        print(f" {marca} {n}")
    objs = objetos()
    if objs:
        print("\nFotos: " + ", ".join(f"{o}={contar_fotos(o)}" for o in objs))
        print(f"Pruebas guardadas: {contar_pruebas()}")
    print("\nSiguiente: " + (f"{siguiente[0]}\n   {siguiente[1]}" if siguiente else "todo hecho"))


def cmd_marcar(a):
    est = leer_json("estado.json", {})
    est[a.clave] = True
    guardar_json("estado.json", est)
    print(f"Marcado: {a.clave}")


# ---------------------------------------------------------------- T2.0 preparar
def cmd_preparar(a):
    fallos = 0

    def mostrar(ok, texto, ayuda=""):
        nonlocal fallos
        print(f" {'✓' if ok else '✗'} {texto}" + ("" if ok or not ayuda else f"\n     -> {ayuda}"))
        fallos += 0 if ok else 1

    for mod in ("serial", "numpy", "scipy", "matplotlib"):
        try:
            __import__(mod)
            mostrar(True, f"Python: {mod}")
        except ImportError:
            mostrar(False, f"Python: {mod}", "pip install -r herramientas/requirements.txt")
    up = shutil.which("edge-impulse-uploader")
    mostrar(bool(up), "edge-impulse-uploader en el PATH", "npm install -g edge-impulse-cli  (luego: edge-impulse-uploader --clean para iniciar sesion)")
    try:
        d = pedir_jpeg(ROBOT + "/capture", 5)
        res = resolucion_jpeg(d)
        mostrar(res is not None, f"Robot responde /capture ({res[0]}x{res[1]})" if res else "Robot: /capture no devolvio un JPEG",
                "revisa que el firmware tenga /capture registrado")
    except Exception as ex:
        mostrar(False, f"Robot: no responde {ROBOT}/capture ({ex})", "conecta la PC al WiFi ESP32Car_Fer y enciende el robot")
    cli = Path(ARDUINO_CLI)
    mostrar(cli.exists(), "arduino-cli", f"no esta en {ARDUINO_CLI}")
    if cli.exists():
        try:
            out = subprocess.run([str(cli), "core", "list"], capture_output=True, text=True, timeout=30).stdout
            esp = [l.split()[1] for l in out.splitlines() if l.startswith("esp32:esp32")]
            mostrar(bool(esp), f"Core ESP32 instalado: {', '.join(esp) if esp else 'ninguno'}", "arduino-cli core install esp32:esp32")
        except Exception as ex:
            mostrar(False, f"No pude consultar el core ({ex})")
    est = leer_json("estado.json", {})
    est["preparar"] = fallos == 0
    guardar_json("estado.json", est)
    print("\nTodo listo." if fallos == 0 else f"\n{fallos} punto(s) por resolver.")


# ---------------------------------------------------------------- T2.1 condiciones
def cmd_condiciones(a):
    c = leer_json("condiciones.json", {})
    print("Condiciones del experimento (Enter conserva el valor anterior).\n")
    c["altura_camara_cm"] = preguntar("Altura de la camara (cm)", c.get("altura_camara_cm"), float)
    c["distancia_punto_cm"] = preguntar("Distancia del punto marcado a la camara (cm)", c.get("distancia_punto_cm"), float)
    c["fondo"] = preguntar("Descripcion del fondo", c.get("fondo"))
    c["iluminacion"] = preguntar("Iluminacion (ej. lampara LED blanca a 50 cm)", c.get("iluminacion"))
    c["flash"] = si_no("Se usa el LED flash", c.get("flash", False))
    previos = [o["nombre"] for o in c.get("objetos", [])]
    nombres = []
    for i in range(3):
        while True:
            n = preguntar(f"Objeto {i + 1} (nombre corto, sin espacios)", previos[i] if i < len(previos) else None).lower()
            if " " in n or not n.isascii():
                print("  Sin espacios ni acentos.")
            elif n in PROHIBIDOS:
                print(f"  '{n}' es uno de los objetos del video ({', '.join(sorted(PROHIBIDOS))}); elige otro.")
            elif n in nombres:
                print("  Ya lo elegiste.")
            else:
                nombres.append(n)
                break
    print("Dos de los objetos deben parecerse (para probar la confusion).")
    par = []
    while len(par) != 2 or not set(par) <= set(nombres) or par[0] == par[1]:
        par = preguntar("Cuales dos se parecen (separados por coma)", ",".join(c.get("parecidos", [])) or None).replace(" ", "").lower().split(",")
    c["parecidos"] = par
    c["por_que_parecen"] = preguntar("Por que se parecen", c.get("por_que_parecen"))
    c["objetos"] = [{"nombre": n} for n in nombres]
    c["fecha"] = datetime.now().isoformat(timespec="seconds")
    guardar_json("condiciones.json", c)
    print(f"\nGuardado en {ruta('condiciones.json')}.\nPunto de control: confirma los objetos con tu profesor/plan antes de capturar.")


# ---------------------------------------------------------------- T2.2 capturar
RES_ESPERADA = (320, 240)
CANDADO_FOTO = threading.Lock()


def indice_foto(nombre):
    """Numero de una foto 'objeto_NNN.jpg' (0 si no tiene)."""
    try:
        return int(Path(nombre).stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def ultima_foto(obj):
    fotos = sorted((ruta("dataset") / obj).glob("*.jpg"), key=lambda f: indice_foto(f.name))
    return fotos[-1] if fotos else None


def guardar_foto(obj):
    """Pide una foto al robot y la guarda. Devuelve dict con ok y datos o error."""
    with CANDADO_FOTO:
        if obj not in objetos():
            return {"ok": False, "error": f"objeto desconocido: {obj}"}
        try:
            d = pedir_jpeg(ROBOT + "/capture")
        except Exception as ex:
            return {"ok": False, "error": f"el robot no responde ({ex})"}
        res = resolucion_jpeg(d)
        if not res or len(d) < 1000:
            return {"ok": False, "error": f"foto vacia o invalida ({len(d)} B)"}
        if res != RES_ESPERADA:
            return {"ok": False, "error": f"resolucion {res[0]}x{res[1]} distinta de {RES_ESPERADA[0]}x{RES_ESPERADA[1]}"}
        carpeta = ruta("dataset") / obj
        carpeta.mkdir(parents=True, exist_ok=True)
        ult = ultima_foto(obj)
        k = (indice_foto(ult.name) if ult else 0) + 1
        nombre = f"{obj}_{k:03d}.jpg"
        (carpeta / nombre).write_bytes(d)
        csv_ruta = ruta("dataset/capturas.csv")
        nuevo = not csv_ruta.exists()
        with open(csv_ruta, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(["archivo", "objeto", "fecha", "bytes", "resolucion"])
            w.writerow([f"{obj}/{nombre}", obj, datetime.now().isoformat(timespec="seconds"), len(d), f"{res[0]}x{res[1]}"])
        return {"ok": True, "archivo": nombre, "n": contar_fotos(obj), "bytes": len(d), "res": f"{res[0]}x{res[1]}"}


def deshacer_foto(obj):
    """Borra la ultima foto del objeto y su fila de capturas.csv."""
    with CANDADO_FOTO:
        f = ultima_foto(obj) if obj in objetos() else None
        if not f:
            return {"ok": False, "error": "no hay fotos que borrar"}
        rel = f"{obj}/{f.name}"
        f.unlink()
        csv_ruta = ruta("dataset/capturas.csv")
        if csv_ruta.exists():
            with open(csv_ruta, encoding="utf-8", newline="") as fh:
                filas = list(csv.reader(fh))
            with open(csv_ruta, "w", encoding="utf-8", newline="") as fh:
                csv.writer(fh).writerows([r for r in filas if not r or r[0] != rel])
        return {"ok": True, "archivo": f.name, "n": contar_fotos(obj)}


def cmd_capturar(a):
    c = leer_json("condiciones.json")
    if not c:
        sys.exit("Falta condiciones.json: corre primero 'condiciones'.")
    if a.objeto not in objetos():
        sys.exit(f"'{a.objeto}' no esta en condiciones.json ({', '.join(objetos())}).")
    print(f"Condiciones: camara a {c['altura_camara_cm']} cm, punto a {c['distancia_punto_cm']} cm, fondo: {c['fondo']}, luz: {c['iluminacion']}, flash: {'si' if c['flash'] else 'no'}.")
    print(f"{a.objeto}: {contar_fotos(a.objeto)} fotos. Meta: {a.n}. Modo {'automatico cada ' + str(a.auto) + ' s' if a.auto else 'manual (Enter = foto, q = salir)'}.")
    fallos = 0
    while contar_fotos(a.objeto) < a.n:
        if a.auto:
            time.sleep(a.auto)
        elif input(f"[{contar_fotos(a.objeto) + 1}/{a.n}] Enter para foto (q sale): ").strip().lower() == "q":
            break
        r = guardar_foto(a.objeto)
        if r["ok"]:
            fallos = 0
            print(f"  {r['n']}/{a.n} {r['archivo']} {r['res']} {r['bytes']} B")
        else:
            fallos += 1
            print(f"  Error ({fallos}/5): {r['error']}")
            if fallos >= 5:
                print("  Demasiados errores seguidos: revisa el WiFi y el robot.")
                break
    print(f"{a.objeto}: {contar_fotos(a.objeto)} fotos.")


# ---------------------------------------------------------------- servir (captura desde el celular)
def ip_local():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.4.1", 9))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "IP-DE-LA-PC"


def cmd_servir(a):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs
    if not objetos():
        sys.exit("Falta condiciones.json: corre primero 'condiciones'.")
    pagina = (AQUI / "captura_movil.html").read_bytes()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def enviar(self, codigo, tipo, cuerpo):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def json(self, obj, codigo=200):
            self.enviar(codigo, "application/json", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        def atender(self, metodo):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            obj = (q.get("objeto") or [""])[0]
            if metodo == "GET" and u.path == "/":
                return self.enviar(200, "text/html; charset=utf-8", pagina)
            if metodo == "GET" and u.path == "/api/estado":
                return self.json({"objetos": [{"nombre": o, "n": contar_fotos(o)} for o in objetos()], "meta": a.meta, "min": MIN_FOTOS})
            if metodo == "GET" and u.path == "/api/ultima":
                f = ultima_foto(obj) if obj in objetos() else None
                return self.enviar(200, "image/jpeg", f.read_bytes()) if f else self.json({"ok": False}, 404)
            if metodo == "POST" and u.path == "/api/foto":
                return self.json(guardar_foto(obj))
            if metodo == "POST" and u.path == "/api/deshacer":
                return self.json(deshacer_foto(obj))
            self.json({"ok": False, "error": "no encontrado"}, 404)

        def do_GET(self):
            self.atender("GET")

        def do_POST(self):
            self.atender("POST")

    srv = ThreadingHTTPServer(("0.0.0.0", a.puerto), H)
    print(f"Captura desde el celular. Conecta el celular al WiFi ESP32Car_Fer y abre:\n\n    http://{ip_local()}:{a.puerto}\n")
    print("(Si Windows pregunta por el firewall, permite Python en redes privadas.)  Ctrl+C para terminar.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


# ---------------------------------------------------------------- T2.3 subir
def cmd_subir(a):
    objs = objetos()
    if not objs:
        sys.exit("Falta condiciones.json.")
    up = shutil.which("edge-impulse-uploader")
    if not up and not a.simulacro:
        sys.exit("No encuentro edge-impulse-uploader (npm install -g edge-impulse-cli).")
    DATOS.mkdir(parents=True, exist_ok=True)
    with open(ruta("subida.log"), "a", encoding="utf-8") as log:
        for o in objs:
            fotos = sorted((ruta("dataset") / o).glob("*.jpg"))
            if len(fotos) < MIN_FOTOS:
                sys.exit(f"{o}: solo {len(fotos)} fotos (minimo {MIN_FOTOS}).")
            cmd = [up or "edge-impulse-uploader", "--category", "split", "--label", o] + [str(x) for x in fotos]
            print(f"{o}: {len(fotos)} fotos -> edge-impulse-uploader --category split --label {o} ...")
            if a.simulacro:
                continue
            r = subprocess.run(cmd, capture_output=True, text=True)
            log.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} {o} (codigo {r.returncode})\n{r.stdout}\n{r.stderr}\n")
            if r.returncode != 0:
                sys.exit(f"Fallo la subida de {o}; revisa {ruta('subida.log')}")
    if not a.simulacro:
        est = leer_json("estado.json", {})
        est["subido"] = True
        guardar_json("estado.json", est)
    print("\nEtiquetado: Edge Impulse Studio -> Data acquisition -> Labeling queue.\n"
          "  Dibuja cuadros ajustados a cada objeto (puedes usar el etiquetado asistido).\n"
          "  Al terminar: python tarea2.py marcar etiquetado")


# ---------------------------------------------------------------- T2.4 entrenamiento
def cmd_entrenamiento(a):
    ent = leer_json("entrenamientos.json", {})
    n = str(a.corrida)
    if n == "2" and "1" not in ent:
        sys.exit("Registra primero la corrida 1.")
    prev = ent.get(n, {})
    objs = objetos()
    print(f"Corrida {n}. Valores de Edge Impulse Studio (Enter conserva el anterior).")
    if n == "1":
        print("Guia: corrida 1 con los valores por defecto.")
    else:
        print("Guia: corrida 2 cambia UN solo parametro segun la confusion observada\n"
              "      (tasa de aprendizaje a 0.01, mas ciclos o mas fotos del objeto confundido).")
    cfg0 = prev.get("config", ent.get("1", {}).get("config", {}))
    cfg = {
        "resolucion": preguntar("Resolucion del impulse", cfg0.get("resolucion", "96x96")),
        "color": preguntar("Modo de color", cfg0.get("color", "escala de grises")),
        "modelo": preguntar("Modelo", cfg0.get("modelo", "FOMO MobileNetV2 0.35")),
        "ciclos": preguntar("Ciclos de entrenamiento", cfg0.get("ciclos", 60), int),
        "tasa": preguntar("Tasa de aprendizaje", cfg0.get("tasa", 0.001), float),
        "aumento": preguntar("Aumento de datos (si/no)", cfg0.get("aumento", "no")),
    }
    reg = {"config": cfg, "fecha": datetime.now().isoformat(timespec="seconds")}
    reg["f1_total"] = preguntar("F1 de validacion total (0-1 o %)", prev.get("f1_total"), float)
    reg["f1_clases"] = {o: preguntar(f"F1 de '{o}'", prev.get("f1_clases", {}).get(o), float) for o in objs}
    etiquetas = objs + ["uncertain"]
    print(f"Matriz de confusion: una fila por clase real, columnas en el orden: {', '.join(etiquetas)}.")
    filas = []
    for e in etiquetas:
        while True:
            txt = input(f"  fila '{e}' ({len(etiquetas)} numeros): ").replace(",", " ").split()
            if len(txt) == len(etiquetas):
                try:
                    filas.append([float(x) for x in txt])
                    break
                except ValueError:
                    pass
            print("  Revisa la cantidad de numeros.")
    reg["matriz"] = {"etiquetas": etiquetas, "filas": filas}
    reg["dispositivo"] = {
        "inferencia_ms": preguntar("Inferencia estimada (ms)", prev.get("dispositivo", {}).get("inferencia_ms"), float),
        "ram_kb": preguntar("RAM (KB)", prev.get("dispositivo", {}).get("ram_kb"), float),
        "flash_kb": preguntar("Flash (KB)", prev.get("dispositivo", {}).get("flash_kb"), float),
    }
    reg["captura"] = f"docs/Tarea2/img/entrenamiento_{n}.png"
    if n == "2":
        reg["cambio"] = {"parametro": preguntar("UNICO parametro que cambio", prev.get("cambio", {}).get("parametro")),
                         "motivo": preguntar("Por que", prev.get("cambio", {}).get("motivo"))}
    ent[n] = reg
    guardar_json("entrenamientos.json", ent)
    print(f"Guardado. Guarda la captura de pantalla en {reg['captura']}.")
    if n == "2":
        print("Punto de control: comparte entrenamientos.json en el chat de Opus antes de desplegar.")


# ---------------------------------------------------------------- T2.6 pruebas
def parsear(linea):
    """DET;t;dsp;clasif;etiqueta;prob;cx;cy;w;h  |  NONE;t;dsp;clasif  ->  dict o None"""
    p = linea.strip().split(";")
    try:
        if p[0] == "DET" and len(p) >= 10:
            return {"tipo": "DET", "dsp": float(p[2]), "clas": float(p[3]), "etiqueta": p[4], "prob": float(p[5]),
                    "x": float(p[6]), "y": float(p[7])}
        if p[0] == "NONE" and len(p) >= 4:
            return {"tipo": "NONE", "dsp": float(p[2]), "clas": float(p[3])}
    except ValueError:
        pass
    return None


class LectorSerie:
    def __init__(self, puerto, baudios=115200):
        import serial
        self.s = serial.Serial(puerto, baudios, timeout=0.2)
        self.s.dtr = False
        self.s.rts = False

    def ventana(self, seg, crudo):
        self.s.reset_input_buffer()
        t0, tramas = time.time(), []
        while time.time() - t0 < seg:
            l = self.s.readline().decode("utf-8", errors="replace")
            if l.strip():
                crudo.write(l if l.endswith("\n") else l + "\n")
                p = parsear(l)
                if p:
                    tramas.append(p)
        return tramas


class LectorSimulado:
    """Genera tramas falsas para probar la app sin robot."""

    def __init__(self):
        self.objeto = None

    def ventana(self, seg, crudo):
        tramas = []
        for _ in range(12):
            if random.random() < 0.15 or not self.objeto:
                t = {"tipo": "NONE", "dsp": 3.0, "clas": 85.0 + random.random() * 4}
                crudo.write("NONE;0;3;86\n")
            else:
                et = self.objeto if random.random() < 0.85 else random.choice(["a", "b", "c"])
                t = {"tipo": "DET", "dsp": 3.0, "clas": 85.0 + random.random() * 4, "etiqueta": et, "prob": random.uniform(.5, .99),
                     "x": 48 + random.gauss(0, 3), "y": 48 + random.gauss(0, 3)}
                crudo.write(f"DET;0;3;86;{et};{t['prob']:.2f};{t['x']:.0f};{t['y']:.0f};10;10\n")
            tramas.append(t)
        return tramas


def cmd_pruebas(a):
    objs = objetos()
    if not objs:
        sys.exit("Falta condiciones.json.")
    lector = LectorSimulado() if a.simular else LectorSerie(a.puerto)
    plan = []
    for o in objs:
        plan += [(o, "entrenamiento", i) for i in range(1, PRUEBAS_ENT + 1)]
        plan += [(o, "otra", i) for i in range(1, PRUEBAS_OTRA + 1)]
    hechas = contar_pruebas()
    print(f"{len(plan)} pruebas en total; ya hay {hechas}. Ventana de lectura: {VENTANA_S:.0f} s. Ctrl+C para pausar.")
    nuevo = not ruta("pruebas.csv").exists()
    DATOS.mkdir(parents=True, exist_ok=True)
    with open(ruta("pruebas.csv"), "a", newline="", encoding="utf-8") as f, open(ruta("pruebas_crudo.log"), "a", encoding="utf-8") as crudo:
        w = csv.DictWriter(f, fieldnames=COLS_PRUEBAS)
        if nuevo:
            w.writeheader()
        for idx in range(hechas, len(plan)):
            obj, cond, num = plan[idx]
            if cond == "otra":
                cond = input("  Condicion de esta prueba: 'posicion' u 'luz' [posicion]: ").strip().lower() or "posicion"
                if cond not in ("posicion", "luz"):
                    cond = "posicion"
            print(f"\nPrueba {idx + 1}/{len(plan)}: objeto {obj} · condicion {cond} · n.o {num}")
            if a.simular:
                lector.objeto = obj
            else:
                input("  Coloca el objeto y presiona Enter... ")
            crudo.write(f"# prueba {idx + 1} {obj} {cond} {datetime.now().isoformat(timespec='seconds')}\n")
            tr = lector.ventana(VENTANA_S, crudo)
            crudo.flush()
            dets = [t for t in tr if t["tipo"] == "DET"]
            if dets:
                mejor = max(dets, key=lambda t: t["prob"])
                etiqueta, prob, x, y = mejor["etiqueta"], mejor["prob"], mejor["x"], mejor["y"]
            else:
                etiqueta, prob, x, y = "sin_deteccion", "", "", ""
            acierto = etiqueta == obj
            print(f"  -> {etiqueta}" + (f" ({prob:.2f}) en ({x:.0f},{y:.0f})" if dets else "") + f" · cuadros: {len(tr)} · acierto: {'si' if acierto else 'no'}")
            if not a.simular:
                r = input("  Enter acepta, 's' o 'n' corrige el acierto, nota opcional despues de ':' : ").strip()
                nota = ""
                if ":" in r:
                    r, nota = r.split(":", 1)
                if r.lower() in ("s", "n"):
                    acierto = r.lower() == "s"
            else:
                nota = ""
            tinf = sum(t["dsp"] + t["clas"] for t in tr) / len(tr) if tr else ""
            w.writerow({"objeto": obj, "condicion": cond, "prueba": num, "etiqueta": etiqueta,
                        "prob": f"{prob:.3f}" if dets else "", "x": f"{x:.1f}" if dets else "", "y": f"{y:.1f}" if dets else "",
                        "acierto": "si" if acierto else "no", "cuadros": len(tr),
                        "t_inf_ms": f"{tinf:.1f}" if tr else "", "nota": nota.strip()})
            f.flush()
    print("\nPruebas completas." if contar_pruebas() >= len(plan) else "\nPausa. Vuelve a correr 'pruebas' para continuar.")


# ---------------------------------------------------------------- T2.7 resultados
def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, c - h), min(1, c + h)


def cmd_resultados(a):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats

    if not ruta("pruebas.csv").exists():
        sys.exit("No hay pruebas.csv.")
    with open(ruta("pruebas.csv"), encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    objs = objetos()
    out = ruta("resultados")
    out.mkdir(parents=True, exist_ok=True)
    fl = lambda x: float(x) if x not in ("", None) else None
    for r in filas:
        r["ok"] = r["acierto"] == "si"
        r["entren"] = r["condicion"] == "entrenamiento"
        r["prob_f"], r["x_f"], r["y_f"], r["t_f"] = fl(r["prob"]), fl(r["x"]), fl(r["y"]), fl(r["t_inf_ms"])
    s = "# Resultados de la Tarea 2\n\n"
    # 1. tabla
    s += "## Tabla de pruebas\n\n| Objeto | Prueba | Condición | Etiqueta detectada | Prob. | (x, y) | Acierto |\n|---|---|---|---|---|---|---|\n"
    for r in filas:
        xy = f"({r['x_f']:.0f}, {r['y_f']:.0f})" if r["x_f"] is not None else "—"
        s += f"| {r['objeto']} | {r['prueba']} | {r['condicion']} | {r['etiqueta']} | {r['prob_f']:.2f} | {xy} | {'sí' if r['ok'] else 'no'} |\n" if r["prob_f"] is not None \
            else f"| {r['objeto']} | {r['prueba']} | {r['condicion']} | {r['etiqueta']} | — | — | {'sí' if r['ok'] else 'no'} |\n"
    # 2. exactitud
    def fila_exac(nombre, sel):
        k, n = sum(r["ok"] for r in sel), len(sel)
        lo, hi = wilson(k, n)
        return f"| {nombre} | {k}/{n} | {100 * k / n:.1f} % | {100 * lo:.1f}–{100 * hi:.1f} % |\n" if n else f"| {nombre} | 0/0 | — | — |\n", (k, n, lo, hi)
    s += "\n## Exactitud (IC95 de Wilson)\n\n| Grupo | Aciertos | Exactitud | IC95 |\n|---|---|---|---|\n"
    barras = []
    for o in objs:
        t, v = fila_exac(f"Objeto {o}", [r for r in filas if r["objeto"] == o])
        s += t
        barras.append((o, v))
    for nombre, sel in [("Posición de entrenamiento", [r for r in filas if r["entren"]]), ("Otra posición o luz", [r for r in filas if not r["entren"]]),
                        ("Global", filas)]:
        t, v = fila_exac(nombre, sel)
        s += t
        barras.append((nombre, v))
    plt.figure(figsize=(8, 4))
    pos = range(len(barras))
    ex = [100 * v[0] / v[1] if v[1] else 0 for _, v in barras]
    err = [[100 * (v[0] / v[1] - v[2]) if v[1] else 0 for _, v in barras], [100 * (v[3] - v[0] / v[1]) if v[1] else 0 for _, v in barras]]
    plt.bar(pos, ex, yerr=err, capsize=4, color="#357")
    plt.xticks(pos, [n for n, _ in barras], rotation=25, ha="right")
    plt.ylabel("Exactitud (%)")
    plt.ylim(0, 105)
    plt.tight_layout()
    plt.savefig(out / "exactitud.png", dpi=150)
    plt.close()
    # 3. matriz de confusion
    cols = list(objs)
    extra = sorted({r["etiqueta"] for r in filas} - set(objs) - {"sin_deteccion"})
    cols += extra + ["sin_deteccion"]
    m = np.zeros((len(objs), len(cols)), int)
    for r in filas:
        m[objs.index(r["objeto"]), cols.index(r["etiqueta"])] += 1
    s += "\n## Matriz de confusión de las pruebas reales\n\n| Real \\ Detectado | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols) + "\n"
    for i, o in enumerate(objs):
        s += f"| {o} | " + " | ".join(str(x) for x in m[i]) + " |\n"
    plt.figure(figsize=(1.2 * len(cols) + 2, 1.0 * len(objs) + 1.5))
    plt.imshow(m, cmap="Blues")
    plt.xticks(range(len(cols)), cols, rotation=30, ha="right")
    plt.yticks(range(len(objs)), objs)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            plt.text(j, i, m[i, j], ha="center", va="center", color="white" if m[i, j] > m.max() / 2 else "black")
    plt.xlabel("Detectado")
    plt.ylabel("Real")
    plt.tight_layout()
    plt.savefig(out / "confusion_pruebas.png", dpi=150)
    plt.close()
    # 4. Fisher
    s += "\n## Entrenamiento vs otra posición o luz (prueba exacta de Fisher)\n\n| Grupo | Entren. (ac/err) | Otra (ac/err) | p |\n|---|---|---|---|\n"
    for nombre, sel in [(o, [r for r in filas if r["objeto"] == o]) for o in objs] + [("Global", filas)]:
        a1, e1 = sum(r["ok"] for r in sel if r["entren"]), sum(not r["ok"] for r in sel if r["entren"])
        a2, e2 = sum(r["ok"] for r in sel if not r["entren"]), sum(not r["ok"] for r in sel if not r["entren"])
        p = stats.fisher_exact([[a1, e1], [a2, e2]])[1] if (a1 + e1) and (a2 + e2) else float("nan")
        s += f"| {nombre} | {a1}/{e1} | {a2}/{e2} | {p:.3f} |\n"
    # 5. probabilidad aciertos vs errores
    pa = [r["prob_f"] for r in filas if r["ok"] and r["prob_f"] is not None]
    pe = [r["prob_f"] for r in filas if not r["ok"] and r["prob_f"] is not None]
    s += "\n## Probabilidad en aciertos vs errores\n\n"
    ms = lambda v: f"{np.mean(v):.3f} ± {np.std(v, ddof=1):.3f} (n = {len(v)})" if len(v) > 1 else (f"{v[0]:.3f} (n = 1)" if v else "sin datos")
    s += f"- Aciertos: {ms(pa)}\n- Errores con detección: {ms(pe)}\n"
    if len(pa) > 1 and len(pe) > 1:
        u = stats.mannwhitneyu(pa, pe, alternative="two-sided")
        s += f"- Mann-Whitney: U = {u.statistic:.1f}, p = {u.pvalue:.3f}\n"
    # 6. estabilidad de coordenadas
    s += "\n## Estabilidad de las coordenadas (posición de entrenamiento, aciertos)\n\n| Objeto | n | x media ± DE | y media ± DE |\n|---|---|---|---|\n"
    for o in objs:
        xs = [r["x_f"] for r in filas if r["objeto"] == o and r["entren"] and r["ok"] and r["x_f"] is not None]
        ys = [r["y_f"] for r in filas if r["objeto"] == o and r["entren"] and r["ok"] and r["y_f"] is not None]
        sdx = lambda v: f"{np.mean(v):.1f} ± {np.std(v, ddof=1):.1f}" if len(v) > 1 else "—"
        s += f"| {o} | {len(xs)} | {sdx(xs)} | {sdx(ys)} |\n"
    # 7. tiempo de inferencia
    tv = [r["t_f"] for r in filas if r["t_f"] is not None]
    s += "\n## Tiempo de inferencia (DSP + clasificación)\n\n"
    if len(tv) > 1:
        s += f"- Media ± DE: {np.mean(tv):.1f} ± {np.std(tv, ddof=1):.1f} ms por cuadro\n- FPS = 1000 / tiempo medio = {1000 / np.mean(tv):.2f}\n"
    else:
        s += "- Sin datos suficientes.\n"
    # 8. entrenamiento
    ent = leer_json("entrenamientos.json", {})
    if ent:
        s += "\n## Entrenamiento: corrida 1 vs corrida 2\n\n| | Corrida 1 | Corrida 2 |\n|---|---|---|\n"
        g = lambda n, k: ent.get(n, {}).get(k)
        s += f"| F1 total | {g('1', 'f1_total')} | {g('2', 'f1_total')} |\n"
        for o in objs:
            s += f"| F1 {o} | {ent.get('1', {}).get('f1_clases', {}).get(o, '—')} | {ent.get('2', {}).get('f1_clases', {}).get(o, '—')} |\n"
        for n in ("1", "2"):
            c = ent.get(n, {}).get("config", {})
            if c:
                s += f"\n**Configuración corrida {n}:** {c.get('resolucion')}, {c.get('color')}, {c.get('modelo')}, {c.get('ciclos')} ciclos, tasa {c.get('tasa')}, aumento: {c.get('aumento')}.\n"
        if "cambio" in ent.get("2", {}):
            cb = ent["2"]["cambio"]
            s += f"\n**Único parámetro que cambió:** {cb['parametro']} ({cb['motivo']}).\n"
        for n in ("1", "2"):
            mx = ent.get(n, {}).get("matriz")
            if mx:
                s += f"\n**Matriz de confusión, corrida {n}** (filas = real):\n\n| | " + " | ".join(mx["etiquetas"]) + " |\n|---|" + "---|" * len(mx["etiquetas"]) + "\n"
                for e, fila in zip(mx["etiquetas"], mx["filas"]):
                    s += f"| {e} | " + " | ".join(f"{x:g}" for x in fila) + " |\n"
    (out / "resultados.md").write_text(s, encoding="utf-8")
    print(f"Escrito {out / 'resultados.md'} y gráficas en {out}")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="App de PC de la Tarea 2 (Edge Impulse)")
    ap.add_argument("--datos", help="carpeta de datos (por defecto herramientas/tarea2/datos)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("estado").set_defaults(f=cmd_estado)
    sub.add_parser("preparar").set_defaults(f=cmd_preparar)
    sub.add_parser("condiciones").set_defaults(f=cmd_condiciones)
    p = sub.add_parser("capturar")
    p.add_argument("--objeto", required=True)
    p.add_argument("--n", type=int, default=META_FOTOS)
    p.add_argument("--auto", type=float, default=0, help="segundos entre fotos (0 = manual)")
    p.set_defaults(f=cmd_capturar)
    p = sub.add_parser("servir")
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--meta", type=int, default=META_FOTOS)
    p.set_defaults(f=cmd_servir)
    p = sub.add_parser("subir")
    p.add_argument("--simulacro", action="store_true", help="solo muestra lo que haria")
    p.set_defaults(f=cmd_subir)
    p = sub.add_parser("entrenamiento")
    p.add_argument("--corrida", type=int, choices=[1, 2], required=True)
    p.set_defaults(f=cmd_entrenamiento)
    p = sub.add_parser("marcar")
    p.add_argument("clave", choices=["etiquetado", "desplegado"])
    p.set_defaults(f=cmd_marcar)
    p = sub.add_parser("pruebas")
    p.add_argument("--puerto", default="COM8")
    p.add_argument("--simular", action="store_true", help="tramas falsas, sin robot")
    p.set_defaults(f=cmd_pruebas)
    sub.add_parser("resultados").set_defaults(f=cmd_resultados)
    a = ap.parse_args()
    global DATOS
    if a.datos:
        DATOS = Path(a.datos).resolve()
    try:
        a.f(a)
    except KeyboardInterrupt:
        print("\nInterrumpido.")


if __name__ == "__main__":
    main()
