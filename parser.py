"""
Módulo: parser.py
Descripción: Analizador Sintáctico Descendente Recursivo LL(1) para Paisascript.
Genera el Árbol de Derivación Sintáctica Completo (CST) según la gramática BNF.
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
    # HELPER MAPPING
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
        self.pos += 1
        if self.pos < len(self.tokens):
            self.token_actual = self.tokens[self.pos]
        else:
            self.token_actual = None

    def match(self, *esperados):
        """Consume un token terminal y retorna un nodo terminal para el árbol."""
        if self.token_actual:
            tipo = self._obtener_tipo()
            lexema = self._obtener_lexema()

            if tipo in esperados or lexema in esperados:
                self.avanzar()
                return {"tipo": f"'{lexema}'", "es_terminal": True, "hijos": []}

        fila = getattr(self.token_actual, 'fila', getattr(self.token_actual, 'linea', '?'))
        col = getattr(self.token_actual, 'columna', '?')
        encontrado = self._obtener_lexema() if self.token_actual else "FIN_DE_ARCHIVO"
        esperados_str = " | ".join(map(str, esperados))

        raise ErrorSintactico(
            f"Error Sintáctico en [Fila {fila}, Columna {col}]: "
            f"Se esperaba '{esperados_str}', pero se encontró '{encontrado}'"
        )

    def _nodo_eps(self):
        return {"tipo": "ε", "es_terminal": True, "hijos": []}

    def parse(self):
        return self.parse_programa()

    # ==========================================
    # 3.1 PROGRAMA Y DECLARACIONES
    # ==========================================

    def parse_programa(self):
        nodo_ld = self.parse_lista_declaraciones()
        return {"tipo": "<programa>", "es_terminal": False, "hijos": [nodo_ld]}

    def parse_lista_declaraciones(self):
        if self.token_actual is not None:
            nodo_dec = self.parse_declaracion()
            nodo_ld = self.parse_lista_declaraciones()
            return {"tipo": "<lista_declaraciones>", "es_terminal": False, "hijos": [nodo_dec, nodo_ld]}
        return {"tipo": "<lista_declaraciones>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_declaracion(self):
        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()
        if tipo == "KW_FUNCION" or lexema == "hagale_pues":
            nodo_df = self.parse_def_funcion()
            return {"tipo": "<declaracion>", "es_terminal": False, "hijos": [nodo_df]}
        else:
            nodo_sent = self.parse_sentencia()
            return {"tipo": "<declaracion>", "es_terminal": False, "hijos": [nodo_sent]}

    # ==========================================
    # 3.2 DEFINICIÓN DE FUNCIONES
    # ==========================================

    def parse_def_funcion(self):
        tok_hf = self.match("KW_FUNCION", "hagale_pues")
        tok_id = self.match("IDENTIFICADOR")
        tok_pa = self.match("PAR_ABRE", "(")
        nodo_params = self.parse_parametros()
        tok_pc = self.match("PAR_CIERRA", ")")
        nodo_tr = self.parse_tipo_retorno()
        tok_dp = self.match("KW_HACER", "dele_pues")
        nodo_blq = self.parse_bloque(("KW_FIN_FUNCION", "ya_quedo"))
        tok_yq = self.match("KW_FIN_FUNCION", "ya_quedo")
        return {
            "tipo": "<def_funcion>",
            "es_terminal": False,
            "hijos": [tok_hf, tok_id, tok_pa, nodo_params, tok_pc, nodo_tr, tok_dp, nodo_blq, tok_yq]
        }

    def parse_tipo_retorno(self):
        if self._obtener_tipo() == "KW_FLECHA" or self._obtener_lexema() == "pa_que_lleve":
            tok_pql = self.match("KW_FLECHA", "pa_que_lleve")
            nodo_t = self.parse_tipo()
            return {"tipo": "<tipo_retorno>", "es_terminal": False, "hijos": [tok_pql, nodo_t]}
        return {"tipo": "<tipo_retorno>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_parametros(self):
        if self._obtener_lexema() in ("numerito", "quebradito", "cuento", "siono") or self._obtener_tipo() in ("KW_TIPO_ENTERO", "KW_TIPO_REAL", "KW_TIPO_CADENA", "KW_TIPO_BOOLEANO"):
            nodo_pl = self.parse_param_lista()
            return {"tipo": "<parametros>", "es_terminal": False, "hijos": [nodo_pl]}
        return {"tipo": "<parametros>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_param_lista(self):
        nodo_t = self.parse_tipo()
        tok_id = self.match("IDENTIFICADOR")
        nodo_pr = self.parse_param_resto()
        return {"tipo": "<param_lista>", "es_terminal": False, "hijos": [nodo_t, tok_id, nodo_pr]}

    def parse_param_resto(self):
        if self._obtener_tipo() == "COMA" or self._obtener_lexema() == ",":
            tok_coma = self.match("COMA", ",")
            nodo_t = self.parse_tipo()
            tok_id = self.match("IDENTIFICADOR")
            nodo_pr = self.parse_param_resto()
            return {"tipo": "<param_resto>", "es_terminal": False, "hijos": [tok_coma, nodo_t, tok_id, nodo_pr]}
        return {"tipo": "<param_resto>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_tipo(self):
        tok_t = self.match(
            "KW_TIPO_ENTERO", "KW_TIPO_REAL", "KW_TIPO_CADENA", "KW_TIPO_BOOLEANO",
            "numerito", "quebradito", "cuento", "siono"
        )
        return {"tipo": "<tipo>", "es_terminal": False, "hijos": [tok_t]}

    # ==========================================
    # 3.3 BLOQUES Y SENTENCIAS
    # ==========================================

    def parse_bloque(self, tokens_cierre=("ya_quedo", "asi_quedo", "hasta_ahi", "listo_pues", "}")):
        nodo_sent = self.parse_sentencia()
        nodo_ls = self.parse_lista_sentencias(tokens_cierre)
        return {"tipo": "<bloque>", "es_terminal": False, "hijos": [nodo_sent, nodo_ls]}

    def parse_lista_sentencias(self, tokens_cierre):
        if self.token_actual:
            tipo_act = self._obtener_tipo()
            lex_act = self._obtener_lexema()
            if tipo_act in tokens_cierre or lex_act in tokens_cierre:
                return {"tipo": "<lista_sentencias>", "es_terminal": False, "hijos": [self._nodo_eps()]}
            nodo_s = self.parse_sentencia()
            nodo_ls = self.parse_lista_sentencias(tokens_cierre)
            return {"tipo": "<lista_sentencias>", "es_terminal": False, "hijos": [nodo_s, nodo_ls]}
        return {"tipo": "<lista_sentencias>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_sentencia(self):
        if not self.token_actual:
            raise ErrorSintactico("Fin de archivo inesperado.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

        if tipo == "KW_DECLARACION" or lexema == "pille_pues":
            nodo_sub = self.parse_sent_declaracion()
        elif tipo == "KW_LECTURA" or lexema == "escuche_pues":
            nodo_sub = self.parse_sent_lectura()
        elif tipo == "KW_IMPRESION" or lexema == "hable_pues":
            nodo_sub = self.parse_sent_impresion()
        elif tipo == "KW_SI" or lexema == "si_acaso":
            nodo_sub = self.parse_sent_si()
        elif tipo == "KW_MIENTRAS" or lexema == "mientras_que":
            nodo_sub = self.parse_sent_mientras()
        elif tipo == "KW_PARA" or lexema == "pa_cada":
            nodo_sub = self.parse_sent_para()
        elif tipo == "KW_PILLEMOS" or lexema == "pillemos":
            nodo_sub = self.parse_sent_pillemos()
        elif tipo == "KW_RETORNAR" or lexema == "entregue_pues":
            nodo_sub = self.parse_sent_retornar()
        elif tipo == "IDENTIFICADOR":
            nodo_sub = self.parse_sent_asignacion_o_llamada()
        else:
            raise ErrorSintactico(
                f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
                f"Inicio de sentencia no válido con '{lexema}'"
            )
        return {"tipo": "<sentencia>", "es_terminal": False, "hijos": [nodo_sub]}

    def parse_sent_declaracion(self):
        tok_pp = self.match("KW_DECLARACION", "pille_pues")
        nodo_to = self.parse_tipo_opcional()
        tok_id = self.match("IDENTIFICADOR")
        tok_eq = self.match("OP_ASIGNACION", "=")
        nodo_expr = self.parse_expresion()
        return {"tipo": "<sent_declaracion>", "es_terminal": False, "hijos": [tok_pp, nodo_to, tok_id, tok_eq, nodo_expr]}

    def parse_tipo_opcional(self):
        if self._obtener_lexema() in ("numerito", "quebradito", "cuento", "siono") or self._obtener_tipo() in ("KW_TIPO_ENTERO", "KW_TIPO_REAL", "KW_TIPO_CADENA", "KW_TIPO_BOOLEANO"):
            nodo_t = self.parse_tipo()
            return {"tipo": "<tipo_opcional>", "es_terminal": False, "hijos": [nodo_t]}
        return {"tipo": "<tipo_opcional>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_sent_lectura(self):
        tok_ep = self.match("KW_LECTURA", "escuche_pues")
        tok_pa = self.match("PAR_ABRE", "(")
        tok_id = self.match("IDENTIFICADOR")
        tok_pc = self.match("PAR_CIERRA", ")")
        return {"tipo": "<sent_lectura>", "es_terminal": False, "hijos": [tok_ep, tok_pa, tok_id, tok_pc]}

    def parse_sent_impresion(self):
        tok_hp = self.match("KW_IMPRESION", "hable_pues")
        tok_pa = self.match("PAR_ABRE", "(")
        nodo_expr = self.parse_expresion()
        tok_pc = self.match("PAR_CIERRA", ")")
        return {"tipo": "<sent_impresion>", "es_terminal": False, "hijos": [tok_hp, tok_pa, nodo_expr, tok_pc]}

    def parse_sent_retornar(self):
        tok_ep = self.match("KW_RETORNAR", "entregue_pues")
        nodo_expr = self.parse_expresion()
        return {"tipo": "<sent_retornar>", "es_terminal": False, "hijos": [tok_ep, nodo_expr]}

    def parse_sent_asignacion_o_llamada(self):
        tok_id = self.match("IDENTIFICADOR")
        if self._obtener_tipo() == "PAR_ABRE" or self._obtener_lexema() == "(":
            tok_pa = self.match("PAR_ABRE", "(")
            nodo_args = self.parse_argumentos()
            tok_pc = self.match("PAR_CIERRA", ")")
            return {"tipo": "<sent_llamada>", "es_terminal": False, "hijos": [tok_id, tok_pa, nodo_args, tok_pc]}
        else:
            tok_eq = self.match("OP_ASIGNACION", "=")
            nodo_expr = self.parse_expresion()
            return {"tipo": "<sent_asignacion>", "es_terminal": False, "hijos": [tok_id, tok_eq, nodo_expr]}

    # ==========================================
    # 3.4 ESTRUCTURAS DE CONTROL
    # ==========================================

    def parse_sent_si(self):
        tok_sa = self.match("KW_SI", "si_acaso")
        nodo_expr = self.parse_expresion()
        tok_ep = self.match("KW_ENTONCES", "entonces_pues")
        nodo_blq = self.parse_bloque(("sino_pues", "asi_quedo", "KW_SINO", "KW_FIN_SI"))
        nodo_rs = self.parse_rama_sino()
        tok_aq = self.match("KW_FIN_SI", "asi_quedo")
        return {"tipo": "<sent_si>", "es_terminal": False, "hijos": [tok_sa, nodo_expr, tok_ep, nodo_blq, nodo_rs, tok_aq]}

    def parse_rama_sino(self):
        if self._obtener_tipo() == "KW_SINO" or self._obtener_lexema() == "sino_pues":
            tok_sp = self.match("KW_SINO", "sino_pues")
            nodo_blq = self.parse_bloque(("asi_quedo", "KW_FIN_SI"))
            return {"tipo": "<rama_sino>", "es_terminal": False, "hijos": [tok_sp, nodo_blq]}
        return {"tipo": "<rama_sino>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_sent_mientras(self):
        tok_mq = self.match("KW_MIENTRAS", "mientras_que")
        nodo_expr = self.parse_expresion()
        tok_dp = self.match("KW_HACER", "dele_pues")
        nodo_blq = self.parse_bloque(("hasta_ahi", "KW_FIN_MIENTRAS"))
        tok_ha = self.match("KW_FIN_MIENTRAS", "hasta_ahi")
        return {"tipo": "<sent_mientras>", "es_terminal": False, "hijos": [tok_mq, nodo_expr, tok_dp, nodo_blq, tok_ha]}

    def parse_sent_para(self):
        tok_pc = self.match("KW_PARA", "pa_cada")
        tok_id = self.match("IDENTIFICADOR")
        tok_des = self.match("KW_DESDE", "desde")
        nodo_expr1 = self.parse_expresion()
        tok_has = self.match("KW_HASTA", "hasta")
        nodo_expr2 = self.parse_expresion()
        nodo_po = self.parse_paso_opcional()
        tok_dp = self.match("KW_HACER", "dele_pues")
        nodo_blq = self.parse_bloque(("listo_pues", "KW_FIN_PARA"))
        tok_lp = self.match("KW_FIN_PARA", "listo_pues")
        return {"tipo": "<sent_para>", "es_terminal": False, "hijos": [tok_pc, tok_id, tok_des, nodo_expr1, tok_has, nodo_expr2, nodo_po, tok_dp, nodo_blq, tok_lp]}

    def parse_paso_opcional(self):
        if self._obtener_tipo() == "KW_PASO" or self._obtener_lexema() == "de_a":
            tok_da = self.match("KW_PASO", "de_a")
            nodo_expr = self.parse_expresion()
            return {"tipo": "<paso_opcional>", "es_terminal": False, "hijos": [tok_da, nodo_expr]}
        return {"tipo": "<paso_opcional>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_sent_pillemos(self):
        tok_p = self.match("KW_PILLEMOS", "pillemos")
        nodo_expr = self.parse_expresion()
        tok_la = self.match("LLAVE_ABRE", "{")
        nodo_lc = self.parse_lista_casos()
        tok_lc = self.match("LLAVE_CIERRA", "}")
        return {"tipo": "<sent_pillemos>", "es_terminal": False, "hijos": [tok_p, nodo_expr, tok_la, nodo_lc, tok_lc]}

    def parse_lista_casos(self):
        nodo_c = self.parse_caso()
        nodo_lcr = self.parse_lista_casos_resto()
        return {"tipo": "<lista_casos>", "es_terminal": False, "hijos": [nodo_c, nodo_lcr]}

    def parse_lista_casos_resto(self):
        if self.token_actual and self._obtener_lexema() != "}":
            nodo_c = self.parse_caso()
            nodo_lcr = self.parse_lista_casos_resto()
            return {"tipo": "<lista_casos_resto>", "es_terminal": False, "hijos": [nodo_c, nodo_lcr]}
        return {"tipo": "<lista_casos_resto>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_caso(self):
        nodo_pat = self.parse_patron()
        tok_fl = self.match("KW_FLECHA", "pa_que_lleve")
        nodo_cc = self.parse_cuerpo_caso()
        return {"tipo": "<caso>", "es_terminal": False, "hijos": [nodo_pat, tok_fl, nodo_cc]}

    def parse_cuerpo_caso(self):
        if self._obtener_tipo() == "LLAVE_ABRE" or self._obtener_lexema() == "{":
            tok_la = self.match("LLAVE_ABRE", "{")
            nodo_blq = self.parse_bloque(("}", "LLAVE_CIERRA"))
            tok_lc = self.match("LLAVE_CIERRA", "}")
            return {"tipo": "<cuerpo_caso>", "es_terminal": False, "hijos": [tok_la, nodo_blq, tok_lc]}
        else:
            nodo_sent = self.parse_sentencia()
            return {"tipo": "<cuerpo_caso>", "es_terminal": False, "hijos": [nodo_sent]}

    def parse_patron(self):
        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()
        if tipo in ("NUM_ENTERO", "NUM_REAL", "CADENA_LITERAL", "LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
            tok = self.match(tipo, lexema)
            return {"tipo": "<patron>", "es_terminal": False, "hijos": [tok]}
        elif tipo == "IDENTIFICADOR":
            tok = self.match("IDENTIFICADOR")
            return {"tipo": "<patron>", "es_terminal": False, "hijos": [tok]}
        elif tipo == "COMODIN" or lexema == "_":
            tok = self.match("COMODIN", "_")
            return {"tipo": "<patron>", "es_terminal": False, "hijos": [tok]}
        raise ErrorSintactico(f"Patrón inválido: '{lexema}'")

    # ==========================================
    # 3.8 EXPRESIONES (Derivación completa)
    # ==========================================

    def parse_expresion(self):
        nodo_eo = self.parse_expr_o()
        return {"tipo": "<expresion>", "es_terminal": False, "hijos": [nodo_eo]}

    def parse_expr_o(self):
        nodo_ey = self.parse_expr_y()
        nodo_eop = self.parse_expr_o_p()
        return {"tipo": "<expr_o>", "es_terminal": False, "hijos": [nodo_ey, nodo_eop]}

    def parse_expr_o_p(self):
        if self._obtener_tipo() == "OP_O" or self._obtener_lexema() == "o_que":
            tok_op = self.match("OP_O", "o_que")
            nodo_ey = self.parse_expr_y()
            nodo_eop = self.parse_expr_o_p()
            return {"tipo": "<expr_o_p>", "es_terminal": False, "hijos": [tok_op, nodo_ey, nodo_eop]}
        return {"tipo": "<expr_o_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_y(self):
        nodo_ei = self.parse_expr_igualdad()
        nodo_eyp = self.parse_expr_y_p()
        return {"tipo": "<expr_y>", "es_terminal": False, "hijos": [nodo_ei, nodo_eyp]}

    def parse_expr_y_p(self):
        if self._obtener_tipo() == "OP_Y" or self._obtener_lexema() == "y_tambien":
            tok_op = self.match("OP_Y", "y_tambien")
            nodo_ei = self.parse_expr_igualdad()
            nodo_eyp = self.parse_expr_y_p()
            return {"tipo": "<expr_y_p>", "es_terminal": False, "hijos": [tok_op, nodo_ei, nodo_eyp]}
        return {"tipo": "<expr_y_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_igualdad(self):
        nodo_er = self.parse_expr_relacional()
        nodo_eip = self.parse_expr_igualdad_p()
        return {"tipo": "<expr_igualdad>", "es_terminal": False, "hijos": [nodo_er, nodo_eip]}

    def parse_expr_igualdad_p(self):
        if self._obtener_tipo() in ("OP_IGUAL", "OP_DISTINTO") or self._obtener_lexema() in ("igualito", "distinto", "==", "!="):
            tok_op = self.match("OP_IGUAL", "OP_DISTINTO", "igualito", "distinto", "==", "!=")
            nodo_er = self.parse_expr_relacional()
            nodo_eip = self.parse_expr_igualdad_p()
            return {"tipo": "<expr_igualdad_p>", "es_terminal": False, "hijos": [tok_op, nodo_er, nodo_eip]}
        return {"tipo": "<expr_igualdad_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_relacional(self):
        nodo_ec = self.parse_expr_concat()
        nodo_erp = self.parse_expr_relacional_p()
        return {"tipo": "<expr_relacional>", "es_terminal": False, "hijos": [nodo_ec, nodo_erp]}

    def parse_expr_relacional_p(self):
        if self._obtener_tipo() in ("OP_MAYOR", "OP_MENOR", "OP_MAYOR_IGUAL", "OP_MENOR_IGUAL") or self._obtener_lexema() in (">", "<", ">=", "<="):
            tok_op = self.match("OP_MAYOR", "OP_MENOR", "OP_MAYOR_IGUAL", "OP_MENOR_IGUAL", ">", "<", ">=", "<=")
            nodo_ec = self.parse_expr_concat()
            nodo_erp = self.parse_expr_relacional_p()
            return {"tipo": "<expr_relacional_p>", "es_terminal": False, "hijos": [tok_op, nodo_ec, nodo_erp]}
        return {"tipo": "<expr_relacional_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_concat(self):
        nodo_ea = self.parse_expr_aditiva()
        nodo_ecp = self.parse_expr_concat_p()
        return {"tipo": "<expr_concat>", "es_terminal": False, "hijos": [nodo_ea, nodo_ecp]}

    def parse_expr_concat_p(self):
        if self._obtener_tipo() == "OP_CONCAT" or self._obtener_lexema() == "<>":
            tok_op = self.match("OP_CONCAT", "<>")
            nodo_ea = self.parse_expr_aditiva()
            nodo_ecp = self.parse_expr_concat_p()
            return {"tipo": "<expr_concat_p>", "es_terminal": False, "hijos": [tok_op, nodo_ea, nodo_ecp]}
        return {"tipo": "<expr_concat_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_aditiva(self):
        nodo_em = self.parse_expr_multiplicativa()
        nodo_eap = self.parse_expr_aditiva_p()
        return {"tipo": "<expr_aditiva>", "es_terminal": False, "hijos": [nodo_em, nodo_eap]}

    def parse_expr_aditiva_p(self):
        if self._obtener_tipo() in ("OP_SUMA", "OP_RESTA") or self._obtener_lexema() in ("+", "-"):
            tok_op = self.match("OP_SUMA", "OP_RESTA", "+", "-")
            nodo_em = self.parse_expr_multiplicativa()
            nodo_eap = self.parse_expr_aditiva_p()
            return {"tipo": "<expr_aditiva_p>", "es_terminal": False, "hijos": [tok_op, nodo_em, nodo_eap]}
        return {"tipo": "<expr_aditiva_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_multiplicativa(self):
        nodo_ep = self.parse_expr_potencia()
        nodo_emp = self.parse_expr_multiplicativa_p()
        return {"tipo": "<expr_multiplicativa>", "es_terminal": False, "hijos": [nodo_ep, nodo_emp]}

    def parse_expr_multiplicativa_p(self):
        if self._obtener_tipo() in ("OP_MULT", "OP_DIV", "OP_MODULO") or self._obtener_lexema() in ("*", "/", "%"):
            tok_op = self.match("OP_MULT", "OP_DIV", "OP_MODULO", "*", "/", "%")
            nodo_ep = self.parse_expr_potencia()
            nodo_emp = self.parse_expr_multiplicativa_p()
            return {"tipo": "<expr_multiplicativa_p>", "es_terminal": False, "hijos": [tok_op, nodo_ep, nodo_emp]}
        return {"tipo": "<expr_multiplicativa_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_potencia(self):
        nodo_eu = self.parse_expr_unaria()
        nodo_epp = self.parse_expr_potencia_p()
        return {"tipo": "<expr_potencia>", "es_terminal": False, "hijos": [nodo_eu, nodo_epp]}

    def parse_expr_potencia_p(self):
        if self._obtener_tipo() == "OP_POTENCIA" or self._obtener_lexema() == "**":
            tok_op = self.match("OP_POTENCIA", "**")
            nodo_ep = self.parse_expr_potencia()
            return {"tipo": "<expr_potencia_p>", "es_terminal": False, "hijos": [tok_op, nodo_ep]}
        return {"tipo": "<expr_potencia_p>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_expr_unaria(self):
        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()
        if tipo in ("OP_NO", "OP_RESTA", "nanai", "-") or lexema in ("nanai", "-"):
            tok_op = self.match("OP_NO", "OP_RESTA", "nanai", "-")
            nodo_eu = self.parse_expr_unaria()
            return {"tipo": "<expr_unaria>", "es_terminal": False, "hijos": [tok_op, nodo_eu]}
        nodo_ep = self.parse_expr_primaria()
        return {"tipo": "<expr_unaria>", "es_terminal": False, "hijos": [nodo_ep]}

    def parse_expr_primaria(self):
        if not self.token_actual:
            raise ErrorSintactico("Expresión incompleta al final del archivo.")

        tipo = self._obtener_tipo()
        lexema = self._obtener_lexema()

        if tipo in ("PAR_ABRE", "(") or lexema == "(":
            tok_pa = self.match("PAR_ABRE", "(")
            nodo_expr = self.parse_expresion()
            tok_pc = self.match("PAR_CIERRA", ")")
            return {"tipo": "<expr_primaria>", "es_terminal": False, "hijos": [tok_pa, nodo_expr, tok_pc]}

        if tipo in ("NUM_ENTERO", "NUM_REAL", "CADENA_LITERAL", "LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
            tok = self.match(tipo, lexema)
            return {"tipo": "<expr_primaria>", "es_terminal": False, "hijos": [tok]}

        if tipo == "IDENTIFICADOR":
            tok_id = self.match("IDENTIFICADOR")
            nodo_suf = self.parse_sufijo_id()
            return {"tipo": "<expr_primaria>", "es_terminal": False, "hijos": [tok_id, nodo_suf]}

        raise ErrorSintactico(
            f"Error Sintáctico en [Fila {getattr(self.token_actual, 'fila', '?')}]: "
            f"Expresión no válida iniciando con '{lexema}'"
        )

    def parse_sufijo_id(self):
        if self._obtener_tipo() == "PAR_ABRE" or self._obtener_lexema() == "(":
            tok_pa = self.match("PAR_ABRE", "(")
            nodo_args = self.parse_argumentos()
            tok_pc = self.match("PAR_CIERRA", ")")
            return {"tipo": "<sufijo_id>", "es_terminal": False, "hijos": [tok_pa, nodo_args, tok_pc]}
        return {"tipo": "<sufijo_id>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_argumentos(self):
        if self._obtener_tipo() != "PAR_CIERRA" and self._obtener_lexema() != ")":
            nodo_al = self.parse_arg_lista()
            return {"tipo": "<argumentos>", "es_terminal": False, "hijos": [nodo_al]}
        return {"tipo": "<argumentos>", "es_terminal": False, "hijos": [self._nodo_eps()]}

    def parse_arg_lista(self):
        nodo_expr = self.parse_expresion()
        nodo_ar = self.parse_arg_resto()
        return {"tipo": "<arg_lista>", "es_terminal": False, "hijos": [nodo_expr, nodo_ar]}

    def parse_arg_resto(self):
        if self._obtener_tipo() == "COMA" or self._obtener_lexema() == ",":
            tok_coma = self.match("COMA", ",")
            nodo_expr = self.parse_expresion()
            nodo_ar = self.parse_arg_resto()
            return {"tipo": "<arg_resto>", "es_terminal": False, "hijos": [tok_coma, nodo_expr, nodo_ar]}
        return {"tipo": "<arg_resto>", "es_terminal": False, "hijos": [self._nodo_eps()]}
