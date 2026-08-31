# -*- coding: utf-8 -*-
"""
mapeo_gleam.py — Correspondencia token de Paisascript -> construccion de Gleam.

Es la forma ejecutable de la tabla del §7.3 de la gramatica. Sirve para dos
cosas:

  1. La interfaz muestra, junto a cada token, en que se convertira. Eso hace
     visible desde la Entrega 1 que el lenguaje fuente fue disenado contra un
     destino concreto y no en el vacio.
  2. El generador de codigo de la entrega final partira de esta tabla.

No depende de streamlit ni de ninguna interfaz: solo de `lexer.TipoToken`.
"""

from __future__ import annotations

from lexer import TipoToken

# Traduccion directa token a token. Cuando la equivalencia no es un simple
# reemplazo de texto se anota la forma general; el detalle de esas cuatro
# construcciones esta en MAPEO_GLEAM.md.
TRADUCCION: dict[TipoToken, str] = {
    # --- Declaraciones y E/S ------------------------------------------------
    TipoToken.KW_DECLARACION:   "let",
    TipoToken.KW_LECTURA:       "erlang.get_line(\"\")",
    TipoToken.KW_IMPRESION:     "io.println",
    TipoToken.KW_FUNCION:       "pub fn",
    TipoToken.KW_FIN_FUNCION:   "}",
    TipoToken.KW_RETORNAR:      "(ultima expresion del cuerpo)",

    # --- Control ------------------------------------------------------------
    TipoToken.KW_SI:            "case",
    TipoToken.KW_ENTONCES:      "True ->",
    TipoToken.KW_SINO:          "False ->",
    TipoToken.KW_FIN_SI:        "}",
    TipoToken.KW_MIENTRAS:      "(funcion recursiva de cola)",
    TipoToken.KW_HACER:         "{",
    TipoToken.KW_FIN_MIENTRAS:  "}",
    TipoToken.KW_PARA:          "list.range(..) |> list.each(..)",
    TipoToken.KW_DESDE:         "list.range(desde, _)",
    TipoToken.KW_HASTA:         "list.range(_, hasta)",
    TipoToken.KW_PASO:          "(recursion con incremento)",
    TipoToken.KW_FIN_PARA:      "}",
    TipoToken.KW_PILLEMOS:      "case",
    TipoToken.KW_FLECHA:        "->",

    # --- Tipos --------------------------------------------------------------
    TipoToken.KW_TIPO_ENTERO:   "Int",
    TipoToken.KW_TIPO_REAL:     "Float",
    TipoToken.KW_TIPO_CADENA:   "String",
    TipoToken.KW_TIPO_BOOLEANO: "Bool",

    # --- Operadores con nombre ----------------------------------------------
    TipoToken.OP_Y:             "&&",
    TipoToken.OP_O:             "||",
    TipoToken.OP_NO:            "!",
    TipoToken.OP_IGUAL:         "==",
    TipoToken.OP_DISTINTO:      "!=",

    # --- Literales ----------------------------------------------------------
    TipoToken.LIT_VERDADERO:    "True",
    TipoToken.LIT_FALSO:        "False",
    TipoToken.NUM_ENTERO:       "Int",
    TipoToken.NUM_REAL:         "Float",
    TipoToken.CADENA_LITERAL:   "String",

    TipoToken.IDENTIFICADOR:    "(mismo nombre, transliterado a ASCII)",

    # --- Operadores simbolicos ----------------------------------------------
    # Los aritmeticos dependen del tipo: Gleam separa Int de Float.
    TipoToken.OP_POTENCIA:      "int.power / float.power",
    TipoToken.OP_MULT:          "*  |  *.",
    TipoToken.OP_DIV:           "/  |  /.",
    TipoToken.OP_MODULO:        "%",
    TipoToken.OP_SUMA:          "+  |  +.",
    TipoToken.OP_RESTA:         "-  |  -.",
    TipoToken.OP_CONCAT:        "<>  (con int.to_string si hace falta)",
    TipoToken.OP_MAYOR_IGUAL:   ">=  |  >=.",
    TipoToken.OP_MENOR_IGUAL:   "<=  |  <=.",
    TipoToken.OP_MAYOR:         ">   |  >.",
    TipoToken.OP_MENOR:         "<   |  <.",
    TipoToken.OP_ASIGNACION:    "=",

    # --- Puntuacion ---------------------------------------------------------
    TipoToken.PAR_ABRE:         "(",
    TipoToken.PAR_CIERRA:       ")",
    TipoToken.LLAVE_ABRE:       "{",
    TipoToken.LLAVE_CIERRA:     "}",
    TipoToken.COMA:             ",",
    TipoToken.COMODIN:          "_",

    TipoToken.FIN_ARCHIVO:      "",
}

# Tokens cuya traduccion NO es un reemplazo directo: exigen que el generador
# reestructure el arbol. Son justamente los cuatro constructos que el §2 del
# enunciado exige y que Gleam no tiene.
NO_DIRECTOS = {
    TipoToken.KW_MIENTRAS,
    TipoToken.KW_PARA,
    TipoToken.KW_PASO,
    TipoToken.KW_RETORNAR,
}


def equivalente(tipo: TipoToken) -> str:
    """Construccion de Gleam a la que corresponde un tipo de token."""
    return TRADUCCION.get(tipo, "")


def es_directo(tipo: TipoToken) -> bool:
    """False si la traduccion exige reestructurar el arbol, no solo sustituir."""
    return tipo not in NO_DIRECTOS


if __name__ == "__main__":
    faltantes = [t.name for t in TipoToken if t not in TRADUCCION]
    print("Tokens sin traduccion definida:", faltantes or "ninguno")
    print(f"Cobertura: {len(TRADUCCION)}/{len(list(TipoToken))}")
