// =====================================================================
// robot_motion.cpp - Implementacion del control de movimiento
// Ver robot_motion.h para la descripcion general.
// =====================================================================
#include "robot_motion.h"
#include "driver/ledc.h"
#include <Preferences.h>
#include <math.h>
#include <stdarg.h>

RobotConfig cfg;
static Preferences prefs;

// ---------------------------------------------------------------------
// PWM (LEDC). La camara usa el canal 0 y el timer 0, asi que los motores
// usan los canales 4-7 con el timer 1. 2 kHz y 8 bits (0-255).
// ---------------------------------------------------------------------
static const ledc_channel_t CH_IZQ_REV = LEDC_CHANNEL_4;  // LEFT_M0
static const ledc_channel_t CH_IZQ_ADE = LEDC_CHANNEL_5;  // LEFT_M1
static const ledc_channel_t CH_DER_REV = LEDC_CHANNEL_6;  // RIGHT_M0
static const ledc_channel_t CH_DER_ADE = LEDC_CHANNEL_7;  // RIGHT_M1
static const uint32_t PWM_FRECUENCIA_HZ = 2000;

static void set_duty(ledc_channel_t canal, uint32_t duty) {
  ledc_set_duty(LEDC_LOW_SPEED_MODE, canal, duty);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, canal);
}

static void configurar_canal(int gpio, ledc_channel_t canal) {
  ledc_channel_config_t c = {
    .gpio_num   = gpio,
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .channel    = canal,
    .intr_type  = LEDC_INTR_DISABLE,
    .timer_sel  = LEDC_TIMER_1,
    .duty       = 0,
    .hpoint     = 0
  };
  ledc_channel_config(&c);
}

// ---------------------------------------------------------------------
// Estado interno
// ---------------------------------------------------------------------
// Un movimiento con duracion es un "segmento". Una rutina (por ejemplo
// la secuencia de la tarea) es una lista de segmentos.
struct Segmento {
  char     etiqueta[24];
  int16_t  izq, der;     // PWM con signo por lado
  uint32_t ms;           // duracion con motores encendidos
  uint32_t pausa;        // pausa con motores apagados al terminar
  float    d_cm;         // avance estimado (para la pose)
  float    d_deg;        // giro estimado (para la pose)
};

enum TipoCmd : uint8_t { CMD_PLAN, CMD_CONTINUO, CMD_PWM_MIN };
#define MAX_SEG 6
struct Comando {
  TipoCmd  tipo;
  uint8_t  n;            // segmentos usados
  char     lado;         // 'I' o 'D' para la rampa de PWM minimo
  Segmento seg[MAX_SEG];
};

enum Estado : uint8_t { E_LIBRE, E_MOVIENDO, E_PAUSA, E_CONTINUO, E_PWM_MIN };
static const char* NOMBRE_ESTADO[] = {"LIBRE", "MOVIENDO", "PAUSA", "CONTINUO", "PWM_MIN"};

static QueueHandle_t   cola;                 // comandos pendientes (web y serie)
static volatile Estado estado = E_LIBRE;
static volatile bool   cancelar = false;     // lo pone robot_stop()
static volatile bool   marcar_min = false;   // lo pone robot_pwm_min_marcar()
static Comando         actual;
static uint8_t         idx = 0;
static uint32_t        t_inicio = 0;
static uint32_t        ultimo_ms_real = 0;   // duracion medida del ultimo segmento
static char            ultimo[80] = "Inicio";

// Rampa de PWM minimo
static int      pwm_rampa = 0;
static uint32_t t_rampa = 0;
static int      pwm_min_izq = -1, pwm_min_der = -1;
static const int      RAMPA_PASO = 5;
static const uint32_t RAMPA_MS   = 400;

// Pose estimada (odometria por tiempo, sin sensores)
static float pose_x = 0, pose_y = 0, pose_th = 0;   // cm, cm, grados

// Imprime en el monitor serie con marca de tiempo y guarda el ultimo evento
static void registrar(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vsnprintf(ultimo, sizeof(ultimo), fmt, args);
  va_end(args);
  Serial.printf("[%8lu ms] %s\n", (unsigned long)millis(), ultimo);
}

// ---------------------------------------------------------------------
// Control de bajo nivel
// ---------------------------------------------------------------------
static int limitar(int v) {
  if (v >  cfg.pwm_max) return  cfg.pwm_max;
  if (v < -cfg.pwm_max) return -cfg.pwm_max;
  return v;
}

// Un lado del robot: valor > 0 adelante, < 0 reversa, 0 detenido
static void lado(ledc_channel_t ch_ade, ledc_channel_t ch_rev, int valor) {
  if (valor >= 0) { set_duty(ch_rev, 0);      set_duty(ch_ade, valor); }
  else            { set_duty(ch_ade, 0);      set_duty(ch_rev, -valor); }
}

// Sin factor de correccion (lo usa la rampa de PWM minimo)
static void motores_crudo(int izq, int der) {
  lado(CH_IZQ_ADE, CH_IZQ_REV, limitar(izq));
  lado(CH_DER_ADE, CH_DER_REV, limitar(der));
}

// Aplica el factor de correccion de cada lado y el limite de PWM
void motores(int izq, int der) {
  motores_crudo((int)lroundf(izq * cfg.trim_izq), (int)lroundf(der * cfg.trim_der));
}

static int pwm_o_default(int pwm, int def) { return pwm < 0 ? def : pwm; }

void adelante(int pwm)  { int p = pwm_o_default(pwm, cfg.pwm_avance); motores( p,  p); }
void atras(int pwm)     { int p = pwm_o_default(pwm, cfg.pwm_avance); motores(-p, -p); }
void izquierda(int pwm) { int p = pwm_o_default(pwm, cfg.pwm_giro);   motores(-p,  p); }
void derecha(int pwm)   { int p = pwm_o_default(pwm, cfg.pwm_giro);   motores( p, -p); }
void detener()          { motores_crudo(0, 0); }

// ---------------------------------------------------------------------
// Calibracion (tiempo <-> distancia/angulo)
// ---------------------------------------------------------------------
// Distancia o angulo estimados para un segmento, segun la regresion.
static float estimar(float pendiente, float ordenada, uint32_t ms) {
  if (pendiente <= 0) return 0;
  float v = pendiente * ms / 1000.0f + ordenada;
  return v > 0 ? v : 0;
}

// Tiempo necesario para una distancia/angulo (inverso de la regresion)
static uint32_t ms_para(float pendiente, float ordenada, float magnitud) {
  if (pendiente <= 0) return 0;
  float t = (fabsf(magnitud) - ordenada) / pendiente;
  if (t < 0.05f) t = 0.05f;           // minimo 50 ms
  return (uint32_t)lroundf(t * 1000.0f);
}

static void llenar_segmento(Segmento& s, const char* etiqueta, int izq, int der,
                            uint32_t ms, uint32_t pausa) {
  strncpy(s.etiqueta, etiqueta, sizeof(s.etiqueta) - 1);
  s.etiqueta[sizeof(s.etiqueta) - 1] = 0;
  s.izq = izq; s.der = der; s.ms = ms; s.pausa = pausa;
  s.d_cm = 0; s.d_deg = 0;
  // Si el movimiento coincide con el PWM calibrado, estima su efecto en la pose
  if (izq == der && abs(izq) == cfg.pwm_avance) {
    s.d_cm = estimar(cfg.v_cm_s, cfg.b_cm, ms) * (izq > 0 ? 1 : -1);
  } else if (izq == -der && abs(izq) == cfg.pwm_giro) {
    s.d_deg = estimar(cfg.w_deg_s, cfg.b_deg, ms) * (der > 0 ? 1 : -1);
  }
}

static void actualizar_pose(const Segmento& s) {
  pose_th += s.d_deg;
  while (pose_th > 180)   pose_th -= 360;
  while (pose_th <= -180) pose_th += 360;
  float rad = pose_th * (float)M_PI / 180.0f;
  pose_x += s.d_cm * cosf(rad);
  pose_y += s.d_cm * sinf(rad);
}

// ---------------------------------------------------------------------
// Ejecucion de comandos (solo desde robot_loop, en la tarea de loop())
// ---------------------------------------------------------------------
static void empezar_segmento() {
  Segmento& s = actual.seg[idx];
  if (s.izq == 0 && s.der == 0) {
    registrar(">> %s (%lu ms)", s.etiqueta, (unsigned long)s.ms);
  } else {
    registrar(">> %s (izq=%d der=%d, %lu ms)", s.etiqueta, s.izq, s.der, (unsigned long)s.ms);
  }
  motores(s.izq, s.der);
  t_inicio = millis();
  estado = E_MOVIENDO;
}

static void siguiente_segmento() {
  idx++;
  if (idx < actual.n) {
    empezar_segmento();
  } else {
    estado = E_LIBRE;
    registrar("Listo. Pose estimada: x=%.1f cm, y=%.1f cm, th=%.1f grados", pose_x, pose_y, pose_th);
  }
}

static void iniciar(const Comando& c) {
  actual = c;
  idx = 0;
  switch (c.tipo) {
    case CMD_CONTINUO:
      motores(c.seg[0].izq, c.seg[0].der);
      estado = E_CONTINUO;
      registrar(">> %s (continuo)", c.seg[0].etiqueta);
      break;
    case CMD_PWM_MIN:
      pwm_rampa = 0;
      t_rampa = millis();
      marcar_min = false;
      estado = E_PWM_MIN;
      registrar(">> PWM minimo lado %s: escribe 'ok' (o /pwmmin_ok) cuando la rueda empiece a girar",
                c.lado == 'I' ? "izquierdo" : "derecho");
      break;
    case CMD_PLAN:
      if (c.n == 0) { estado = E_LIBRE; return; }
      empezar_segmento();
      break;
  }
}

static void paso_rampa() {
  if (marcar_min) {
    marcar_min = false;
    detener();
    if (actual.lado == 'I') pwm_min_izq = pwm_rampa; else pwm_min_der = pwm_rampa;
    estado = E_LIBRE;
    registrar("PWM minimo lado %s = %d", actual.lado == 'I' ? "izquierdo" : "derecho", pwm_rampa);
    return;
  }
  if (millis() - t_rampa < RAMPA_MS) return;
  t_rampa = millis();
  pwm_rampa += RAMPA_PASO;
  if (pwm_rampa > cfg.pwm_max) {
    detener();
    estado = E_LIBRE;
    registrar("La rueda no se marco antes de pwm_max=%d. Prueba terminada.", cfg.pwm_max);
    return;
  }
  if (actual.lado == 'I') motores_crudo(pwm_rampa, 0); else motores_crudo(0, pwm_rampa);
  Serial.printf("[%8lu ms]    rampa PWM = %d\n", (unsigned long)millis(), pwm_rampa);
}

// ---------------------------------------------------------------------
// Comandos por el monitor serie (115200 baudios, fin de linea "Nueva linea")
// ---------------------------------------------------------------------
static void imprimir_ayuda() {
  Serial.println(F(
    "\n=== Comandos del robot ===\n"
    "a [ms] / r [ms]      adelante / atras (sin ms: usa t_adelante / t_atras)\n"
    "i [ms] / d [ms]      giro izquierda / derecha (sin ms: usa t90)\n"
    "g                    giro de 360 grados (usa t360)\n"
    "m IZQ DER MS         motores con PWM por lado (-255..255) durante MS\n"
    "seq                  secuencia de la tarea (Parte C)\n"
    "mot                  prueba de sentido de cada motor (Parte B)\n"
    "min i | min d        rampa de PWM minimo, lado izq/der (Parte B)\n"
    "ok                   marca el PWM minimo (la rueda ya giro)\n"
    "cm D                 avanzar D cm (negativo = atras)\n"
    "gr A                 girar A grados (positivo = izquierda)\n"
    "ir X Y               ir a la coordenada (X, Y) en cm\n"
    "origen               fija la pose actual como (0, 0, 0)\n"
    "s                    PARO inmediato\n"
    "cfg / estado         ver configuracion / estado (JSON)\n"
    "set CLAVE VALOR      cambia y guarda un parametro. Claves:\n"
    "                     pwm pwm_giro pwm_max trim_i trim_d t_adelante\n"
    "                     t_atras t90 t360 v b w bg\n"
    "reset_cfg            vuelve a la configuracion de fabrica\n"));
}

static void ejecutar_linea(char* linea) {
  char cmd[16] = {0};
  char clave[16] = {0};
  float a = NAN, b = NAN, c = NAN;
  int n = sscanf(linea, "%15s %f %f %f", cmd, &a, &b, &c);
  if (n <= 0) return;
  for (char* p = cmd; *p; p++) *p = tolower(*p);

  auto ms_o = [&](uint32_t def) { return (n >= 2 && a > 0) ? (uint32_t)a : def; };

  if      (!strcmp(cmd, "s") || !strcmp(cmd, "x") || !strcmp(cmd, "stop")) robot_stop();
  else if (!strcmp(cmd, "a"))   robot_mover( cfg.pwm_avance,  cfg.pwm_avance, ms_o(cfg.t_adelante), "Adelante");
  else if (!strcmp(cmd, "r"))   robot_mover(-cfg.pwm_avance, -cfg.pwm_avance, ms_o(cfg.t_atras), "Atras");
  else if (!strcmp(cmd, "i"))   robot_mover(-cfg.pwm_giro,    cfg.pwm_giro,   ms_o(cfg.t_giro90), "Izquierda");
  else if (!strcmp(cmd, "d"))   robot_mover( cfg.pwm_giro,   -cfg.pwm_giro,   ms_o(cfg.t_giro90), "Derecha");
  else if (!strcmp(cmd, "g"))   girar360();
  else if (!strcmp(cmd, "m") && n == 4) robot_mover((int)a, (int)b, (uint32_t)c, "Manual");
  else if (!strcmp(cmd, "seq")) robot_secuencia_tarea();
  else if (!strcmp(cmd, "mot")) robot_prueba_motores();
  else if (!strcmp(cmd, "ok"))  robot_pwm_min_marcar();
  else if (!strcmp(cmd, "min")) {
    char l = 0;
    sscanf(linea, "%*s %c", &l);
    l = toupper(l);
    if (l == 'I' || l == 'D') robot_pwm_min(l); else Serial.println("Uso: min i | min d");
  }
  else if (!strcmp(cmd, "cm") && n >= 2)  { if (!robot_avanzar_cm(a))  Serial.println("Falta calibrar v (set v ...)"); }
  else if (!strcmp(cmd, "gr") && n >= 2)  { if (!robot_girar_grados(a)) Serial.println("Falta calibrar w (set w ...)"); }
  else if (!strcmp(cmd, "ir") && n >= 3)  { if (!robot_ir_a(a, b)) Serial.println("Falta calibrar v y w"); }
  else if (!strcmp(cmd, "origen")) robot_origen();
  else if (!strcmp(cmd, "cfg"))    Serial.println(robot_config_json());
  else if (!strcmp(cmd, "estado")) Serial.println(robot_estado_json());
  else if (!strcmp(cmd, "reset_cfg")) { robot_config_default(); robot_set_param("pwm", cfg.pwm_avance); Serial.println(robot_config_json()); }
  else if (!strcmp(cmd, "set")) {
    float valor;
    if (sscanf(linea, "%*s %15s %f", clave, &valor) == 2 && robot_set_param(clave, valor)) {
      Serial.println(robot_config_json());
    } else {
      Serial.println("Uso: set CLAVE VALOR (escribe 'ayuda' para ver las claves)");
    }
  }
  else imprimir_ayuda();
}

static void leer_serie() {
  static char buf[64];
  static uint8_t len = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      buf[len] = 0;
      if (len) ejecutar_linea(buf);
      len = 0;
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = ch;
    }
  }
}

// ---------------------------------------------------------------------
// API publica
// ---------------------------------------------------------------------
void robot_config_default() {
  cfg.pwm_avance = 140;
  cfg.pwm_giro   = 140;
  cfg.pwm_max    = 145;   // ~6 V promedio con bateria llena (ver docs/PENDIENTES.md)
  cfg.trim_izq   = 1.0f;
  cfg.trim_der   = 1.0f;
  cfg.t_adelante = 2000;
  cfg.t_atras    = 2000;
  cfg.t_giro90   = 500;
  cfg.t_giro360  = 1800;
  cfg.v_cm_s  = 0; cfg.b_cm  = 0;
  cfg.w_deg_s = 0; cfg.b_deg = 0;
}

void robot_setup() {
  ledc_timer_config_t timer = {
    .speed_mode      = LEDC_LOW_SPEED_MODE,
    .duty_resolution = LEDC_TIMER_8_BIT,
    .timer_num       = LEDC_TIMER_1,
    .freq_hz         = PWM_FRECUENCIA_HZ,
    .clk_cfg         = LEDC_AUTO_CLK
  };
  ledc_timer_config(&timer);
  configurar_canal(LEFT_M0,  CH_IZQ_REV);
  configurar_canal(LEFT_M1,  CH_IZQ_ADE);
  configurar_canal(RIGHT_M0, CH_DER_REV);
  configurar_canal(RIGHT_M1, CH_DER_ADE);
  pinMode(33, OUTPUT);   // LED rojo de la placa

  // Calibracion guardada en flash (si no hay, valores de fabrica)
  robot_config_default();
  prefs.begin("robot", false);
  if (prefs.getBytesLength("cfg") == sizeof(RobotConfig)) {
    prefs.getBytes("cfg", &cfg, sizeof(RobotConfig));
  }

  cola = xQueueCreate(4, sizeof(Comando));
  detener();
}

void robot_stop() {
  cancelar = true;       // robot_loop vacia la cola y vuelve a LIBRE
  detener();             // y los motores se apagan ya, sin esperar al loop
}

void robot_loop() {
  leer_serie();

  if (cancelar) {
    cancelar = false;
    xQueueReset(cola);
    detener();
    if (estado != E_LIBRE) registrar("PARO");
    estado = E_LIBRE;
  }

  uint32_t ahora = millis();
  switch (estado) {
    case E_MOVIENDO: {
      Segmento& s = actual.seg[idx];
      if (ahora - t_inicio >= s.ms) {
        detener();
        ultimo_ms_real = ahora - t_inicio;
        actualizar_pose(s);
        if (s.pausa > 0) { estado = E_PAUSA; t_inicio = ahora; }
        else siguiente_segmento();
      }
      break;
    }
    case E_PAUSA:
      if (ahora - t_inicio >= actual.seg[idx].pausa) siguiente_segmento();
      break;
    case E_PWM_MIN:
      paso_rampa();
      break;
    default:
      break;
  }

  // Un comando nuevo entra cuando no hay rutina en curso
  // (un movimiento continuo si se puede reemplazar).
  if (estado == E_LIBRE || estado == E_CONTINUO) {
    Comando c;
    if (xQueueReceive(cola, &c, 0) == pdTRUE) iniciar(c);
  }
}

static bool encolar(const Comando& c) {
  if (!cola) return false;
  if (xQueueSend(cola, &c, 0) != pdTRUE) {
    Serial.println("Cola llena: comando ignorado");
    return false;
  }
  return true;
}

bool robot_mover(int izq, int der, uint32_t ms, const char* etiqueta) {
  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 1;
  llenar_segmento(c.seg[0], etiqueta, izq, der, ms, 0);
  return encolar(c);
}

bool robot_continuo(int izq, int der, const char* etiqueta) {
  Comando c = {};
  c.tipo = CMD_CONTINUO; c.n = 1;
  llenar_segmento(c.seg[0], etiqueta, izq, der, 0, 0);
  return encolar(c);
}

bool girar360() {
  return robot_mover(-cfg.pwm_giro, cfg.pwm_giro, cfg.t_giro360, "Giro 360");
}

// Parte C: adelante, atras, izquierda, derecha y 360, con 1 s de pausa
bool robot_secuencia_tarea() {
  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 6;
  const int p = cfg.pwm_avance, g = cfg.pwm_giro;
  llenar_segmento(c.seg[0], "Inicio (3 s)",   0,  0, 3000,           0);
  llenar_segmento(c.seg[1], "1 Adelante",     p,  p, cfg.t_adelante, 1000);
  llenar_segmento(c.seg[2], "2 Atras",       -p, -p, cfg.t_atras,    1000);
  llenar_segmento(c.seg[3], "3 Izquierda 90",-g,  g, cfg.t_giro90,   1000);
  llenar_segmento(c.seg[4], "4 Derecha 90",   g, -g, cfg.t_giro90,   1000);
  llenar_segmento(c.seg[5], "5 Giro 360",    -g,  g, cfg.t_giro360,  0);
  return encolar(c);
}

// Parte B: cada lado adelante y atras 1 s (con las ruedas en el aire)
bool robot_prueba_motores() {
  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 5;
  const int p = cfg.pwm_avance;
  llenar_segmento(c.seg[0], "Inicio (2 s)",     0,  0, 2000, 0);
  llenar_segmento(c.seg[1], "Izq adelante",     p,  0, 1000, 700);
  llenar_segmento(c.seg[2], "Izq atras",       -p,  0, 1000, 700);
  llenar_segmento(c.seg[3], "Der adelante",     0,  p, 1000, 700);
  llenar_segmento(c.seg[4], "Der atras",        0, -p, 1000, 0);
  return encolar(c);
}

bool robot_pwm_min(char lado) {
  Comando c = {};
  c.tipo = CMD_PWM_MIN; c.n = 0; c.lado = lado;
  return encolar(c);
}

void robot_pwm_min_marcar() { marcar_min = true; }

bool robot_avanzar_cm(float cm) {
  if (cfg.v_cm_s <= 0) return false;
  int p = cm >= 0 ? cfg.pwm_avance : -cfg.pwm_avance;
  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 1;
  llenar_segmento(c.seg[0], cm >= 0 ? "Avanzar cm" : "Retroceder cm", p, p,
                  ms_para(cfg.v_cm_s, cfg.b_cm, cm), 0);
  c.seg[0].d_cm = cm;    // la pose usa el valor pedido
  return encolar(c);
}

bool robot_girar_grados(float grados) {
  if (cfg.w_deg_s <= 0) return false;
  int g = grados >= 0 ? cfg.pwm_giro : -cfg.pwm_giro;
  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 1;
  llenar_segmento(c.seg[0], grados >= 0 ? "Girar izq" : "Girar der", -g, g,
                  ms_para(cfg.w_deg_s, cfg.b_deg, grados), 0);
  c.seg[0].d_deg = grados;
  return encolar(c);
}

// Gira hacia el punto y luego avanza en linea recta
bool robot_ir_a(float x_cm, float y_cm) {
  if (cfg.v_cm_s <= 0 || cfg.w_deg_s <= 0) return false;
  float dx = x_cm - pose_x, dy = y_cm - pose_y;
  float dist = sqrtf(dx * dx + dy * dy);
  float rumbo = atan2f(dy, dx) * 180.0f / (float)M_PI;
  float giro = rumbo - pose_th;
  while (giro > 180)   giro -= 360;
  while (giro <= -180) giro += 360;

  Comando c = {};
  c.tipo = CMD_PLAN; c.n = 0;
  if (fabsf(giro) >= 2.0f) {
    int g = giro >= 0 ? cfg.pwm_giro : -cfg.pwm_giro;
    Segmento& s = c.seg[c.n++];
    llenar_segmento(s, "Ir a: giro", -g, g, ms_para(cfg.w_deg_s, cfg.b_deg, giro), 300);
    s.d_cm = 0; s.d_deg = giro;
  }
  if (dist >= 1.0f) {
    Segmento& s = c.seg[c.n++];
    llenar_segmento(s, "Ir a: avance", cfg.pwm_avance, cfg.pwm_avance,
                    ms_para(cfg.v_cm_s, cfg.b_cm, dist), 0);
    s.d_cm = dist; s.d_deg = 0;
  }
  registrar("Ir a (%.1f, %.1f): girar %.1f grados y avanzar %.1f cm", x_cm, y_cm, giro, dist);
  return encolar(c);
}

void robot_origen() {
  pose_x = pose_y = pose_th = 0;
  registrar("Pose reiniciada a (0, 0, 0)");
}

bool robot_ocupado() {
  return estado != E_LIBRE || (cola && uxQueueMessagesWaiting(cola) > 0);
}

bool robot_set_param(const char* k, float v) {
  auto pwm_valido = [](float x) { return x >= 0 && x <= 255; };
  if      (!strcmp(k, "pwm")        && pwm_valido(v)) cfg.pwm_avance = (int)v;
  else if (!strcmp(k, "pwm_giro")   && pwm_valido(v)) cfg.pwm_giro   = (int)v;
  else if (!strcmp(k, "pwm_max")    && pwm_valido(v)) cfg.pwm_max    = (int)v;
  else if (!strcmp(k, "trim_i")     && v >= 0.3f && v <= 1.0f) cfg.trim_izq = v;
  else if (!strcmp(k, "trim_d")     && v >= 0.3f && v <= 1.0f) cfg.trim_der = v;
  else if (!strcmp(k, "t_adelante") && v > 0) cfg.t_adelante = (uint32_t)v;
  else if (!strcmp(k, "t_atras")    && v > 0) cfg.t_atras    = (uint32_t)v;
  else if (!strcmp(k, "t90")        && v > 0) cfg.t_giro90   = (uint32_t)v;
  else if (!strcmp(k, "t360")       && v > 0) cfg.t_giro360  = (uint32_t)v;
  else if (!strcmp(k, "v")  && v >= 0) cfg.v_cm_s  = v;
  else if (!strcmp(k, "b"))            cfg.b_cm    = v;
  else if (!strcmp(k, "w")  && v >= 0) cfg.w_deg_s = v;
  else if (!strcmp(k, "bg"))           cfg.b_deg   = v;
  else return false;
  prefs.putBytes("cfg", &cfg, sizeof(RobotConfig));
  registrar("Config: %s = %g (guardado)", k, v);
  return true;
}

String robot_config_json() {
  char b[400];
  snprintf(b, sizeof(b),
    "{\"pwm\":%d,\"pwm_giro\":%d,\"pwm_max\":%d,\"trim_i\":%.3f,\"trim_d\":%.3f,"
    "\"t_adelante\":%lu,\"t_atras\":%lu,\"t90\":%lu,\"t360\":%lu,"
    "\"v\":%.3f,\"b\":%.3f,\"w\":%.3f,\"bg\":%.3f,\"pwm_hz\":%lu}",
    cfg.pwm_avance, cfg.pwm_giro, cfg.pwm_max, cfg.trim_izq, cfg.trim_der,
    (unsigned long)cfg.t_adelante, (unsigned long)cfg.t_atras,
    (unsigned long)cfg.t_giro90, (unsigned long)cfg.t_giro360,
    cfg.v_cm_s, cfg.b_cm, cfg.w_deg_s, cfg.b_deg, (unsigned long)PWM_FRECUENCIA_HZ);
  return String(b);
}

String robot_estado_json() {
  char b[400];
  snprintf(b, sizeof(b),
    "{\"ocupado\":%s,\"estado\":\"%s\",\"ultimo\":\"%s\",\"ultimo_ms_real\":%lu,"
    "\"pose\":{\"x\":%.1f,\"y\":%.1f,\"th\":%.1f},"
    "\"pwm_min_izq\":%d,\"pwm_min_der\":%d,\"rampa\":%d,\"t_ms\":%lu}",
    robot_ocupado() ? "true" : "false", NOMBRE_ESTADO[estado], ultimo,
    (unsigned long)ultimo_ms_real, pose_x, pose_y, pose_th,
    pwm_min_izq, pwm_min_der, pwm_rampa, (unsigned long)millis());
  return String(b);
}
