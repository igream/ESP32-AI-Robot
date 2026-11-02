# Pendientes

## Mediciones físicas (necesito herramientas)
- [ ] **L**: distancia entre el centro de las llantas izquierdas y el de las derechas (cm).
- [ ] **Distancia entre ejes** (llanta delantera a trasera, mismo lado), en cm. Influye en cuánto derrapan los giros de un carro 4WD.
- [ ] **Diámetro de llanta** (cm).
- [ ] **Voltaje de la batería** cargada y en reposo (V), y su voltaje bajo carga con los motores girando.

## Decisiones tomadas
- [x] **PWM (Tarea 1):** se queda en los pines IN, con los jumpers ENA/ENB puestos y la velocidad variable por software. Se explica así en el reporte. El paso a ENA/ENB queda para cuando el ESP32-WROOM-32D controle los motores.
- [x] **Voltaje de motores:** el manual no lo especifica y el motor no tiene etiqueta. Se asume un motor TT típico de 3–6 V (máximo 6 V).
  - Batería llena: 12.6 V − ~2 V de caída en el L298N = ~10.6 V al motor con PWM al 100 %.
  - `PWM_MAX = 145/255` (≈57 %) para no pasar de ~6 V promedio. El código del kit usa 150, lo que confirma esa estimación.
- [x] **Calibración:** script de Python en la PC, conectado al WiFi del carro, que registra cada prueba en CSV y calcula la estadística.
- [x] **Arquitectura futura:** Raspberry Pi 5 de 4 GB (visión y voz) + ESP32-WROOM-32D (motores, LEDs, sensores) por UART.

## Compras
- [ ] Raspberry Pi 5 de 4 GB.
- [ ] Fuente de 5 V / 5 A para la Pi desde la batería (convertidor reductor).
- [ ] Cámara para la Pi (Camera Module 3 o una webcam USB). Se decide en el punto 3.

## Decisiones abiertas
- [ ] Repositorio: decidir si el manual del fabricante (PDF) se queda en el repo público.

## Tarea 1 – Robot móvil diferencial
- [ ] Firmware de calibración: WiFi `ESP32Car_Fer`, funciones modulares, ajuste por motor y `PWM_MAX`.
- [ ] Endpoint `/move` y secuencia de la tarea con etiquetas en el monitor serie.
- [ ] Prueba de PWM mínimo (ruedas en el aire).
- [ ] Script de PC para registrar pruebas y calcular estadística.
- [ ] Tablas de calibración, video, fotos, diagrama y reporte PDF.
