# -*- coding: utf-8 -*-
"""
Módulo: compilador.py
Descripción: ORQUESTADOR del compilador de Paisascript (Entrega Final).

Encadena las cuatro fases en orden y es el único punto donde se decide si
hay salida o no:

    1. Análisis léxico       lexer.py                -> tokens
    2. Análisis sintáctico   parser.py               -> CST
    3. Análisis semántico    analizador_semantico.py -> tabla de símbolos
    4. Traducción (SDT)      traductor_sdt.py        -> código Gleam

Reglas de encadenamiento que exige el enunciado:

  * Las fases corren en orden; cada una recibe lo que produjo la anterior.
  * Si hay errores LÉXICOS o SINTÁCTICOS, no se intenta el análisis semántico
    (el árbol no es confiable) y por supuesto no se genera salida.
  * Si hay errores SEMÁNTICOS, **no se genera código de salida**: solo se
    reportan todos los errores encontrados.
  * El reporte de errores es unificado: fase, fila, columna, lexema y
    mensaje descriptivo, para las tres fases de análisis.
  * Cada fase continúa tras un error cuando puede (recuperación), de modo que
    una sola ejecución reporte el mayor número posible de problemas.

Uso como programa:

    python compilador.py entrada.txt                 # muestra el Gleam
    python compilador.py entrada.txt -o salida.gleam # lo escribe en archivo
    python compilador.py entrada.txt --tabla         # + tabla de símbolos

Uso como biblioteca:

    from compilador import compilar
    resultado = compilar(codigo_fuente)
    if resultado.exitoso:
        print(resultado.codigo_gleam)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lexer import Lexer
from parser import Parser
from analizador_semantico import AnalizadorSemantico
from traductor_sdt import TraductorSDT

# Nombres de las fases, tal como aparecen en el reporte unificado.
FASE_LEXICA = "LÉXICA"
FASE_SINTACTICA = "SINTÁCTICA"
FASE_SEMANTICA = "SEMÁNTICA"


# El parser entrega sus errores ya formateados como texto, con la posición
# dentro del mensaje ("... en [Fila 11, Columna 5]: ..."). Estas expresiones
# la recuperan para poder presentarla en columnas propias.
_PATRON_POSICION = re.compile(r"\[Fila (\d+)(?:, Columna (\d+))?\]")
_PATRON_LEXEMA = re.compile(r"(?:se encontró|no válido con) '([^']*)'")
_PATRON_LIMPIEZA = re.compile(r"^Error Sintáctico en \[[^\]]*\]:\s*")


def _desglosar_sintactico(texto):
    """De un error sintáctico en texto a (fila, columna, lexema, mensaje)."""
    texto = str(texto)
    posicion = _PATRON_POSICION.search(texto)
    fila = posicion.group(1) if posicion else "?"
    columna = posicion.group(2) if posicion and posicion.group(2) else "?"
    lexema_encontrado = _PATRON_LEXEMA.search(texto)
    lexema = lexema_encontrado.group(1) if lexema_encontrado else ""
    mensaje = _PATRON_LIMPIEZA.sub("", texto).strip()
    return fila, columna, lexema, mensaje


class ErrorCompilacion:
    """Un error de cualquier fase, con el formato unificado del enunciado."""

    def __init__(self, fase, fila, columna, lexema, mensaje, regla=""):
        self.fase = fase
        self.fila = fila
        self.columna = columna
        self.lexema = lexema
        self.mensaje = mensaje
        self.regla = regla

    def __str__(self):
        etiqueta = f"[{self.regla}] " if self.regla else ""
        lexema = f" sobre '{self.lexema}'" if self.lexema else ""
        return (f"[{self.fase}] Fila {self.fila}, Columna {self.columna}"
                f"{lexema}: {etiqueta}{self.mensaje}")

    def como_fila(self):
        return {
            "Fase": self.fase,
            "Regla": self.regla,
            "Fila": self.fila,
            "Columna": self.columna,
            "Lexema": self.lexema,
            "Mensaje": self.mensaje,
        }


class ResultadoCompilacion:
    """Lo que devuelve una corrida completa del compilador."""

    def __init__(self):
        self.tokens = []
        self.cst = None
        self.tabla = None
        self.errores: list[ErrorCompilacion] = []
        self.codigo_gleam = ""
        self.fase_alcanzada = FASE_LEXICA

    @property
    def exitoso(self):
        """Hubo salida: ningún error en ninguna de las tres fases."""
        return not self.errores and bool(self.codigo_gleam)

    def errores_de(self, fase):
        return [e for e in self.errores if e.fase == fase]

    def reporte(self):
        """Reporte unificado de errores, en texto plano."""
        if not self.errores:
            return "Sin errores. Compilación exitosa."
        lineas = [f"Se encontraron {len(self.errores)} error(es):", ""]
        for fase in (FASE_LEXICA, FASE_SINTACTICA, FASE_SEMANTICA):
            de_la_fase = self.errores_de(fase)
            if not de_la_fase:
                continue
            lineas.append(f"--- Fase {fase} ({len(de_la_fase)}) ---")
            lineas.extend(f"  {e}" for e in de_la_fase)
            lineas.append("")
        return "\n".join(lineas).rstrip()


# =============================================================================
#  LAS CUATRO FASES, ENCADENADAS
# =============================================================================

def compilar(codigo_fuente):
    """Corre las cuatro fases y devuelve un ResultadoCompilacion."""
    resultado = ResultadoCompilacion()

    # --- Fase 1: análisis léxico -------------------------------------------
    lexer = Lexer(codigo_fuente)
    resultado.tokens = lexer.tokenizar()
    for error in getattr(lexer, "errores", []):
        resultado.errores.append(ErrorCompilacion(
            FASE_LEXICA,
            getattr(error, "fila", "?"),
            getattr(error, "columna", "?"),
            getattr(error, "lexema", ""),
            getattr(error, "mensaje", str(error)),
        ))

    # --- Fase 2: análisis sintáctico ---------------------------------------
    resultado.fase_alcanzada = FASE_SINTACTICA
    parser = Parser(resultado.tokens)
    try:
        cst, _pasos, errores_sint = parser.parse_con_pasos()
    except Exception as e:                                  # noqa: BLE001
        resultado.errores.append(ErrorCompilacion(
            FASE_SINTACTICA, "?", "?", "", str(e)))
        return resultado

    resultado.cst = cst
    for error in errores_sint:
        fila, columna, lexema, mensaje = _desglosar_sintactico(error)
        resultado.errores.append(ErrorCompilacion(
            FASE_SINTACTICA, fila, columna, lexema, mensaje))

    # Con el árbol roto, seguir analizando produce ruido, no información.
    if resultado.errores:
        return resultado

    # --- Fase 3: análisis semántico ----------------------------------------
    resultado.fase_alcanzada = FASE_SEMANTICA
    analizador = AnalizadorSemantico(cst)
    errores_sem = analizador.analizar()
    resultado.tabla = analizador.tabla
    for error in errores_sem:
        resultado.errores.append(ErrorCompilacion(
            FASE_SEMANTICA, error.fila, error.columna,
            error.lexema, error.mensaje, error.regla,
        ))

    # Requisito del enunciado: con errores semánticos NO se genera salida.
    if resultado.errores:
        return resultado

    # --- Fase 4: traducción orientada por la sintaxis ----------------------
    resultado.fase_alcanzada = "SDT"
    resultado.codigo_gleam = TraductorSDT(cst, analizador.tabla).traducir()
    return resultado


# =============================================================================
#  INTERFAZ DE LÍNEA DE COMANDOS
# =============================================================================

def main(argv=None):
    parser_cli = argparse.ArgumentParser(
        description="Compilador de Paisascript a Gleam (Entrega Final).")
    parser_cli.add_argument("entrada", help="archivo .txt o .paisa a compilar")
    parser_cli.add_argument("-o", "--salida", help="archivo .gleam de salida")
    parser_cli.add_argument("--tabla", action="store_true",
                            help="mostrar también la tabla de símbolos")
    args = parser_cli.parse_args(argv)

    ruta = Path(args.entrada)
    if not ruta.exists():
        print(f"No se encontró el archivo: {ruta}", file=sys.stderr)
        return 2

    resultado = compilar(ruta.read_text(encoding="utf-8"))

    print("=" * 70)
    print(f"  Compilando: {ruta.name}")
    print("=" * 70)

    if args.tabla and resultado.tabla is not None:
        print()
        print("--- TABLA DE SÍMBOLOS " + "-" * 48)
        filas = resultado.tabla.filas()
        if filas:
            for fila in filas:
                print(f"  {fila['Ámbito']:<16} {fila['Lexema']:<18} "
                      f"{fila['Tipo']:<12} {fila['Categoría']:<10} "
                      f"fila {fila['Fila']}")
        else:
            print("  (vacía)")

    if resultado.errores:
        print()
        print("--- ERRORES " + "-" * 58)
        print(resultado.reporte())
        print()
        print("No se generó código de salida.")
        return 1

    print()
    print("--- SALIDA EN GLEAM " + "-" * 50)
    print()
    print(resultado.codigo_gleam)

    if args.salida:
        destino = Path(args.salida)
        destino.write_text(resultado.codigo_gleam, encoding="utf-8")
        print(f"Código escrito en: {destino}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
