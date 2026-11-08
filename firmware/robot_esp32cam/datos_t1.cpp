#include "datos_t1.h"
#include <LittleFS.h>

static const char* RUTA_DATOS  = "/t1.json";
static const char* RUTA_BAK    = "/t1.bak";
static const char* RUTA_NUEVO  = "/t1.new";

bool datos_t1_begin() {
  bool ok = LittleFS.begin(true);   // true = formatear si no hay sistema de archivos
  Serial.printf("LittleFS: %s (%u de %u bytes usados)\n", ok ? "ok" : "ERROR",
                ok ? (unsigned)LittleFS.usedBytes() : 0, ok ? (unsigned)LittleFS.totalBytes() : 0);
  return ok;
}

String datos_t1_leer(const char* ruta) {
  File f = LittleFS.open(ruta, "r");
  if (!f) return "";
  String s = f.readString();
  f.close();
  return s;
}

// Escribe primero /t1.new y solo si salio completo reemplaza /t1.json,
// que pasa a ser /t1.bak. Si se va la luz a media escritura no se pierde nada.
bool datos_t1_guardar(const uint8_t* buf, size_t n) {
  if (n == 0 || n > T1_MAX_BYTES) return false;
  File f = LittleFS.open(RUTA_NUEVO, "w");
  if (!f) return false;
  size_t escritos = f.write(buf, n);
  f.close();
  if (escritos != n) { LittleFS.remove(RUTA_NUEVO); return false; }
  if (LittleFS.exists(RUTA_DATOS)) {
    LittleFS.remove(RUTA_BAK);
    LittleFS.rename(RUTA_DATOS, RUTA_BAK);
  }
  return LittleFS.rename(RUTA_NUEVO, RUTA_DATOS);
}
