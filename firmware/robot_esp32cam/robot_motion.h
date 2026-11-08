// =====================================================================
// robot_motion.h - Control de movimiento del robot diferencial
// ---------------------------------------------------------------------
// Hardware: ESP32-CAM (AI-Thinker) + driver L298N + 4 motores TT
//           (los 2 motores de cada lado van en paralelo en la misma
//           salida del L298N, asi que el robot se comporta como uno
//           diferencial de 2 ruedas).
//
// Velocidad: los jumpers ENA/ENB del L298N estan puestos, y la
// velocidad se regula mandando PWM directo a los pines IN:
//   - adelante: IN_adelante = PWM, IN_reversa = 0
//   - reversa : IN_adelante = 0,   IN_reversa = PWM
// Asi no se necesitan pines extra (el ESP32-CAM ya no tiene libres).
//
// Todos los movimientos con duracion son NO bloqueantes: se encolan y
// se ejecutan en robot_loop(), que se llama desde loop(). Asi el
// servidor web y la camara siguen funcionando mientras el robot se mueve.
// =====================================================================
#pragma once
#include <Arduino.h>

// ---------------- Pines del L298N ----------------
#define LEFT_M0   13   // IN: lado izquierdo, reversa
#define LEFT_M1   12   // IN: lado izquierdo, adelante
#define RIGHT_M0  14   // IN: lado derecho, reversa
#define RIGHT_M1  15   // IN: lado derecho, adelante

// ---------------- Parametros de calibracion ----------------
// Se guardan en la memoria flash (NVS), asi que sobreviven a reinicios.
struct RobotConfig {
  int      pwm_avance;   // PWM para adelante/atras (0-255)
  int      pwm_giro;     // PWM para los giros (0-255)
  int      pwm_max;      // Limite de PWM: ~6 V promedio en el motor
  float    trim_izq;     // Factor de correccion del lado izquierdo (0.5-1.0)
  float    trim_der;     // Factor de correccion del lado derecho (0.5-1.0)
  uint32_t t_adelante;   // ms de "adelante" en la secuencia de la tarea
  uint32_t t_atras;      // ms de "atras" en la secuencia de la tarea
  uint32_t t_giro90;     // ms para girar ~90 grados a la izquierda
  uint32_t t_giro90_der; // ms para girar ~90 grados a la derecha (el lado derecho tiene mas friccion)
  uint32_t t_giro360;    // ms para girar ~360 grados
  // Resultado de la regresion lineal (script calibrar.py):
  //   distancia = v_cm_s * t + b_cm      angulo = w_deg_s * t + b_deg
  float    v_cm_s;       // velocidad lineal a pwm_avance (cm/s); 0 = sin calibrar
  float    b_cm;         // ordenada al origen de la recta (cm)
  float    w_deg_s;      // velocidad angular a pwm_giro (grados/s); 0 = sin calibrar
  float    b_deg;        // ordenada al origen del giro (grados)
};

extern RobotConfig cfg;

// ---------------- Inicializacion y ciclo ----------------
void robot_setup();          // Configura PWM, carga la calibracion y detiene
void robot_loop();           // Llamar en cada loop(): ejecuta la cola y lee el serie
void robot_stop();           // Paro inmediato: detiene motores y cancela todo

// ---------------- Funciones basicas (continuas) ----------------
// Se quedan girando hasta que se llama detener(). pwm < 0 usa el de la config.
void motores(int izq, int der);   // -255..255 por lado (signo = sentido)
void adelante(int pwm = -1);
void atras(int pwm = -1);
void izquierda(int pwm = -1);     // giro sobre su eje: izq atras, der adelante
void derecha(int pwm = -1);       // giro sobre su eje: izq adelante, der atras
void detener();

// ---------------- Movimientos encolados (con duracion) ----------------
bool robot_mover(int izq, int der, uint32_t ms, const char* etiqueta);
bool robot_continuo(int izq, int der, const char* etiqueta);  // botones de la pagina
bool girar360();                  // usa cfg.t_giro360
bool robot_secuencia_tarea();     // secuencia de la Parte C
bool robot_prueba_motores();      // Parte B: cada lado adelante y atras
bool robot_pwm_min(char lado);    // Parte B: rampa de PWM ('I' o 'D')
void robot_pwm_min_marcar();      // el usuario indica que la rueda ya giro

// ---------------- Movimiento por coordenadas ----------------
// Necesitan v_cm_s y w_deg_s calibrados. Marco de referencia:
//   origen = donde se llamo robot_origen(), x hacia el frente del robot,
//   y hacia su izquierda, angulo positivo = giro a la izquierda.
bool robot_avanzar_cm(float cm);      // negativo = reversa
bool robot_girar_grados(float grados);// positivo = izquierda
bool robot_ir_a(float x_cm, float y_cm);
void robot_origen();                  // pose actual = (0, 0, 0 grados)

// ---------------- Configuracion y estado ----------------
bool   robot_set_param(const char* clave, float valor);  // guarda en flash
void   robot_config_default();
String robot_config_json();
String robot_estado_json();
bool   robot_ocupado();
