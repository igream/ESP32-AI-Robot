# Herramientas de calibración (Tarea 1)

`calibrar.py` corre en tu PC, se conecta al robot por WiFi y guarda cada prueba en `datos/pruebas.csv`.

## Instalación (una sola vez)

Desde la carpeta del proyecto:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r herramientas\requirements.txt
```

Cada vez que abras una terminal nueva, activa el entorno para que `python` tenga las librerías:

```bash
.venv\Scripts\activate
```

Luego conecta la PC al WiFi **ESP32Car_Fer** (contraseña `Fer12345.`). El robot está en `192.168.4.1`.

## Protocolo de medición sugerido

Material: cinta métrica, cinta de color en el piso (línea de 1 m y una cruz de ángulos) y multímetro para la batería.

| Paso | Comando | Para qué |
|---|---|---|
| 1. Sentido de motores (ruedas en el aire) | `mot` desde el monitor serie, o el botón **Prueba motores** | Parte B: confirmar que cada lado gira hacia donde debe |
| 2. PWM mínimo (ruedas en el aire) | Monitor serie: `min i`, escribe `ok` cuando la rueda arranque; repetir con `min d` | Parte B: tabla de PWM mínimo |
| 3. Recta, varias duraciones | `python herramientas\calibrar.py barrido --tipo adelante --ms 500 1000 1500 2000 2500 -n 5` | Velocidad lineal `v` y desviación |
| 4. Giros, varias duraciones | `python herramientas\calibrar.py barrido --tipo giro_izq --ms 300 500 700 900 -n 5` | Velocidad angular `w` |
| 5. Simetría y comparaciones | `prueba --tipo giro_der --ms 500 -n 10`, `prueba --tipo atras --ms 2000 -n 10`, `prueba --tipo pivote_izq --ms 500 -n 10`, `prueba --tipo ida_vuelta --ms 2000 -n 10` | Preguntas de análisis |
| 6. Analizar | `python herramientas\calibrar.py analizar --L <cm medidos>` | Estadística, gráficas y parámetros sugeridos |
| 7. Aplicar | `python herramientas\calibrar.py aplicar` | Guarda `v`, `w`, `t90`, `t360` y la corrección en el robot |
| 8. Repetir paso 3 con la corrección | `prueba --tipo adelante --ms 4000 -n 10` | Comprobar que la desviación bajó (t de Welch antes/después) |
| 9. Validar coordenadas | `python herramientas\calibrar.py validar --puntos "50,0 50,50 0,50 0,0" -n 3` | Error de posición final (RMSE) |

Notas:
- **Mide siempre igual.** El avance se mide sobre la dirección del movimiento, desde el mismo punto del robot (por ejemplo, el eje de las llantas traseras). La desviación es lateral: + a la izquierda del robot y − a la derecha. El ángulo se captura positivo.
- **Anota el voltaje de la batería** cada varias pruebas para poder analizar su efecto.
- El `barrido` corre las duraciones en **orden aleatorio**, para que la descarga de la batería no se cargue a una sola duración.
- En cualquier dato puedes escribir `r` para descartar y repetir esa prueba, o `q` para terminar.
- Para probar el script sin robot, agrega `--simular` (los datos son ficticios; usa otro `--csv` para no mezclarlos).
- Con `Ctrl+C` el script manda PARO al robot.

## Qué calcula `analizar`

1. **Descriptiva por condición:** media, desviación estándar, coeficiente de variación, IC95 (t de Student), Shapiro-Wilk, atípicos (IQR) y n necesario para un error dado.
2. **Desviación en línea recta:** prueba t de una muestra contra 0 y factor de corrección sugerido.
3. **Regresión lineal** tiempo → distancia / ángulo. La pendiente es la velocidad real; la ordenada es la pérdida por arranque y frenado.
4. **Modelo cinemático:** tiempo teórico de 90° contra el medido, L efectiva y factor de derrape.
5. **t de Welch:** giro izquierda vs derecha, adelante vs atrás, giro sobre su eje vs un motor detenido, y antes vs después de la corrección.
6. **Batería y superficie:** correlación de Pearson voltaje–residuo y ANOVA por superficie.

Resultados en `datos/analisis/resumen.md` (tablas listas para el reporte) y gráficas `.png`.
