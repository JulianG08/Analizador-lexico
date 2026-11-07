# -*- coding: utf-8 -*-
"""
Módulo: test_entrega_final.py
Descripción: Pruebas automáticas del compilador completo (Entrega Final).

Verifica lo que exige el enunciado sobre el encadenamiento de las cuatro
fases y sobre la fase SDT:

  * los tres archivos de prueba obligatorios se comportan como se espera;
  * con errores semánticos NO se genera código de salida;
  * el reporte de errores es unificado (fase, fila, columna, lexema, mensaje);
  * la traducción cubre los tres bucles, el condicional, el calce de patrones
    y las llamadas a función;
  * el Gleam generado es estructuralmente válido (llaves balanceadas, ningún
    bloque que termine en `let`, todo `import` que se usa está declarado).

Ejecutar:  python test_entrega_final.py
"""

from pathlib import Path

from compilador import compilar, FASE_SEMANTICA, FASE_SINTACTICA

RAIZ = Path(__file__).parent
PRUEBAS = RAIZ / "pruebas_entrega_final"

# Módulos de la biblioteca estándar de Gleam que el traductor puede emitir.
MODULOS_CONOCIDOS = {
    "gleam/io", "gleam/int", "gleam/float", "gleam/list",
    "gleam/string", "gleam/result", "gleam/bool", "gleam/erlang",
}


def validar_gleam(codigo):
    """Comprobaciones estructurales sobre el código generado."""
    problemas = []

    if codigo.count("{") != codigo.count("}"):
        problemas.append(
            f"llaves desbalanceadas ({codigo.count('{')} abren, "
            f"{codigo.count('}')} cierran)")
    if codigo.count("(") != codigo.count(")"):
        problemas.append("paréntesis desbalanceados")

    lineas = codigo.splitlines()

    # Ningún bloque puede terminar en `let`: en Gleam todo bloque devuelve
    # un valor, así que eso sería un error de compilación.
    for indice, linea in enumerate(lineas):
        if linea.strip().startswith("let ") and indice + 1 < len(lineas):
            siguiente = lineas[indice + 1].strip()
            if siguiente in ("}", "})"):
                problemas.append(f"línea {indice + 1}: el bloque termina en 'let'")

    # Todo módulo usado debe estar importado.
    importados = {l.split()[1] for l in lineas if l.startswith("import ")}
    for modulo in MODULOS_CONOCIDOS:
        alias = modulo.split("/")[1]
        usado = any(f"{alias}." in l for l in lineas if not l.startswith("import"))
        if usado and modulo not in importados:
            problemas.append(f"se usa '{alias}.' pero falta 'import {modulo}'")

    for modulo in importados:
        if modulo not in MODULOS_CONOCIDOS:
            problemas.append(f"import desconocido: {modulo}")

    return problemas


def main():
    fallos = 0
    total = 0

    # ------------------------------------------------------------------
    # Caso 1: programa sin errores -> las cuatro fases y salida completa
    # ------------------------------------------------------------------
    total += 1
    codigo = (PRUEBAS / "1_sin_errores.paisa").read_text(encoding="utf-8")
    resultado = compilar(codigo)
    problemas = validar_gleam(resultado.codigo_gleam)
    if not resultado.exitoso or problemas:
        fallos += 1
        print("FALLO caso 1 (1_sin_errores.paisa)")
        print("  errores:", [str(e) for e in resultado.errores])
        print("  problemas de la salida:", problemas)
    else:
        print(f"OK   caso 1  — sin errores: las 4 fases corren y producen "
              f"{len(resultado.codigo_gleam.splitlines())} líneas de Gleam válido")

    # ------------------------------------------------------------------
    # Caso 2: errores semánticos -> NO se genera salida
    # ------------------------------------------------------------------
    total += 1
    codigo = (PRUEBAS / "2_errores_semanticos.paisa").read_text(encoding="utf-8")
    resultado = compilar(codigo)
    semanticos = resultado.errores_de(FASE_SEMANTICA)
    reglas = {e.regla for e in semanticos}
    completos = all(
        e.fila != "?" and e.columna != "?" and e.lexema and e.mensaje
        for e in semanticos)
    if (resultado.codigo_gleam or len(semanticos) < 8
            or not completos
            or not {"SEM-1", "SEM-6", "SEM-7", "SEM-8"} <= reglas):
        fallos += 1
        print("FALLO caso 2 (2_errores_semanticos.paisa)")
        print("  ¿generó salida?:", bool(resultado.codigo_gleam))
        print("  errores:", [str(e) for e in semanticos])
    else:
        print(f"OK   caso 2  — {len(semanticos)} errores semánticos "
              f"({len(reglas)} reglas distintas), con fila/columna/lexema, "
              f"y NO se generó salida")

    # ------------------------------------------------------------------
    # Caso 3: errores sintácticos -> se reportan y no hay salida
    # ------------------------------------------------------------------
    total += 1
    codigo = (PRUEBAS / "3_errores_sintacticos.paisa").read_text(encoding="utf-8")
    resultado = compilar(codigo)
    sintacticos = resultado.errores_de(FASE_SINTACTICA)
    con_fila = [e for e in sintacticos if e.fila != "?"]
    if resultado.codigo_gleam or len(sintacticos) < 2 or not con_fila:
        fallos += 1
        print("FALLO caso 3 (3_errores_sintacticos.paisa)")
        print("  ¿generó salida?:", bool(resultado.codigo_gleam))
        print("  errores:", [str(e) for e in sintacticos])
    else:
        print(f"OK   caso 3  — {len(sintacticos)} errores sintácticos "
              f"(recuperación), {len(con_fila)} con fila, y NO se generó salida")

    # ------------------------------------------------------------------
    # Caso 4: los tres bucles se traducen a recursión de cola
    # ------------------------------------------------------------------
    total += 1
    fuente = '''
hagale_pues demo(numerito n) pa_que_lleve numerito dele_pues
    pille_pues numerito suma = 0
    pille_pues numerito i = 1
    mientras_que i <= n dele_pues
        pille_pues suma = suma + i
        pille_pues i = i + 1
    hasta_ahi
    entregue_pues suma
ya_quedo

pa_cada k desde 0 hasta 6 de_a 2 dele_pues
    hable_pues("k = " <> k)
listo_pues

pille_pues numerito v = 0
repita_pues
    pille_pues v = v + 1
hasta_que v >= 3

hable_pues("total: " <> demo(5))
'''
    resultado = compilar(fuente)
    salida = resultado.codigo_gleam
    tiene_recursion = salida.count("fn bucle_") >= 3
    tiene_range = "list.range(" in salida or "fn bucle_" in salida
    if not resultado.exitoso or not tiene_recursion or validar_gleam(salida):
        fallos += 1
        print("FALLO caso 4 (los tres bucles)")
        print("  errores:", [str(e) for e in resultado.errores])
        print("  problemas:", validar_gleam(salida))
        print(salida)
    else:
        print(f"OK   caso 4  — los tres bucles generan "
              f"{salida.count('fn bucle_')} funciones recursivas de cola")

    # ------------------------------------------------------------------
    # Caso 5: la fase SDT elige el operador según el tipo (Int vs Float)
    # ------------------------------------------------------------------
    total += 1
    fuente = '''
pille_pues quebradito a = 2.5
pille_pues quebradito b = 1.5
pille_pues quebradito suma = a + b
pille_pues numerito x = 2
pille_pues numerito y = 3
pille_pues numerito producto = x * y
hable_pues("real: " <> suma)
hable_pues("entero: " <> producto)
'''
    resultado = compilar(fuente)
    salida = resultado.codigo_gleam
    usa_flotante = "a +. b" in salida
    usa_entero = "x * y" in salida
    convierte = "float.to_string(" in salida and "int.to_string(" in salida
    if not (resultado.exitoso and usa_flotante and usa_entero and convierte):
        fallos += 1
        print("FALLO caso 5 (operadores según el tipo)")
        print("  errores:", [str(e) for e in resultado.errores])
        print(salida)
    else:
        print("OK   caso 5  — SDT emite '+.' para Float, '*' para Int e "
              "inserta int.to_string / float.to_string en la concatenación")

    # ------------------------------------------------------------------
    # Caso 6: retorno anticipado reestructurado (Gleam no tiene `return`)
    # ------------------------------------------------------------------
    total += 1
    fuente = '''
hagale_pues es_par(numerito n) pa_que_lleve siono dele_pues
    si_acaso n % 2 igualito 0 entonces_pues
        entregue_pues sizas
    asi_quedo
    entregue_pues naranjas
ya_quedo

si_acaso es_par(4) entonces_pues
    hable_pues("es par")
sino_pues
    hable_pues("es impar")
asi_quedo
'''
    resultado = compilar(fuente)
    salida = resultado.codigo_gleam
    # El `entregue_pues naranjas` final debe haber quedado DENTRO de la rama
    # False del case, no suelto después de él.
    bien_estructurado = "False -> {" in salida and salida.count("case") >= 1
    if not resultado.exitoso or not bien_estructurado or validar_gleam(salida):
        fallos += 1
        print("FALLO caso 6 (retorno anticipado)")
        print("  errores:", [str(e) for e in resultado.errores])
        print(salida)
    else:
        print("OK   caso 6  — el retorno anticipado se reestructura: lo que "
              "seguía pasa a la rama False del case")

    print()
    if fallos:
        print(f"RESULTADO: {fallos}/{total} prueba(s) fallaron.")
        raise SystemExit(1)
    print(f"RESULTADO: {total}/{total} pruebas superadas.")


if __name__ == "__main__":
    main()
