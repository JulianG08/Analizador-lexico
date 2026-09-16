"""
Módulo: arbol_grafico.py
Descripción: Generador de Árbol Sintáctico Gráfico (ASCII/Unicode en consola 
y exportador a formato Graphviz DOT).
"""

def imprimir_arbol_ascii(nodo, prefijo="", es_ultimo=True):
    """Renderiza el AST como un árbol visual en consola."""
    if isinstance(nodo, dict):
        tipo = nodo.get("tipo", "Nodo")
        
        # Etiqueta según el tipo de nodo
        if tipo == "Programa":
            label = "PROGRAMA"
        elif tipo == "Declaracion":
            label = f"DECLARACION [{nodo.get('tipo_dato')} {nodo.get('identificador')}]"
        elif tipo == "Impresion":
            label = "IMPRESION (hable_pues)"
        elif tipo == "Asignacion":
            label = f"ASIGNACION [{nodo.get('identificador')}]"
        elif tipo == "OperacionBinaria":
            label = f"OP_BINARIA ({nodo.get('operador')})"
        elif tipo == "Literal":
            label = f"LITERAL ({nodo.get('valor_tipo')}: {nodo.get('valor')})"
        elif tipo == "Identificador":
            label = f"ID ({nodo.get('nombre')})"
        else:
            label = tipo

        conector = "└── " if es_ultimo else "├── "
        print(prefijo + conector + label)

        nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")

        # Recorrer subnodos/hijos
        hijos = []
        if "instrucciones" in nodo:
            hijos.extend(nodo["instrucciones"])
        if "valor" in nodo and nodo["valor"]:
            hijos.append(nodo["valor"])
        if "expresion" in nodo and nodo["expresion"]:
            hijos.append(nodo["expresion"])
        if "izquierda" in nodo:
            hijos.append(nodo["izquierda"])
        if "derecha" in nodo:
            hijos.append(nodo["derecha"])

        for i, hijo in enumerate(hijos):
            imprimir_arbol_ascii(hijo, nuevo_prefijo, i == len(hijos) - 1)


def exportar_dot(ast, ruta_archivo="arbol_sintactico.dot"):
    """Genera un archivo .dot compatible con Graphviz para exportar a PNG."""
    lineas = ["digraph AST {", '    node [shape=box, style="filled,rounded", color="#1E293B", fontname="Courier", fontcolor="white", fillcolor="#334155"];', '    edge [color="#64748B"];']
    contador = [0]

    def recorrer(nodo, id_padre=None):
        contador[0] += 1
        id_actual = f"node{contador[0]}"
        
        if isinstance(nodo, dict):
            tipo = nodo.get("tipo", "Nodo")
            if tipo == "Programa":
                lbl = "PROGRAMA"
            elif tipo == "Declaracion":
                lbl = f"Declaración\\n{nodo.get('tipo_dato')} {nodo.get('identificador')}"
            elif tipo == "Impresion":
                lbl = "hable_pues"
            elif tipo == "OperacionBinaria":
                lbl = f"OP: {nodo.get('operador')}"
            elif tipo == "Literal":
                lbl = f"Literal\\n{nodo.get('valor')}"
            elif tipo == "Identificador":
                lbl = f"ID\\n{nodo.get('nombre')}"
            else:
                lbl = tipo

            lineas.append(f'    {id_actual} [label="{lbl}"];')
            if id_padre:
                lineas.append(f"    {id_padre} -> {id_actual};")

            hijos = []
            if "instrucciones" in nodo:
                hijos.extend(nodo["instrucciones"])
            if "valor" in nodo and nodo["valor"]:
                hijos.append(nodo["valor"])
            if "expresion" in nodo and nodo["expresion"]:
                hijos.append(nodo["expresion"])
            if "izquierda" in nodo:
                hijos.append(nodo["izquierda"])
            if "derecha" in nodo:
                hijos.append(nodo["derecha"])

            for hijo in hijos:
                recorrer(hijo, id_actual)

    recorrer(ast)
    lineas.append("}")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


def mostrar_arbol_sintactico(ast):
    """Punto de entrada para renderizar el árbol."""
    print("\n==============================================================================")
    print("                 8. ARBOL DE DERIVACION SINTACTICA GRAFICO")
    print("==============================================================================\n")
    imprimir_arbol_ascii(ast)
    exportar_dot(ast)
    print("\n[INFO] Archivo 'arbol_sintactico.dot' generado exitosamente.")
