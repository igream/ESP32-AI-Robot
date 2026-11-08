// =====================================================================
// datos_t1.h - Almacenamiento de los datos de la Tarea 1 en LittleFS
// ---------------------------------------------------------------------
// Guarda un documento JSON (/t1.json) y su respaldo (/t1.bak) en la
// memoria flash del robot, para que los datos no dependan del navegador
// del celular. Esquema de particiones: huge_app (3 MB app / 1 MB datos).
// =====================================================================
#pragma once
#include <Arduino.h>

#define T1_MAX_BYTES 32768   // tamano maximo del documento

bool   datos_t1_begin();                                  // monta LittleFS (la formatea si hace falta)
String datos_t1_leer(const char* ruta);                   // "" si no existe
bool   datos_t1_guardar(const uint8_t* buf, size_t n);    // respalda el anterior y escribe el nuevo
