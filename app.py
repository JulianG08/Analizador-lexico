# -*- coding: utf-8 -*-
"""
app.py — Interfaz web (Streamlit) del analizador léxico y sintáctico de Paisascript.

Es la SEGUNDA interfaz construida sobre los mismos módulos core (`lexer.py`, 
`parser.py`), demostrando la encapsulación e independencia exigida en el 
requisito 15 del enunciado.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from chequeo_estructural import verificar_balance
from ejemplos import EJEMPLOS
from lexer import Lexer, TipoToken
from mapeo_gleam import equivalente, es_directo
from parser import Parser, ErrorSintactico

RAIZ = Path(__file__).parent

# Soporte para entrada en vivo
try:
    from componente_entrada_viva import area_texto_viva
    _ENTRADA_VIVA_DISPONIBLE = True
except Exception:
    _ENTRADA_VIVA_DISPONIBLE = False

# Soporte condicional para Árbol Gráfico (Graphviz)
try:
    from arbol_grafico import generar_grafo_ast
    _ARBOL_GRAFICO_DISPONIBLE = True
except ImportError:
    _ARBOL_GRAFICO_DISPONIBLE = False


# =============================================================================
#  CONFIGURACION Y ESTILOS
# =============================================================================

st.set_page_config(
    page_title="Paisascript — Frontend Compilador",
    page_icon="🪕",
    layout="wide",
)

COLORES = {
    "RESERVADA":     "#c678dd",
    "TIPO":          "#56b6c2",
    "OPERADOR":      "#e5c07b",
    "LITERAL":       "#98c379",
    "IDENTIFICADOR": "#61afef",
    "PUNTUACION":    "#8b93a1",
    "FIN":           "#5c6370",
}
FONDO = "#282c34"
TENUE = "#5c6370"
ROJO = "#e06c75"

st.markdown(f"""
<style>
  .lienzo {{
      background: {FONDO};
      border-radius: 8px;
      padding: 16px 18px;
      overflow-x: auto;
      font-family: "Cascadia Code", "Consolas", "SF Mono", monospace;
      font-size: 13.5px;
      line-height: 1.65;
  }}
  .lienzo pre {{ margin: 0; color: {TENUE}; white-space: pre; }}
  .num {{ color: {TENUE}; user-select: none; }}
  .err {{
      background: {ROJO}; color: {FONDO};
      font-weight: 700; border-radius: 3px; padding: 0 2px;
  }}
  .ficha {{
      display: inline-block; margin: 3px 4px 3px 0;
      border-radius: 6px; overflow: hidden;
      font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px;
      border: 1px solid rgba(255,255,255,.12);
  }}
  .ficha .lex {{ padding: 3px 8px; font-weight: 700; }}
  .ficha .tip {{ padding: 3px 8px; background: rgba(0,0,0,.28); font-size: 11px; }}
  .leyenda span {{
      display: inline-block; margin-right: 14px;
      font-size: 12px; font-weight: 700;
  }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
#  ANALISIS  (cacheado: solo se reanaliza cuando cambia el texto)
# =============================================================================

@st.cache_data(show_spinner=False)
def analizar(codigo: str):
    # FASE 1: Análisis Léxico
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]
    
    filas = [
        {
            "#": i,
            "Lexema": t.lexema,
            "TokenType": t.tipo.name,
            "Categoría": t.categoria,
            "Fila": t.fila,
            "Columna": t.columna,
            "Valor": "" if t.valor is None else str(t.valor),
            "Gleam": equivalente(t.tipo),
            "Directo": "sí" if es_directo(t.tipo) else "reestructura",
        }
        for i, t in enumerate(utiles, start=1)
    ]
    
    errores = [
        {"#": i, "Fila": e.fila, "Columna": e.columna,
         "Lexema": e.lexema, "Causa": e.mensaje}
        for i, e in enumerate(lexer.errores, start=1)
    ]
    
    chequeo = verificar_balance(utiles)

    # FASE 2: Análisis Sintáctico (AST)
    ast = None
    error_sintactico = None
    try:
        parser = Parser(tokens)
        ast = parser.parse()
    except ErrorSintactico as e:
        error_sintactico = str(e)
    except Exception as e:
        error_sintactico = f"Error interno en el Parser: {str(e)}"

    return (utiles, lexer.errores, pd.DataFrame(filas), pd.DataFrame(errores),
            lexer.resumen_identificadores(), chequeo, ast, error_sintactico)


# =============================================================================
#  VISTAS HTML
# =============================================================================

def html_codigo(codigo: str, tokens, errores) -> str:
    marcas: dict[int, list] = {}
    for t in tokens:
        marcas.setdefault(t.fila, []).append(
            (t.columna, t.lexema, COLORES.get(t.categoria, "#fff"), False)
        )
    for e in errores:
        marcas.setdefault(e.fila, []).append((e.columna, e.lexema, None, True))

    ancho = len(str(max(1, codigo.count("\n") + 1)))
    salida = []
    for i, linea in enumerate(codigo.split("\n"), start=1):
        partes = [f'<span class="num">{i:>{ancho}} │ </span>']
        cursor = 0
        for columna, lexema, color, es_error in sorted(marcas.get(i, [])):
            inicio = columna - 1
            if inicio < cursor:
                continue
            partes.append(html.escape(linea[cursor:inicio]))
            texto = html.escape(linea[inicio:inicio + len(lexema)])
            if es_error:
                partes.append(f'<span class="err">{texto}</span>')
            else:
                partes.append(f'<span style="color:{color}">{texto}</span>')
            cursor = inicio + len(lexema)
        partes.append(html.escape(linea[cursor:]))
        salida.append("".join(partes))

    return f'<div class="lienzo"><pre>{chr(10).join(salida)}</pre></div>'


def html_leyenda() -> str:
    piezas = [f'<span style="color:{c}">{n}</span>' for n, c in COLORES.items()
              if n != "FIN"]
    piezas.append(f'<span class="err">ERROR</span>')
    return f'<div class="leyenda">{"".join(piezas)}</div>'


def html_fichas(tokens) -> str:
    fichas = []
    for t in tokens:
        color = COLORES.get(t.categoria, "#fff")
        lexema = html.escape(t.lexema) or "&nbsp;"
        fichas.append(
            f'<span class="ficha" style="background:{FONDO}">'
            f'<span class="lex" style="color:{color}">{lexema}</span>'
            f'<span class="tip" style="color:{color}">{t.tipo.name}</span>'
            f'</span>'
        )
    return f'<div class="lienzo" style="line-height:2.2">{"".join(fichas)}</div>'


def extraer_fragmento(fuente: str, inicio: str, fin: str) -> str:
    i = fuente.index(inicio)
    j = fuente.index(fin, i) + len(fin)
    return fuente[i:j]


def html_error(codigo: str, e) -> str:
    lineas = codigo.split("\n")
    texto = lineas[e.fila - 1] if 1 <= e.fila <= len(lineas) else ""
    cursor = " " * (e.columna - 1) + "^" * max(1, len(e.lexema))
    return (
        f'<div class="lienzo"><pre>'
        f'<span class="num">{e.fila:>3} │ </span>{html.escape(texto)}\n'
        f'<span class="num">    │ </span>'
        f'<span style="color:{ROJO};font-weight:700">{html.escape(cursor)}</span>'
        f'</pre></div>'
    )


# =============================================================================
#  BARRA LATERAL — ENTRADA
# =============================================================================

st.sidebar.title("🪕 Paisascript")
st.sidebar.caption("Frontend: Análisis Léxico y Sintáctico")
st.sidebar.divider()

modo = st.sidebar.radio(
    "Modo de ingreso de la cadena",
    ["Cadena predefinida", "Cadena libre", "Archivo .paisa"],
)

codigo = ""
titulo_fuente = ""

if modo == "Cadena predefinida":
    nombres = [n for n, _, _ in EJEMPLOS]
    elegido = st.sidebar.selectbox("Programa", nombres, index=0)
    idx = nombres.index(elegido)
    st.sidebar.info(EJEMPLOS[idx][1])
    codigo = EJEMPLOS[idx][2]
    titulo_fuente = elegido

elif modo == "Cadena libre":
    if "codigo_libre" not in st.session_state:
        st.session_state.codigo_libre = (
            'pille_pues numerito x = 10 % 3 ** 2\n'
            'hable_pues("El resultado es: " <> x)'
        )

    en_vivo = _ENTRADA_VIVA_DISPONIBLE and st.sidebar.toggle(
        "⚡ Analizar en vivo (beta)",
        value=False,
    )

    if en_vivo:
        st.session_state.codigo_libre = area_texto_viva(
            st.session_state.codigo_libre, altura=260, key="area_viva",
        )
    else:
        st.session_state.codigo_libre = st.sidebar.text_area(
            "Escriba su código Paisascript",
            value=st.session_state.codigo_libre,
            height=260,
            key="area_clasica",
        )
        st.sidebar.button("🔎 Analizar ahora", width="stretch")

    codigo = st.session_state.codigo_libre
    titulo_fuente = "cadena digitada"

else:
    subido = st.sidebar.file_uploader("Archivo de código", type=["paisa", "txt"])
    if subido is not None:
        codigo = subido.getvalue().decode("utf-8", errors="replace")
        titulo_fuente = subido.name
    else:
        st.sidebar.warning("Suba un archivo para analizar.")

st.sidebar.divider()


# =============================================================================
#  CUERPO PRINCIPAL
# =============================================================================

st.title("Frontend Compilador Paisascript")

if not codigo.strip():
    st.info("Elija una cadena predefinida, escriba código o suba un archivo.")
    st.stop()

tokens, errores, tabla, tabla_err, identificadores, chequeo, ast, error_sintactico = analizar(codigo)

# --- Metricas ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tokens Validos", len(tokens))
c2.metric("Errores Léxicos", len(errores), delta=None if not errores else f"{len(errores)} fallos", delta_color="inverse")
c3.metric("Líneas", codigo.count("\n") + 1)
estado_parser = "Exitoso" if not error_sintactico else "Fallido"
c4.metric("Parser (Sintaxis)", estado_parser, delta=None if not error_sintactico else "1 error", delta_color="inverse")

with st.expander("Ver / editar el código fuente", expanded=False):
    st.code(codigo, language=None)

# Añadimos la nueva pestaña del AST y desplazamos las demás
pestañas = st.tabs([
    "Análisis Sintáctico (AST)",  # Nueva vista principal
    "Código segmentado",
    "Flujo de tokens",
    "Tabla de símbolos",
    "Errores y verificación",
    "Resumen",
    "Traducción a Gleam",
    "Código del analizador",
    "Referencia",
])

# --- 0. Analisis Sintactico (NUEVA PESTAÑA) ---------------------------------
with pestañas[0]:
    st.subheader("Árbol de Sintaxis Abstracta (AST)")
    
    if error_sintactico:
        st.error(f"No se pudo generar el AST debido a un error de sintaxis: {error_sintactico}")
        st.caption("Revise el código fuente. El Parser descendente recursivo LL(1) encontró una estructura no válida según la gramática.")
    elif ast:
        st.success("Análisis sintáctico exitoso. El flujo de tokens coincide perfectamente con la gramática.")
        
        vista_col1, vista_col2 = st.columns([1, 1])
        
        with vista_col1:
            st.markdown("##### AST (Formato JSON)")
            st.json(ast, expanded=True)
            
        with vista_col2:
            st.markdown("##### Árbol Gráfico Visual")
            if _ARBOL_GRAFICO_DISPONIBLE:
                try:
                    grafo = generar_grafo_ast(ast)
                    st.graphviz_chart(grafo, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo renderizar el grafo: {e}")
            else:
                st.info("Para ver el árbol gráfico, asegúrese de que `arbol_grafico.py` exporte la función `generar_grafo_ast(ast)` que retorne un objeto `graphviz.Digraph`, y que Graphviz esté instalado en el sistema.")

# --- 1. Codigo segmentado ---------------------------------------------------
with pestañas[1]:
    st.subheader("El fuente dividido en tokens")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_codigo(codigo, tokens, errores), unsafe_allow_html=True)

# --- 2. Flujo de tokens -----------------------------------------------------
with pestañas[2]:
    st.subheader("Secuencia de tokens emitida")
    st.markdown(html_leyenda(), unsafe_allow_html=True)
    st.markdown(html_fichas(tokens), unsafe_allow_html=True)

# --- 3. Tabla de simbolos ---------------------------------------------------
with pestañas[3]:
    st.subheader("Tabla de símbolos léxicos")
    cats = sorted(tabla["Categoría"].unique()) if not tabla.empty else []
    filtro = st.multiselect("Filtrar por categoría", cats, default=cats)
    vista = tabla[tabla["Categoría"].isin(filtro)] if filtro else tabla

    st.dataframe(
        vista[["#", "Lexema", "TokenType", "Categoría", "Fila", "Columna", "Valor"]],
        width="stretch", hide_index=True, height=460,
    )

# --- 4. Errores -------------------------------------------------------------
with pestañas[4]:
    st.subheader("Reporte de errores léxicos")
    if not errores:
        st.success("No se encontró ningún error léxico en esta entrada.")
    else:
        st.dataframe(tabla_err, width="stretch", hide_index=True)
        st.divider()
        for e in errores:
            st.markdown(f"**Error en fila {e.fila}, columna {e.columna}** — {e.mensaje}")
            st.markdown(html_error(codigo, e), unsafe_allow_html=True)

# --- 5. Resumen -------------------------------------------------------------
with pestañas[5]:
    st.subheader("Distribución de tokens por categoría")
    conteo = (tabla["Categoría"].value_counts().rename_axis("Categoría")
              .reset_index(name="Tokens"))
    izq, der = st.columns([2, 1])
    izq.bar_chart(conteo.set_index("Categoría"), height=340)
    der.dataframe(conteo, width="stretch", hide_index=True)

# --- 6. Traduccion a Gleam --------------------------------------------------
with pestañas[6]:
    st.subheader("En qué se convierte cada token")
    st.dataframe(
        tabla[["#", "Lexema", "TokenType", "Gleam", "Directo"]],
        width="stretch", hide_index=True, height=420,
    )

# --- 7. Codigo del analizador ----------------------------------------------
with pestañas[7]:
    st.subheader("El analizador léxico y sintáctico, en Python puro")
    st.caption("Fragmentos leídos en vivo de los módulos core.")
    
    _fuente_lexer = (RAIZ / "lexer.py").read_text(encoding="utf-8") if (RAIZ / "lexer.py").exists() else "No encontrado"
    
    with st.expander("Ver lexer.py completo"):
        st.code(_fuente_lexer, language="python")

# --- 8. Referencia ----------------------------------------------------------
with pestañas[8]:
    st.subheader("Documentación del lenguaje")
    doc = st.radio("Documento", ["Gramática BNF", "Mapeo a Gleam", "README"], horizontal=True)
    archivo = {"Gramática BNF": "gramatica_BNF_Paisascript.txt",
               "Mapeo a Gleam": "MAPEO_GLEAM.md",
               "README": "README.md"}[doc]
    ruta = RAIZ / archivo
    if ruta.exists():
        texto = ruta.read_text(encoding="utf-8")
        if archivo.endswith(".md"):
            st.markdown(texto)
        else:
            st.text(texto)
    else:
        st.error(f"No se encontró {archivo} junto a app.py.")