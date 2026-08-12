import re

def analizar_lexico(codigo_fuente):
    # 1. Definición de tokens y expresiones regulares (Basado en la Parte 2)
    # IMPORTANTE: El orden importa. Las palabras clave deben ir antes que el IDENTIFICADOR.
    especificacion_tokens = [
        ('KW_ASIGNACION',   r'pille_pues\b'),
        ('KW_LECTURA',      r'escuche_pues\b'),
        ('KW_IMPRESION',    r'hable_pues\b'),
        ('KW_MATCH',        r'pillemos\b'),
        ('KW_FLECHA',       r'pa_que_lleve\b'),
        ('BOOL_VERDADERO',  r'sizas\b'),
        ('BOOL_FALSO',      r'naranjas\b'),
        ('OP_LOG_AND',      r'y_tambien\b'),
        ('OP_LOG_OR',       r'o_que\b'),
        ('OP_LOG_NOT',      r'nanai\b'),
        ('OP_IGUALDAD',     r'igualito\b'),
        ('OP_DESIGUALDAD',  r'distinto\b'),
        ('OP_MAYOR_IGUAL',  r'>='),
        ('OP_MENOR_IGUAL',  r'<='),
        ('OP_MAYOR',        r'>'),
        ('OP_MENOR',        r'<'),
        ('COMODIN',         r'_(?![a-zA-Z0-9_])'), # Guion bajo que no sea parte de un identificador
        ('IDENTIFICADOR',   r'[a-z_][a-zA-Z0-9_]*'),
        ('NUM_ENTERO',      r'\d+'),
        ('CADENA_LITERAL',  r'"[^"]*"'),
        ('OP_CONCATENAR',   r'<>'),
        ('OP_SUMA',         r'\+'),
        ('OP_RESTA',        r'-'),
        ('OP_MULT',         r'\*'),
        ('OP_DIV',          r'/'),
        ('OP_ASIGNACION',   r'='),
        ('PAR_ABRE',        r'\('),
        ('PAR_CIERRA',      r'\)'),
        ('LLAVE_ABRE',      r'\{'),
        ('LLAVE_CIERRA',    r'\}'),
        ('ESPACIOS',        r'[ \t\n]+'), # Espacios, tabulaciones y saltos de línea
        ('ERROR_LEXICO',    r'.'),        # Cualquier otro carácter que no haga match
    ]

    # 2. Compilar todas las expresiones regulares en un solo patrón
    regex_unificado = '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in especificacion_tokens)
    
    # 3. Imprimir el encabezado de la tabla
    print(f"{'Lexema':<25} | {'Tipo de token'}")
    print("-" * 50)

    # 4. Recorrer la cadena y tokenizar
    for coincidencia in re.finditer(regex_unificado, codigo_fuente):
        tipo = coincidencia.lastgroup
        lexema = coincidencia.group(tipo)

        if tipo == 'ESPACIOS':
            continue # Ignoramos los espacios en blanco
        elif tipo == 'ERROR_LEXICO':
            print(f">>> ERROR LÉXICO REPORTADO: Carácter no reconocido '{lexema}' en el índice {coincidencia.start()} <<<")
        else:
            # Imprimir la fila de la tabla
            print(f"{lexema:<25} | {tipo}")

# ==========================================
# PRUEBA DEL ANALIZADOR
# ==========================================
if __name__ == '__main__':
    # Cadena de ejemplo válida (combina lectura, aritmética, cadenas y escritura)
    codigo_prueba = """
    escuche_pues(edad)
    pille_pues calculo = (edad * 2) + 5
    pille_pues mensaje = "El resultado es: " <> calculo
    hable_pues(mensaje)
    @ # Esto debe generar un error léxico
    """
    
    print("Iniciando análisis léxico de Paisascript...\n")
    analizar_lexico(codigo_prueba)