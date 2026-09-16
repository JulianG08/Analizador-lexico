"""
Módulo: tabla_ll1.py
Descripción: Generador y visualizador de la Tabla de Análisis Sintáctico LL(1) M[A, a].
"""

# Categorías visuales para la consola
COLOR_TITULO = "\033[1;36m"
COLOR_HEADER = "\033[1;33m"
R = "\033[0m"

# Definición de la Gramática LL(1)
GRAMATICA = {
    "Programa (P)": [
        ("pille_pues", "P -> S P"),
        ("parce_si", "P -> S P"),
        ("mientras_parce", "P -> S P"),
        ("hable_pues", "P -> S P"),
        ("IDENTIFICADOR", "P -> S P"),
        ("$", "P -> ε"),
        ("}", "P -> ε")
    ],
    "Sentencia (S)": [
        ("pille_pues", "S -> Declaracion (D)"),
        ("parce_si", "S -> Condicional (C)"),
        ("mientras_parce", "S -> Ciclo (W)"),
        ("hable_pues", "S -> Impresion (I)"),
        ("IDENTIFICADOR", "S -> Asignacion (A)")
    ],
    "Declaracion (D)": [
        ("pille_pues", "D -> pille_pues Tipo id Valor")
    ],
    "Condicional (C)": [
        ("parce_si", "C -> parce_si ( Exp ) Bloque Sino")
    ],
    "Ciclo (W)": [
        ("mientras_parce", "W -> mientras_parce ( Exp ) Bloque")
    ],
    "Impresion (I)": [
        ("hable_pues", "I -> hable_pues ( Exp )")
    ],
    "Asignacion (A)": [
        ("IDENTIFICADOR", "A -> id = Exp")
    ]
}

TERMINALES = [
    "pille_pues", "parce_si", "mientras_parce", 
    "hable_pues", "IDENTIFICADOR", "}", "$"
]

def construir_tabla_ll1():
    """Construye la matriz M[NoTerminal, Terminal]."""
    tabla = {}
    for nt, reglas in GRAMATICA.items():
        tabla[nt] = {}
        for term in TERMINALES:
            tabla[nt][term] = "—"
        for t, produccion in reglas:
            if t in TERMINALES:
                tabla[nt][t] = produccion
    return tabla

def mostrar_tabla_ll1():
    """Imprime la tabla de análisis sintáctico formateada en consola."""
    tabla = construir_tabla_ll1()
    
    print(f"\n{COLOR_TITULO}==============================================================================")
    print("                     TABLA DE ANALISIS SINTACTICO LL(1)")
    print(f"=============================================================================={R}\n")

    # Ancho de columnas
    col_width_nt = 18
    col_width = 28

    # Imprimir Encabezados (Terminales)
    header = f"{'No Terminal':<{col_width_nt}} | " + " | ".join([f"{t:<{col_width}}" for t in TERMINALES])
    print(f"{COLOR_HEADER}{header}{R}")
    print("-" * len(header))

    # Imprimir Filas (No Terminales -> Reglas)
    for nt, terminales in tabla.items():
        fila_str = f"{nt:<{col_width_nt}} | "
        celdas = []
        for t in TERMINALES:
            regla = terminales.get(t, "—")
            # Truncar si la regla es muy larga para mantener el alineamiento
            regla_corta = (regla[:col_width-3] + "...") if len(regla) > col_width else regla
            celdas.append(f"{regla_corta:<{col_width}}")
        fila_str += " | ".join(celdas)
        print(fila_str)
    
    print("-" * len(header))
    print(f"\n{COLOR_TITULO}Explicación:{R} La celda M[A, a] indica la producción que selecciona el parser predictivo")
    print("al estar en el No Terminal A y evaluar el token terminal a.\n")

if __name__ == "__main__":
    mostrar_tabla_ll1()
