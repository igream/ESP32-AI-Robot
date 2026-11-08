# Entrenamientos con el dataset v1 (laptop a 55 cm) — 2026-11-08

Evidencia previa a rehacer la captura de la laptop a 75 cm (v2). Valores leídos del Studio (conjunto de validación, ~28 imágenes, por lo que son ruidosos).

Configuración común: RGB, 96×96, Fit shortest axis, FOMO MobileNetV2 0.35, tasa de aprendizaje 0.001, aumento de datos activado, CPU, int8.
Dataset v1: vasorojo 60, jarraroja 59, laptop 54 (139 train / 34 test).

| Corrida | Ciclos | F1 total | F1 vasorojo | F1 jarraroja | F1 laptop | laptop → fondo |
|---|---|---|---|---|---|---|
| 1 | 60 | 90.5 % | 1.00 | 1.00 | 0.67 | 50 % |
| 2 | 100 | 90.0 % | 1.00 | 1.00 | 0.60 | 57.1 % |

Precisión (sin fondo) 1.00 en ambas; recall 0.83 (corrida 1) y 0.82 (corrida 2).
Dispositivo (estimación EON, Cortex-M4F 80 MHz): inferencia 628 ms, RAM 133 KB, flash 81.3 KB (leído en la corrida 2; el modelo es el mismo en la 1).

## Diagnóstico
Más ciclos no mejoró la laptop. Causa atribuida a la adquisición: laptop demasiado grande para el escenario a 55 cm, forma muy variable al girarla y 12 cuadros fuera del recorte central (x 40–280), algunos tocando el borde superior.

## Corrección (dataset v2)
Laptop recapturada a 75 cm (60 fotos, todas dentro del recorte; cuadros de 138–156 px de ancho, x entre 47 y 268). Fotos viejas en `dataset/_dataset_v1/laptop/`.
