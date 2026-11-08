# App de PC de la Tarea 2 (`tarea2.py`)

Una etapa por subcomando; `python tarea2.py estado` dice cuál sigue. Los datos quedan en `herramientas/tarea2/datos/` (`--datos DIR` los redirige).
Dependencias: `pip install -r herramientas/requirements.txt`. La PC debe estar en el WiFi `ESP32Car_Fer` para `preparar` y `capturar`.

| Etapa | Comando |
|---|---|
| T2.0 | `python tarea2.py preparar` |
| T2.1 | `python tarea2.py condiciones` |
| T2.2 | `python tarea2.py capturar --objeto NOMBRE --n 60 --auto 2` |
| T2.2 (celular) | `python tarea2.py servir` y abrir en el celular la dirección que imprime (celular y PC en el WiFi `ESP32Car_Fer`; si Windows pregunta por el firewall, permitir Python en redes privadas) |
| T2.3 | `python tarea2.py subir` (luego etiquetar en el Studio y `python tarea2.py marcar etiquetado`) |
| T2.4 | `python tarea2.py entrenamiento --corrida 1` y `--corrida 2` |
| T2.5 | despliegue a mano; `python tarea2.py marcar desplegado` |
| T2.6 | `python tarea2.py pruebas --puerto COM8` (`--simular` prueba sin robot) |
| T2.7 | `python tarea2.py resultados` |

`pruebas` espera del sketch una línea por cuadro: `DET;t;dsp;clasif;etiqueta;prob;cx;cy;w;h` o `NONE;t;dsp;clasif` (ver `docs/PLAN_IMPLEMENTACION.md`, T2.5.3).

`servir` muestra la vista previa del robot con las líneas del recorte que ve el modelo, un botón por objeto (con contador), **TOMAR FOTO**, modo automático y **Deshacer última**. Las fotos se guardan en la PC.
