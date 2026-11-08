// Pagina /tarea1: app de verificacion de la Tarea 1 (etapas E0-E4, prueba libre y datos).
// Evolucion de /calibrar. El documento completo se guarda en el robot (POST /t1/datos,
// LittleFS) y una copia en localStorage. Ver docs/PLAN_IMPLEMENTACION.md, seccion T1.2.
#pragma once
#include <pgmspace.h>

static const char TAREA1_HTML[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tarea 1</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}
#cab{position:sticky;top:0;z-index:5;background:#181818;border-bottom:1px solid #333;padding:6px 10px}
#fila1{display:flex;gap:8px;align-items:center}
#est{flex:1;font-family:monospace;font-size:12px;color:#fc6;min-height:16px;overflow:hidden}
#paro{width:auto;margin:0;padding:8px 18px;font-size:16px;background:#a33}
#tabs{display:flex;gap:4px;overflow-x:auto;margin-top:6px;padding-bottom:2px}
#tabs button{width:auto;margin:0;padding:7px 10px;font-size:13px;background:#2a2a2a;white-space:nowrap}
#tabs button.sel{background:#357}
#tabs .completa{border-bottom:3px solid #2a7a3a}#tabs .disponible{border-bottom:3px solid #fc6}#tabs .bloqueada{border-bottom:3px solid #555;color:#888}
main{max-width:600px;margin:auto;padding:10px 12px 40px}
h2{font-size:16px;margin:8px 0;color:#9cf}h3{font-size:14px;margin:12px 0 4px;color:#cde}
label{display:block;font-size:13px;margin-top:8px;color:#bbb}
input,select,textarea{width:100%;box-sizing:border-box;font-size:17px;padding:9px;border-radius:6px;border:1px solid #444;background:#222;color:#fff}
.fila{display:flex;gap:8px}.fila>div{flex:1}
button{font-size:16px;padding:11px;border:0;border-radius:6px;margin-top:8px;width:100%;color:#fff;background:#357}
button.ok{background:#2a7a3a}button.mal{background:#a33}button.gris{background:#444;font-size:14px;padding:8px}
button:disabled{opacity:.4}
.tarj{border:1px solid #333;border-radius:8px;padding:10px;margin:10px 0;background:#161616}
.tarj.ok{border-color:#2a7a3a}
.med{border:2px solid #2a7a3a;border-radius:8px;padding:8px;margin-top:8px}
.aviso{background:#3a2a10;border:1px solid #a70;border-radius:6px;padding:8px;font-size:13px;margin:8px 0}
.err{background:#3a1515;border-color:#a33}
.peq{font-size:12px;color:#999}
table{border-collapse:collapse;width:100%;font-size:12px}
td,th{border-bottom:1px solid #333;padding:4px 3px;text-align:right}th:first-child,td:first-child{text-align:left}
.obs{color:#f77;text-decoration:line-through}
a{color:#9cf}code{color:#fc6}
</style></head><body>
<div id="cab">
 <div id="fila1"><div id="est">Conectando...</div><button id="paro" onclick="paro()">PARO</button></div>
 <div id="tabs"></div>
</div>
<main id="vista"></main>

<script>
// ---------- constantes ----------
var VERSION=1, KEYD="t1_doc", KEYO="t1_otro", MAXB=32768;
var MOV={
 adelante:{n:"Adelante",s:[1,1],g:"pwm",obj:100,tol:3,u:"cm",c:["avance_cm","desviacion_cm"],clave:"t_adelante",ini:2000},
 atras:{n:"Atrás",s:[-1,-1],g:"pwm",obj:100,tol:3,u:"cm",c:["avance_cm","desviacion_cm"],clave:"t_atras",ini:2000},
 giro_izq:{n:"Giro izquierda",s:[-1,1],g:"pwm_giro",obj:90,tol:5,u:"°",c:["angulo_deg"],clave:"t90",ini:500},
 giro_der:{n:"Giro derecha",s:[1,-1],g:"pwm_giro",obj:90,tol:5,u:"°",c:["angulo_deg"],clave:"t90d",ini:500},
 giro360:{n:"Giro 360° (izq.)",s:[-1,1],g:"pwm_giro",obj:360,tol:10,u:"°",c:["angulo_deg"],clave:"t360",ini:1800},
 ida_vuelta:{n:"Atrás (ida y vuelta)",s:[1,1],g:"pwm",c:["dist_origen_cm"]}
};
var MOVE2=["adelante","atras","giro_izq","giro_der","giro360"];
var MOVD=["adelante","ida_vuelta","giro_izq","giro_der","giro360"];
var CLAVES=["t_adelante","t_atras","t90","t90d","t360"];
var AYUDA={avance_cm:"Avance recorrido (cm, positivo)",desviacion_cm:"Desviación lateral (cm, + izquierda / − derecha)",
 angulo_deg:"Ángulo girado (°, positivo)",dist_origen_cm:"Distancia del final al punto de inicio (cm)"};
var ETAPAS=[["E0","E0 Medidas"],["E1","E1 Parte B"],["E2","E2 Tiempos"],["E2b","E2b Video"],["E3","E3 Parte D"],["E4","E4 Resultados"],["libre","Prueba libre"],["datos","Datos"]];
var COLS=["fecha","sesion","tipo","pwm_izq","pwm_der","ms","ms_real","trim_i","trim_d","avance_cm","desviacion_cm","angulo_deg","dist_origen_cm","voltaje","superficie","nota"];
var T95=[0,12.706,4.303,3.182,2.776,2.571,2.447,2.365,2.306,2.262,2.228,2.201,2.179,2.160,2.145,2.131,2.120,2.110,2.101,2.093,2.086,2.080,2.074,2.069,2.064,2.060,2.056,2.052,2.048,2.045,2.042];

// ---------- estado ----------
var D=null, cfg={}, est={}, tab="E0", U={}, pend=null, ocupado=false, otro=null;
var SESION=new Date().toISOString().replace(/[-:T]/g,"").slice(0,14);
var syncMsg="", guardando=false, otraVez=false, tmr=null;

function $(i){return document.getElementById(i)}
function isn(x){return typeof x==="number"&&isFinite(x)}
function num(s){var x=parseFloat(String(s).replace(",","."));return isNaN(x)?null:x}
function f1(x,d){return isn(x)?x.toFixed(d===undefined?1:d):"—"}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
function get(p){return fetch(p+(p.indexOf("?")<0?"?":"&")+"_="+Date.now()).then(function(r){return r.json()})}
function ls(k,d){try{var v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}}
function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
var tMsg=0;
function msg(t){tMsg=Date.now();$("est").textContent=t}
function u(el){U[el.dataset.k]=el.value}
function ui(k,d){return U[k]!==undefined?U[k]:(d===undefined?"":d)}
function mean(a){return a.length?a.reduce(function(x,y){return x+y},0)/a.length:null}
function sd(a){if(a.length<2)return null;var m=mean(a);return Math.sqrt(a.reduce(function(x,y){return x+(y-m)*(y-m)},0)/(a.length-1))}
function ic95(a){var s=sd(a);if(s===null)return null;var df=a.length-1;return (df<=30?T95[df]:1.96)*s/Math.sqrt(a.length)}
function nums(a){return (a||[]).filter(isn)}
function esc(s){return String(s===undefined||s===null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}

// ---------- documento ----------
function docNuevo(){
 return {version:VERSION,sig:0,
  fisicas:{L_cm:[],ejes_cm:[],diam_cm:[],v_reposo:null,v_carga:null},
  parteB:{izq:[65,70,70,70,70,70,70],der:[85,70,85,70,90,85,70],sentido_ok:true},
  calib:[],tiempos:{t_adelante:null,t_atras:null,t90:null,t90d:null,t360:null},
  parteD:[],video:{grabado:false},entregables:{fotos:false,diagrama:false,conclusiones:false},estado:{}};
}
function completar(d){
 var n=docNuevo();
 for(var k in n){if(d[k]===undefined)d[k]=n[k]}
 ["L_cm","ejes_cm","diam_cm"].forEach(function(k){if(!d.fisicas[k])d.fisicas[k]=[]});
 return d;
}
function puntaje(d){
 if(!d||!d.version)return -1;
 var p=(d.calib||[]).length+(d.parteD||[]).length;
 if(d.fisicas)["L_cm","ejes_cm","diam_cm"].forEach(function(k){p+=nums(d.fisicas[k]).length});
 if(d.parteB)p+=(d.parteB.izq||[]).length+(d.parteB.der||[]).length;
 if(d.tiempos)CLAVES.forEach(function(k){if(isn(d.tiempos[k]))p++});
 return p;
}
function tiempoRef(m){
 var t=D.tiempos;
 if(m==="ida_vuelta")return t.t_adelante+"/"+t.t_atras;
 return String(t[MOV[m].clave]);
}
function vig(m){return D.parteD.filter(function(r){return r.mov===m&&r.tref===tiempoRef(m)})}
function obsoletos(){return D.parteD.filter(function(r){return r.tref!==tiempoRef(r.mov)}).length}
function estados(){
 var f=D.fisicas,t=D.tiempos;
 var e0=nums(f.L_cm).length>=3&&isn(f.v_reposo)&&isn(f.v_carga);
 var e2=CLAVES.every(function(k){return isn(t[k])});
 var e3=e2&&MOVD.every(function(m){return vig(m).length>=3});
 var en=D.entregables;
 var e={E0:e0?"completa":"disponible",E1:"completa",E2:e2?"completa":"disponible",
  E2b:!e2?"bloqueada":(D.video.grabado?"completa":"disponible"),
  E3:!e2?"bloqueada":(e3?"completa":"disponible"),
  E4:(e0&&e3)?((en.fotos&&en.diagrama&&en.conclusiones&&D.video.grabado)?"completa":"disponible"):"bloqueada"};
 e.libre="disponible";e.datos="disponible";
 return e;
}
function falta(e){
 var f=D.fisicas;
 if(e==="E0"){var a=[];if(nums(f.L_cm).length<3)a.push("3 mediciones de L");if(!isn(f.v_reposo))a.push("voltaje en reposo");if(!isn(f.v_carga))a.push("voltaje con carga");return a.join(", ")}
 if(e==="E2"||e==="E2b"||e==="E3"){
  if(e==="E2")return CLAVES.filter(function(k){return !isn(D.tiempos[k])}).join(", ");
  if(estados().E2!=="completa")return "terminar E2 (aceptar los 5 tiempos)";
  if(e==="E3")return MOVD.map(function(m){return MOV[m].n+" "+vig(m).length+"/3"}).join(" · ");
  return D.video.grabado?"":"grabar el video";
 }
 if(e==="E4"){var a2=[];if(estados().E0!=="completa")a2.push("E0");if(estados().E3!=="completa")a2.push("E3");return a2.length?"terminar "+a2.join(" y "):""}
 return "";
}

// ---------- guardado ----------
function guardar(){
 D.estado=estados();
 lsSet(KEYD,D);
 clearTimeout(tmr);tmr=setTimeout(enviar,400);
}
async function enviar(){
 if(guardando){otraVez=true;return}
 guardando=true;
 try{
  var s=JSON.stringify(D);
  if(s.length>MAXB){syncMsg="⚠ El documento mide "+s.length+" B (> 32 KB): NO se guardó en el robot. Descarga el JSON y borra registros viejos.";guardando=false;barra();return}
  var r=await fetch("/t1/datos",{method:"POST",headers:{"Content-Type":"application/json"},body:s});
  var j=await r.json();
  syncMsg=j.ok?"✓ guardado en el robot ("+j.bytes+" B)":"⚠ el robot no guardó: "+(j.error||r.status);
 }catch(x){syncMsg="⚠ sin conexión: guardado solo en este celular"}
 guardando=false;barra();
 if(otraVez){otraVez=false;enviar()}
}
function barra(){var e=$("syncinfo");if(e)e.textContent=syncMsg}

async function cargar(){
 var local=ls(KEYD,null),rob=null;
 try{var r=await get("/t1/datos");if(r&&r.version)rob=r}catch(e){syncMsg="⚠ sin conexión con el robot"}
 var pr=puntaje(rob),pl=puntaje(local);
 var elegido=pr>=pl?rob:local;
 if(rob&&local&&JSON.stringify(rob)!==JSON.stringify(local)){
  otro=pr>=pl?local:rob;lsSet(KEYO,otro);
  syncMsg="Los datos del robot ("+pr+" registros) y del celular ("+pl+") eran distintos: se usó el de más registros. El otro quedó en 'Datos'.";
 }
 D=completar(elegido||docNuevo());
 guardar();
}

// ---------- movimiento ----------
async function esperar(max){
 var t0=Date.now();await sleep(300);
 while(Date.now()-t0<max*1000){
  var e=await get("/estado");
  if(!e.ocupado)return e;
  await sleep(200);
 }
 await get("/stop");throw new Error("El robot no terminó; se mandó PARO");
}
// Ejecuta un movimiento. ida_vuelta: va ms, pausa 500 ms y regresa ms2 (o ms).
async function correr(m,ms,ms2,pwmOver){
 cfg=await get("/config");
 var M=MOV[m],pwm=pwmOver||cfg[M.g],l=M.s[0]*pwm,r=M.s[1]*pwm;
 msg("Ejecutando "+M.n+" "+ms+" ms...");
 var x=await get("/move?l="+l+"&r="+r+"&ms="+ms);
 if(!x.ok)throw new Error("Rechazado: "+(x.error||""));
 var e=await esperar(ms/1000+15),res={l:l,r:r,ms_real:e.ultimo_ms_real,ti:cfg.trim_i,td:cfg.trim_d};
 if(m==="ida_vuelta"){
  var b=ms2||ms;msg("Regresando...");await sleep(500);
  x=await get("/move?l="+(-l)+"&r="+(-r)+"&ms="+b);
  if(!x.ok)throw new Error("Rechazado: "+(x.error||""));
  e=await esperar(b/1000+15);res.ms2=b;res.ms_real2=e.ultimo_ms_real;
 }
 return res;
}
function paro(){get("/stop");msg("PARO")}

async function lanzar(donde,m,ms,ms2,extra){
 if(ocupado||pend)return;
 var v=num(ui("volt"));
 ocupado=true;vista();
 try{
  var res=await correr(m,ms,ms2,extra&&extra.pwm);
  pend={donde:donde,mov:m,ms:ms,ms2:res.ms2,ms_real:res.ms_real,ms_real2:res.ms_real2,l:res.l,r:res.r,
   ti:res.ti,td:res.td,v:v,sup:ui("sup","piso"),nota:ui("nota"),fecha:new Date().toISOString().slice(0,19)};
  msg("Listo ("+res.ms_real+" ms reales). Captura la medición.");
 }catch(x){msg("Error: "+x.message)}
 ocupado=false;vista();
}
function formMed(donde,m){
 if(!pend||pend.donde!==donde||pend.mov!==m)return "";
 var h='<div class="med"><b>Medición</b> <span class="peq">('+pend.ms_real+' ms reales)</span>';
 MOV[m].c.forEach(function(c){h+='<label>'+AYUDA[c]+'</label><input id="m_'+c+'" type="text" inputmode="decimal">'});
 return h+'<button class="ok" onclick="guardarMed()">Guardar</button><button class="gris" onclick="descartar()">Descartar y repetir</button></div>';
}
function guardarMed(){
 if(!pend)return;
 var M=MOV[pend.mov],med={};
 for(var i=0;i<M.c.length;i++){
  var v=num($("m_"+M.c[i]).value);
  if(v===null){msg("Falta: "+AYUDA[M.c[i]]);return}
  med[M.c[i]]=v;
 }
 var e={id:++D.sig,fecha:pend.fecha,mov:pend.mov,ms:pend.ms,ms_real:pend.ms_real,pwm_l:pend.l,pwm_r:pend.r,voltaje:pend.v,medido:med};
 if(pend.ti!==1&&pend.ti!==undefined)e.ti=pend.ti;
 if(pend.td!==1&&pend.td!==undefined)e.td=pend.td;
 if(pend.ms2){e.ms2=pend.ms2;e.ms_real2=pend.ms_real2}
 if(pend.donde==="E3"){e.rep=vig(pend.mov).length+1;e.tref=tiempoRef(pend.mov);D.parteD.push(e)}
 else{e.etapa=pend.donde;if(pend.sup&&pend.sup!=="piso")e.sup=pend.sup;if(pend.nota)e.nota=pend.nota;D.calib.push(e)}
 if(isn(pend.v))U.volt=String(pend.v);
 pend=null;guardar();msg("Guardada.");vista();
}
function descartar(){pend=null;msg("Descartada. Repite.");vista()}

// ---------- E0 ----------
function stat(a){a=nums(a);return a.length?f1(mean(a),2)+" ± "+f1(sd(a),2)+" (n="+a.length+")":"—"}
function viewE0(){
 var f=D.fisicas,h="<h2>E0 · Medidas físicas</h2><p class='peq'>Mide 3 veces cada una con regla o calibrador. Faltan: "+esc(falta("E0")||"nada")+".</p>";
 [["L_cm","L: distancia entre llantas izquierda y derecha (cm, centro a centro)"],["ejes_cm","Distancia entre ejes (cm)"],["diam_cm","Diámetro de llanta (cm)"]].forEach(function(p){
  h+="<h3>"+p[1]+"</h3><div class='fila'>";
  for(var i=0;i<3;i++)h+="<div><input type='text' inputmode='decimal' data-f='"+p[0]+"' data-i='"+i+"' value='"+(isn(f[p[0]][i])?f[p[0]][i]:"")+"' onchange='fis(this)'></div>";
  h+="</div><div class='peq'>"+stat(f[p[0]])+"</div>";
 });
 h+="<h3>Voltaje (V)</h3><div class='fila'><div><label>En reposo</label><input type='text' inputmode='decimal' data-f='v_reposo' value='"+(isn(f.v_reposo)?f.v_reposo:"")+"' onchange='fis(this)'></div>"+
  "<div><label>Con motores girando</label><input type='text' inputmode='decimal' data-f='v_carga' value='"+(isn(f.v_carga)?f.v_carga:"")+"' onchange='fis(this)'></div></div>"+
  "<button onclick='aire()' "+(ocupado?"disabled":"")+">Girar en el aire 3 s (PWM 140)</button><p class='peq'>Pon el robot con las llantas en el aire y mide el voltaje con el multímetro mientras gira.</p>";
 return h;
}
function fis(el){
 var k=el.dataset.f,v=num(el.value);
 if(el.dataset.i!==undefined){var i=+el.dataset.i,a=D.fisicas[k];while(a.length<=i)a.push(null);a[i]=v;D.fisicas[k]=a}
 else D.fisicas[k]=v;
 guardar();vista();
}
async function aire(){
 if(ocupado)return;ocupado=true;vista();
 try{var x=await get("/move?l=140&r=140&ms=3000");msg(x.ok?"Girando 3 s...":"Rechazado: "+(x.error||""));await esperar(20)}catch(e){msg("Error: "+e.message)}
 ocupado=false;vista();
}

// ---------- E1 ----------
function viewE1(){
 var b=D.parteB,h="<h2>E1 · Parte B (completa)</h2><table><tr><th>Lado</th><th>Valores (orden)</th><th>Media ± DE</th><th>IC95</th></tr>";
 [["izq","Izquierdo"],["der","Derecho"]].forEach(function(p){
  var a=nums(b[p[0]]),ic=ic95(a);
  h+="<tr><td>"+p[1]+"</td><td>"+a.join(" / ")+"</td><td>"+f1(mean(a))+" ± "+f1(sd(a))+"</td><td>"+(ic===null?"—":f1(mean(a)-ic)+"–"+f1(mean(a)+ic))+"</td></tr>";
 });
 h+="</table><p class='peq'>Sentido de los motores correcto: "+(b.sentido_ok?"sí":"no")+".</p>"+
  "<div class='tarj'>Texto fijo de <code>REPORTE.md</code> §6.1 (n = 7 por lado): t de Welch t = 2.92, gl ≈ 6.5, p = 0.024; Mann-Whitney U = 40, p = 0.025. El lado derecho tiene más fricción estática (arranca con PWM 70 u 85–90). Estos dos contrastes no se recalculan si se agregan valores.</div>"+
  "<h3>Repetir la rampa</h3><div class='fila'><div><button onclick=\"rampa('I')\">Rampa izquierda</button></div><div><button onclick=\"rampa('D')\">Rampa derecha</button></div></div>"+
  "<button class='ok' onclick='rampaOk()'>OK: giran las dos llantas</button>"+
  "<div class='fila'><div><label>Lado</label><select data-k='bl' onchange='u(this)'><option value='izq'"+(ui('bl')==='der'?'':' selected')+">Izquierdo</option><option value='der'"+(ui('bl')==='der'?' selected':'')+">Derecho</option></select></div>"+
  "<div><label>PWM mínimo</label><input data-k='bv' type='text' inputmode='numeric' value='"+esc(ui('bv'))+"' oninput='u(this)'></div></div>"+
  "<div class='fila'><div><button class='gris' onclick='traerMin()'>Traer del robot</button></div><div><button class='ok' onclick='agregarB()'>Agregar valor</button></div></div>";
 return h;
}
async function rampa(l){try{var x=await get("/pwmmin?lado="+l);msg(x.ok?"Rampa "+l+": escribe OK cuando giren las dos llantas":"Rechazado: "+(x.error||""))}catch(e){msg("Error: "+e.message)}}
async function rampaOk(){try{await get("/pwmmin_ok");msg("Marcado OK");}catch(e){msg("Error: "+e.message)}}
async function traerMin(){
 try{var e=await get("/estado"),k=ui("bl","izq")==="der"?e.pwm_min_der:e.pwm_min_izq;
  if(k>0){U.bv=String(k);vista()}else msg("El robot no tiene un valor de ese lado")}catch(x){msg("Error: "+x.message)}
}
function agregarB(){
 var v=num(ui("bv"));if(v===null||v<=0){msg("PWM inválido");return}
 D.parteB[ui("bl","izq")].push(Math.round(v));U.bv="";guardar();vista();
}

// ---------- E2 ----------
function intentos(m){return D.calib.filter(function(c){return c.etapa==="E2"&&c.mov===m})}
function medidoP(c,m){return c.medido[MOV[m].c[0]]}
function ajuste(m){
 var at=intentos(m).filter(function(c){return isn(medidoP(c,m))}),xs=at.map(function(c){return c.ms}),ys=at.map(function(c){return medidoP(c,m)});
 var dist={};xs.forEach(function(x){dist[x]=1});
 if(Object.keys(dist).length<2)return null;
 var mx=mean(xs),my=mean(ys),sxx=0,sxy=0,syy=0;
 for(var i=0;i<xs.length;i++){sxx+=(xs[i]-mx)*(xs[i]-mx);sxy+=(xs[i]-mx)*(ys[i]-my);syy+=(ys[i]-my)*(ys[i]-my)}
 var a=sxy/sxx,b=my-a*mx;return {a:a,b:b,r2:syy>0?sxy*sxy/(sxx*syy):1}
}
function sugerido(m){
 var M=MOV[m],at=intentos(m),base=isn(cfg[M.clave])?cfg[M.clave]:M.ini;
 if(!at.length)return base;
 var aj=ajuste(m),t;
 if(aj&&aj.a>0)t=(M.obj-aj.b)/aj.a;
 else{var l=at[at.length-1],med=medidoP(l,m);if(!(med>0))return l.ms;t=l.ms*M.obj/med}
 return Math.max(50,Math.round(t/10)*10);
}
function converge(m){
 var M=MOV[m],at=intentos(m);if(at.length<2)return false;
 var a=at[at.length-1],b=at[at.length-2];
 return a.ms===b.ms&&[a,b].every(function(c){return Math.abs(medidoP(c,m)-M.obj)<=M.tol});
}
function viewE2(){
 var h="<h2>E2 · Parte C: calibrar tiempos</h2><p class='peq'>Ejecuta, mide y repite hasta que 2 ejecuciones seguidas con la misma duración caigan en la tolerancia. Luego acepta el tiempo.</p>"+
  "<label>Voltaje de la batería/fuente (V)</label><input data-k='volt' type='text' inputmode='decimal' value='"+esc(ui('volt'))+"' oninput='u(this)'>"+
  "<label>Superficie</label><input data-k='sup' type='text' value='"+esc(ui('sup','piso'))+"' oninput='u(this)'>";
 MOVE2.forEach(function(m){
  var M=MOV[m],acc=D.tiempos[M.clave],at=intentos(m),aj=ajuste(m),sug=sugerido(m);
  h+="<div class='tarj"+(isn(acc)?" ok":"")+"'><b>"+M.n+"</b> · objetivo "+M.obj+" "+M.u+" ± "+M.tol+" · clave <code>"+M.clave+"</code>";
  if(isn(acc)){
   h+="<div>✓ Aceptado: <b>"+acc+" ms</b></div><button class='gris' onclick=\"reabrir('"+m+"')\">Reabrir</button>";
  }else{
   h+="<label>Duración (ms)</label><input data-k='ms_"+m+"' type='text' inputmode='numeric' value='"+esc(ui('ms_'+m,sug))+"' oninput='u(this)'>"+
    "<button class='ok' "+((ocupado||pend)?"disabled":"")+" onclick=\"ejecutarE2('"+m+"')\">Ejecutar (robot en la marca)</button>"+formMed("E2",m);
   if(aj)h+="<div class='peq'>Regresión: medido = "+aj.a.toFixed(4)+"·t + "+aj.b.toFixed(2)+" · R² = "+aj.r2.toFixed(3)+(aj.r2<0.9?" ⚠ R² < 0.9: comparte la tabla (Datos) en el chat":"")+"</div>";
   h+="<div class='peq'>Siguiente duración sugerida: <b>"+sug+" ms</b></div>";
   if(at.length>=6&&!converge(m))h+="<div class='aviso'>6 intentos sin converger: exporta los datos (Datos) y compártelos en el chat.</div>";
   h+="<button class='ok' "+(converge(m)?"":"disabled")+" onclick=\"aceptar('"+m+"')\">Aceptar tiempo</button>";
  }
  if(at.length){
   h+="<table><tr><th>#</th><th>ms</th><th>Medido</th><th>Error</th><th>V</th></tr>";
   at.forEach(function(c,i){var md=medidoP(c,m);h+="<tr><td>"+(i+1)+"</td><td>"+c.ms+"</td><td>"+f1(md)+"</td><td>"+f1(md-M.obj)+"</td><td>"+(isn(c.voltaje)?c.voltaje:"")+"</td></tr>"});
   h+="</table>";
  }
  h+="</div>";
 });
 return h;
}
function ejecutarE2(m){
 var ms=parseInt(ui("ms_"+m,sugerido(m)));
 if(!(ms>0)){msg("Revisa la duración");return}
 lanzar("E2",m,ms);
}
async function aceptar(m){
 var M=MOV[m],at=intentos(m),ms=at[at.length-1].ms;
 if(D.parteD.some(function(r){return r.mov===m||(m==="atras"&&r.mov==="ida_vuelta")||(m==="adelante"&&r.mov==="ida_vuelta")})&&!confirm("Ya hay repeticiones de la Parte D con el tiempo anterior; quedarán obsoletas. ¿Aceptar?"))return;
 try{
  var x=await get("/config?"+M.clave+"="+ms);
  if(x[M.clave]===undefined&&x.pwm===undefined){msg("El robot rechazó el valor");return}
  D.tiempos[M.clave]=ms;guardar();msg(M.clave+" = "+ms+" ms guardado en el robot");vista();
 }catch(e){msg("Error: "+e.message)}
}
function reabrir(m){
 var M=MOV[m];
 if(D.parteD.length&&!confirm("Reabrir este tiempo dejará obsoletas las repeticiones de la Parte D que lo usan. ¿Seguir?"))return;
 D.tiempos[M.clave]=null;guardar();vista();
}

// ---------- E2b ----------
function viewE2b(){
 return "<h2>E2b · Secuencia para el video</h2><p>Graba con el celular el robot, el piso y el monitor serie de la laptop (115200 baudios, con las etiquetas). La secuencia usa los tiempos aceptados en E2.</p>"+
  "<button class='ok' "+(ocupado?"disabled":"")+" onclick='secuencia()'>Ejecutar secuencia</button>"+
  "<label style='display:flex;gap:8px;align-items:center'><input type='checkbox' style='width:auto' "+(D.video.grabado?"checked":"")+" onchange='D.video.grabado=this.checked;guardar();vista()'> Video grabado</label>"+
  "<p class='peq'>No bloquea E3; solo cuenta para la lista de entregables de E4.</p>";
}
async function secuencia(){
 if(ocupado)return;
 try{var x=await get("/seq");msg(x.ok?"Secuencia en curso...":"Rechazado: "+(x.error||""))}catch(e){msg("Error: "+e.message)}
}

// ---------- E3 ----------
function viewE3(){
 var h="<h2>E3 · Parte D: 3 repeticiones</h2><p class='peq'>Usa solo los tiempos aceptados en E2. Para cambiarlos, reabre el tiempo en E2.</p>",
  ob=obsoletos();
 if(ob)h+="<div class='aviso err'>"+ob+" repetición(es) obsoleta(s): se hicieron con un tiempo que ya cambió y no cuentan. Bórralas en Datos o repítelas.</div>";
 var vv=aviso05();if(vv)h+="<div class='aviso'>"+vv+"</div>";
 h+="<label>Voltaje de la batería/fuente (V)</label><input data-k='volt' type='text' inputmode='decimal' value='"+esc(ui('volt'))+"' oninput='u(this)'>";
 MOVD.forEach(function(m){
  var M=MOV[m],rs=vig(m),n=rs.length,tm=m==="ida_vuelta"?(D.tiempos.t_adelante+" + pausa 500 + "+D.tiempos.t_atras):(D.tiempos[M.clave]);
  h+="<div class='tarj"+(n>=3?" ok":"")+"'><b>"+M.n+"</b> · "+n+"/3 · tiempo "+tm+" ms";
  h+="<button class='ok' "+((ocupado||pend||n>=3)?"disabled":"")+" onclick=\"ejecutarE3('"+m+"')\">Ejecutar repetición "+Math.min(n+1,3)+"</button>"+formMed("E3",m);
  if(rs.length){
   h+="<table><tr><th>Rep</th><th>Medido</th><th>V</th><th></th></tr>";
   rs.forEach(function(r){h+="<tr><td>"+r.rep+"</td><td>"+MOV[m].c.map(function(c){return f1(r.medido[c])}).join(" / ")+"</td><td>"+(isn(r.voltaje)?r.voltaje:"")+"</td><td><button class='gris' style='width:auto;margin:0;padding:3px 8px' onclick='borrarD("+r.id+")'>×</button></td></tr>"});
   h+="</table>";
  }
  h+="</div>";
 });
 return h;
}
function ejecutarE3(m){
 var t=D.tiempos,ms=m==="ida_vuelta"?t.t_adelante:t[MOV[m].clave],ms2=m==="ida_vuelta"?t.t_atras:undefined;
 lanzar("E3",m,ms,ms2);
}
function borrarD(id){
 var r=D.parteD.filter(function(x){return x.id===id})[0];if(!r)return;
 if(!confirm("¿Borrar la repetición de "+MOV[r.mov].n+" (rep. "+r.rep+")?"))return;
 D.parteD=D.parteD.filter(function(x){return x.id!==id});
 MOVD.forEach(function(m){vig(m).forEach(function(x,i){x.rep=i+1})});
 guardar();vista();
}
function aviso05(){
 var v2=[],v3=nums(D.parteD.filter(function(r){return r.tref===tiempoRef(r.mov)}).map(function(r){return r.voltaje}));
 MOVE2.forEach(function(m){var at=intentos(m);if(at.length&&isn(at[at.length-1].voltaje))v2.push(at[at.length-1].voltaje)});
 if(v2.length&&v3.length&&Math.abs(mean(v2)-mean(v3))>0.5)return "El voltaje medio cambió "+f1(Math.abs(mean(v2)-mean(v3)),2)+" V entre E2 ("+f1(mean(v2),2)+" V) y E3 ("+f1(mean(v3),2)+" V). Los tiempos pueden haber dejado de valer: considera recalibrar.";
 return "";
}

// ---------- E4 ----------
function calc(){
 var f=D.fisicas,t=D.tiempos,r={},L=mean(nums(f.L_cm));
 function med(m,c){return mean(nums(vig(m).map(function(x){return x.medido[c]})))}
 var av=med("adelante","avance_cm"),msr=mean(nums(vig("adelante").map(function(x){return x.ms_real})));
 r.L=L;r.v=(isn(av)&&isn(msr)&&msr>0)?av/(msr/1000):null;
 r.wi=isn(med("giro_izq","angulo_deg"))?med("giro_izq","angulo_deg")/(t.t90/1000):null;
 r.wd=isn(med("giro_der","angulo_deg"))?med("giro_der","angulo_deg")/(t.t90d/1000):null;
 r.w360=isn(med("giro360","angulo_deg"))?med("giro360","angulo_deg")/(t.t360/1000):null;
 r.t90teo=(isn(L)&&isn(r.v))?Math.PI*L/(4*r.v):null;
 r.Lef=(isn(r.v)&&isn(r.wi)&&r.wi>0)?2*r.v/(r.wi*Math.PI/180):null;
 r.der=(isn(r.Lef)&&isn(L))?r.Lef/L:null;
 r.err=[];
 [["adelante","Adelante","avance_cm",100,"cm"],["ida_vuelta","Atrás (dist. al origen)","dist_origen_cm",0,"cm"],["giro_izq","Izquierda","angulo_deg",90,"°"],["giro_der","Derecha","angulo_deg",90,"°"],["giro360","360°","angulo_deg",360,"°"]].forEach(function(p){
  var a=nums(vig(p[0]).map(function(x){return x.medido[p[2]]})),m=mean(a);
  r.err.push({mov:p[0],n:p[1],a:a,m:m,obj:p[3],u:p[4],e:isn(m)?m-p[3]:null,pc:(isn(m)&&p[3]!==0)?(m-p[3])/p[3]*100:null});
 });
 r.desv=nums(vig("adelante").map(function(x){return x.medido.desviacion_cm}));
 var vc=f.v_carga;
 r.vm=function(pwm){return isn(vc)&&isn(pwm)?pwm/255*(vc-2):null};
 return r;
}
function viewE4(){
 var c=calc(),en=D.entregables,h="<h2>E4 · Resultados</h2>";
 var vv=aviso05();if(vv)h+="<div class='aviso'>"+vv+"</div>";
 h+="<table><tr><th>Magnitud</th><th>Valor</th></tr>"+
  "<tr><td>L (media E0)</td><td>"+f1(c.L,2)+" cm</td></tr>"+
  "<tr><td>v = avance / tiempo real</td><td>"+f1(c.v,2)+" cm/s</td></tr>"+
  "<tr><td>ω izquierda</td><td>"+f1(c.wi,1)+" °/s</td></tr>"+
  "<tr><td>ω derecha</td><td>"+f1(c.wd,1)+" °/s</td></tr>"+
  "<tr><td>ω 360°</td><td>"+f1(c.w360,1)+" °/s</td></tr>"+
  "<tr><td>t90 teórico = π·L/(4v)</td><td>"+(isn(c.t90teo)?f1(c.t90teo*1000,0)+" ms (medido "+D.tiempos.t90+" ms)":"—")+"</td></tr>"+
  "<tr><td>L efectiva = 2v/ω</td><td>"+f1(c.Lef,2)+" cm</td></tr>"+
  "<tr><td>Factor de derrape L_ef/L</td><td>"+f1(c.der,2)+"</td></tr>"+
  "<tr><td>Voltaje medio al motor (adelante)</td><td>"+f1(c.vm(cfg.pwm),2)+" V</td></tr>"+
  "<tr><td>Voltaje medio al motor (giros)</td><td>"+f1(c.vm(cfg.pwm_giro),2)+" V</td></tr></table>"+
  "<h3>Error por movimiento</h3><table><tr><th>Movimiento</th><th>Media</th><th>Error</th><th>%</th></tr>";
 c.err.forEach(function(e){h+="<tr><td>"+e.n+"</td><td>"+f1(e.m)+" "+e.u+"</td><td>"+f1(e.e)+"</td><td>"+(e.pc===null?"—":f1(e.pc))+"</td></tr>"});
 h+="</table><p class='peq'>Desviación lateral media (adelante): "+f1(mean(c.desv),1)+" cm.</p>"+
  "<h3>Entregables</h3>"+
  chk("Video grabado (E2b)",D.video.grabado,"D.video.grabado")+chk("Fotos",en.fotos,"D.entregables.fotos")+chk("Diagrama de conexiones dibujado",en.diagrama,"D.entregables.diagrama")+chk("Conclusiones escritas",en.conclusiones,"D.entregables.conclusiones")+
  "<button class='ok' onclick='copiarMd()'>Copiar Markdown</button>"+
  "<button onclick=\"bajar('json')\">Descargar JSON</button><button onclick=\"bajar('csv')\">Descargar CSV</button>"+
  "<textarea id='md' rows='10' style='display:none;font-size:11px'></textarea>";
 return h;
}
function chk(t,v,ref){return "<label style='display:flex;gap:8px;align-items:center'><input type='checkbox' style='width:auto' "+(v?"checked":"")+" onchange='"+ref+"=this.checked;guardar();vista()'> "+t+"</label>"}
function markdown(){
 var c=calc(),t=D.tiempos,s="### 6.2 Parte C – Rutinas de movimiento\n\n| # | Movimiento | PWM izq / der | Duración inicial | Duración calibrada |\n|---|---|---|---|---|\n";
 MOVE2.forEach(function(m,i){
  var M=MOV[m],p=cfg[M.g]||140;
  s+="| "+(i+1)+" | "+M.n+" | "+(M.s[0]>0?"+":"−")+p+" / "+(M.s[1]>0?"+":"−")+p+" | "+M.ini+" ms | "+t[M.clave]+" ms |\n";
 });
 s+="\n### 6.3 Parte D – Calibración y medición (3 repeticiones)\n\n| Movimiento | Tiempo (ms) | Resultado esperado | Medido (rep. 1 / 2 / 3) | Promedio | Error |\n|---|---|---|---|---|---|\n";
 function rep(m,cs,sep){return vig(m).map(function(r){return cs.map(function(k){return f1(r.medido[k])}).join(sep)}).join(" / ")}
 s+="| Adelante | "+t.t_adelante+" | Línea recta de 1 m | Avance: "+rep("adelante",["avance_cm"],"")+" cm; desviación lateral: "+rep("adelante",["desviacion_cm"],"")+" cm | "+f1(c.err[0].m)+" cm (desv. "+f1(mean(c.desv))+" cm) | "+f1(c.err[0].e)+" cm |\n";
 s+="| Atrás | "+t.t_atras+" | Regreso al punto de inicio | Distancia al origen: "+rep("ida_vuelta",["dist_origen_cm"],"")+" cm | "+f1(c.err[1].m)+" cm | "+f1(c.err[1].e)+" cm |\n";
 [["giro_izq","Izquierda",t.t90,2,"90°"],["giro_der","Derecha",t.t90d,3,"90°"],["giro360","360°",t.t360,4,"360°"]].forEach(function(p){
  var e=c.err[p[3]];s+="| "+p[1]+" | "+p[2]+" | "+p[4]+" | "+rep(p[0],["angulo_deg"],"")+" ° | "+f1(e.m)+"° | "+f1(e.e)+"° ("+f1(e.pc)+" %) |\n";
 });
 s+="\n### Valores de la Parte E\n\n- L = "+f1(c.L,2)+" cm; v = "+f1(c.v,2)+" cm/s\n- ω izquierda = "+f1(c.wi,1)+" °/s; ω derecha = "+f1(c.wd,1)+" °/s; ω 360° = "+f1(c.w360,1)+" °/s\n"+
  "- t90 teórico = "+(isn(c.t90teo)?f1(c.t90teo*1000,0):"—")+" ms contra "+t.t90+" ms medidos\n- L efectiva = "+f1(c.Lef,2)+" cm; factor de derrape = "+f1(c.der,2)+"\n"+
  "- Voltaje de la batería: "+f1(D.fisicas.v_reposo,2)+" V en reposo, "+f1(D.fisicas.v_carga,2)+" V con carga\n- Desviación lateral media en 1 m: "+f1(mean(c.desv),1)+" cm\n";
 return s;
}
function copiarMd(){
 var ta=$("md");ta.style.display="block";ta.value=markdown();ta.select();
 var ok=false;try{ok=document.execCommand("copy")}catch(e){}
 msg(ok?"Markdown copiado":"Selecciona el texto y cópialo");
}
function csvFilas(){
 var f=[];
 function fila(e,tipo,nota){
  var o={fecha:e.fecha,sesion:SESION,tipo:tipo,pwm_izq:e.pwm_l,pwm_der:e.pwm_r,ms:e.ms,ms_real:e.ms_real,trim_i:e.ti===undefined?1:e.ti,trim_d:e.td===undefined?1:e.td,
   voltaje:e.voltaje,superficie:e.sup||"piso",nota:nota};
  for(var k in e.medido)o[k]=e.medido[k];
  f.push(o);
 }
 D.calib.forEach(function(e){fila(e,e.mov==="giro360"?"giro_izq":e.mov,(e.nota||"")+(e.etapa==="E2"?" E2":""))});
 D.parteD.forEach(function(e){fila(e,e.mov==="giro360"?"giro_izq":e.mov,"parteD rep "+e.rep+(e.tref===tiempoRef(e.mov)?"":" obsoleta"))});
 return f;
}
function csvTexto(){
 var s=COLS.join(",")+"\n";
 csvFilas().forEach(function(o){s+=COLS.map(function(c){var v=o[c];if(v===undefined||v===null)v="";v=String(v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}).join(",")+"\n"});
 return s;
}
function bajar(tipo){
 var txt=tipo==="json"?JSON.stringify(D,null,1):csvTexto(),b=new Blob([txt],{type:tipo==="json"?"application/json":"text/csv"}),a=document.createElement("a");
 a.href=URL.createObjectURL(b);a.download="tarea1_"+SESION+"."+tipo;document.body.appendChild(a);a.click();a.remove();
}

// ---------- Prueba libre ----------
function viewLibre(){
 var t=ui("lt","adelante"),M=MOV[t],h="<h2>Prueba libre</h2><p class='peq'>Un movimiento suelto con cualquier duración y PWM. Un giro de 360° es «Giro 360°». Se guarda en los datos con las columnas de <code>calibrar.py</code>.</p>"+
  "<label>Tipo</label><select data-k='lt' onchange='u(this);vista()'>"+["adelante","atras","giro_izq","giro_der","giro360","ida_vuelta"].map(function(k){return "<option value='"+k+"'"+(k===t?" selected":"")+">"+MOV[k].n+"</option>"}).join("")+"</select>"+
  "<div class='fila'><div><label>Duración (ms)</label><input data-k='lms' type='text' inputmode='numeric' value='"+esc(ui('lms','2000'))+"' oninput='u(this)'></div>"+
  "<div><label>PWM</label><input data-k='lpwm' type='text' inputmode='numeric' value='"+esc(ui('lpwm',cfg[M.g]||140))+"' oninput='u(this)'></div></div>"+
  "<div class='fila'><div><label>Voltaje (V)</label><input data-k='volt' type='text' inputmode='decimal' value='"+esc(ui('volt'))+"' oninput='u(this)'></div>"+
  "<div><label>Superficie</label><input data-k='sup' type='text' value='"+esc(ui('sup','piso'))+"' oninput='u(this)'></div></div>"+
  "<label>Nota</label><input data-k='nota' type='text' value='"+esc(ui('nota'))+"' oninput='u(this)'>"+
  "<button class='ok' "+((ocupado||pend)?"disabled":"")+" onclick='ejecutarLibre()'>Ejecutar (robot en la marca)</button>"+formMed("libre",t);
 var n=D.calib.filter(function(c){return c.etapa==="libre"}).length;
 return h+"<p class='peq'>"+n+" pruebas libres guardadas (ver «Datos»).</p>";
}
function ejecutarLibre(){
 var t=ui("lt","adelante"),ms=parseInt(ui("lms","2000")),pwm=parseInt(ui("lpwm",cfg[MOV[t].g]||140));
 if(!(ms>0)||!(pwm>0)){msg("Revisa duración y PWM");return}
 lanzar("libre",t,ms,undefined,{pwm:pwm});
}

// ---------- Datos ----------
function todos(){
 var f=[];
 D.calib.forEach(function(c){f.push({k:"calib",c:c,etq:c.etapa||"libre"})});
 D.parteD.forEach(function(c){f.push({k:"parteD",c:c,etq:"E3 rep "+c.rep+(c.tref===tiempoRef(c.mov)?"":" (obsoleta)")})});
 f.sort(function(a,b){return a.c.id-b.c.id});
 return f;
}
function viewDatos(){
 var s=JSON.stringify(D).length,fs=todos();
 var h="<h2>Datos</h2><div class='peq'>Documento: "+s+" B de 32768 · <span id='syncinfo'>"+esc(syncMsg)+"</span></div>"+
  "<h3>Registros ("+fs.length+")</h3><div style='overflow-x:auto'><table><tr><th>#</th><th>Etapa</th><th>Mov</th><th>ms</th><th>Medido</th><th>V</th><th></th></tr>";
 fs.forEach(function(x){var c=x.c;h+="<tr><td>"+c.id+"</td><td>"+esc(x.etq)+"</td><td>"+esc(MOV[c.mov].n)+"</td><td>"+c.ms+"</td><td>"+Object.keys(c.medido).map(function(k){return f1(c.medido[k])}).join(" / ")+"</td><td>"+(isn(c.voltaje)?c.voltaje:"")+"</td><td><button class='gris' style='width:auto;margin:0;padding:3px 8px' onclick=\"borrarReg('"+x.k+"',"+c.id+")\">×</button></td></tr>"});
 h+="</table></div><p class='peq'>Tiempos aceptados: "+CLAVES.map(function(k){return k+"="+(isn(D.tiempos[k])?D.tiempos[k]:"—")}).join(" · ")+"</p>"+
  "<button onclick=\"bajar('json')\">Descargar JSON</button><button onclick=\"bajar('csv')\">Descargar CSV</button>"+
  "<label>Importar JSON (reemplaza todo)</label><input type='file' accept='.json,application/json' onchange='importar(this)'>"+
  "<button class='gris' onclick='verRespaldo()'>Ver respaldo del robot (/t1/respaldo)</button>"+
  (otro?"<button class='gris' onclick='bajarOtro()'>Descargar los datos que no se usaron (n="+puntaje(otro)+")</button>":"")+
  "<textarea id='resp' rows='8' style='display:none;font-size:11px'></textarea>";
 return h;
}
function borrarReg(k,id){
 if(!confirm("¿Borrar el registro #"+id+"? No se puede deshacer."))return;
 D[k]=D[k].filter(function(x){return x.id!==id});
 MOVD.forEach(function(m){vig(m).forEach(function(x,i){x.rep=i+1})});
 guardar();vista();
}
function importar(el){
 var fl=el.files[0];if(!fl)return;
 var r=new FileReader();r.onload=function(){
  try{var d=JSON.parse(r.result);if(!d.version)throw new Error("no tiene version");
   if(!confirm("¿Reemplazar TODOS los datos por los del archivo ("+puntaje(d)+" registros)?"))return;
   D=completar(d);guardar();vista();msg("Importado")}catch(e){msg("Archivo inválido: "+e.message)}
 };r.readAsText(fl);
}
async function verRespaldo(){
 try{var r=await fetch("/t1/respaldo"),t=await r.text(),ta=$("resp");ta.style.display="block";ta.value=t}catch(e){msg("Error: "+e.message)}
}
function bajarOtro(){
 var b=new Blob([JSON.stringify(otro,null,1)],{type:"application/json"}),a=document.createElement("a");
 a.href=URL.createObjectURL(b);a.download="tarea1_otro_"+SESION+".json";document.body.appendChild(a);a.click();a.remove();
}

// ---------- interfaz ----------
var VISTAS={E0:viewE0,E1:viewE1,E2:viewE2,E2b:viewE2b,E3:viewE3,E4:viewE4,libre:viewLibre,datos:viewDatos};
function vista(){
 if(!D)return;
 est=estados();
 var tb="";
 ETAPAS.forEach(function(p){tb+="<button class='"+est[p[0]]+(p[0]===tab?" sel":"")+"' onclick=\"ir('"+p[0]+"')\">"+p[1]+"</button>"});
 $("tabs").innerHTML=tb;
 var h="";
 if(est[tab]==="bloqueada")h="<h2>"+tab+" bloqueada</h2><div class='aviso'>Falta: "+esc(falta(tab))+".</div>";
 else{
  h=VISTAS[tab]();
  if(tab!=="datos"&&tab!=="libre"&&tab!=="E1"&&syncMsg)h+="<p class='peq'>"+esc(syncMsg)+"</p>";
 }
 var y=window.scrollY;$("vista").innerHTML=h;window.scrollTo(0,y);
 var m=document.querySelector("[id^=m_]");if(m&&document.activeElement===document.body)m.focus();
}
function ir(t){if(est[t]==="bloqueada"&&t!=="datos"){tab=t;vista();return}tab=t;vista();window.scrollTo(0,0)}

async function sondeo(){
 try{
  var e=await get("/estado");
  if(!ocupado&&Date.now()-tMsg>8000)$("est").textContent=(e.ocupado?"OCUPADO":"LIBRE")+" · "+(e.ultimo||"");
 }catch(x){msg("Sin conexión con el robot")}
 setTimeout(sondeo,3000);
}
(async function(){
 try{cfg=await get("/config")}catch(e){}
 await cargar();
 vista();sondeo();
 if(location.hash==="#libre")ir("libre");
 if(syncMsg&&syncMsg.indexOf("eran distintos")>=0)alert(syncMsg);
})();
</script></body></html>)rawliteral";
