"""
Módulo: arbol_grafico.py
Descripción: Generador y visualizador del Árbol de Derivación Sintáctica (CST).
"""

def capturar_arbol_ascii(nodo, prefijo="", es_ultimo=True) -> str:
    """Renderiza el árbol de derivación en texto plano para la consola."""
    if not isinstance(nodo, dict):
        return ""

    lineas = []
    tipo = nodo.get("tipo", "Nodo")
    conector = "└── " if es_ultimo else "├── "
    lineas.append(prefijo + conector + tipo)

    nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")
    hijos = nodo.get("hijos", [])

    for i, hijo in enumerate(hijos):
        res = capturar_arbol_ascii(hijo, nuevo_prefijo, i == len(hijos) - 1)
        if res:
            lineas.append(res)

    return "\n".join(lineas)


def imprimir_arbol_ascii(nodo):
    print(capturar_arbol_ascii(nodo))


def exportar_dot(ast, ruta_archivo="arbol_sintactico.dot") -> str:
    """Genera el código DOT del Árbol de Derivación Sintáctica con nodos coloreados."""
    lineas = [
        "digraph CST {", 
        '    graph [bgcolor="transparent", rankdir=TB, nodesep=0.2, ranksep=0.4];',
        '    edge [color="#94A3B8", penwidth=1.2];'
    ]
    contador = [0]

    def _limpiar(texto):
        if texto is None:
            return ""
        return str(texto).replace('"', '\\"').replace('<', '&lt;').replace('>', '&gt;')

    def recorrer(nodo, id_padre=None):
        if not isinstance(nodo, dict):
            return
            
        contador[0] += 1
        id_actual = f"node{contador[0]}"
        tipo = nodo.get("tipo", "Nodo")
        es_terminal = nodo.get("es_terminal", False)
        
        lbl = _limpiar(tipo)
        
        # Estilos diferenciados según el tipo de nodo en la derivación
        if es_terminal:
            if tipo == "ε":
                lineas.append(f'    {id_actual} [label="{lbl}", shape=ellipse, style="filled", color="#64748B", fontname="Courier", fontcolor="#94A3B8", fillcolor="#1E293B"];')
            else:
                lineas.append(f'    {id_actual} [label="{lbl}", shape=box, style="filled,rounded", color="#10B981", fontname="Courier", fontcolor="#F8FAFC", fillcolor="#065F46"];')
        else:
            lineas.append(f'    {id_actual} [label="{lbl}", shape=box, style="filled,rounded", color="#38BDF8", fontname="Courier-Bold", fontcolor="#F8FAFC", fillcolor="#0F172A"];')
        
        if id_padre:
            lineas.append(f"    {id_padre} -> {id_actual};")

        for hijo in nodo.get("hijos", []):
            recorrer(hijo, id_padre=id_actual)

    recorrer(ast)
    lineas.append("}")
    dot_codigo = "\n".join(lineas)

    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(dot_codigo)
    except Exception:
        pass

    return dot_codigo


def generar_grafo_ast(ast) -> str:
    return exportar_dot(ast)


def mostrar_arbol_sintactico(ast):
    imprimir_arbol_ascii(ast)
    return exportar_dot(ast)
