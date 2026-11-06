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
Ya tengo: ESP32-CAM (cámara del kit), ESP32-WROOM-32D, chasis, motores, L298N y batería 3×18650.

### Indispensables
- [ ] Raspberry Pi 5 de 4 GB (~$110 USD).
- [ ] microSD de 32–64 GB, clase A2 (~$10).
- [ ] Disipador con ventilador para la Pi 5 (Active Cooler, ~$5). Sin él, la Pi baja su velocidad al correr modelos.
- [ ] Convertidor reductor de 5 V / 5 A con entrada de 12 V, para alimentar la Pi desde la batería (~$10–15).
- [ ] Micrófono USB pequeño (~$5–10). La Pi 5 no tiene entrada de audio.
- [ ] LED rojo, LED azul y resistencias de 220 Ω (~$2).
- [ ] Cables Dupont macho-hembra (~$3).

### Recomendados para precisión y sensores (van al ESP32-WROOM-32D)
- [ ] IMU MPU6050 (~$3): mide el ángulo real del giro.
- [ ] Sensor ultrasónico HC-SR04P (versión 3–5 V: alimentado a 3.3 V no necesita divisor).
- [ ] Resistencias para un divisor de voltaje que mida la batería (por ejemplo 30 kΩ + 7.5 kΩ).
- Descartado por ahora: encoders LM393.

### Lista final revisada (2026-11-02) – todo compatible
- Mercado Libre:
  - Raspberry Pi 5 4 GB ($3,201).
  - Convertidor JELELECRONICA MDC-DC12-24A5V5A: entrada 9–36 V, salida 5 V 5 A (30 W), con USB ($78).
  - MPU6050 ×5 ($215).
- Amazon:
  - microSD SanDisk Extreme PRO 64 GB, vendida por Amazon México ($499).
  - 2 cables Fasgear USB-A → USB-C de 30 cm, 3 A ($240).
  - HC-SR04P ($66), Active Cooler para Pi 5 ($235), micrófono USB SunFounder ($191).
- Ya tengo: LEDs rojo/azul, resistencias de 220 Ω y cables Dupont.
- Al instalar la Pi: configurar `PSU_MAX_CURRENT=5000` en la EEPROM, porque el convertidor no negocia corriente por USB-C.

### Solo si hace falta después
- [ ] Cámara para la Pi (Camera Module 3), si el video del ESP32-CAM no alcanza en el punto 4.
- [ ] AI HAT+ para la Pi, si la detección de objetos va muy lenta.

## Decisiones abiertas
- [ ] Repositorio: decidir si el manual del fabricante (PDF) se queda en el repo público.

## Tarea 1 – Robot móvil diferencial
- [x] Firmware de calibración (`firmware/robot_esp32cam/`): WiFi `ESP32Car_Fer`, funciones modulares, corrección por lado y `pwm_max`. Compila con el core ESP32 3.3.12.
- [x] Endpoint `/move`, secuencia de la tarea, prueba de motores y rampa de PWM mínimo, con etiquetas en el monitor serie.
- [x] Script de PC para registrar pruebas y calcular estadística (`herramientas/calibrar.py`), probado con datos simulados.
- [x] Borrador del reporte (`docs/Tarea1/REPORTE.md`).
- [x] Subir el firmware al robot y probarlo con las ruedas en el aire (sentido de motores y PWM mínimo, Parte B).
- [x] Página `/calibrar` en el robot (captura de mediciones desde el celular, exporta CSV). Subida al robot y probada por Fer (2026-11-06); evoluciona a `/tarea1` (ver `docs/PLAN_IMPLEMENTACION.md`).
- [ ] Mediciones: barridos, pruebas de comparación y validación por coordenadas.
- [ ] Llenar las tablas del reporte, fotos, diagrama dibujado, video y exportar a PDF.
