"""
Módulo: parser.py
Descripción: Analizador Sintáctico Descendente Recursivo adaptado a las 
propiedades (tipo, lexema, fila, columna) emitidas por tu Lexer de Paisascript.
"""

class ErrorSintactico(Exception):
    """Excepción personalizada para errores de análisis sintáctico."""
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = [
            t for t in tokens 
            if self._obtener_tipo(t) not in ("ESPACIO", "COMENTARIO", "FIN_ARCHIVO", "FIN")
        ]
        self.pos = 0
        self.token_actual = self.tokens[0] if self.tokens else None

    # ==========================================
    # HELPER MAPPING (Léxico Lexer -> Parser)
    # ==========================================

    def _obtener_tipo(self, token=None):
        tok = token or self.token_actual
        if not tok:
            return None
        if hasattr(tok, 'tipo'):
            return tok.tipo.name if hasattr(tok.tipo, 'name') else str(tok.tipo)
        return getattr(tok, 'type', None)

    def _obtener_lexema(self, token=None):
        tok = token or self.token_actual
        if not tok:
            return ""
        if hasattr(tok, 'lexema'):
            return tok.lexema
        return getattr(tok, 'value', str(tok))

    def avanzar(self):
        """Avanza al siguiente token en la secuencia."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.token_actual = self.tokens[self.pos]
        else:
            self.token_actual = None

    def match(self, *esperados):
        """Verifica coincidencia por nombre de TipoToken o Lexema."""
        if self.token_actual:
            tipo = self._obtener_tipo()
            lexema = self._obtener_lexema()

            if tipo in esperados or lexema in esperados:
                token_consumido = self.token_actual
                self.avanzar()
                return token_consumido

        fila = getattr(self.token_actual, 'fila', getattr(self.token_actual, 'linea', '?'))
        col = getattr(self.token_actual, 'columna', '?')
        encontrado = self._obtener_lexema() if self.token_actual else "FIN_DE_ARCHIVO"
        esperados_str = " | ".join(map(str, esperados))

        raise ErrorSintactico(
            f"Error Sintáctico en [Fila {fila}, Columna {col}]: "
            f"Se esperaba '{esperados_str}', pero se encontró '{encontrado}'"
        )

    def parse(self):
        """Punto de entrada principal."""
        return self.parse_programa()

    # ==========================================
    # REGLAS RECURSIVAS DE LA GRAMÁTICA
    # ==========================================

    def parse_programa(self):
        instrucciones = []
        while self.token_actual is not None:
            instrucciones.append(self.parse_sentencia())
        return {
            "tipo": "Programa",
            "instrucciones": instrucciones
        }

    def parse_sentencia(self):
        if not self.token_actual:
            raise ErrorSintactico("Fin de archivo inesperado.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

        if tipo == "KW_DECLARACION" or lexema == "pille_pues":
            return self.parse_declaracion()
        elif tipo in ("KW_PARCE_SI", "PARCE_SI") or lexema == "parce_si":
            return self.parse_condicional()
        elif tipo in ("KW_MIENTRAS_PARCE", "MIENTRAS_PARCE") or lexema == "mientras_parce":
            return self.parse_ciclo()
        elif tipo == "KW_IMPRESION" or lexema in ("hable_pues", "hablar"):
            return self.parse_impresion()
        elif tipo in ("KW_TRAMITE", "TRAMITE") or lexema == "tramite":
            return self.parse_retorno()
        elif tipo == "IDENTIFICADOR":
            return self.parse_asignacion()
        else:
            raise ErrorSintactico(
                f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
                f"Inicio de sentencia no válido con '{lexema}'"
            )

    def parse_declaracion(self):
        """pille_pues <Tipo> <Identificador> [ = <Expresion> ] [;]"""
        self.match("KW_DECLARACION", "pille_pues")
        tipo_tok = self.match(
            "KW_TIPO_ENTERO", "KW_TIPO_CADENA", "KW_TIPO_REAL", "KW_TIPO_BANDERA",
            "numerito", "cuento", "quebradito", "bandera", "entero", "texto"
        )
        id_tok = self.match("IDENTIFICADOR")

        valor = None
        if self._obtener_tipo() == "OP_ASIGNACION" or self._obtener_lexema() == "=":
            self.avanzar()
            valor = self.parse_expresion()

        # Consumir ';' si está presente pero no forzarlo si se omitió
        if self._obtener_tipo() in ("PUNTO_Y_COMA", "SEMICOLON") or self._obtener_lexema() == ";":
            self.avanzar()

        return {
            "tipo": "Declaracion",
            "tipo_dato": self._obtener_lexema(tipo_tok),
            "identificador": self._obtener_lexema(id_tok),
            "valor": valor
        }

    def parse_asignacion(self):
        """IDENTIFICADOR = <Expresion> [;]"""
        id_tok = self.match("IDENTIFICADOR")
        self.match("OP_ASIGNACION", "=")
        valor = self.parse_expresion()

        if self._obtener_tipo() in ("PUNTO_Y_COMA", "SEMICOLON") or self._obtener_lexema() == ";":
            self.avanzar()

        return {
            "tipo": "Asignacion",
            "identificador": self._obtener_lexema(id_tok),
            "valor": valor
        }

    def parse_condicional(self):
        """parce_si ( <Expresion> ) <Bloque> [ sino <Bloque> ]"""
        self.match("KW_PARCE_SI", "PARCE_SI", "parce_si")
        self.match("PAR_ABRE", "(")
        condicion = self.parse_expresion()
        self.match("PAR_CIERRA", ")")

        bloque_si = self.parse_bloque()
        bloque_sino = None

        if self._obtener_tipo() in ("KW_SINO", "SINO") or self._obtener_lexema() == "sino":
            self.avanzar()
            bloque_sino = self.parse_bloque()

        return {
            "tipo": "Condicional",
            "condicion": condicion,
            "bloque_si": bloque_si,
            "bloque_sino": bloque_sino
        }

    def parse_ciclo(self):
        """mientras_parce ( <Expresion> ) <Bloque>"""
        self.match("KW_MIENTRAS_PARCE", "MIENTRAS_PARCE", "mientras_parce")
        self.match("PAR_ABRE", "(")
        condicion = self.parse_expresion()
        self.match("PAR_CIERRA", ")")
        bloque = self.parse_bloque()

        return {
            "tipo": "Ciclo",
            "condicion": condicion,
            "bloque": bloque
        }

    def parse_impresion(self):
        """hable_pues ( <Expresion> ) [;]"""
        self.match("KW_IMPRESION", "hable_pues", "hablar")
        self.match("PAR_ABRE", "(")
        expresion = self.parse_expresion()
        self.match("PAR_CIERRA", ")")

        if self._obtener_tipo() in ("PUNTO_Y_COMA", "SEMICOLON") or self._obtener_lexema() == ";":
            self.avanzar()

        return {
            "tipo": "Impresion",
            "expresion": expresion
        }

    def parse_retorno(self):
        """tramite [ <Expresion> ] [;]"""
        self.match("KW_TRAMITE", "TRAMITE", "tramite")

        expresion = None
        if self._obtener_tipo() not in ("PUNTO_Y_COMA", "SEMICOLON") and self._obtener_lexema() != ";":
            expresion = self.parse_expresion()

        if self._obtener_tipo() in ("PUNTO_Y_COMA", "SEMICOLON") or self._obtener_lexema() == ";":
            self.avanzar()

        return {
            "tipo": "Retorno",
            "expresion": expresion
        }

    def parse_bloque(self):
        """{ <ListaSentencias> }"""
        self.match("LLAVE_ABRE", "{")
        instrucciones = []

        while self.token_actual and self._obtener_tipo() != "LLAVE_CIERRA" and self._obtener_lexema() != "}":
            instrucciones.append(self.parse_sentencia())

        self.match("LLAVE_CIERRA", "}")

        return {
            "tipo": "Bloque",
            "instrucciones": instrucciones
        }

    # ==========================================
    # EXPRESIONES Y PRECEDENCIA DE OPERADORES
    # ==========================================

    def parse_expresion(self):
        return self.parse_exp_logica()

    def parse_exp_logica(self):
        nodo_izq = self.parse_exp_relacional()

        ops = ("OP_LOGICO_Y", "OP_LOGICO_O", "&&", "||")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_der = self.parse_exp_relacional()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": nodo_der
            }

        return nodo_izq

    def parse_exp_relacional(self):
        nodo_izq = self.parse_exp_aritmetica()

        ops = ("OP_IGUALDAD", "OP_DIFERENTE", "OP_MENOR", "OP_MAYOR", "OP_MENOR_IGUAL", "OP_MAYOR_IGUAL",
               "==", "!=", "<", ">", "<=", ">=")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_der = self.parse_exp_aritmetica()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": nodo_der
            }

        return nodo_izq

    def parse_exp_aritmetica(self):
        nodo_izq = self.parse_termino()

        # Incluye concatenación <> propia de Paisascript
        ops = ("OP_SUMA", "OP_RESTA", "OP_CONCAT", "+", "-", "<>")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_der = self.parse_termino()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": nodo_der
            }

        return nodo_izq

    def parse_termino(self):
        nodo_izq = self.parse_factor()

        ops = ("OP_MULT", "OP_DIV", "OP_MOD", "*", "/", "%")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_der = self.parse_factor()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": nodo_der
            }

        return nodo_izq

    def parse_factor(self):
        if not self.token_actual:
            raise ErrorSintactico("Expresión incompleta al final del archivo.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

        if tipo in ("OP_NOT", "!") or lexema == "!":
            self.avanzar()
            expresion = self.parse_factor()
            return {
                "tipo": "OperacionUnaria",
                "operador": "!",
                "expresion": expresion
            }

        if tipo in ("PAR_ABRE", "(") or lexema == "(":
            self.avanzar()
            expresion = self.parse_expresion()
            self.match("PAR_CIERRA", ")")
            return expresion

        if tipo in ("NUM_ENTERO", "NUM_REAL"):
            self.avanzar()
            return {"tipo": "Literal", "valor_tipo": tipo.lower(), "valor": lexema}

        if tipo == "CADENA_LITERAL":
            self.avanzar()
            return {"tipo": "Literal", "valor_tipo": "texto", "valor": lexema}

        if tipo == "BOOLEANO_LITERAL" or lexema in ("melo", "boleta", "true", "false"):
            self.avanzar()
            return {"tipo": "Literal", "valor_tipo": "bandera", "valor": lexema}

        if tipo == "IDENTIFICADOR":
            self.avanzar()
            return {"tipo": "Identificador", "nombre": lexema}

        raise ErrorSintactico(
            f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
            f"Expresión no válida iniciando con '{lexema}'"
        )
