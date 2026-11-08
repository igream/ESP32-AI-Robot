/*
 * deteccion_ei.ino — Tarea 2: detección de objetos (FOMO de Edge Impulse) en el ESP32-CAM.
 *
 * Basado en el ejemplo "esp32_camera" que trae la librería exportada de Edge Impulse.
 * Toda la inferencia corre en el ESP32 (sin nube).
 *
 * Salida por puerto serie (115200 baudios), una línea por cuadro, fácil de leer por la
 * app de PC (herramientas/tarea2/tarea2.py pruebas):
 *   INFO;modelo=<nombre>;entrada=96x96;umbral=<x>;core=<versión>          (una vez, al arrancar)
 *   DET;<t_ms>;<dsp_ms>;<clasif_ms>;<etiqueta>;<prob>;<cx>;<cy>;<w>;<h>   (una por detección)
 *   NONE;<t_ms>;<dsp_ms>;<clasif_ms>                                      (cuadro sin detecciones)
 * cx y cy son el centro del cuadro delimitador, en píxeles de la entrada del modelo.
 *
 * Evidencia sin computadora (no hay OLED): el LED flash (GPIO4) se enciende 200 ms cada
 * vez que se detecta un objeto con probabilidad >= UMBRAL.
 *
 * IMPORTANTE:
 *  - Mismo modelo de cámara y mismo vflip que el firmware del robot, para que las imágenes
 *    de inferencia tengan la orientación de las del dataset.
 *  - El "resize mode" del Impulse en Edge Impulse debe ser "Fit shortest axis" (recorte
 *    central), que es lo que hace crop_and_interpolate_rgb888 de este sketch.
 *  - Este sketch reemplaza el firmware del robot: para volver a mover el robot hay que
 *    volver a subir firmware/robot_esp32cam.
 */
#include <Arduino.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "modelo_ei.h"                              // librería de Edge Impulse (ver ese archivo)
#include "edge-impulse-sdk/dsp/image/image.hpp"

// ---------------- Configuración ----------------
#define UMBRAL            0.50f   // probabilidad mínima para reportar y para encender el flash
#define FLASH_MS          200     // duración del destello del LED flash
#define PIN_FLASH         4       // LED flash (activo en alto)
#define PIN_LED_ROJO      33      // LED rojo de la placa (activo en bajo)

// Resolución de captura (igual que la del dataset: QVGA con vflip, como el robot)
#define CAM_ANCHO         320
#define CAM_ALTO          240

// ---------------- Cámara AI Thinker (idéntica al firmware del robot) ----------------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

static uint8_t *bufer_img = nullptr;     // imagen RGB888 decodificada (en PSRAM)
static unsigned long apagar_flash_en = 0;

// Entrega al clasificador los píxeles del bufer como floats (0xRRGGBB), como pide Edge Impulse.
static int obtener_datos(size_t desplazamiento, size_t largo, float *salida) {
  size_t px = desplazamiento * 3;
  for (size_t i = 0; i < largo; i++, px += 3) {
    salida[i] = (bufer_img[px + 2] << 16) + (bufer_img[px + 1] << 8) + bufer_img[px];
  }
  return 0;
}

static bool iniciar_camara() {
  camera_config_t c = {};                 // en ceros, igual que en el robot
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;
  c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM;
  c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;
  c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;        // JPEG como en el dataset; se decodifica a RGB888
  c.frame_size = FRAMESIZE_QVGA;
  c.jpeg_quality = 12;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  if (esp_camera_init(&c) != ESP_OK) return false;
  sensor_t *s = esp_camera_sensor_get();
  s->set_hmirror(s, 0);
  s->set_vflip(s, 1);                     // igual que el firmware del robot
  return true;
}

// Captura un cuadro, lo decodifica y lo reduce a la entrada del modelo. true si salió bien.
static bool capturar_cuadro() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return false;
  bool ok = fmt2rgb888(fb->buf, fb->len, PIXFORMAT_JPEG, bufer_img);
  esp_camera_fb_return(fb);
  if (!ok) return false;
  // Recorte central + interpolación a la entrada del modelo (96x96 con este proyecto)
  ei::image::processing::crop_and_interpolate_rgb888(
      bufer_img, CAM_ANCHO, CAM_ALTO, bufer_img,
      EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
  return true;
}

void setup() {
  Serial.begin(115200);

  // Pines del L298N como salida en LOW: sin esto flotan y los motores pueden moverse.
  for (int pin : {12, 13, 14, 15}) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  pinMode(PIN_FLASH, OUTPUT);
  digitalWrite(PIN_FLASH, LOW);
  pinMode(PIN_LED_ROJO, OUTPUT);
  digitalWrite(PIN_LED_ROJO, HIGH);       // apagado (activo en bajo)

  if (!psramFound() || !iniciar_camara()) {
    Serial.println("ERROR;camara");
    while (true) delay(1000);
  }
  bufer_img = (uint8_t *)ps_malloc(CAM_ANCHO * CAM_ALTO * 3);
  if (!bufer_img) {
    Serial.println("ERROR;memoria");
    while (true) delay(1000);
  }

  Serial.printf("INFO;modelo=%s;entrada=%dx%d;umbral=%.2f;core=%d.%d.%d\n",
                EI_CLASSIFIER_PROJECT_NAME, EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT, UMBRAL,
                ESP_ARDUINO_VERSION_MAJOR, ESP_ARDUINO_VERSION_MINOR, ESP_ARDUINO_VERSION_PATCH);
  digitalWrite(PIN_LED_ROJO, LOW);        // encendido: listo
}

void loop() {
  if (apagar_flash_en && millis() >= apagar_flash_en) {
    digitalWrite(PIN_FLASH, LOW);
    apagar_flash_en = 0;
  }
  if (!capturar_cuadro()) {
    Serial.println("ERROR;captura");
    delay(100);
    return;
  }

  ei::signal_t senal;
  senal.total_length = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
  senal.get_data = &obtener_datos;
  ei_impulse_result_t r = {};
  if (run_classifier(&senal, &r, false) != EI_IMPULSE_OK) {
    Serial.println("ERROR;clasificador");
    return;
  }

  unsigned long t = millis();
  int n = 0;
#if EI_CLASSIFIER_OBJECT_DETECTION == 1
  for (uint32_t i = 0; i < r.bounding_boxes_count; i++) {
    auto bb = r.bounding_boxes[i];
    if (bb.value < UMBRAL) continue;      // FOMO devuelve value = 0 donde no hay objeto
    Serial.printf("DET;%lu;%d;%d;%s;%.3f;%u;%u;%u;%u\n", t, (int)r.timing.dsp, (int)r.timing.classification,
                  bb.label, bb.value, (unsigned)(bb.x + bb.width / 2), (unsigned)(bb.y + bb.height / 2),
                  (unsigned)bb.width, (unsigned)bb.height);
    n++;
  }
#endif
  if (n == 0) {
    Serial.printf("NONE;%lu;%d;%d\n", t, (int)r.timing.dsp, (int)r.timing.classification);
  } else {
    digitalWrite(PIN_FLASH, HIGH);        // destello: hubo detección
    apagar_flash_en = millis() + FLASH_MS;
  }
}
