"""
Módulo: parser_ll1.py
Descripción: Motor de Análisis Predictivo Descendente LL(1) mediante Pila.
Genera la traza paso a paso y construye el árbol de derivación sintáctica.
"""
from tabla_ll1 import generar_datos_completos_ll1, es_terminal

class NodoArbol:
    """Estructura para los nodos del Árbol de Sintaxis Concreta (CST)."""
    def __init__(self, valor, tipo="no_terminal"):
        self.valor = valor
        self.tipo = tipo  # 'no_terminal', 'terminal', 'epsilon'
        self.hijos = []

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)

class ErrorSintacticoLL1(Exception):
    def __init__(self, mensaje, paso):
        super().__init__(f"Error en paso {paso}: {mensaje}")
        self.paso = paso

def obtener_simbolo_token(token):
    """Mapea el objeto token del lexer al símbolo terminal de la gramática."""
    
    # 1. Manejo del token EOF simulado interno de parser_ll1
    if getattr(token, "tipo", None) == "EOF":
        return "$"
        
    # 2. Manejo de los tokens reales del lexer (Enums)
    if hasattr(token.tipo, "name"):
        nombre_token = token.tipo.name
        
        # Traducir el fin de archivo nativo del lexer al símbolo de la gramática
        if nombre_token == "FIN_ARCHIVO":
            return "$"
            
        return nombre_token
        
    # 3. Respaldo
    return str(token.tipo)

def analisis_predictivo(tokens):
    """
    Ejecuta el análisis de pila LL(1).
    Retorna: (traza_pasos, raiz_arbol, es_valido, mensaje_error)
    """
    _, _, tabla_M, _ = generar_datos_completos_ll1()
    
    # 1. Inicialización
    raiz = NodoArbol("<programa>")
    # La pila guarda tuplas: (Símbolo_Gramatical, Nodo_Asociado)
    pila = [("$", None), ("<programa>", raiz)] 
    
    # Lista de tokens restantes (se asume que el lexer ya incluye un token EOF o lo simulamos)
    entrada = tokens.copy()
    if not entrada or entrada[-1].tipo != "EOF":
        # Clase dummy para simular el fin de cadena si el lexer no lo provee nativamente
        class TokenEOF:
            tipo = "EOF"
            lexema = "$"
            fila = -1
            columna = -1
        entrada.append(TokenEOF())

    traza = []
    paso = 1
    es_valido = True
    mensaje_error = ""

    # 2. Ciclo principal del autómata de pila
    while len(pila) > 0:
        tope_simbolo, tope_nodo = pila.pop()
        token_actual = entrada[0]
        lookahead = obtener_simbolo_token(token_actual)

        # Capturar el estado actual para la traza visual
        estado_pila = " ".join([s[0] for s in pila] + [tope_simbolo])
        estado_entrada = " ".join([obtener_simbolo_token(t) for t in entrada])
        accion = ""

        if tope_simbolo == "$":
            if lookahead == "$":
                accion = "Aceptar: Fin de cadena"
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
                break
            else:
                es_valido = False
                mensaje_error = f"Se esperaba fin de archivo, pero se encontró '{token_actual.lexema}'"
                accion = f"Error: {mensaje_error}"
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
                break

        elif es_terminal(tope_simbolo):
            if tope_simbolo == lookahead:
                accion = f"Hacer match: {tope_simbolo}"
                if tope_nodo:
                    tope_nodo.valor = f"{tope_simbolo} ({token_actual.lexema})"
                entrada.pop(0) # Consumir token
            else:
                es_valido = False
                mensaje_error = f"Se esperaba '{tope_simbolo}', se encontró '{token_actual.lexema}' en {token_actual.fila}:{token_actual.columna}"
                accion = f"Error: {mensaje_error}"
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
                break

        else: # Es un No-Terminal
            if lookahead not in tabla_M[tope_simbolo]:
                es_valido = False
                mensaje_error = f"Token inesperado '{token_actual.lexema}' para {tope_simbolo}."
                accion = f"Error: {mensaje_error}"
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
                break
                
            produccion = tabla_M[tope_simbolo][lookahead]
            
            if produccion is None:
                es_valido = False
                mensaje_error = f"Error sintáctico en {token_actual.fila}:{token_actual.columna}. No hay regla en M[{tope_simbolo}, {lookahead}]"
                accion = f"Error: {mensaje_error}"
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
                break
                
            accion = f"Expandir: {tope_simbolo} -> " + " ".join(produccion)
            
            # Expansión de la producción y construcción del árbol
            if produccion == ["ε"]:
                nodo_eps = NodoArbol("ε", "epsilon")
                tope_nodo.agregar_hijo(nodo_eps)
            else:
                # Crear los hijos y apilarlos en orden INVERSO (LIFO)
                hijos_creados = []
                for sim in produccion:
                    tipo_n = "terminal" if es_terminal(sim) else "no_terminal"
                    nuevo_nodo = NodoArbol(sim, tipo_n)
                    hijos_creados.append(nuevo_nodo)
                    tope_nodo.agregar_hijo(nuevo_nodo)
                
                # Apilar al revés para que el primero de la producción quede en el tope
                for nodo in reversed(hijos_creados):
                    pila.append((nodo.valor, nodo))

        traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada, "Acción": accion})
        paso += 1

    return traza, raiz, es_valido, mensaje_error
