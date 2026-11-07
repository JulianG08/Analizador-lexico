# -*- coding: utf-8 -*-
"""
Módulo: generar_documento_final.py
Descripción: Genera el PDF entregable de la ENTREGA FINAL.

Produce la gramática ampliada completa con la convención de colores que pide
el enunciado:

    ROJO         reglas originales de la gramática (producción sintáctica)
    FONDO ÁMBAR  reglas semánticas (atributos, restricciones, validación)
    AZUL         reglas de traducción orientada por la sintaxis (SDT)

Reutiliza el motor del documento del Quiz 4 (`generar_documento_semantico`):
la extracción de las producciones BNF desde el archivo de gramática, las ocho
reglas semánticas y la conversión a PDF. Sobre eso añade la capa SDT.

Ejecutar:  python generar_documento_final.py
Salida:    gramatica_ampliada_final.html  y  gramatica_ampliada_final.pdf
"""

from __future__ import annotations

import html
import shutil
import subprocess
import time
from pathlib import Path

from generar_documento_semantico import (
    REGLAS_SEMANTICAS,
    extraer_bloques_gramatica,
    _es_produccion,
    _producciones_definidas,
    NAVEGADORES,
)
from reglas_sdt import REGLAS_SDT

RAIZ = Path(__file__).parent
HTML_SALIDA = RAIZ / "gramatica_ampliada_final.html"
PDF_SALIDA = RAIZ / "gramatica_ampliada_final.pdf"


# =============================================================================
#  RENDERIZADO DE LAS CAJAS DE REGLAS
# =============================================================================

def _caja(regla, clase_cuerpo, color_fondo, etiqueta):
    filas = "".join(
        f'<tr><td class="etq">{etiqueta_fila}</td><td>{contenido}</td></tr>'
        for etiqueta_fila, contenido in regla["filas"]
    )
    return f"""
    <table class="regla"><tr>
      <td class="{clase_cuerpo}" bgcolor="{color_fondo}"
          style="background-color:{color_fondo};">
      <p class="regtitulo">{etiqueta} {regla['id']} — {regla['titulo']}</p>
      <p class="regnodos">Nodos de la gramática: {regla['nodos']}</p>
      <table class="regtabla">{filas}</table>
    </td></tr></table>
    """


def _caja_semantica(regla):
    return _caja(regla, "cuerpo_sem", "#FFBF00", "REGLA")


def _caja_sdt(regla):
    return _caja(regla, "cuerpo_sdt", "#DCE9FB", "REGLA")


def render_gramatica():
    """Producciones en rojo, con las cajas ámbar y azules intercaladas."""
    piezas = []
    for bloque in extraer_bloques_gramatica():
        cuerpo = "<br>".join(html.escape(bloque).split("\n"))
        clase = "gram" if _es_produccion(bloque) else "comentario"
        piezas.append(f'<div class="{clase}">{cuerpo}</div>')

        definidas = _producciones_definidas(bloque)
        for regla in REGLAS_SEMANTICAS:
            if regla["ancla"] in definidas:
                piezas.append(_caja_semantica(regla))
        for regla in REGLAS_SDT:
            if regla["ancla"] in definidas:
                piezas.append(_caja_sdt(regla))
    return "\n".join(piezas)


# =============================================================================
#  ESTILO
# =============================================================================

CSS = """
@page { size: A4; margin: 1.8cm 1.9cm 1.8cm 1.9cm; }
/* Chromium descarta los fondos al imprimir si no se le pide lo contrario, y
   los fondos de color son parte de la convencion que exige el enunciado. */
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10pt;
       color: #111111; line-height: 1.34; }
h1 { font-size: 19pt; margin: 0 0 6px 0; color: #7A3E00; }
h2 { font-size: 13.5pt; margin: 18px 0 8px 0; color: #7A3E00;
     border-bottom: 1.4px solid #B8860B; padding-bottom: 3px; }
p { margin: 4px 0; text-align: left; }
.portada { text-align: center; padding-top: 4.2cm; page-break-after: always; }
.portada .uni { font-size: 12pt; letter-spacing: .5px; }
.portada .titulo { font-size: 24pt; margin: 18px 0 6px 0; color: #7A3E00; }
.portada .sub { font-size: 12pt; color: #444; }
.portada .meta { margin-top: 2.2cm; font-size: 10.5pt; }
.gram { font-family: "DejaVu Sans Mono", "Courier New", monospace;
        font-size: 8.6pt; color: #C00000; white-space: pre;
        margin: 6px 0 6px 0; line-height: 1.18; page-break-inside: avoid; }
.comentario { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
              color: #B05050; white-space: pre; margin: 4px 0; line-height: 1.18; }
table.regla { border-collapse: collapse; width: 100%;
              margin: 8px 0 14px 0; page-break-inside: avoid; }
table.regla td.cuerpo_sem { background-color: #FFBF00; color: #000000;
                            border: 1.6px solid #7A5A00; padding: 7px 9px; }
table.regla td.cuerpo_sdt { background-color: #DCE9FB; color: #0B3D91;
                            border: 1.6px solid #0B3D91; padding: 7px 9px; }
td.cuerpo_sdt .regtitulo, td.cuerpo_sdt .regnodos, td.cuerpo_sdt td { color: #0B3D91; }
.regtitulo { font-weight: bold; font-size: 11pt; margin: 0 0 3px 0; }
.regnodos { font-size: 8.8pt; margin: 0 0 6px 0; }
table.regtabla { border-collapse: collapse; width: 100%; }
table.regtabla td { border: 1px solid #9A7200; padding: 3px 5px;
                    vertical-align: top; font-size: 8.9pt; text-align: left; }
td.cuerpo_sdt table.regtabla td { border: 1px solid #7FA6DD; }
table.regtabla td.etq { font-weight: bold; width: 21%;
                        background-color: #FFD97A; }
td.cuerpo_sdt table.regtabla td.etq { background-color: #C3D9F5; }
.leyenda { border: 1px solid #999; padding: 8px 10px; margin: 10px 0;
           background: #FAFAFA; font-size: 9.2pt; }
.leyenda .rojo { color: #C00000; font-family: "DejaVu Sans Mono", monospace; }
.leyenda .ambar { background-color: #FFBF00; padding: 1px 4px; }
.leyenda .azul { background-color: #DCE9FB; color: #0B3D91; padding: 1px 4px;
                 font-weight: bold; }
table.resumen { border-collapse: collapse; width: 100%; font-size: 8.8pt;
                margin: 8px 0 14px 0; }
table.resumen th, table.resumen td { border: 1px solid #999; padding: 4px 5px;
                                     vertical-align: top; text-align: left; }
table.resumen th { background: #F0E0B0; }
table.resumen th.azul { background: #C3D9F5; color: #0B3D91; }
.codigo { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
          background: #F4F4F4; border-left: 3px solid #B8860B;
          padding: 7px 9px; white-space: pre-wrap; margin: 7px 0; }
.gleam { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt;
         background: #F2F7FF; border-left: 3px solid #0B3D91;
         padding: 7px 9px; white-space: pre-wrap; margin: 7px 0; color: #0B3D91; }
.ia { border: 1.4px dashed #7A5A00; background: #FFF7E0; padding: 8px 10px;
      font-size: 9.2pt; margin: 8px 0; }
.salto { page-break-before: always; }
"""


# =============================================================================
#  DOCUMENTO
# =============================================================================

def _resumen_sdt():
    filas = "".join(
        f"<tr><td>{r['id']}</td><td>{r['nodos']}</td>"
        f"<td>{r['titulo']}</td></tr>"
        for r in REGLAS_SDT
    )
    return f"""
    <table class="resumen">
      <tr><th class="azul" width="8%">Regla</th>
          <th class="azul" width="47%">Producciones que cubre</th>
          <th class="azul" width="45%">Qué genera</th></tr>
      {filas}
    </table>
    """


def _resumen_semantico():
    filas = "".join(
        f"<tr><td>{r['id']}</td><td>{r['nodos']}</td><td>{r['titulo']}</td></tr>"
        for r in REGLAS_SEMANTICAS
    )
    return f"""
    <table class="resumen">
      <tr><th width="8%">Regla</th><th width="47%">Nodos de la gramática</th>
          <th width="45%">Qué valida</th></tr>
      {filas}
    </table>
    """


def construir_html():
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Paisascript — Gramática ampliada final</title>
  <style>{CSS}</style>
</head>
<body>

<!-- ============================ PORTADA ============================ -->
<div class="portada">
  <div class="uni">Universidad Católica de Oriente · Facultad de Ingeniería</div>
  <div class="uni">Compiladores — Entrega Final · Semestre 2-2026</div>
  <div class="titulo">Paisascript</div>
  <div class="sub">Gramática ampliada final<br>
  Análisis léxico, sintáctico, semántico y traducción orientada por la sintaxis</div>
  <div class="meta">
    <p><b>Lenguaje fuente:</b> Paisascript</p>
    <p><b>Lenguaje destino:</b> Gleam</p>
    <p><b>Integrantes:</b> Andres Felipe Velez &middot;
       Angie Amaya Fernandez &middot;
       Julian David Guarnizo Castrillon</p>
    <p><b>Repositorio:</b> github.com/JulianG08/Analizador-lexico</p>
    <p><b>App en vivo:</b> compiladorlex.streamlit.app</p>
    <p><b>Bonus:</b> Modalidad C — validación del código generado con IA
       y sugerencias de optimización</p>
  </div>
</div>

<!-- ============================ PARTE 1 ============================ -->
<h1>1. Gramática ampliada final</h1>

<p>Este documento presenta la gramática completa de Paisascript con las tres
capas de anotación que el proyecto fue acumulando entrega tras entrega. Las
<b>producciones sintácticas originales</b> van en
<span class="rojo" style="color:#C00000">rojo</span> y son idénticas a las de
las entregas anteriores. Las <b>reglas semánticas</b> van sobre
<span class="ambar" style="background-color:#FFBF00">fondo ámbar</span>. Las
<b>reglas de traducción orientada por la sintaxis</b> van en
<span class="azul" style="background-color:#DCE9FB;color:#0B3D91">azul</span>.</p>

<div class="leyenda">
  <p><span class="rojo">&lt;produccion&gt; ::= ...</span> — regla original de la
  gramática (producción sintáctica sin ampliar).</p>
  <p><span class="ambar">REGLA SEM-x</span> — regla semántica: atributos,
  dominio de valores y acciones de validación.</p>
  <p><span class="azul">REGLA SDT-x</span> — regla de traducción: atributos,
  acción de generación y la salida que produce en el lenguaje destino.</p>
</div>

<h2>1.1 Por qué la traducción necesita las otras dos capas</h2>

<p>En Gleam <tt>Int</tt> y <tt>Float</tt> son tipos <b>disjuntos</b>, con
operadores distintos: la suma de enteros es <tt>+</tt> y la de reales es
<tt>+.</tt>. El operador de concatenación <tt>&lt;&gt;</tt> exige
<tt>String</tt> en los dos lados. Eso significa que la fase SDT
<b>no puede</b> decidir qué emitir mirando solo la forma de la expresión:
necesita saber el tipo de cada operando.</p>

<p>Ese tipo lo resolvió el análisis semántico y llega a la fase SDT por dos
caminos: la <b>tabla de símbolos</b>, que el traductor recibe ya construida, y
el atributo sintetizado <tt>type</tt>, que el analizador anotó sobre cada nodo
de expresión del árbol. Las tres capas del documento no son tres documentos
pegados: la azul se apoya en la ámbar, que se apoya en la roja.</p>

<h2>1.2 Resumen de las reglas semánticas (fondo ámbar)</h2>
{_resumen_semantico()}

<h2>1.3 Resumen de las reglas de traducción (azul)</h2>
{_resumen_sdt()}

<p>Las trece reglas SDT cubren todas las producciones que contribuyen a la
salida. <b>SDT-12</b> atiende de forma explícita lo que el enunciado exige
sobre las listas vacías (producciones ε) y las producciones recursivas, que en
esta gramática aparecen en todas las listas y en las colas de expresión.</p>

<!-- ============================ GRAMÁTICA ============================ -->
<h1 class="salto">2. Producciones BNF con las reglas intercaladas</h1>

<p>Se reproduce la sección de producciones de la gramática. Cada regla aparece
inmediatamente después del nodo que restringe o traduce.</p>

{render_gramatica()}

<!-- ============================ PARTE 2 ============================ -->
<h1 class="salto">3. El compilador: cuatro fases encadenadas</h1>

<p>El compilador procesa la entrada en cuatro fases, cada una en su propio
módulo, y cada una recibe exactamente lo que produjo la anterior.</p>

<table class="resumen">
  <tr><th width="6%">#</th><th width="20%">Fase</th><th width="26%">Módulo</th>
      <th width="48%">Qué produce</th></tr>
  <tr><td>1</td><td>Análisis léxico</td><td><tt>lexer.py</tt></td>
      <td>Tokens con lexema, fila y columna. Reporta los no reconocidos.</td></tr>
  <tr><td>2</td><td>Análisis sintáctico</td><td><tt>parser.py</tt></td>
      <td>El CST según la gramática BNF. Recuperación de errores para seguir
          analizando.</td></tr>
  <tr><td>3</td><td>Análisis semántico</td><td><tt>analizador_semantico.py</tt></td>
      <td>Tabla de símbolos y validación de las ocho reglas. Anota el tipo
          sintetizado sobre cada nodo de expresión.</td></tr>
  <tr><td>4</td><td>Traducción (SDT)</td><td><tt>traductor_sdt.py</tt></td>
      <td>Recorre el CST aplicando las acciones SDT y emite el código Gleam.</td></tr>
</table>

<p>El encadenamiento lo gobierna <tt>compilador.py</tt>, que es el único punto
donde se decide si hay salida:</p>

<div class="codigo">from compilador import compilar

resultado = compilar(codigo_fuente)
if resultado.exitoso:
    print(resultado.codigo_gleam)
else:
    print(resultado.reporte())      # errores de las tres fases, unificados</div>

<h2>3.1 Si hay errores, no hay salida</h2>
<p>Es una regla dura del enunciado y está implementada como tal: mientras
exista un error léxico, sintáctico o semántico, la fase SDT <b>no se
ejecuta</b> y el compilador se limita a reportar. Un error sintáctico además
detiene el análisis semántico, porque un árbol roto solo produciría errores
falsos.</p>

<h2>3.2 Reporte de errores unificado</h2>
<p>Las tres fases de análisis entregan sus errores al mismo objeto
<tt>ErrorCompilacion</tt>, con <b>fase, fila, columna, lexema y mensaje
descriptivo</b>. Cada fase aplica recuperación, de modo que una sola ejecución
reporte el mayor número posible de problemas.</p>

<div class="codigo">--- Fase SEMÁNTICA (8) ---
  [SEMÁNTICA] Fila 13, Columna 21 sobre 'edad': [SEM-1] Se declara 'edad'
  como numerito, pero la expresión es de tipo cuento
  [SEMÁNTICA] Fila 33, Columna 1 sobre 'mientras_que': [SEM-6] El cuerpo de
  'mientras_que' no redefine ninguna variable de la condición (tope): el
  bucle nunca termina</div>

<h2>3.3 La tabla de símbolos durante la fase SDT</h2>
<p>El traductor recibe la tabla de símbolos ya construida y la consulta para
los tipos de las variables y las firmas de las funciones. Es lo que le permite
saber que <tt>escuche_pues(edad)</tt> necesita <tt>int.parse</tt> cuando
<tt>edad</tt> es numerito, y que <tt>a + b</tt> debe emitirse como
<tt>a +. b</tt> cuando los operandos son quebradito.</p>

<h2>3.4 Un ejemplo completo</h2>
<p><b>Entrada en Paisascript:</b></p>
<div class="codigo">hagale_pues sumatoria(numerito n) pa_que_lleve numerito dele_pues
    pille_pues numerito acumulado = 0
    pille_pues numerito i = 1
    mientras_que i &lt;= n dele_pues
        pille_pues acumulado = acumulado + i
        pille_pues i = i + 1
    hasta_ahi
    entregue_pues acumulado
ya_quedo

pille_pues numerito total = sumatoria(10)
hable_pues("La sumatoria de 1 a 10 es: " &lt;&gt; total)</div>

<p><b>Salida que produce la fase SDT:</b></p>
<div class="gleam">import gleam/int
import gleam/io

pub fn main() {{
  let total = sumatoria(10)
  io.println("La sumatoria de 1 a 10 es: " &lt;&gt; int.to_string(total))
}}

pub fn sumatoria(n: Int) -&gt; Int {{
  let acumulado = 0
  let i = 1
  let #(acumulado, i) = bucle_1(n, acumulado, i)
  acumulado
}}

fn bucle_1(n: Int, acumulado: Int, i: Int) -&gt; #(Int, Int) {{
  case i &lt;= n {{
    True -&gt; {{
      let acumulado = acumulado + i
      let i = i + 1
      bucle_1(n, acumulado, i)
    }}
    False -&gt; #(acumulado, i)
  }}
}}</div>

<p>Obsérvense tres decisiones de la fase SDT en este fragmento: el
<tt>int.to_string</tt> que exige la concatenación (SDT-11), el parámetro
<tt>n</tt> que viaja a la función auxiliar porque el bucle lo lee aunque no lo
modifique (SDT-7), y la tupla <tt>#(acumulado, i)</tt> con el estado del
bucle, que es lo que reemplaza a la mutación que Gleam no tiene.</p>

<h2>3.5 Archivos de prueba</h2>
<table class="resumen">
  <tr><th width="34%">Archivo</th><th width="20%">Qué contiene</th>
      <th width="46%">Resultado esperado</th></tr>
  <tr><td><tt>1_sin_errores.paisa</tt></td><td>Programa válido</td>
      <td>Las cuatro fases corren y se produce la salida completa en Gleam.</td></tr>
  <tr><td><tt>2_errores_semanticos.paisa</tt></td><td>8 errores semánticos</td>
      <td>Se reportan los ocho con fila, columna y lexema. <b>No se genera
          salida.</b></td></tr>
  <tr><td><tt>3_errores_sintacticos.paisa</tt></td><td>5 errores sintácticos</td>
      <td>Se reportan con recuperación. No se llega al análisis semántico ni
          se genera salida.</td></tr>
</table>

<!-- ============================ BONUS ============================ -->
<h1 class="salto">4. Bonus — Validación del código generado con IA</h1>

<p><b>Modalidad C: combinación de validación y sugerencias.</b> Una vez que la
fase SDT produce el código Gleam, ese texto se envía a un modelo de lenguaje
que primero comprueba si es sintáctica y semánticamente correcto para Gleam y,
si lo es, propone mejoras concretas.</p>

<p>Es una capa <b>adicional</b>: el compilador funciona completo sin ella, y si
no hay clave de API o no hay red, la interfaz lo indica y el resto sigue
funcionando igual.</p>

<h2>4.1 El prompt</h2>
<div class="codigo">Eres un revisor experto del lenguaje Gleam.

Este codigo fue GENERADO automaticamente por un compilador que traduce
desde Paisascript. Revisa dos cosas y responde en espanol:

1. VALIDEZ: ¿es sintactica y semanticamente correcto en Gleam? Revisa en
   particular: que los tipos Int y Float no se mezclen (Gleam usa + y +.
   como operadores distintos), que todo bloque termine en una expresion y
   no en un 'let', que los modulos usados esten importados, y que las
   ramas de cada 'case' devuelvan el mismo tipo.
2. OPTIMIZACION: propon mejoras concretas e idiomaticas.

Codigo generado:
{{codigo_gleam}}</div>

<h2>4.2 Flujo de integración</h2>
<ol>
  <li>El compilador ejecuta las cuatro fases y produce el código Gleam.</li>
  <li>La interfaz ofrece el botón «Validar y optimizar con IA».</li>
  <li><tt>ai_assistant.validar_codigo_generado(codigo_gleam)</tt> construye el
      prompt y llama a la API.</li>
  <li>La respuesta se muestra junto al código, separada de él y claramente
      etiquetada como sugerencia.</li>
</ol>

</body>
</html>
"""


# =============================================================================
#  CONVERSIÓN A PDF
# =============================================================================

def _pdf_con_libreoffice():
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        return None
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(RAIZ), str(HTML_SALIDA)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return PDF_SALIDA if PDF_SALIDA.exists() else None


def _pdf_con_navegador():
    navegador = next(
        (ruta for ruta in NAVEGADORES if Path(ruta).exists()),
        shutil.which("msedge") or shutil.which("chrome"),
    )
    if navegador is None:
        return None
    subprocess.run(
        [str(navegador), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={PDF_SALIDA}", HTML_SALIDA.as_uri()],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
    )
    # El navegador escribe el archivo de forma asincrona: se le da un margen
    # antes de darlo por fallido.
    for _ in range(20):
        if PDF_SALIDA.exists():
            return PDF_SALIDA
        time.sleep(0.5)
    return None


def convertir_a_pdf():
    for motor, nombre in ((_pdf_con_libreoffice, "LibreOffice"),
                          (_pdf_con_navegador, "Edge/Chrome headless")):
        try:
            pdf = motor()
        except Exception as e:                      # noqa: BLE001
            print(f"AVISO: {nombre} falló ({e}).")
            continue
        if pdf is not None:
            print(f"Motor de PDF: {nombre}")
            return pdf
    print("AVISO: no se encontró LibreOffice ni un navegador Chromium; "
          "se generó solo el HTML.")
    return None


def main():
    HTML_SALIDA.write_text(construir_html(), encoding="utf-8")
    print(f"HTML generado: {HTML_SALIDA}")
    pdf = convertir_a_pdf()
    if pdf:
        print(f"PDF generado : {pdf}")
    else:
        print("No se pudo generar el PDF automáticamente.")


if __name__ == "__main__":
    main()
