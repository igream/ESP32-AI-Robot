# Resultados de la Tarea 2

## Tabla de pruebas

| Objeto | Prueba | Condición | Etiqueta detectada | Prob. | (x, y) | Acierto |
|---|---|---|---|---|---|---|
| vasorojo | 1 | entrenamiento | vasorojo | 0.96 | (36, 44) | sí |
| vasorojo | 2 | entrenamiento | vasorojo | 0.53 | (28, 52) | sí |
| vasorojo | 3 | entrenamiento | vasorojo | 0.59 | (60, 44) | sí |
| vasorojo | 4 | entrenamiento | vasorojo | 0.96 | (28, 44) | sí |
| vasorojo | 5 | entrenamiento | vasorojo | 0.83 | (28, 44) | sí |
| vasorojo | 6 | entrenamiento | vasorojo | 0.98 | (20, 44) | sí |
| vasorojo | 7 | entrenamiento | vasorojo | 0.92 | (56, 44) | sí |
| vasorojo | 8 | entrenamiento | vasorojo | 0.99 | (60, 48) | sí |
| vasorojo | 9 | entrenamiento | vasorojo | 0.90 | (76, 44) | sí |
| vasorojo | 10 | entrenamiento | vasorojo | 0.95 | (44, 44) | sí |
| vasorojo | 1 | posicion | sin_deteccion | — | — | no |
| vasorojo | 2 | posicion | vasorojo | 0.59 | (68, 44) | sí |
| vasorojo | 3 | luz | vasorojo | 0.56 | (36, 52) | sí |
| vasorojo | 4 | posicion | jarraroja | 0.75 | (20, 48) | no |
| vasorojo | 5 | posicion | vasorojo | 0.99 | (44, 44) | sí |
| jarraroja | 1 | entrenamiento | jarraroja | 0.80 | (36, 36) | sí |
| jarraroja | 2 | entrenamiento | jarraroja | 0.93 | (60, 40) | sí |
| jarraroja | 3 | entrenamiento | jarraroja | 0.89 | (36, 32) | sí |
| jarraroja | 4 | entrenamiento | jarraroja | 0.73 | (28, 36) | sí |
| jarraroja | 5 | entrenamiento | jarraroja | 0.84 | (28, 40) | sí |
| jarraroja | 6 | entrenamiento | jarraroja | 0.84 | (24, 32) | sí |
| jarraroja | 7 | entrenamiento | jarraroja | 0.94 | (40, 36) | sí |
| jarraroja | 8 | entrenamiento | jarraroja | 0.73 | (40, 40) | sí |
| jarraroja | 9 | entrenamiento | jarraroja | 0.93 | (36, 40) | sí |
| jarraroja | 10 | entrenamiento | jarraroja | 0.96 | (36, 36) | sí |
| jarraroja | 1 | posicion | jarraroja | 0.84 | (36, 40) | sí |
| jarraroja | 2 | posicion | jarraroja | 0.84 | (36, 44) | sí |
| jarraroja | 3 | posicion | sin_deteccion | — | — | no |
| jarraroja | 4 | luz | laptop | 0.60 | (44, 48) | no |
| jarraroja | 5 | luz | laptop | 0.77 | (44, 44) | no |
| laptop | 1 | entrenamiento | laptop | 0.71 | (36, 40) | sí |
| laptop | 2 | entrenamiento | laptop | 0.82 | (44, 44) | sí |
| laptop | 3 | entrenamiento | laptop | 0.88 | (40, 44) | sí |
| laptop | 4 | entrenamiento | laptop | 0.86 | (48, 44) | sí |
| laptop | 5 | entrenamiento | laptop | 0.86 | (44, 44) | sí |
| laptop | 6 | entrenamiento | laptop | 0.94 | (36, 44) | sí |
| laptop | 7 | entrenamiento | laptop | 0.96 | (36, 44) | sí |
| laptop | 8 | entrenamiento | laptop | 0.86 | (32, 40) | sí |
| laptop | 9 | entrenamiento | laptop | 0.83 | (36, 40) | sí |
| laptop | 10 | entrenamiento | laptop | 0.56 | (48, 44) | sí |
| laptop | 1 | posicion | laptop | 0.69 | (44, 44) | sí |
| laptop | 2 | posicion | laptop | 0.92 | (60, 44) | sí |
| laptop | 3 | posicion | laptop | 0.65 | (12, 28) | sí |
| laptop | 4 | luz | laptop | 0.76 | (36, 40) | sí |
| laptop | 5 | luz | laptop | 0.81 | (60, 44) | sí |

## Exactitud (IC95 de Wilson)

| Grupo | Aciertos | Exactitud | IC95 |
|---|---|---|---|
| Objeto vasorojo | 13/15 | 86.7 % | 62.1–96.3 % |
| Objeto jarraroja | 12/15 | 80.0 % | 54.8–93.0 % |
| Objeto laptop | 15/15 | 100.0 % | 79.6–100.0 % |
| Posición de entrenamiento | 30/30 | 100.0 % | 88.6–100.0 % |
| Otra posición o luz | 10/15 | 66.7 % | 41.7–84.8 % |
| Global | 40/45 | 88.9 % | 76.5–95.2 % |

## Matriz de confusión de las pruebas reales

| Real \ Detectado | vasorojo | jarraroja | laptop | sin_deteccion |
|---|---|---|---|---|
| vasorojo | 13 | 1 | 0 | 1 |
| jarraroja | 0 | 12 | 2 | 1 |
| laptop | 0 | 0 | 15 | 0 |

## Entrenamiento vs otra posición o luz (prueba exacta de Fisher)

| Grupo | Entren. (ac/err) | Otra (ac/err) | p |
|---|---|---|---|
| vasorojo | 10/0 | 3/2 | 0.095 |
| jarraroja | 10/0 | 2/3 | 0.022 |
| laptop | 10/0 | 5/0 | 1.000 |
| Global | 30/0 | 10/5 | 0.002 |

## Probabilidad en aciertos vs errores

- Aciertos: 0.828 ± 0.131 (n = 40)
- Errores con detección: 0.708 ± 0.090 (n = 3)
- Mann-Whitney: U = 94.0, p = 0.110

## Estabilidad de las coordenadas (posición de entrenamiento, aciertos)

| Objeto | n | x media ± DE | y media ± DE |
|---|---|---|---|
| vasorojo | 10 | 43.6 ± 18.5 | 45.2 ± 2.7 |
| jarraroja | 10 | 36.4 ± 9.9 | 36.8 ± 3.2 |
| laptop | 10 | 40.0 ± 5.7 | 42.8 ± 1.9 |

## Tiempo de inferencia (DSP + clasificación)

- Media ± DE: 798.0 ± 0.1 ms por cuadro
- FPS = 1000 / tiempo medio = 1.25

## Entrenamiento: corrida 1 vs corrida 2

| | Corrida 1 | Corrida 2 |
|---|---|---|
| F1 total | 1.0 | None |
| F1 vasorojo | 1.0 | — |
| F1 jarraroja | 1.0 | — |
| F1 laptop | 1.0 | — |

**Configuración corrida 1:** 96x96, RGB, FOMO MobileNetV2 0.35, 100 ciclos, tasa 0.001, aumento: si.

**Matriz de confusión, corrida 1** (filas = real):

| | vasorojo | jarraroja | laptop | uncertain |
|---|---|---|---|---|
| vasorojo | 100 | 0 | 0 | 0 |
| jarraroja | 0 | 100 | 0 | 0 |
| laptop | 0 | 0 | 100 | 0 |
| uncertain | 0 | 0 | 0 | 100 |
