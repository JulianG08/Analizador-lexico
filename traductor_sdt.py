# -*- coding: utf-8 -*-
"""
Módulo: traductor_sdt.py
Descripción: Fase de TRADUCCIÓN ORIENTADA POR LA SINTAXIS (SDT) — Entrega Final.

Es la CUARTA fase del compilador y la última del encadenamiento:

    lexer.py  ->  parser.py  ->  analizador_semantico.py  ->  traductor_sdt.py
    (léxico)      (sintáctico)   (semántico)                  (SDT)

Recorre el mismo CST que produjo el parser y, aplicando una acción SDT por
producción, emite código **Gleam** válido. No vuelve a analizar nada: las
decisiones que necesita (¿este '+' es de Int o de Float? ¿este identificador
qué tipo tiene?) ya fueron resueltas por la fase semántica y llegan aquí de
dos maneras:

  1. La TABLA DE SÍMBOLOS (`TablaSimbolos`), que el traductor recibe
     construida y consulta para los tipos de variables y las firmas de
     funciones.
  2. El atributo sintetizado `tipo_sem`, que el analizador semántico anotó
     sobre cada nodo de expresión del árbol.

Por qué hace falta esa información: en Gleam `Int` y `Float` son tipos
disjuntos con operadores DISTINTOS (`+` contra `+.`, `>` contra `>.`), y `<>`
exige String en ambos lados. Sin los tipos, el traductor no podría elegir el
operador correcto ni insertar las conversiones, y la salida no compilaría.

Las tres construcciones que Gleam no tiene (los tres bucles) se traducen a
recursión de cola, que el BEAM ejecuta en espacio constante:

  mientras_que  ->  función auxiliar; el cuerpo va DENTRO de la rama True
  repita_pues   ->  función auxiliar; el cuerpo va ANTES del case (post-test)
  pa_cada       ->  list.range |> list.each  (paso 1) o recursión (paso != 1)

Uso:
    from traductor_sdt import TraductorSDT
    traductor = TraductorSDT(cst, tabla_simbolos)
    codigo_gleam = traductor.traducir()
"""

from __future__ import annotations

from analizador_semantico import (
    NUMERITO, QUEBRADITO, CUENTO, SIONO, DESCONOCIDO, ERROR,
)

# Tipo de Paisascript -> tipo de Gleam.
TIPOS_GLEAM = {
    NUMERITO: "Int",
    QUEBRADITO: "Float",
    CUENTO: "String",
    SIONO: "Bool",
}

# Operadores aritméticos y relacionales: Gleam usa una variante con punto
# para Float. Esta tabla es la que consulta la acción SDT de cada operador.
OPERADOR_FLOTANTE = {
    "+": "+.", "-": "-.", "*": "*.", "/": "/.",
    ">": ">.", "<": "<.", ">=": ">=.", "<=": "<=.",
}

# Operadores con nombre de Paisascript -> símbolo de Gleam.
OPERADOR_NOMBRADO = {
    "igualito": "==",
    "distinto": "!=",
    "y_tambien": "&&",
    "o_que": "||",
}

# Niveles de la cadena de expresiones del CST (A ::= B A', A' ::= op B A').
NIVELES_BINARIOS = (
    "expr_o", "expr_y", "expr_igualdad", "expr_relacional",
    "expr_concat", "expr_aditiva", "expr_multiplicativa", "expr_potencia",
)

SANGRIA = "  "


class TraductorSDT:
    """Visitor que aplica las acciones SDT sobre el CST y emite Gleam."""

    def __init__(self, cst, tabla_simbolos=None):
        self.cst = cst
        self.tabla = tabla_simbolos
        self._contador_bucles = 0      # para nombrar bucle_1, bucle_2, ...
        self._funciones_auxiliares = []  # recursiones de cola generadas
        self._modulos = set()          # imports que la salida va a necesitar
        # Tipos de las variables vivas, por nombre. Se alimenta de las
        # declaraciones a medida que el recorrido avanza, igual que lo haría
        # la tabla de símbolos durante el análisis.
        self._tipos_variables = {}
        self._firmas = {}              # nombre de función -> (params, retorno)

    # ==================================================================
    #  PUNTO DE ENTRADA
    # ==================================================================
    def traducir(self):
        """Devuelve el programa Gleam completo como una sola cadena."""
        self._precargar_firmas()

        funciones, sueltas = self._separar_declaraciones(self.cst)

        bloques_funcion = [self._v_def_funcion(f) for f in funciones]

        cuerpo_main = []
        for sentencia in sueltas:
            cuerpo_main.extend(self._v_sentencia(sentencia))

        partes = []
        if cuerpo_main:
            partes.append(self._envolver_main(cuerpo_main))
        partes.extend(bloques_funcion)
        partes.extend(self._funciones_auxiliares)

        encabezado = self._encabezado()
        cuerpo = "\n\n".join(p for p in partes if p.strip())
        return f"{encabezado}\n\n{cuerpo}\n" if encabezado else f"{cuerpo}\n"

    def _encabezado(self):
        """Los `import` que el código generado necesita, en orden estable."""
        if not self._modulos:
            return ""
        return "\n".join(f"import {m}" for m in sorted(self._modulos))

    @staticmethod
    def _cerrar_bloque(lineas):
        """Garantiza que el bloque termine en una EXPRESION, no en un `let`.

        En Gleam todo bloque devuelve un valor, asi que terminar en una
        asignacion es un error de compilacion. Cuando la ultima sentencia
        traducida es un enlace, se cierra el bloque con `Nil`, que es el
        valor unitario del lenguaje.
        """
        if not lineas:
            return ["Nil"]
        ultima = lineas[-1].strip()
        if ultima.startswith("let ") or ultima.startswith("//"):
            return lineas + ["Nil"]
        return lineas

    def _envolver_main(self, lineas):
        cuerpo = "\n".join(SANGRIA + l for l in self._cerrar_bloque(lineas))
        return f"pub fn main() {{\n{cuerpo}\n}}"

    # ==================================================================
    #  UTILIDADES DE NAVEGACIÓN (misma forma de CST que el semántico)
    # ==================================================================
    @staticmethod
    def _hijos(nodo):
        return nodo.get("hijos", []) if isinstance(nodo, dict) else []

    @staticmethod
    def _nombre(nodo):
        if not isinstance(nodo, dict):
            return ""
        tipo = nodo.get("tipo", "")
        if tipo.startswith("<") and tipo.endswith(">"):
            return tipo[1:-1]
        return tipo

    @classmethod
    def _es_eps(cls, nodo):
        return cls._nombre(nodo) == "ε"

    @classmethod
    def _deriva_vacio(cls, nodo):
        if not isinstance(nodo, dict):
            return False
        if cls._es_eps(nodo):
            return True
        hijos = nodo.get("hijos") or []
        return bool(hijos) and all(cls._deriva_vacio(h) for h in hijos)

    @staticmethod
    def _token_tipo(nodo):
        if not isinstance(nodo, dict):
            return None
        if nodo.get("token_tipo"):
            return nodo["token_tipo"]
        return str(nodo.get("tipo", "")).split(" (", 1)[0]

    @staticmethod
    def _lexema(nodo):
        if not isinstance(nodo, dict):
            return ""
        if "lexema" in nodo:
            return nodo["lexema"]
        tipo = str(nodo.get("tipo", ""))
        if " (" in tipo and tipo.endswith(")"):
            return tipo[tipo.index(" (") + 2:-1]
        return ""

    def _hijo_nt(self, nodo, nombre):
        for hijo in self._hijos(nodo):
            if self._nombre(hijo) == nombre:
                return hijo
        return None

    def _tipo_de(self, nodo):
        """Lee el atributo sintetizado que dejó el analizador semántico."""
        if isinstance(nodo, dict) and "tipo_sem" in nodo:
            return nodo["tipo_sem"]
        return DESCONOCIDO

    # ==================================================================
    #  RECORRIDO DEL PROGRAMA
    # ==================================================================
    def _separar_declaraciones(self, nodo):
        """Separa definiciones de función de las sentencias de nivel superior.

        Gleam no admite sentencias sueltas fuera de una función, así que las
        de nivel superior se recogen para envolverlas en `pub fn main()`.
        """
        funciones, sueltas = [], []

        def recorrer(n):
            nombre = self._nombre(n)
            if nombre == "def_funcion":
                funciones.append(n)
                return
            if nombre == "sentencia":
                sueltas.append(n)
                return
            for hijo in self._hijos(n):
                recorrer(hijo)

        recorrer(nodo)
        return funciones, sueltas

    def _precargar_firmas(self):
        """Registra las firmas de las funciones antes de traducir el cuerpo."""
        funciones, _ = self._separar_declaraciones(self.cst)
        for definicion in funciones:
            hijos = self._hijos(definicion)
            if len(hijos) < 8:
                continue
            nombre = self._lexema(hijos[1])
            params = self._colectar_parametros(hijos[3])
            retorno = self._tipo_retorno(hijos[5])
            self._firmas[nombre] = (params, retorno)

    def _colectar_parametros(self, nodo_parametros):
        """[(nombre, tipo_paisascript), ...] en orden de declaración."""
        params = []

        def recorrer(n):
            if not isinstance(n, dict) or self._deriva_vacio(n):
                return
            nombre_nt = self._nombre(n)
            if nombre_nt in ("param_lista", "param_resto"):
                hijos = self._hijos(n)
                tipo_nodo = next(
                    (h for h in hijos if self._nombre(h) == "tipo"), None)
                id_nodo = next(
                    (h for h in hijos if self._token_tipo(h) == "IDENTIFICADOR"),
                    None)
                if tipo_nodo is not None and id_nodo is not None:
                    params.append(
                        (self._lexema(id_nodo), self._tipo_literal(tipo_nodo)))
            for hijo in self._hijos(n):
                recorrer(hijo)

        recorrer(nodo_parametros)
        return params

    def _tipo_literal(self, nodo_tipo):
        """Lexema de un nodo <tipo> ('numerito', 'cuento', ...)."""
        for hijo in self._hijos(nodo_tipo):
            lexema = self._lexema(hijo)
            if lexema in TIPOS_GLEAM:
                return lexema
        return DESCONOCIDO

    def _tipo_retorno(self, nodo_tipo_retorno):
        if self._deriva_vacio(nodo_tipo_retorno):
            return DESCONOCIDO
        nodo_tipo = self._hijo_nt(nodo_tipo_retorno, "tipo")
        return self._tipo_literal(nodo_tipo) if nodo_tipo else DESCONOCIDO

    # ==================================================================
    #  ACCIÓN SDT: <def_funcion>
    # ==================================================================
    def _v_def_funcion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 8:
            return ""
        nombre = self._lexema(hijos[1])
        params = self._colectar_parametros(hijos[3])
        retorno = self._tipo_retorno(hijos[5])

        # Los parámetros son variables vivas dentro del cuerpo.
        guardado = dict(self._tipos_variables)
        for nombre_param, tipo_param in params:
            self._tipos_variables[nombre_param] = tipo_param

        lineas = self._v_bloque(hijos[7])

        self._tipos_variables = guardado

        firma_params = ", ".join(
            f"{n}: {TIPOS_GLEAM.get(t, 'Int')}" for n, t in params)
        flecha = f" -> {TIPOS_GLEAM[retorno]}" if retorno in TIPOS_GLEAM else ""
        cuerpo = "\n".join(SANGRIA + l for l in self._cerrar_bloque(lineas))
        return f"pub fn {nombre}({firma_params}){flecha} {{\n{cuerpo}\n}}"

    # ==================================================================
    #  ACCIÓN SDT: bloques y sentencias
    # ==================================================================
    def _v_bloque(self, nodo):
        """Lista de líneas Gleam de un <bloque>."""
        return self._v_secuencia(self._sentencias_de(nodo))

    def _v_secuencia(self, sentencias, continuacion=None):
        """Traduce una secuencia sabiendo qué hacer cuando termina.

        `continuacion` son las líneas que se emiten si la secuencia llega a su
        final sin haber devuelto. Dentro del cuerpo de un bucle, por ejemplo,
        la continuación es la llamada recursiva.

        Gleam no tiene `return`, así que los retornos anticipados se eliminan
        reestructurando el flujo, y para eso hace falta saber qué venía
        después: eso es exactamente la continuación.
        """
        lineas = []
        for indice, sentencia in enumerate(sentencias):
            hijos = self._hijos(sentencia)
            interna = hijos[0] if hijos else None
            nombre = self._nombre(interna)
            resto = sentencias[indice + 1:]

            # Retorno anticipado dentro de un si_acaso sin sino.
            if resto and nombre == "sent_si" and self._es_retorno_anticipado(interna):
                lineas.extend(self._v_si_con_resto(interna, resto, continuacion))
                return lineas

            # Retorno anticipado dentro de un bucle: la salida normal del
            # bucle se convierte en todo lo que venía después de él.
            if (nombre in ("sent_mientras", "sent_repita")
                    and self._contiene_retorno(interna)):
                salida = self._v_secuencia(resto, continuacion)
                hijos_bucle = self._hijos(interna)
                if nombre == "sent_mientras":
                    lineas.extend(self._bucle_recursivo(
                        hijos_bucle[1], hijos_bucle[3], False, salida))
                else:
                    lineas.extend(self._bucle_recursivo(
                        hijos_bucle[3], hijos_bucle[1], True, salida))
                return lineas

            lineas.extend(self._v_sentencia(sentencia))

        if continuacion:
            lineas.extend(continuacion)
        return lineas

    def _contiene_retorno(self, nodo):
        """¿Hay algún `entregue_pues` en este subárbol?"""
        if not isinstance(nodo, dict):
            return False
        if self._nombre(nodo) == "sent_retornar":
            return True
        return any(self._contiene_retorno(h) for h in self._hijos(nodo))

    def _es_retorno_anticipado(self, nodo_si):
        """`si_acaso` sin `sino` cuyo cuerpo termina en `entregue_pues`."""
        hijos = self._hijos(nodo_si)
        if len(hijos) < 5 or not self._deriva_vacio(hijos[4]):
            return False
        sentencias = self._sentencias_de(hijos[3])
        if not sentencias:
            return False
        ultima = self._hijos(sentencias[-1])
        return bool(ultima) and self._nombre(ultima[0]) == "sent_retornar"

    def _v_si_con_resto(self, nodo_si, resto, continuacion_externa=None):
        """Emite el `case` con el resto del cuerpo en la rama False."""
        hijos = self._hijos(nodo_si)
        condicion = self._v_expresion(hijos[1])
        entonces = self._cerrar_bloque(self._v_bloque(hijos[3]))
        continuacion = self._cerrar_bloque(
            self._v_secuencia(resto, continuacion_externa))

        lineas = [f"case {condicion} {{"]
        lineas.append(SANGRIA + "True -> {")
        lineas.extend(SANGRIA * 2 + l for l in entonces)
        lineas.append(SANGRIA + "}")
        lineas.append(SANGRIA + "False -> {")
        lineas.extend(SANGRIA * 2 + l for l in continuacion)
        lineas.append(SANGRIA + "}")
        lineas.append("}")
        return lineas

    def _sentencias_de(self, nodo):
        """Sentencias de un <bloque>/<lista_sentencias>, en orden."""
        encontradas = []

        def recorrer(n):
            if not isinstance(n, dict) or self._deriva_vacio(n):
                return
            if self._nombre(n) == "sentencia":
                encontradas.append(n)
                return
            for hijo in self._hijos(n):
                recorrer(hijo)

        recorrer(nodo)
        return encontradas

    def _v_sentencia(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return []
        interna = hijos[0]
        despacho = {
            "sent_declaracion": self._v_sent_declaracion,
            "sent_lectura": self._v_sent_lectura,
            "sent_impresion": self._v_sent_impresion,
            "sent_retornar": self._v_sent_retornar,
            "sent_si": self._v_sent_si,
            "sent_mientras": self._v_sent_mientras,
            "sent_para": self._v_sent_para,
            "sent_repita": self._v_sent_repita,
            "sent_pillemos": self._v_sent_pillemos,
            "sent_llamada": self._v_sent_llamada,
            "sent_asignacion": self._v_sent_asignacion,
        }
        metodo = despacho.get(self._nombre(interna))
        return metodo(interna) if metodo else []

    # --- pille_pues -> let ------------------------------------------------
    def _v_sent_declaracion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 5:
            return []
        nombre = self._lexema(hijos[2])
        expresion = self._v_expresion(hijos[4])
        tipo = self._tipo_de(hijos[4])
        if tipo in (DESCONOCIDO, ERROR):
            tipo = self._tipo_literal(hijos[1]) if not self._deriva_vacio(hijos[1]) else tipo
        self._tipos_variables[nombre] = tipo
        return [f"let {nombre} = {expresion}"]

    # --- escuche_pues -> erlang.get_line ----------------------------------
    def _v_sent_lectura(self, nodo):
        hoja_id = next((h for h in self._hijos(nodo)
                        if self._token_tipo(h) == "IDENTIFICADOR"), None)
        if hoja_id is None:
            return []
        nombre = self._lexema(hoja_id)
        self._modulos.add("gleam/erlang")
        lineas = [f'let assert Ok({nombre}) = erlang.get_line("")']

        # La consola entrega texto; si la variable se usa como número hay que
        # convertirla, porque Gleam no hace conversiones implícitas.
        tipo = self._tipos_variables.get(nombre) or self._tipo_en_tabla(nombre)
        if tipo == NUMERITO:
            self._modulos.update(("gleam/int", "gleam/string"))
            lineas.append(
                f"let assert Ok({nombre}) = int.parse(string.trim({nombre}))")
        elif tipo == QUEBRADITO:
            self._modulos.update(("gleam/float", "gleam/string"))
            lineas.append(
                f"let assert Ok({nombre}) = float.parse(string.trim({nombre}))")
        else:
            self._tipos_variables[nombre] = CUENTO
        return lineas

    def _tipo_en_tabla(self, nombre):
        """Consulta la tabla de símbolos que dejó la fase semántica."""
        if self.tabla is None:
            return DESCONOCIDO
        simbolo = self.tabla.buscar(nombre)
        return simbolo.tipo if simbolo is not None else DESCONOCIDO

    # --- hable_pues -> io.println -----------------------------------------
    def _v_sent_impresion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 3:
            return []
        self._modulos.add("gleam/io")
        texto = self._como_cadena(hijos[2])
        return [f"io.println({texto})"]

    # --- entregue_pues -> última expresión del cuerpo ---------------------
    def _v_sent_retornar(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 2:
            return []
        return [self._v_expresion(hijos[1])]

    # --- si_acaso -> case -------------------------------------------------
    def _v_sent_si(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 5:
            return []
        condicion = self._v_expresion(hijos[1])
        entonces = self._cerrar_bloque(self._v_bloque(hijos[3]))
        rama_sino = hijos[4]
        if self._deriva_vacio(rama_sino):
            sino = ["Nil"]
        else:
            bloque_sino = self._hijo_nt(rama_sino, "bloque")
            sino = self._cerrar_bloque(
                self._v_bloque(bloque_sino) if bloque_sino else [])

        lineas = [f"case {condicion} {{"]
        lineas.append(SANGRIA + "True -> {")
        lineas.extend(SANGRIA * 2 + l for l in entonces)
        lineas.append(SANGRIA + "}")
        lineas.append(SANGRIA + "False -> {")
        lineas.extend(SANGRIA * 2 + l for l in sino)
        lineas.append(SANGRIA + "}")
        lineas.append("}")
        return lineas

    # --- pillemos -> case con patrones ------------------------------------
    def _v_sent_pillemos(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 4:
            return []
        sujeto = self._v_expresion(hijos[1])
        lineas = [f"case {sujeto} {{"]
        for caso in self._casos_de(self._hijo_nt(nodo, "lista_casos")):
            hijos_caso = self._hijos(caso)
            if len(hijos_caso) < 3:
                continue
            patron = self._v_patron(hijos_caso[0])
            cuerpo = self._cerrar_bloque(self._v_cuerpo_caso(hijos_caso[2]))
            if len(cuerpo) == 1:
                lineas.append(SANGRIA + f"{patron} -> {cuerpo[0]}")
            else:
                lineas.append(SANGRIA + f"{patron} -> {{")
                lineas.extend(SANGRIA * 2 + l for l in cuerpo)
                lineas.append(SANGRIA + "}")
        lineas.append("}")
        return lineas

    def _casos_de(self, nodo):
        encontrados = []

        def recorrer(n):
            if not isinstance(n, dict) or self._deriva_vacio(n):
                return
            if self._nombre(n) == "caso":
                encontrados.append(n)
                return
            for hijo in self._hijos(n):
                recorrer(hijo)

        recorrer(nodo)
        return encontrados

    def _v_patron(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return "_"
        hoja = hijos[0]
        lexema = self._lexema(hoja)
        if lexema == "_":
            return "_"
        if lexema == "sizas":
            return "True"
        if lexema == "naranjas":
            return "False"
        if self._token_tipo(hoja) == "CADENA_LITERAL":
            return lexema if lexema.startswith('"') else f'"{lexema}"'
        if self._token_tipo(hoja) == "NUM_REAL":
            return self._literal_flotante(lexema)
        return lexema

    def _v_cuerpo_caso(self, nodo):
        if self._nombre(nodo) != "cuerpo_caso":
            return []
        bloque = self._hijo_nt(nodo, "bloque")
        if bloque is not None:
            return self._v_bloque(bloque)
        sentencia = self._hijo_nt(nodo, "sentencia")
        return self._v_sentencia(sentencia) if sentencia else []

    # --- llamada y asignación ---------------------------------------------
    def _v_sent_llamada(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return []
        nombre = self._lexema(hijos[0])
        argumentos = self._v_argumentos(self._hijo_nt(nodo, "argumentos"))
        return [f"{nombre}({', '.join(argumentos)})"]

    def _v_sent_asignacion(self, nodo):
        # Paisascript es inmutable: la fase semántica ya reportó esto como
        # error, así que aquí solo se emite la forma con shadowing.
        hijos = self._hijos(nodo)
        if len(hijos) < 3:
            return []
        return [f"let {self._lexema(hijos[0])} = {self._v_expresion(hijos[2])}"]

    def _v_argumentos(self, nodo):
        if nodo is None or self._deriva_vacio(nodo):
            return []
        expresiones = []

        def recorrer(n):
            if not isinstance(n, dict) or self._deriva_vacio(n):
                return
            if self._nombre(n) == "expresion":
                expresiones.append(n)
                return
            for hijo in self._hijos(n):
                recorrer(hijo)

        recorrer(nodo)
        return [self._v_expresion(e) for e in expresiones]

    # ==================================================================
    #  ACCIÓN SDT: LOS TRES BUCLES -> RECURSIÓN DE COLA
    # ==================================================================
    def _estado_del_bucle(self, nodo_cuerpo):
        """Variables que el cuerpo vuelve a enlazar: el estado del bucle.

        Son exactamente las que la función auxiliar recursiva debe recibir
        como parámetros y devolver, porque son las únicas que cambian de una
        vuelta a la siguiente.
        """
        nombres = []

        def recorrer(n):
            if not isinstance(n, dict):
                return
            nombre_nt = self._nombre(n)
            hijos = self._hijos(n)
            if nombre_nt == "sent_declaracion" and len(hijos) >= 3:
                lexema = self._lexema(hijos[2])
                if lexema and lexema not in nombres:
                    nombres.append(lexema)
            elif nombre_nt == "sent_asignacion" and hijos:
                lexema = self._lexema(hijos[0])
                if lexema and lexema not in nombres:
                    nombres.append(lexema)
            elif nombre_nt == "sent_lectura":
                for hijo in hijos:
                    if self._token_tipo(hijo) == "IDENTIFICADOR":
                        lexema = self._lexema(hijo)
                        if lexema and lexema not in nombres:
                            nombres.append(lexema)
            for hijo in hijos:
                recorrer(hijo)

        recorrer(nodo_cuerpo)
        # Solo las que ya existían fuera del bucle forman el estado; las que
        # nacen dentro son locales de la vuelta.
        return [n for n in nombres if n in self._tipos_variables]

    def _variables_libres(self, nodos, excluir):
        """Identificadores que el bucle LEE y que vienen de fuera.

        La función auxiliar recursiva se genera fuera del ámbito donde vivía
        el bucle, así que todo lo que el bucle lee y no produce él mismo
        tiene que entrar como parámetro. Si no, el código generado haría
        referencia a un nombre que en Gleam no existe en ese alcance.

        No son estado: no cambian entre vueltas, así que se pasan pero no se
        devuelven.
        """
        libres = []

        def recorrer(n):
            if not isinstance(n, dict):
                return
            hijos = self._hijos(n)
            if not hijos and self._token_tipo(n) == "IDENTIFICADOR":
                nombre = self._lexema(n)
                if (nombre in self._tipos_variables
                        and nombre not in excluir
                        and nombre not in libres
                        and nombre not in self._firmas):
                    libres.append(nombre)
            for hijo in hijos:
                recorrer(hijo)

        for nodo in nodos:
            recorrer(nodo)
        return libres

    def _firma_parametros(self, nombres):
        return ", ".join(
            f"{n}: {TIPOS_GLEAM.get(self._tipos_variables.get(n), 'Int')}"
            for n in nombres
        )

    def _firma_estado(self, estado):
        return ", ".join(
            f"{n}: {TIPOS_GLEAM.get(self._tipos_variables.get(n), 'Int')}"
            for n in estado
        )

    def _tipo_estado(self, estado):
        tipos = [TIPOS_GLEAM.get(self._tipos_variables.get(n), "Int")
                 for n in estado]
        if len(tipos) == 1:
            return tipos[0]
        return "#(" + ", ".join(tipos) + ")"

    def _valor_estado(self, estado):
        if len(estado) == 1:
            return estado[0]
        return "#(" + ", ".join(estado) + ")"

    def _destino_estado(self, estado):
        if len(estado) == 1:
            return f"let {estado[0]} = "
        return "let #(" + ", ".join(estado) + ") = "

    # --- mientras_que: condición al principio ------------------------------
    def _v_sent_mientras(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 4:
            return []
        return self._bucle_recursivo(hijos[1], hijos[3], False)

    # --- repita_pues: condición al final (post-test) -----------------------
    def _v_sent_repita(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 4:
            return []
        return self._bucle_recursivo(hijos[3], hijos[1], True)

    def _bucle_recursivo(self, condicion_nodo, cuerpo_nodo, post_test,
                         salida=None):
        """Genera la función auxiliar de cola y la llamada que la dispara.

        post_test=False (mientras_que): el cuerpo va DENTRO de la rama True;
        la condición es de permanencia.
        post_test=True (repita_pues): el cuerpo va ANTES del case y la
        condición es de SALIDA, así que las ramas se invierten.

        `salida` son las líneas que se ejecutan cuando el bucle termina
        normalmente. Se usa cuando el cuerpo tiene un `entregue_pues`: en ese
        caso el bucle ES la cola de la función, así que su rama de salida
        contiene todo lo que venía después y la auxiliar devuelve el valor de
        la función. Sin `salida`, el bucle solo devuelve su estado.
        """
        self._contador_bucles += 1
        nombre_fn = f"bucle_{self._contador_bucles}"
        estado = self._estado_del_bucle(cuerpo_nodo)

        if not estado and salida is None:
            # Sin estado no hay recursión que termine; la fase semántica ya
            # lo reportó (SEM-6). Se emite un comentario antes que código roto.
            return ["// bucle sin estado: no se puede generar (ver SEM-6)"]

        # Las variables que el bucle solo lee también viajan como parámetros.
        libres = self._variables_libres([condicion_nodo, cuerpo_nodo], estado)
        parametros = libres + estado
        llamada = f"{nombre_fn}({', '.join(parametros)})"

        guardado = dict(self._tipos_variables)
        cuerpo = self._v_secuencia(self._sentencias_de(cuerpo_nodo), [llamada])
        condicion = self._v_expresion(condicion_nodo)
        self._tipos_variables = guardado

        if salida is None:
            rama_salida = [self._valor_estado(estado)]
            anotacion = f" -> {self._tipo_estado(estado)}"
        else:
            # El tipo de retorno lo infiere Gleam: aquí la auxiliar devuelve
            # lo mismo que la función que la contiene.
            rama_salida = self._cerrar_bloque(list(salida))
            anotacion = ""

        firma = self._firma_parametros(parametros)
        lineas_fn = [f"fn {nombre_fn}({firma}){anotacion} {{"]
        if post_test:
            # El cuerpo corre primero: por eso se ejecuta al menos una vez.
            lineas_fn.extend(SANGRIA + l for l in cuerpo[:-1])
            lineas_fn.append(SANGRIA + f"case {condicion} {{")
            lineas_fn.extend(self._rama("True", rama_salida))
            lineas_fn.extend(self._rama("False", [cuerpo[-1]]))
            lineas_fn.append(SANGRIA + "}")
        else:
            lineas_fn.append(SANGRIA + f"case {condicion} {{")
            lineas_fn.extend(self._rama("True", cuerpo))
            lineas_fn.extend(self._rama("False", rama_salida))
            lineas_fn.append(SANGRIA + "}")
        lineas_fn.append("}")
        self._funciones_auxiliares.append("\n".join(lineas_fn))

        if salida is None:
            return [f"{self._destino_estado(estado)}{llamada}"]
        return [llamada]

    @staticmethod
    def _rama(etiqueta, lineas):
        """Una rama de `case`: en una línea si cabe, en bloque si no."""
        if len(lineas) == 1:
            return [SANGRIA * 2 + f"{etiqueta} -> {lineas[0]}"]
        salida = [SANGRIA * 2 + f"{etiqueta} -> {{"]
        salida.extend(SANGRIA * 3 + l for l in lineas)
        salida.append(SANGRIA * 2 + "}")
        return salida

    # --- pa_cada: contador --------------------------------------------------
    def _v_sent_para(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 9:
            return []
        variable = self._lexema(hijos[1])
        desde = self._v_expresion(hijos[3])
        hasta = self._v_expresion(hijos[5])
        nodo_paso = hijos[6]

        paso = None
        if not self._deriva_vacio(nodo_paso):
            expr_paso = self._hijo_nt(nodo_paso, "expresion")
            if expr_paso is not None:
                paso = self._v_expresion(expr_paso)

        guardado = dict(self._tipos_variables)
        self._tipos_variables[variable] = NUMERITO
        cuerpo = self._cerrar_bloque(
            self._v_bloque(self._hijo_nt(nodo, "bloque")))
        self._tipos_variables = guardado

        if paso is None or paso == "1":
            # Paso 1: list.range compuesto con list.each es lo idiomático.
            self._modulos.add("gleam/list")
            lineas = [f"list.range({desde}, {hasta})"]
            lineas.append(f"|> list.each(fn({variable}) {{")
            lineas.extend(SANGRIA + l for l in cuerpo)
            lineas.append("})")
            return lineas

        # Paso distinto de 1: list.range no admite incremento -> recursión.
        self._contador_bucles += 1
        nombre_fn = f"bucle_{self._contador_bucles}"
        comparacion = f"{variable} <= {hasta}" if not paso.startswith("-") \
            else f"{variable} >= {hasta}"
        lineas_fn = [f"fn {nombre_fn}({variable}: Int) -> Nil {{"]
        lineas_fn.append(SANGRIA + f"case {comparacion} {{")
        lineas_fn.append(SANGRIA * 2 + "True -> {")
        lineas_fn.extend(SANGRIA * 3 + l for l in cuerpo)
        lineas_fn.append(SANGRIA * 3 + f"{nombre_fn}({variable} + {paso})")
        lineas_fn.append(SANGRIA * 2 + "}")
        lineas_fn.append(SANGRIA * 2 + "False -> Nil")
        lineas_fn.append(SANGRIA + "}")
        lineas_fn.append("}")
        self._funciones_auxiliares.append("\n".join(lineas_fn))
        return [f"{nombre_fn}({desde})"]

    # ==================================================================
    #  ACCIÓN SDT: EXPRESIONES
    # ==================================================================
    def _v_expresion(self, nodo):
        nombre = self._nombre(nodo)

        if nombre == "expresion":
            hijos = self._hijos(nodo)
            return self._v_expresion(hijos[0]) if hijos else "Nil"

        if nombre in NIVELES_BINARIOS:
            hijos = self._hijos(nodo)
            if not hijos:
                return "Nil"
            izquierda = self._v_expresion(hijos[0])
            tipo_izq = self._tipo_de(hijos[0])
            if len(hijos) < 2 or self._deriva_vacio(hijos[1]):
                return izquierda
            return self._v_cadena(izquierda, tipo_izq, hijos[1])

        if nombre == "expr_unaria":
            hijos = self._hijos(nodo)
            if len(hijos) == 2:
                operador = self._lexema(hijos[0])
                operando = self._v_expresion(hijos[1])
                if operador == "nanai":
                    return f"!{operando}"
                if self._tipo_de(hijos[1]) == QUEBRADITO:
                    return f"-. {operando}"
                return f"-{operando}"
            return self._v_expresion(hijos[0]) if hijos else "Nil"

        if nombre == "expr_primaria":
            return self._v_primaria(nodo)

        return "Nil"

    def _v_cadena(self, izquierda, tipo_izq, nodo_p):
        """Recorre la cola `A' ::= op B A'` emitiendo el operador de Gleam."""
        if not isinstance(nodo_p, dict) or self._deriva_vacio(nodo_p):
            return izquierda
        hijos = self._hijos(nodo_p)
        if len(hijos) < 2:
            return izquierda

        operador = self._lexema(hijos[0])
        derecha = self._v_expresion(hijos[1])
        tipo_der = self._tipo_de(hijos[1])

        texto, tipo_resultado = self._emitir_operador(
            operador, izquierda, derecha, tipo_izq, tipo_der)

        resto = hijos[2] if len(hijos) > 2 else None
        return self._v_cadena(texto, tipo_resultado, resto)

    def _emitir_operador(self, operador, izquierda, derecha, tipo_izq, tipo_der):
        """La decisión central del SDT: qué operador de Gleam corresponde."""
        # Concatenación: Gleam exige String en ambos lados.
        if operador == "<>":
            izq = self._convertir_a_cadena(izquierda, tipo_izq)
            der = self._convertir_a_cadena(derecha, tipo_der)
            return f"{izq} <> {der}", CUENTO

        # Potencia: en Gleam es una llamada que devuelve Result.
        if operador == "**":
            self._modulos.add("gleam/int")
            if QUEBRADITO in (tipo_izq, tipo_der):
                self._modulos.update(("gleam/float", "gleam/result"))
                return (f"result.unwrap(float.power({izquierda}, {derecha}), 0.0)",
                        QUEBRADITO)
            self._modulos.add("gleam/result")
            return (f"result.unwrap(int.power({izquierda}, {derecha}), 0)",
                    QUEBRADITO)

        # Operadores con nombre.
        if operador in OPERADOR_NOMBRADO:
            simbolo = OPERADOR_NOMBRADO[operador]
            tipo = SIONO
            return f"{izquierda} {simbolo} {derecha}", tipo

        # División entera y módulo de Gleam.
        if operador == "/" and tipo_izq == NUMERITO and tipo_der == NUMERITO:
            return f"{izquierda} / {derecha}", NUMERITO
        if operador == "%":
            return f"{izquierda} % {derecha}", NUMERITO

        # Aritméticos y relacionales: variante con punto si son Float.
        es_flotante = QUEBRADITO in (tipo_izq, tipo_der)
        simbolo = OPERADOR_FLOTANTE[operador] if (
            es_flotante and operador in OPERADOR_FLOTANTE) else operador

        if operador in (">", "<", ">=", "<="):
            return f"{izquierda} {simbolo} {derecha}", SIONO
        tipo_resultado = QUEBRADITO if es_flotante else tipo_izq
        return f"{izquierda} {simbolo} {derecha}", tipo_resultado

    def _convertir_a_cadena(self, texto, tipo):
        """Inserta int.to_string / float.to_string donde Gleam lo exige."""
        if tipo == NUMERITO:
            self._modulos.add("gleam/int")
            return f"int.to_string({texto})"
        if tipo == QUEBRADITO:
            self._modulos.add("gleam/float")
            return f"float.to_string({texto})"
        if tipo == SIONO:
            self._modulos.add("gleam/bool")
            return f"bool.to_string({texto})"
        return texto

    def _como_cadena(self, nodo_expresion):
        """Para io.println, que solo acepta String."""
        texto = self._v_expresion(nodo_expresion)
        return self._convertir_a_cadena(texto, self._tipo_de(nodo_expresion))

    def _v_primaria(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return "Nil"

        # "(" <expresion> ")"
        if len(hijos) == 3 and self._token_tipo(hijos[0]) == "PAR_ABRE":
            return f"({self._v_expresion(hijos[1])})"

        hoja = hijos[0]
        tipo_token = self._token_tipo(hoja)
        lexema = self._lexema(hoja)

        if tipo_token == "NUM_REAL":
            return self._literal_flotante(lexema)
        if tipo_token == "NUM_ENTERO":
            return lexema
        if tipo_token == "CADENA_LITERAL":
            return lexema if lexema.startswith('"') else f'"{lexema}"'
        if tipo_token == "LIT_VERDADERO" or lexema == "sizas":
            return "True"
        if tipo_token == "LIT_FALSO" or lexema == "naranjas":
            return "False"

        if tipo_token == "IDENTIFICADOR":
            sufijo = hijos[1] if len(hijos) > 1 else None
            if self._es_llamada(sufijo):
                argumentos = self._v_argumentos(
                    self._hijo_nt(sufijo, "argumentos"))
                return f"{lexema}({', '.join(argumentos)})"
            return lexema

        return lexema or "Nil"

    @staticmethod
    def _literal_flotante(lexema):
        """Gleam exige punto decimal explícito en los Float."""
        return lexema if "." in lexema else f"{lexema}.0"

    def _es_llamada(self, sufijo):
        if not isinstance(sufijo, dict):
            return False
        return any(self._token_tipo(h) == "PAR_ABRE"
                   for h in self._hijos(sufijo))


def traducir(cst, tabla_simbolos=None):
    """Atajo funcional: CST (+ tabla de símbolos) -> código Gleam."""
    return TraductorSDT(cst, tabla_simbolos).traducir()
