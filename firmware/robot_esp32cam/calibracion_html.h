// Pagina /calibrar: ejecuta un movimiento, pide la medicion y la registra.
// Los datos se guardan en el navegador (localStorage) con las mismas columnas
// que herramientas/calibrar.py, y se exportan a CSV para "calibrar.py analizar".
#pragma once
#include <pgmspace.h>

static const char CALIBRAR_HTML[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calibración del robot</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:12px;background:#111;color:#eee;max-width:560px;margin:auto}
h1{font-size:18px;margin:4px 0 10px}
h2{font-size:15px;margin:16px 0 6px;color:#9cf}
label{display:block;font-size:13px;margin-top:8px;color:#bbb}
input,select,textarea{width:100%;box-sizing:border-box;font-size:17px;padding:9px;border-radius:6px;border:1px solid #444;background:#222;color:#fff}
.fila{display:flex;gap:8px}.fila>div{flex:1}
button{font-size:17px;padding:12px;border:0;border-radius:6px;margin-top:10px;width:100%;color:#fff;background:#357}
button.ok{background:#2a7a3a}button.mal{background:#a33}button.gris{background:#444;font-size:14px;padding:9px}
#estado{font-family:monospace;font-size:13px;color:#fc6;min-height:18px;margin-top:8px}
#medir{display:none;border:2px solid #2a7a3a;border-radius:8px;padding:10px;margin-top:10px}
table{border-collapse:collapse;width:100%;font-size:12px}
td,th{border-bottom:1px solid #333;padding:4px 3px;text-align:right}th:first-child,td:first-child{text-align:left}
a{color:#9cf}
</style></head><body>
<h1>Calibración · <a href="/">Control</a></h1>

<h2>1. Movimiento</h2>
<label>Tipo</label>
<select id="tipo">
<option value="adelante">Adelante (avance y desviación)</option>
<option value="atras">Atrás (avance y desviación)</option>
<option value="giro_izq">Giro izquierda (ángulo)</option>
<option value="giro_der">Giro derecha (ángulo)</option>
<option value="ida_vuelta">Ida y vuelta (distancia al origen)</option>
</select>
<div class="fila">
<div><label>Duración (ms)</label><input id="ms" type="number" inputmode="numeric" value="2000"></div>
<div><label>PWM</label><input id="pwm" type="number" inputmode="numeric" value="140"></div>
</div>
<div class="fila">
<div><label>Voltaje batería (V)</label><input id="voltaje" type="text" inputmode="decimal"></div>
<div><label>Superficie</label><input id="superficie" type="text" value="piso"></div>
</div>
<label>Nota</label><input id="nota" type="text">
<button id="bEjecutar" class="ok" onclick="ejecutar()">Ejecutar (robot en la marca)</button>
<button class="mal" onclick="paro()">PARO</button>
<div id="estado"></div>

<div id="medir">
<h2 style="margin-top:0">2. Medición</h2>
<div id="campos"></div>
<button class="ok" onclick="guardar()">Guardar prueba</button>
<button class="gris" onclick="descartar()">Descartar y repetir</button>
</div>

<h2>3. Resumen (<span id="total">0</span> pruebas)</h2>
<div style="overflow-x:auto"><table id="resumen"></table></div>
<button class="gris" onclick="deshacer()">Borrar la última prueba</button>
<button onclick="descargar()">Descargar CSV</button>
<button class="gris" onclick="verCsv()">Ver / copiar CSV</button>
<textarea id="csv" rows="8" style="display:none;font-size:11px"></textarea>
<button class="gris" onclick="borrarTodo()">Borrar todos los datos</button>
<p style="font-size:12px;color:#888">Guarda el CSV como <code>herramientas/datos/pruebas.csv</code> y analiza con <code>python calibrar.py analizar</code>. Un giro de 360° es "Giro izquierda" con duración ≈ t360.</p>

<script>
var COLS=["fecha","sesion","tipo","pwm_izq","pwm_der","ms","ms_real","trim_i","trim_d","avance_cm","desviacion_cm","angulo_deg","dist_origen_cm","voltaje","superficie","nota"];
var T={adelante:{l:1,r:1,c:["avance_cm","desviacion_cm"],g:"pwm"},
 atras:{l:-1,r:-1,c:["avance_cm","desviacion_cm"],g:"pwm"},
 giro_izq:{l:-1,r:1,c:["angulo_deg"],g:"pwm_giro"},
 giro_der:{l:1,r:-1,c:["angulo_deg"],g:"pwm_giro"},
 ida_vuelta:{l:1,r:1,c:["dist_origen_cm"],g:"pwm"}};
var AYUDA={avance_cm:"Avance recorrido (cm)",desviacion_cm:"Desviación lateral (cm, + izquierda / − derecha)",
 angulo_deg:"Ángulo girado (°, positivo)",dist_origen_cm:"Distancia del final al inicio (cm)"};
var KEY="calib_pruebas", KEYA="calib_ajustes";
var SESION=new Date().toISOString().replace(/[-:T]/g,"").slice(0,14);
var cfg={}, pend=null, ocupado=false;
function $(i){return document.getElementById(i)}
function ls(k,d){try{var v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}}
function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function get(p){return fetch(p+(p.indexOf("?")<0?"?":"&")+"_="+Date.now()).then(function(r){return r.json()})}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
function msg(t){$("estado").textContent=t}
function num(s){var x=parseFloat(String(s).replace(",","."));return isNaN(x)?"":x}

function ajustes(){
 var a=ls(KEYA,{});
 ["tipo","ms","voltaje","superficie","nota"].forEach(function(k){if(a[k]!==undefined)$(k).value=a[k]});
}
function guardaAjustes(){
 var a={};["tipo","ms","voltaje","superficie","nota"].forEach(function(k){a[k]=$(k).value});lsSet(KEYA,a);
}
function pwmDefecto(){
 var g=T[$("tipo").value].g;
 if(cfg[g]!==undefined)$("pwm").value=cfg[g];
}
$("tipo").onchange=function(){pwmDefecto();guardaAjustes()};
["ms","voltaje","superficie","nota"].forEach(function(k){$(k).onchange=guardaAjustes});

async function esperar(max){
 var t0=Date.now();await sleep(300);
 while(Date.now()-t0<max*1000){
  var e=await get("/estado");
  if(!e.ocupado)return e;
  await sleep(200);
 }
 await get("/stop");throw new Error("El robot no terminó; se mandó PARO");
}

async function ejecutar(){
 if(ocupado||pend)return;
 var t=$("tipo").value,d=T[t],ms=parseInt($("ms").value),pwm=parseInt($("pwm").value);
 if(!(ms>0)||!(pwm>0)){msg("Revisa duración y PWM");return}
 ocupado=true;$("bEjecutar").disabled=true;
 try{
  cfg=await get("/config");
  var l=d.l*pwm,r=d.r*pwm;
  msg("Ejecutando "+t+" "+ms+" ms...");
  var m=await get("/move?l="+l+"&r="+r+"&ms="+ms);
  if(!m.ok)throw new Error("Rechazado: "+(m.error||""));
  var e=await esperar(ms/1000+15);
  if(t==="ida_vuelta"){
   msg("Regresando...");await sleep(500);
   m=await get("/move?l="+(-l)+"&r="+(-r)+"&ms="+ms);
   if(!m.ok)throw new Error("Rechazado: "+(m.error||""));
   e=await esperar(ms/1000+15);
  }
  pend={fecha:new Date().toISOString().slice(0,19),sesion:SESION,tipo:t,pwm_izq:l,pwm_der:r,ms:ms,
   ms_real:e.ultimo_ms_real,trim_i:cfg.trim_i,trim_d:cfg.trim_d,voltaje:num($("voltaje").value),
   superficie:$("superficie").value,nota:$("nota").value};
  var h="";
  d.c.forEach(function(c){
   h+='<label>'+AYUDA[c]+'</label><input id="m_'+c+'" type="text" inputmode="decimal">';
  });
  $("campos").innerHTML=h;$("medir").style.display="block";
  var p=$("m_"+d.c[0]);if(p)p.focus();
  msg("Listo ("+e.ultimo_ms_real+" ms reales). Captura la medición.");
 }catch(x){msg("Error: "+x.message)}
 ocupado=false;$("bEjecutar").disabled=false;
}

function guardar(){
 if(!pend)return;
 var d=T[pend.tipo];
 for(var i=0;i<d.c.length;i++){
  var v=num($("m_"+d.c[i]).value);
  if(v===""){msg("Falta: "+AYUDA[d.c[i]]);return}
  pend[d.c[i]]=v;
 }
 var datos=ls(KEY,[]);datos.push(pend);lsSet(KEY,datos);
 pend=null;$("medir").style.display="none";
 msg("Guardada. Pon el robot en la marca y ejecuta otra.");render();
}
function descartar(){pend=null;$("medir").style.display="none";msg("Prueba descartada. Repite.")}
function paro(){get("/stop");msg("PARO")}
function deshacer(){var d=ls(KEY,[]);if(d.length&&confirm("¿Borrar la última prueba ("+d[d.length-1].tipo+" "+d[d.length-1].ms+" ms)?")){d.pop();lsSet(KEY,d);render()}}
function borrarTodo(){if(confirm("¿Borrar TODAS las pruebas? Descarga el CSV antes.")){lsSet(KEY,[]);render()}}

function csvTexto(){
 var d=ls(KEY,[]),s=COLS.join(",")+"\n";
 d.forEach(function(f){
  s+=COLS.map(function(c){var v=f[c];if(v===undefined||v===null)v="";v=String(v);
   return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}).join(",")+"\n";
 });
 return s;
}
function descargar(){
 var b=new Blob([csvTexto()],{type:"text/csv"}),a=document.createElement("a");
 a.href=URL.createObjectURL(b);a.download="pruebas_"+SESION+".csv";document.body.appendChild(a);a.click();a.remove();
}
function verCsv(){var t=$("csv");t.style.display="block";t.value=csvTexto();t.select()}

function render(){
 var d=ls(KEY,[]);$("total").textContent=d.length;
 var g={};
 d.forEach(function(f){var k=f.tipo+"|"+f.ms;(g[k]=g[k]||[]).push(f)});
 var h="<tr><th>Tipo · ms</th><th>n</th><th>Medida</th><th>Media</th><th>DE</th></tr>";
 Object.keys(g).sort().forEach(function(k){
  var fs=g[k],p=k.split("|");
  T[p[0]].c.forEach(function(c,i){
   var v=fs.map(function(f){return f[c]}).filter(function(x){return typeof x==="number"});
   var m=v.reduce(function(a,b){return a+b},0)/(v.length||1);
   var sd=v.length>1?Math.sqrt(v.reduce(function(a,b){return a+(b-m)*(b-m)},0)/(v.length-1)):0;
   h+="<tr><td>"+(i?"":p[0]+" · "+p[1])+"</td><td>"+(i?"":fs.length)+"</td><td>"+c.replace("_cm","").replace("_deg","")+"</td><td>"+m.toFixed(1)+"</td><td>"+sd.toFixed(1)+"</td></tr>";
  });
 });
 $("resumen").innerHTML=d.length?h:"";
}

ajustes();render();
get("/config").then(function(c){cfg=c;pwmDefecto()}).catch(function(){msg("Sin conexión con el robot")});
</script></body></html>)rawliteral";
