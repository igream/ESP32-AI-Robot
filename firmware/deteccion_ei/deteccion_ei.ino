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
#include "driver/ledc.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "freertos/semphr.h"

// ---------------- Configuración ----------------
#define UMBRAL            0.50f   // probabilidad mínima para reportar y para encender el flash
// El destello se DESACTIVA por defecto: ilumina el cuadro siguiente (el flash no se usó en el dataset)
// y calienta el LED. Poner 1 solo para una demostración sin computadora.
#define USAR_FLASH        0
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

// ---------------- Estado compartido con la página del celular ----------------
// El bucle principal escribe y el servidor HTTP (otra tarea) lee, protegido con un mutex.
static SemaphoreHandle_t mtx = nullptr;
static char est_clase[24] = "";          // clase con mayor probabilidad del último cuadro ("" = ninguna)
static float est_prob = 0;
static int est_x = 0, est_y = 0, est_ms = 0, est_ngestos = 0;
static char est_gesto[16] = "";          // gesto en curso ("" = ninguno)
static char eventos[8][56];              // registro de los últimos eventos (anillo)
static int n_eventos = 0;
static const size_t JPG_MAX = 40 * 1024;
static uint8_t *jpg_buf = nullptr;       // último JPEG de la cámara (lo toma el bucle)
static uint8_t *jpg_tx = nullptr;        // copia para enviar sin bloquear el bucle
static size_t jpg_len = 0;

static void registrar(const char *texto) {
  unsigned long t = millis();
  xSemaphoreTake(mtx, portMAX_DELAY);
  snprintf(eventos[n_eventos % 8], sizeof(eventos[0]), "%lu.%lu s  %s", t / 1000, (t % 1000) / 100, texto);
  n_eventos++;
  xSemaphoreGive(mtx);
}

// Entrega al clasificador los píxeles del bufer como floats (0xRRGGBB), como pide Edge Impulse.
static int obtener_datos(size_t desplazamiento, size_t largo, float *salida) {
  size_t px = desplazamiento * 3;
  for (size_t i = 0; i < largo; i++, px += 3) {
    // En este core (3.3.x) fmt2rgb888 deja los bytes en orden R,G,B (verificado con el volcado 'i':
    // un vaso rojo salía azul con el orden B,G,R del ejemplo de Edge Impulse).
    salida[i] = (bufer_img[px] << 16) + (bufer_img[px + 1] << 8) + bufer_img[px + 2];
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
  if (jpg_buf && fb->len <= JPG_MAX) {     // guarda el JPEG para la página del celular
    xSemaphoreTake(mtx, portMAX_DELAY);
    memcpy(jpg_buf, fb->buf, fb->len);
    jpg_len = fb->len;
    xSemaphoreGive(mtx);
  }
  bool ok = fmt2rgb888(fb->buf, fb->len, PIXFORMAT_JPEG, bufer_img);
  esp_camera_fb_return(fb);
  if (!ok) return false;
  // Recorte central + interpolación a la entrada del modelo (96x96 con este proyecto)
  ei::image::processing::crop_and_interpolate_rgb888(
      bufer_img, CAM_ANCHO, CAM_ALTO, bufer_img,
      EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
  return true;
}

// ---------------- Gestos al detectar (movimientos cortos con los motores) ----------------
// Pines del L298N (igual que firmware/robot_esp32cam): izquierdo 13 reversa / 12 adelante, derecho 14 reversa / 15 adelante.
// El PWM va por LEDC (canales 4-7, timer 1; la cámara usa el canal 0 y el timer 0). Con 12 V NO se debe usar
// encendido total: los motores TT son de ~6 V, por eso el PWM se limita a PWM_GESTO.
#define USAR_GESTOS       1       // 0 = el sketch solo detecta (sin mover el robot)
#define PWM_GESTO         140     // 0-255, como pwm_max del robot
#define PAUSA_GESTO_MS    3000    // tras un gesto se ignoran las detecciones (el movimiento cambia la imagen)

static const ledc_channel_t CH_IZQ_REV = LEDC_CHANNEL_4;
static const ledc_channel_t CH_IZQ_ADE = LEDC_CHANNEL_5;
static const ledc_channel_t CH_DER_REV = LEDC_CHANNEL_6;
static const ledc_channel_t CH_DER_ADE = LEDC_CHANNEL_7;
static bool gestos_activos = USAR_GESTOS;
static unsigned long ignorar_hasta = 0;
static char historial[3][24] = {"", "", ""};   // clase dominante de los últimos 3 cuadros

static void configurar_motores() {
  ledc_timer_config_t timer = {};
  timer.speed_mode = LEDC_LOW_SPEED_MODE;
  timer.duty_resolution = LEDC_TIMER_8_BIT;
  timer.timer_num = LEDC_TIMER_1;
  timer.freq_hz = 2000;
  timer.clk_cfg = LEDC_AUTO_CLK;
  ledc_timer_config(&timer);
  const struct { int gpio; ledc_channel_t canal; } m[] = {{13, CH_IZQ_REV}, {12, CH_IZQ_ADE}, {14, CH_DER_REV}, {15, CH_DER_ADE}};
  for (auto &x : m) {
    ledc_channel_config_t c = {};
    c.gpio_num = x.gpio;
    c.speed_mode = LEDC_LOW_SPEED_MODE;
    c.channel = x.canal;
    c.intr_type = LEDC_INTR_DISABLE;
    c.timer_sel = LEDC_TIMER_1;
    c.duty = 0;
    c.hpoint = 0;
    ledc_channel_config(&c);
  }
}

static void lado(ledc_channel_t ade, ledc_channel_t rev, int v) {   // v > 0 adelante, < 0 reversa
  ledc_set_duty(LEDC_LOW_SPEED_MODE, v >= 0 ? rev : ade, 0);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, v >= 0 ? rev : ade);
  ledc_set_duty(LEDC_LOW_SPEED_MODE, v >= 0 ? ade : rev, v >= 0 ? v : -v);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, v >= 0 ? ade : rev);
}

static void mover(int izq, int der, int ms) {                       // movimiento con duración y parada
  lado(CH_IZQ_ADE, CH_IZQ_REV, izq);
  lado(CH_DER_ADE, CH_DER_REV, der);
  delay(ms);
  lado(CH_IZQ_ADE, CH_IZQ_REV, 0);
  lado(CH_DER_ADE, CH_DER_REV, 0);
  delay(150);
}

static void hacer_gesto(const char *clase) {
  const int P = PWM_GESTO;
  if (strcmp(clase, "vasorojo") == 0) {            // asentir ("sí"): adelante y atrás, dos veces
    for (int i = 0; i < 2; i++) { mover(P, P, 300); mover(-P, -P, 300); }
  } else if (strcmp(clase, "jarraroja") == 0) {    // negar ("no"): giro izquierda, derecha, izquierda
    mover(-P, P, 250); mover(P, -P, 500); mover(-P, P, 250);
  } else if (strcmp(clase, "laptop") == 0) {       // celebración: una vuelta en el sitio (tiempo fijo, sin calibrar)
    mover(-P, P, 1800);
  }
}

// Confirmación 2 de 3: solo se hace el gesto si la misma clase domina en al menos 2 de los últimos 3 cuadros.
static void actualizar_gestos(const char *mejor) {
  if (!gestos_activos) return;
  if (millis() < ignorar_hasta) {
    for (auto &h : historial) h[0] = 0;
    return;
  }
  strcpy(historial[0], historial[1]);
  strcpy(historial[1], historial[2]);
  strncpy(historial[2], mejor ? mejor : "", sizeof(historial[2]) - 1);
  historial[2][sizeof(historial[2]) - 1] = 0;
  if (!mejor) return;
  int veces = 0;
  for (auto &h : historial) veces += strcmp(h, mejor) == 0;
  if (veces < 2) return;
  Serial.printf("GESTO;%lu;%s\n", millis(), mejor);
  const char *nombre = strcmp(mejor, "vasorojo") == 0 ? "asiente" : strcmp(mejor, "jarraroja") == 0 ? "niega" : "gira";
  char linea[56];
  snprintf(linea, sizeof(linea), "%s: gesto %s", mejor, nombre);
  registrar(linea);
  xSemaphoreTake(mtx, portMAX_DELAY);
  strncpy(est_gesto, nombre, sizeof(est_gesto) - 1);
  xSemaphoreGive(mtx);
  hacer_gesto(mejor);
  xSemaphoreTake(mtx, portMAX_DELAY);
  est_gesto[0] = 0;
  est_ngestos++;
  xSemaphoreGive(mtx);
  for (auto &h : historial) h[0] = 0;
  ignorar_hasta = millis() + PAUSA_GESTO_MS;
}

// ---------------- Página para el celular (punto de acceso propio) ----------------
// Solo MUESTRA lo que el robot detecta y hace; la detección y el gesto ocurren dentro del ESP32.
// Conectar el celular a la red ESP32Det_Fer y abrir http://192.168.4.1
#define WIFI_SSID  "ESP32Det_Fer"
#define WIFI_CLAVE "Det12345."

static const char PAGINA[] PROGMEM = R"rawliteral(<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Detector ESP32-CAM</title>
<style>
:root{--bg:#f4f5f7;--c:#fff;--t:#1b1f24;--m:#667;--a:#1f5fbf;--v:#1a7f37;--bd:#d8dce2}
@media(prefers-color-scheme:dark){:root{--bg:#121417;--c:#1c2026;--t:#e8eaed;--m:#9aa3ad;--a:#6aa4ff;--v:#4cc27a;--bd:#323a44}}
body{margin:0;padding:12px 16px;background:var(--bg);color:var(--t);font:16px/1.4 system-ui,sans-serif;max-width:520px;margin-inline:auto}
.c{background:var(--c);border:1px solid var(--bd);border-radius:12px;padding:12px;margin:10px 0;text-align:center}
img{width:100%;border-radius:8px;background:#000;image-rendering:auto}
#cl{font-size:42px;font-weight:800;margin:4px 0}#pr{color:var(--m)}
#gs{font-size:22px;font-weight:700;min-height:30px;color:var(--v)}
button{font:inherit;padding:10px 14px;border-radius:10px;border:1px solid var(--bd);background:var(--c);color:var(--t);cursor:pointer}
ul{list-style:none;padding:0;margin:6px 0;text-align:left;font-size:14px;color:var(--m)}h1{font-size:15px;color:var(--m);margin:2px 0}
</style></head><body>
<h1>Detector de objetos en el ESP32-CAM (sin PC ni internet)</h1>
<div class="c"><img id="f" alt="cámara"><div id="cl">—</div><div id="pr"></div><div id="gs"></div></div>
<div class="c"><button id="b" onclick="tg()">Gestos: …</button> <span id="ng" class="m"></span>
<ul id="lg"></ul></div>
<script>
const N={vasorojo:'VASO',jarraroja:'JARRA',laptop:'LAPTOP'};let on=true;
async function t(){try{const e=await(await fetch('/estado',{cache:'no-store'})).json();
document.getElementById('cl').textContent=e.clase?N[e.clase]||e.clase:'Sin objeto';
document.getElementById('pr').textContent=e.clase?'prob. '+e.prob.toFixed(2)+' · centro ('+e.x+', '+e.y+') · '+e.ms+' ms por cuadro':'';
document.getElementById('gs').textContent=e.gesto?'Gesto: '+e.gesto+'…':'';
on=e.gestos_on;document.getElementById('b').textContent='Gestos: '+(on?'ACTIVADOS':'desactivados');
document.getElementById('ng').textContent='Hechos: '+e.n_gestos;
document.getElementById('lg').innerHTML=e.log.map(x=>'<li>'+x+'</li>').join('');
document.getElementById('f').src='/foto?'+Date.now();}catch(_){}}
async function tg(){await fetch('/gestos?v='+(on?0:1));t();}
setInterval(t,800);t();
</script></body></html>)rawliteral";

static httpd_handle_t servidor = nullptr;

static esp_err_t h_pagina(httpd_req_t *r) {
  httpd_resp_set_type(r, "text/html; charset=utf-8");
  return httpd_resp_send(r, PAGINA, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t h_estado(httpd_req_t *r) {
  static char json[1100];
  char clase[24], gesto[16], ev[8][56];
  float prob; int x, y, ms, ng, ne;
  xSemaphoreTake(mtx, portMAX_DELAY);
  strcpy(clase, est_clase); strcpy(gesto, est_gesto);
  prob = est_prob; x = est_x; y = est_y; ms = est_ms; ng = est_ngestos; ne = n_eventos;
  memcpy(ev, eventos, sizeof(ev));
  xSemaphoreGive(mtx);
  int n = snprintf(json, sizeof(json),
                   "{\"clase\":\"%s\",\"prob\":%.2f,\"x\":%d,\"y\":%d,\"ms\":%d,\"gesto\":\"%s\",\"gestos_on\":%s,\"n_gestos\":%d,\"log\":[",
                   clase, prob, x, y, ms, gesto, gestos_activos ? "true" : "false", ng);
  for (int i = 0; i < ne && i < 8 && n < (int)sizeof(json) - 80; i++) {
    n += snprintf(json + n, sizeof(json) - n, "%s\"%s\"", i ? "," : "", ev[(ne - 1 - i) % 8]);
  }
  snprintf(json + n, sizeof(json) - n, "]}");
  httpd_resp_set_type(r, "application/json");
  httpd_resp_set_hdr(r, "Cache-Control", "no-store");
  return httpd_resp_send(r, json, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t h_foto(httpd_req_t *r) {
  xSemaphoreTake(mtx, portMAX_DELAY);
  size_t n = jpg_len;
  if (n) memcpy(jpg_tx, jpg_buf, n);
  xSemaphoreGive(mtx);
  if (!n) return httpd_resp_send_404(r);
  httpd_resp_set_type(r, "image/jpeg");
  httpd_resp_set_hdr(r, "Cache-Control", "no-store");
  return httpd_resp_send(r, (const char *)jpg_tx, n);
}

static esp_err_t h_gestos(httpd_req_t *r) {
  char q[16], v[4];
  if (httpd_req_get_url_query_str(r, q, sizeof(q)) == ESP_OK && httpd_query_key_value(q, "v", v, sizeof(v)) == ESP_OK) {
    gestos_activos = v[0] == '1';
    registrar(gestos_activos ? "gestos activados" : "gestos desactivados");
  }
  return httpd_resp_send(r, "ok", HTTPD_RESP_USE_STRLEN);
}

static void iniciar_web() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_CLAVE);
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = 80;
  cfg.max_uri_handlers = 6;
  if (httpd_start(&servidor, &cfg) != ESP_OK) {
    Serial.println("ERROR;web");
    return;
  }
  const httpd_uri_t rutas[] = {{"/", HTTP_GET, h_pagina, nullptr}, {"/estado", HTTP_GET, h_estado, nullptr},
                               {"/foto", HTTP_GET, h_foto, nullptr}, {"/gestos", HTTP_GET, h_gestos, nullptr}};
  for (auto &u : rutas) httpd_register_uri_handler(servidor, &u);
  Serial.printf("WIFI;%s;%s\n", WIFI_SSID, WiFi.softAPIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  mtx = xSemaphoreCreateMutex();

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

  jpg_buf = (uint8_t *)ps_malloc(JPG_MAX);   // si falta memoria, la página solo pierde la foto
  jpg_tx = (uint8_t *)ps_malloc(JPG_MAX);
  if (!jpg_tx) jpg_buf = nullptr;
  configurar_motores();                   // después de la cámara: los motores quedan en duty 0 (pines en bajo)
  iniciar_web();

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

  // Depuración: al recibir 'i' por el serie vuelca la imagen exacta que ve el modelo (RGB, hex).
  // 'g' activa o desactiva los gestos (útil durante las 45 pruebas para que el robot no se mueva).
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'i') {
      Serial.printf("IMG;%d;%d;", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);
      for (int i = 0; i < EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT; i++) {
        Serial.printf("%02x%02x%02x", bufer_img[i * 3], bufer_img[i * 3 + 1], bufer_img[i * 3 + 2]);
      }
      Serial.println();
    } else if (c == 'g') {
      gestos_activos = !gestos_activos;
      Serial.printf("GESTOS;%s\n", gestos_activos ? "on" : "off");
    }
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
  const char *mejor = nullptr;            // clase con mayor probabilidad en este cuadro
  float mejor_p = 0;
  int mx = 0, my = 0;
#if EI_CLASSIFIER_OBJECT_DETECTION == 1
  for (uint32_t i = 0; i < r.bounding_boxes_count; i++) {
    auto bb = r.bounding_boxes[i];
    if (bb.value < UMBRAL) continue;      // FOMO devuelve value = 0 donde no hay objeto
    Serial.printf("DET;%lu;%d;%d;%s;%.3f;%u;%u;%u;%u\n", t, (int)r.timing.dsp, (int)r.timing.classification,
                  bb.label, bb.value, (unsigned)(bb.x + bb.width / 2), (unsigned)(bb.y + bb.height / 2),
                  (unsigned)bb.width, (unsigned)bb.height);
    n++;
    if (bb.value > mejor_p) {
      mejor_p = bb.value; mejor = bb.label;
      mx = bb.x + bb.width / 2; my = bb.y + bb.height / 2;
    }
  }
#endif
  xSemaphoreTake(mtx, portMAX_DELAY);       // estado para la página del celular
  strncpy(est_clase, mejor ? mejor : "", sizeof(est_clase) - 1);
  est_clase[sizeof(est_clase) - 1] = 0;
  est_prob = mejor_p; est_x = mx; est_y = my;
  est_ms = (int)(r.timing.dsp + r.timing.classification);
  xSemaphoreGive(mtx);
  if (n == 0) {
    Serial.printf("NONE;%lu;%d;%d\n", t, (int)r.timing.dsp, (int)r.timing.classification);
  }
#if USAR_FLASH
  else {
    digitalWrite(PIN_FLASH, HIGH);        // destello: hubo detección
    apagar_flash_en = millis() + FLASH_MS;
  }
#endif
  actualizar_gestos(mejor);
}
