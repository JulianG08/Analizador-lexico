"""
Módulo: parser.py
Descripción: Analizador Sintáctico Descendente Recursivo adaptado a la 
gramática LL(1) de Paisascript.
"""

class ErrorSintactico(Exception):
    """Excepción personalizada para errores de análisis sintáctico."""
    pass

class Parser:
    def __init__(self, tokens):
        # Filtramos espacios y comentarios si el lexer no lo ha hecho ya
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
        if not tok: return None
        if hasattr(tok, 'tipo'):
            return tok.tipo.name if hasattr(tok.tipo, 'name') else str(tok.tipo)
        return getattr(tok, 'type', None)

    def _obtener_lexema(self, token=None):
        tok = token or self.token_actual
        if not tok: return ""
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
    # 3.1 PROGRAMA Y DECLARACIONES
    # ==========================================

    def parse_programa(self):
        declaraciones = []
        while self.token_actual is not None:
            declaraciones.append(self.parse_declaracion())
        return {
            "tipo": "Programa",
            "declaraciones": declaraciones
        }

    def parse_declaracion(self):
        if self._obtener_tipo() == "KW_FUNCION" or self._obtener_lexema() == "hagale_pues":
            return self.parse_def_funcion()
        else:
            return self.parse_sentencia()

    # ==========================================
    # 3.2 DEFINICIÓN DE FUNCIONES
    # ==========================================

    def parse_def_funcion(self):
        """hagale_pues IDENTIFICADOR ( <parametros> ) <tipo_retorno> dele_pues <bloque> ya_quedo"""
        self.match("KW_FUNCION", "hagale_pues")
        id_tok = self.match("IDENTIFICADOR")
        self.match("PAR_ABRE", "(")
        
        parametros = []
        if self._obtener_tipo() != "PAR_CIERRA" and self._obtener_lexema() != ")":
            parametros = self.parse_parametros()
            
        self.match("PAR_CIERRA", ")")
        
        tipo_retorno = None
        if self._obtener_tipo() == "KW_FLECHA" or self._obtener_lexema() == "pa_que_lleve":
            self.avanzar()
            tipo_retorno = self.parse_tipo()

        self.match("KW_HACER", "dele_pues")
        bloque = self.parse_bloque(("KW_FIN_FUNCION", "ya_quedo"))
        self.match("KW_FIN_FUNCION", "ya_quedo")

        return {
            "tipo": "DefFuncion",
            "nombre": self._obtener_lexema(id_tok),
            "parametros": parametros,
            "tipo_retorno": tipo_retorno,
            "cuerpo": bloque
        }

    def parse_parametros(self):
        """<tipo> IDENTIFICADOR <param_resto>"""
        params = []
        while True:
            tipo_param = self.parse_tipo()
            id_param = self.match("IDENTIFICADOR")
            params.append({"tipo_dato": tipo_param, "nombre": self._obtener_lexema(id_param)})
            
            if self._obtener_tipo() == "COMA" or self._obtener_lexema() == ",":
                self.avanzar()
            else:
                break
        return params

    def parse_tipo(self):
        tipo_tok = self.match(
            "KW_TIPO_ENTERO", "KW_TIPO_REAL", "KW_TIPO_CADENA", "KW_TIPO_BOOLEANO",
            "numerito", "quebradito", "cuento", "siono"
        )
        return self._obtener_lexema(tipo_tok)

    # ==========================================
    # 3.3 BLOQUES Y SENTENCIAS
    # ==========================================

    def parse_bloque(self, tokens_cierre):
        """Parsea una lista de sentencias hasta encontrar un token de cierre."""
        instrucciones = []
        while self.token_actual:
            tipo_act = self._obtener_tipo()
            lex_act = self._obtener_lexema()
            if tipo_act in tokens_cierre or lex_act in tokens_cierre:
                break
            instrucciones.append(self.parse_sentencia())
            
        return {
            "tipo": "Bloque",
            "instrucciones": instrucciones
        }

    def parse_sentencia(self):
        if not self.token_actual:
            raise ErrorSintactico("Fin de archivo inesperado.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

        if tipo == "KW_DECLARACION" or lexema == "pille_pues":
            return self.parse_sent_declaracion()
        elif tipo == "KW_LECTURA" or lexema == "escuche_pues":
            return self.parse_sent_lectura()
        elif tipo == "KW_IMPRESION" or lexema == "hable_pues":
            return self.parse_sent_impresion()
        elif tipo == "KW_SI" or lexema == "si_acaso":
            return self.parse_sent_si()
        elif tipo == "KW_MIENTRAS" or lexema == "mientras_que":
            return self.parse_sent_mientras()
        elif tipo == "KW_PARA" or lexema == "pa_cada":
            return self.parse_sent_para()
        elif tipo == "KW_PILLEMOS" or lexema == "pillemos":
            return self.parse_sent_pillemos()
        elif tipo == "KW_RETORNAR" or lexema == "entregue_pues":
            return self.parse_sent_retornar()
        elif tipo == "IDENTIFICADOR":
            return self.parse_asignacion_o_llamada()
        else:
            raise ErrorSintactico(
                f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
                f"Inicio de sentencia no válido con '{lexema}'"
            )

    def parse_sent_declaracion(self):
        """pille_pues <tipo_opcional> IDENTIFICADOR = <expresion>"""
        self.match("KW_DECLARACION", "pille_pues")
        
        tipo_dato = None
        if self._obtener_lexema() in ("numerito", "quebradito", "cuento", "siono"):
            tipo_dato = self.parse_tipo()
            
        id_tok = self.match("IDENTIFICADOR")
        self.match("OP_ASIGNACION", "=")
        valor = self.parse_expresion()

        return {
            "tipo": "Declaracion",
            "tipo_dato": tipo_dato,
            "identificador": self._obtener_lexema(id_tok),
            "valor": valor
        }

    def parse_sent_lectura(self):
        """escuche_pues ( IDENTIFICADOR )"""
        self.match("KW_LECTURA", "escuche_pues")
        self.match("PAR_ABRE", "(")
        id_tok = self.match("IDENTIFICADOR")
        self.match("PAR_CIERRA", ")")
        
        return {
            "tipo": "Lectura",
            "identificador": self._obtener_lexema(id_tok)
        }

    def parse_sent_impresion(self):
        """hable_pues ( <expresion> )"""
        self.match("KW_IMPRESION", "hable_pues")
        self.match("PAR_ABRE", "(")
        expresion = self.parse_expresion()
        self.match("PAR_CIERRA", ")")

        return {
            "tipo": "Impresion",
            "expresion": expresion
        }

    def parse_sent_retornar(self):
        """entregue_pues <expresion>"""
        self.match("KW_RETORNAR", "entregue_pues")
        expresion = self.parse_expresion()

        return {
            "tipo": "Retorno",
            "expresion": expresion
        }

    def parse_asignacion_o_llamada(self):
        """IDENTIFICADOR = <expresion> | IDENTIFICADOR ( <argumentos> )"""
        id_tok = self.match("IDENTIFICADOR")
        
        if self._obtener_tipo() == "PAR_ABRE" or self._obtener_lexema() == "(":
            # Es una llamada a función usada como sentencia
            self.avanzar()
            argumentos = self.parse_argumentos()
            self.match("PAR_CIERRA", ")")
            return {
                "tipo": "LlamadaFuncion",
                "identificador": self._obtener_lexema(id_tok),
                "argumentos": argumentos
            }
        else:
            # Es una reasignación (shadowing contextual)
            self.match("OP_ASIGNACION", "=")
            valor = self.parse_expresion()
            return {
                "tipo": "Asignacion",
                "identificador": self._obtener_lexema(id_tok),
                "valor": valor
            }

    # ==========================================
    # 3.4 a 3.7 ESTRUCTURAS DE CONTROL
    # ==========================================

    def parse_sent_si(self):
        """si_acaso <expresion> entonces_pues <bloque> [ sino_pues <bloque> ] asi_quedo"""
        self.match("KW_SI", "si_acaso")
        condicion = self.parse_expresion()
        self.match("KW_ENTONCES", "entonces_pues")
        
        bloque_si = self.parse_bloque(("KW_SINO", "sino_pues", "KW_FIN_SI", "asi_quedo"))
        bloque_sino = None

        if self._obtener_tipo() == "KW_SINO" or self._obtener_lexema() == "sino_pues":
            self.avanzar()
            bloque_sino = self.parse_bloque(("KW_FIN_SI", "asi_quedo"))

        self.match("KW_FIN_SI", "asi_quedo")

        return {
            "tipo": "Condicional",
            "condicion": condicion,
            "bloque_si": bloque_si,
            "bloque_sino": bloque_sino
        }

    def parse_sent_mientras(self):
        """mientras_que <expresion> dele_pues <bloque> hasta_ahi"""
        self.match("KW_MIENTRAS", "mientras_que")
        condicion = self.parse_expresion()
        self.match("KW_HACER", "dele_pues")
        
        bloque = self.parse_bloque(("KW_FIN_MIENTRAS", "hasta_ahi"))
        self.match("KW_FIN_MIENTRAS", "hasta_ahi")

        return {
            "tipo": "Mientras",
            "condicion": condicion,
            "bloque": bloque
        }

    def parse_sent_para(self):
        """pa_cada IDENTIFICADOR desde <expresion> hasta <expresion> [de_a <expresion>] dele_pues <bloque> listo_pues"""
        self.match("KW_PARA", "pa_cada")
        id_tok = self.match("IDENTIFICADOR")
        
        self.match("KW_DESDE", "desde")
        desde_expr = self.parse_expresion()
        
        self.match("KW_HASTA", "hasta")
        hasta_expr = self.parse_expresion()
        
        paso_expr = None
        if self._obtener_tipo() == "KW_PASO" or self._obtener_lexema() == "de_a":
            self.avanzar()
            paso_expr = self.parse_expresion()
            
        self.match("KW_HACER", "dele_pues")
        bloque = self.parse_bloque(("KW_FIN_PARA", "listo_pues"))
        self.match("KW_FIN_PARA", "listo_pues")
        
        return {
            "tipo": "Para",
            "identificador": self._obtener_lexema(id_tok),
            "desde": desde_expr,
            "hasta": hasta_expr,
            "paso": paso_expr,
            "bloque": bloque
        }

    def parse_sent_pillemos(self):
        """pillemos <expresion> { <lista_casos> }"""
        self.match("KW_PILLEMOS", "pillemos")
        expresion = self.parse_expresion()
        self.match("LLAVE_ABRE", "{")
        
        casos = []
        while self.token_actual and self._obtener_lexema() != "}":
            casos.append(self.parse_caso())
            
        self.match("LLAVE_CIERRA", "}")
        
        return {
            "tipo": "Pillemos",
            "expresion": expresion,
            "casos": casos
        }

    def parse_caso(self):
        """<patron> pa_que_lleve <cuerpo_caso>"""
        patron = self.parse_patron()
        self.match("KW_FLECHA", "pa_que_lleve")
        
        if self._obtener_tipo() == "LLAVE_ABRE" or self._obtener_lexema() == "{":
            self.avanzar()
            cuerpo = self.parse_bloque(("LLAVE_CIERRA", "}"))
            self.match("LLAVE_CIERRA", "}")
        else:
            cuerpo = self.parse_sentencia()
            
        return {
            "tipo": "Caso",
            "patron": patron,
            "cuerpo": cuerpo
        }

    def parse_patron(self):
        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()
        
        if tipo in ("NUM_ENTERO", "NUM_REAL", "CADENA_LITERAL"):
            self.avanzar()
            return {"tipo": "PatronLiteral", "valor": lexema}
        elif tipo in ("LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
            self.avanzar()
            return {"tipo": "PatronBooleano", "valor": lexema}
        elif tipo == "IDENTIFICADOR":
            self.avanzar()
            return {"tipo": "PatronIdentificador", "nombre": lexema}
        elif tipo == "COMODIN" or lexema == "_":
            self.avanzar()
            return {"tipo": "PatronComodin", "valor": "_"}
            
        raise ErrorSintactico(f"Patrón inválido: '{lexema}'")

    # ==========================================
    # 3.8 EXPRESIONES (Precedencia estricta LL1)
    # ==========================================

    def parse_expresion(self):
        return self.parse_expr_o()

    def parse_expr_o(self):
        nodo_izq = self.parse_expr_y()
        ops = ("OP_O", "o_que")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_y()
            }
        return nodo_izq

    def parse_expr_y(self):
        nodo_izq = self.parse_expr_igualdad()
        ops = ("OP_Y", "y_tambien")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_igualdad()
            }
        return nodo_izq

    def parse_expr_igualdad(self):
        nodo_izq = self.parse_expr_relacional()
        ops = ("OP_IGUAL", "OP_DISTINTO", "igualito", "distinto", "==", "!=")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_relacional()
            }
        return nodo_izq

    def parse_expr_relacional(self):
        nodo_izq = self.parse_expr_concat()
        ops = ("OP_MAYOR", "OP_MENOR", "OP_MAYOR_IGUAL", "OP_MENOR_IGUAL", ">", "<", ">=", "<=")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_concat()
            }
        return nodo_izq

    def parse_expr_concat(self):
        nodo_izq = self.parse_expr_aditiva()
        ops = ("OP_CONCAT", "<>")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_aditiva()
            }
        return nodo_izq

    def parse_expr_aditiva(self):
        nodo_izq = self.parse_expr_multiplicativa()
        ops = ("OP_SUMA", "OP_RESTA", "+", "-")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_multiplicativa()
            }
        return nodo_izq

    def parse_expr_multiplicativa(self):
        nodo_izq = self.parse_expr_potencia()
        ops = ("OP_MULT", "OP_DIV", "OP_MODULO", "*", "/", "%")
        while self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_potencia()
            }
        return nodo_izq

    def parse_expr_potencia(self):
        # La potencia asocia a la derecha
        nodo_izq = self.parse_expr_unaria()
        ops = ("OP_POTENCIA", "**")
        if self.token_actual and (self._obtener_tipo() in ops or self._obtener_lexema() in ops):
            op_tok = self.token_actual
            self.avanzar()
            nodo_izq = {
                "tipo": "OperacionBinaria",
                "operador": self._obtener_lexema(op_tok),
                "izquierda": nodo_izq,
                "derecha": self.parse_expr_potencia()  # Llamada recursiva para asoc. derecha
            }
        return nodo_izq

    def parse_expr_unaria(self):
        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()
        
        if tipo in ("OP_NO", "OP_RESTA", "nanai", "-") or lexema in ("nanai", "-"):
            op_tok = self.token_actual
            self.avanzar()
            return {
                "tipo": "OperacionUnaria",
                "operador": self._obtener_lexema(op_tok),
                "expresion": self.parse_expr_unaria()
            }
            
        return self.parse_expr_primaria()

    def parse_expr_primaria(self):
        if not self.token_actual:
            raise ErrorSintactico("Expresión incompleta al final del archivo.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

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
            return {"tipo": "Literal", "valor_tipo": "cuento", "valor": lexema}

        if tipo in ("LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
            self.avanzar()
            return {"tipo": "Literal", "valor_tipo": "siono", "valor": lexema}

        if tipo == "IDENTIFICADOR":
            id_tok = self.token_actual
            self.avanzar()
            # Validar Sufijo (Llamada a función)
            if self._obtener_tipo() == "PAR_ABRE" or self._obtener_lexema() == "(":
                self.avanzar()
                argumentos = self.parse_argumentos()
                self.match("PAR_CIERRA", ")")
                return {
                    "tipo": "LlamadaFuncion",
                    "identificador": self._obtener_lexema(id_tok),
                    "argumentos": argumentos
                }
            return {"tipo": "Identificador", "nombre": self._obtener_lexema(id_tok)}

        raise ErrorSintactico(
            f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
            f"Expresión no válida iniciando con '{lexema}'"
        )

    def parse_argumentos(self):
        """<arg_lista> | e"""
        args = []
        if self._obtener_tipo() != "PAR_CIERRA" and self._obtener_lexema() != ")":
            while True:
                args.append(self.parse_expresion())
                if self._obtener_tipo() == "COMA" or self._obtener_lexema() == ",":
                    self.avanzar()
                else:
                    break
        return args