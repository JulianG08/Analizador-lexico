# -*- coding: utf-8 -*-
"""
Módulo: reglas_sdt.py
Descripción: Las REGLAS DE TRADUCCIÓN ORIENTADA POR LA SINTAXIS (Entrega Final).

Es la especificación, en prosa, de lo que `traductor_sdt.py` implementa. Cada
entrada corresponde a una producción de la gramática y describe:

  * los atributos que la acción usa (y de dónde vienen: sintetizados por el
    análisis semántico, heredados del contexto, o de la tabla de símbolos);
  * la acción de traducción propiamente dicha;
  * cómo queda la salida en el lenguaje destino.

`generar_documento_final.py` las renderiza en AZUL sobre la producción que
les corresponde, siguiendo la convención de colores del enunciado.
"""

REGLAS_SDT = [
    {
        "ancla": "programa",
        "id": "SDT-1",
        "titulo": "Estructura del módulo de salida",
        "nodos": "&lt;programa&gt;, &lt;lista_declaraciones&gt;, &lt;declaracion&gt;",
        "filas": [
            ("Atributos",
             "<b>modulos</b>: <i>sintetizado</i> acumulado en todo el recorrido. "
             "Conjunto de módulos de la biblioteca estándar de Gleam que las "
             "demás acciones SDT pidieron (<tt>gleam/io</tt>, <tt>gleam/int</tt>, …).<br>"
             "<b>code(decl)</b>: <i>sintetizado</i> en cada &lt;declaracion&gt;."),
            ("Acción de traducción",
             "<tt>programa.code ← imports(modulos) ‖ funciones ‖ main</tt><br>"
             "1. Separar las &lt;declaracion&gt; en definiciones de función y "
             "sentencias de nivel superior.<br>"
             "2. Gleam no admite sentencias fuera de una función: las de nivel "
             "superior se envuelven en <tt>pub fn main() { … }</tt>.<br>"
             "3. Emitir los <tt>import</tt> al principio, ordenados, solo los "
             "que alguna acción haya pedido.<br>"
             "4. Añadir al final las funciones auxiliares generadas por los "
             "bucles."),
            ("Salida en Gleam",
             "<tt>import gleam/io<br>import gleam/int<br><br>"
             "pub fn main() { … }<br><br>pub fn f(…) { … }<br><br>"
             "fn bucle_1(…) { … }</tt>"),
        ],
    },
    {
        "ancla": "def_funcion",
        "id": "SDT-2",
        "titulo": "Definición de función",
        "nodos": ("&lt;def_funcion&gt;, &lt;parametros&gt;, &lt;param_lista&gt;, "
                  "&lt;param_resto&gt;, &lt;tipo_retorno&gt;"),
        "filas": [
            ("Atributos",
             "<b>nombre</b>: <i>heredado</i> del token IDENTIFICADOR.<br>"
             "<b>params</b>: <i>sintetizado</i> recorriendo &lt;param_lista&gt; y "
             "su cola recursiva &lt;param_resto&gt;. Lista de pares (nombre, tipo).<br>"
             "<b>tipo_retorno</b>: <i>sintetizado</i> en &lt;tipo_retorno&gt;; vale ⊥ "
             "cuando la producción deriva en ε.<br>"
             "<b>code(bloque)</b>: <i>sintetizado</i> en el cuerpo."),
            ("Acción de traducción",
             "<tt>code ← \"pub fn \" nombre \"(\" params \") -> \" T \" {\" code(bloque) \"}\"</tt><br>"
             "1. Traducir cada tipo de Paisascript al de Gleam: numerito→Int, "
             "quebradito→Float, cuento→String, siono→Bool.<br>"
             "2. Si <b>tipo_retorno = ⊥</b> se omite la flecha y Gleam infiere "
             "el tipo.<br>"
             "3. Registrar los parámetros como variables vivas antes de "
             "traducir el cuerpo, y restaurar el entorno al salir.<br>"
             "4. Cerrar el cuerpo con una expresión (ver SDT-11)."),
            ("Salida en Gleam",
             "<tt>hagale_pues f(numerito n) pa_que_lleve numerito dele_pues … ya_quedo</tt><br>"
             "se convierte en<br>"
             "<tt>pub fn f(n: Int) -> Int { … }</tt>"),
        ],
    },
    {
        "ancla": "sent_declaracion",
        "id": "SDT-3",
        "titulo": "Declaración de variable",
        "nodos": "&lt;sent_declaracion&gt;, &lt;tipo_opcional&gt;",
        "filas": [
            ("Atributos",
             "<b>id.lexema</b>: <i>heredado</i> del token.<br>"
             "<b>code(expr)</b> y <b>type(expr)</b>: <i>sintetizados</i> en la "
             "expresión; el tipo lo resolvió el análisis semántico y queda "
             "anotado en el nodo.<br>"
             "<b>entorno</b>: <i>heredado</i>; la tabla de tipos vivos que la "
             "fase SDT va alimentando."),
            ("Acción de traducción",
             "<tt>code ← \"let \" id.lexema \" = \" code(expr)</tt><br>"
             "1. Emitir el enlace con <tt>let</tt>.<br>"
             "2. Registrar <tt>entorno[id] ← type(expr)</tt>, porque las "
             "acciones posteriores necesitan ese tipo para elegir operadores.<br>"
             "3. La redeclaración del mismo nombre es válida: en Gleam "
             "<tt>let</tt> crea un enlace nuevo (shadowing), que es justo la "
             "semántica de Paisascript."),
            ("Salida en Gleam",
             "<tt>pille_pues numerito x = 5</tt> &nbsp;→&nbsp; <tt>let x = 5</tt>"),
        ],
    },
    {
        "ancla": "sent_lectura",
        "id": "SDT-4",
        "titulo": "Lectura de consola, con conversión de tipo",
        "nodos": "&lt;sent_lectura&gt;",
        "filas": [
            ("Atributos",
             "<b>id.lexema</b>: <i>heredado</i>.<br>"
             "<b>id.type</b>: consultado en la <b>tabla de símbolos</b> que "
             "construyó el análisis semántico."),
            ("Acción de traducción",
             "<tt>code ← \"let assert Ok(\" id \") = erlang.get_line(\\\"\\\")\"</tt><br>"
             "1. Pedir el módulo <tt>gleam/erlang</tt>.<br>"
             "2. La consola entrega <b>String</b>. Si la tabla de símbolos dice "
             "que la variable es numerito o quebradito, añadir la conversión, "
             "porque Gleam no convierte de forma implícita:<br>"
             "<tt>let assert Ok(x) = int.parse(string.trim(x))</tt><br>"
             "3. Si el tipo es desconocido, la variable queda como cuento."),
            ("Salida en Gleam",
             "<tt>escuche_pues(edad)</tt> con <tt>edad: numerito</tt> →<br>"
             "<tt>let assert Ok(edad) = erlang.get_line(\"\")<br>"
             "let assert Ok(edad) = int.parse(string.trim(edad))</tt>"),
        ],
    },
    {
        "ancla": "sent_impresion",
        "id": "SDT-5",
        "titulo": "Impresión por consola",
        "nodos": "&lt;sent_impresion&gt;",
        "filas": [
            ("Atributos",
             "<b>code(expr)</b> y <b>type(expr)</b>: <i>sintetizados</i>."),
            ("Acción de traducción",
             "<tt>code ← \"io.println(\" aCadena(code(expr), type(expr)) \")\"</tt><br>"
             "La función auxiliar <tt>aCadena</tt> es la misma de SDT-9: "
             "<tt>io.println</tt> solo acepta String, así que un numerito pasa "
             "por <tt>int.to_string</tt>, un quebradito por "
             "<tt>float.to_string</tt> y un siono por <tt>bool.to_string</tt>."),
            ("Salida en Gleam",
             "<tt>hable_pues(total)</tt> con total numerito →<br>"
             "<tt>io.println(int.to_string(total))</tt>"),
        ],
    },
    {
        "ancla": "sent_si",
        "id": "SDT-6",
        "titulo": "Condicional y reestructuración del retorno anticipado",
        "nodos": "&lt;sent_si&gt;, &lt;rama_sino&gt;, &lt;sent_retornar&gt;",
        "filas": [
            ("Atributos",
             "<b>code(cond)</b>, <b>code(entonces)</b>, <b>code(sino)</b>: "
             "<i>sintetizados</i>.<br>"
             "<b>continuacion</b>: <i>heredado</i>. Es la lista de sentencias "
             "que vienen DESPUÉS del condicional. Es el atributo que hace "
             "posible eliminar el retorno anticipado."),
            ("Acción de traducción",
             "Caso general:<br>"
             "<tt>code ← \"case \" code(cond) \" { True -> {\" entonces \"} "
             "False -> {\" sino \"} }\"</tt><br>"
             "Caso del <b>retorno anticipado</b> (un <tt>si_acaso</tt> sin "
             "<tt>sino_pues</tt> cuyo cuerpo termina en <tt>entregue_pues</tt>): "
             "Gleam no tiene <tt>return</tt>, así que la rama False recibe la "
             "<b>continuación</b> completa.<br>"
             "Sin esta transformación las dos ramas del <tt>case</tt> tendrían "
             "tipos distintos y el código no compilaría."),
            ("Salida en Gleam",
             "<tt>si_acaso n &lt; 2 entonces_pues entregue_pues naranjas asi_quedo<br>"
             "… resto … </tt><br>se convierte en<br>"
             "<tt>case n &lt; 2 {<br>&nbsp;&nbsp;True -> { False }<br>"
             "&nbsp;&nbsp;False -> { … resto … }<br>}</tt>"),
        ],
    },
    {
        "ancla": "sent_mientras",
        "id": "SDT-7",
        "titulo": "Bucle de condición al principio → recursión de cola",
        "nodos": "&lt;sent_mientras&gt;",
        "filas": [
            ("Atributos",
             "<b>estado</b>: <i>sintetizado</i> del cuerpo. Variables que el "
             "cuerpo vuelve a enlazar Y que ya existían fuera: son las únicas "
             "que cambian de una vuelta a otra.<br>"
             "<b>libres</b>: <i>sintetizado</i>. Variables que el bucle solo "
             "LEE y vienen de fuera.<br>"
             "<b>tipos</b>: de la <b>tabla de símbolos</b>, para anotar la firma.<br>"
             "<b>continuacion</b>: <i>heredado</i> (ver SDT-6)."),
            ("Acción de traducción",
             "Gleam no tiene <tt>while</tt>: se genera una función auxiliar "
             "recursiva de cola, que el BEAM ejecuta en espacio constante.<br>"
             "1. Calcular <b>estado</b> y <b>libres</b>. Los dos entran como "
             "parámetros; solo el estado se devuelve.<br>"
             "2. Emitir <tt>fn bucle_k(libres, estado) -> T { case cond { True "
             "-> { cuerpo; bucle_k(…) } False -> estado } }</tt>.<br>"
             "3. En el punto de la llamada: "
             "<tt>let estado = bucle_k(libres, estado)</tt>.<br>"
             "4. Si el cuerpo contiene un <tt>entregue_pues</tt>, la rama False "
             "recibe la continuación y la auxiliar devuelve el valor de la "
             "función que la contiene."),
            ("Salida en Gleam",
             "<tt>mientras_que i &lt;= n dele_pues … hasta_ahi</tt> →<br>"
             "<tt>fn bucle_1(n: Int, acumulado: Int, i: Int) -> #(Int, Int) {<br>"
             "&nbsp;&nbsp;case i &lt;= n {<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;True -> { … bucle_1(n, acumulado, i) }<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;False -> #(acumulado, i)<br>"
             "&nbsp;&nbsp;}<br>}</tt>"),
        ],
    },
    {
        "ancla": "sent_para",
        "id": "SDT-8",
        "titulo": "Bucle con contador → list.range o recursión",
        "nodos": "&lt;sent_para&gt;, &lt;paso_opcional&gt;",
        "filas": [
            ("Atributos",
             "<b>var</b>: <i>heredado</i>, la variable de control.<br>"
             "<b>code(desde)</b>, <b>code(hasta)</b>: <i>sintetizados</i>.<br>"
             "<b>paso</b>: <i>sintetizado</i> de &lt;paso_opcional&gt;; vale 1 "
             "cuando la producción deriva en ε (ver SDT-12)."),
            ("Acción de traducción",
             "Hay dos caminos, y la elección depende del paso:<br>"
             "<b>paso = 1</b> → la forma idiomática de Gleam:<br>"
             "<tt>list.range(desde, hasta) |&gt; list.each(fn(var) { cuerpo })</tt><br>"
             "Pide el módulo <tt>gleam/list</tt>.<br>"
             "<b>paso ≠ 1</b> → <tt>list.range</tt> de Gleam NO admite "
             "incremento, así que se genera recursión de cola con la "
             "comparación orientada según el signo del paso "
             "(<tt>&lt;=</tt> si avanza, <tt>&gt;=</tt> si retrocede)."),
            ("Salida en Gleam",
             "<tt>pa_cada k desde 0 hasta 10 de_a 2 dele_pues … listo_pues</tt> →<br>"
             "<tt>fn bucle_2(k: Int) -> Nil {<br>"
             "&nbsp;&nbsp;case k &lt;= 10 {<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;True -> { … bucle_2(k + 2) }<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;False -> Nil<br>&nbsp;&nbsp;}<br>}</tt>"),
        ],
    },
    {
        "ancla": "sent_repita",
        "id": "SDT-9",
        "titulo": "Bucle de condición al final → cuerpo antes del case",
        "nodos": "&lt;sent_repita&gt;",
        "filas": [
            ("Atributos",
             "Los mismos de SDT-7: <b>estado</b>, <b>libres</b>, "
             "<b>continuacion</b>.<br>"
             "<b>sentido</b>: <i>heredado</i> de la construcción. En "
             "<tt>repita_pues</tt> la condición es de SALIDA, no de "
             "permanencia."),
            ("Acción de traducción",
             "Es la misma recursión de cola de SDT-7 con dos diferencias, y "
             "las dos vienen de la semántica post-test:<br>"
             "1. El cuerpo se emite <b>ANTES</b> del <tt>case</tt>, no dentro "
             "de una de sus ramas. Eso es lo que hace que corra al menos una "
             "vez.<br>"
             "2. Las ramas se invierten: <tt>True</tt> (se cumplió "
             "<tt>hasta_que</tt>) devuelve el estado y es el caso base; "
             "<tt>False</tt> vuelve a llamar."),
            ("Salida en Gleam",
             "<tt>repita_pues … hasta_que v &gt;= 3</tt> →<br>"
             "<tt>fn bucle_3(v: Int) -> Int {<br>"
             "&nbsp;&nbsp;… cuerpo …<br>"
             "&nbsp;&nbsp;case v &gt;= 3 {<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;True -> v<br>"
             "&nbsp;&nbsp;&nbsp;&nbsp;False -> bucle_3(v)<br>"
             "&nbsp;&nbsp;}<br>}</tt>"),
        ],
    },
    {
        "ancla": "sent_pillemos",
        "id": "SDT-10",
        "titulo": "Calce de patrones",
        "nodos": ("&lt;sent_pillemos&gt;, &lt;lista_casos&gt;, "
                  "&lt;lista_casos_resto&gt;, &lt;caso&gt;, &lt;patron&gt;, "
                  "&lt;cuerpo_caso&gt;"),
        "filas": [
            ("Atributos",
             "<b>code(sujeto)</b>: <i>sintetizado</i>.<br>"
             "<b>code(patron)</b>: <i>sintetizado</i> en cada &lt;patron&gt;.<br>"
             "<b>casos</b>: <i>sintetizado</i> recorriendo la cola recursiva "
             "&lt;lista_casos_resto&gt; (ver SDT-12)."),
            ("Acción de traducción",
             "<tt>code ← \"case \" code(sujeto) \" { \" casos \" }\"</tt><br>"
             "Es la traducción más directa del lenguaje, porque "
             "<tt>pillemos</tt> se diseñó contra el <tt>case</tt> de Gleam.<br>"
             "Conversión de patrones: <tt>sizas</tt>→<tt>True</tt>, "
             "<tt>naranjas</tt>→<tt>False</tt>, <tt>_</tt>→<tt>_</tt>, y los "
             "literales reales reciben punto decimal explícito.<br>"
             "Un cuerpo de una sola línea va en la misma línea del patrón; uno "
             "de varias va entre llaves."),
            ("Salida en Gleam",
             "<tt>pillemos x { 10 pa_que_lleve hable_pues(\"diez\") }</tt> →<br>"
             "<tt>case x { 10 -> io.println(\"diez\") }</tt>"),
        ],
    },
    {
        "ancla": "expr_multiplicativa_p",
        "id": "SDT-11",
        "titulo": "Operadores: la elección depende del tipo",
        "nodos": ("&lt;expr_aditiva&gt;, &lt;expr_multiplicativa&gt;, "
                  "&lt;expr_potencia&gt;, &lt;expr_relacional&gt;, "
                  "&lt;expr_igualdad&gt;, &lt;expr_concat&gt;, &lt;expr_y&gt;, "
                  "&lt;expr_o&gt;, &lt;expr_unaria&gt;"),
        "filas": [
            ("Atributos",
             "<b>type_izq</b> y <b>type_der</b>: <i>sintetizados</i> por el "
             "análisis semántico y anotados en el árbol. <b>Son el atributo "
             "crítico de toda la fase SDT.</b><br>"
             "<b>code_izq</b>, <b>code_der</b>: <i>sintetizados</i>."),
            ("Acción de traducción",
             "En Gleam <tt>Int</tt> y <tt>Float</tt> son tipos disjuntos con "
             "operadores <b>distintos</b>, así que la acción consulta el tipo "
             "antes de emitir:<br>"
             "<tt>SI type ∈ {quebradito} → + - * / &gt; &lt; &gt;= &lt;= "
             "se emiten como +. -. *. /. &gt;. &lt;. &gt;=. &lt;=.</tt><br>"
             "<tt>igualito → ==</tt>, <tt>distinto → !=</tt>, "
             "<tt>y_tambien → &amp;&amp;</tt>, <tt>o_que → ||</tt>, "
             "<tt>nanai → !</tt><br>"
             "<tt>**</tt> no es operador en Gleam: se emite "
             "<tt>int.power</tt> / <tt>float.power</tt>, que devuelven "
             "<tt>Result</tt>, envueltos en <tt>result.unwrap</tt>.<br>"
             "<tt>&lt;&gt;</tt> exige String en ambos lados: la acción inserta "
             "<tt>int.to_string</tt> / <tt>float.to_string</tt> donde haga falta."),
            ("Salida en Gleam",
             "<tt>a + b</tt> con quebradito &nbsp;→&nbsp; <tt>a +. b</tt><br>"
             "<tt>x + y</tt> con numerito &nbsp;→&nbsp; <tt>x + y</tt><br>"
             "<tt>\"n = \" &lt;&gt; x</tt> &nbsp;→&nbsp; "
             "<tt>\"n = \" &lt;&gt; int.to_string(x)</tt>"),
        ],
    },
    {
        "ancla": "lista_sentencias",
        "id": "SDT-12",
        "titulo": "Listas vacías (ε) y producciones recursivas",
        "nodos": ("&lt;lista_declaraciones&gt;, &lt;lista_sentencias&gt;, "
                  "&lt;param_resto&gt;, &lt;arg_resto&gt;, "
                  "&lt;lista_casos_resto&gt;, &lt;rama_sino&gt;, "
                  "&lt;paso_opcional&gt;, &lt;tipo_opcional&gt;, "
                  "&lt;expr_o_p&gt; … &lt;expr_potencia_p&gt;"),
        "filas": [
            ("Atributos",
             "<b>code</b>: <i>sintetizado</i> en cada nodo de la lista.<br>"
             "<b>heredado_izq</b>: en las colas de expresión "
             "(&lt;expr_X_p&gt;), el código y el tipo del operando izquierdo "
             "bajan como atributo <i>heredado</i>, porque la gramática está "
             "factorizada a la derecha para ser LL(1)."),
            ("Acción de traducción",
             "La gramática es recursiva por la derecha, así que cada lista "
             "tiene una producción vacía. Las reglas son uniformes:<br>"
             "<b>Producción ε</b> → <tt>code ← \"\"</tt>. No emite nada. En "
             "&lt;rama_sino&gt; vacía la acción emite <tt>False -> Nil</tt>, "
             "porque un <tt>case</tt> de Gleam debe cubrir todos los casos. En "
             "&lt;paso_opcional&gt; vacío, <tt>paso ← 1</tt>. En "
             "&lt;tipo_opcional&gt; vacío el tipo se infiere de la expresión.<br>"
             "<b>Producción recursiva</b> → <tt>code ← code(elemento) ‖ "
             "code(resto)</tt>: se concatena el elemento con el resultado de "
             "la cola, separando con salto de línea las sentencias y con coma "
             "los parámetros y argumentos.<br>"
             "<b>Colas de expresión</b> → <tt>A' ::= op B A'</tt> se resuelve "
             "pasando el resultado parcial hacia la derecha como atributo "
             "heredado, de modo que <tt>a - b - c</tt> se asocie a la "
             "izquierda, como corresponde."),
            ("Salida en Gleam",
             "<tt>&lt;lista_sentencias&gt; ::= ε</tt> → no emite nada.<br>"
             "<tt>&lt;rama_sino&gt; ::= ε</tt> → <tt>False -> Nil</tt><br>"
             "<tt>&lt;paso_opcional&gt; ::= ε</tt> → paso 1 → "
             "<tt>list.range(a, b)</tt>"),
        ],
    },
    {
        "ancla": "sent_llamada",
        "id": "SDT-13",
        "titulo": "Llamada a función y cierre de bloque",
        "nodos": ("&lt;sent_llamada&gt;, &lt;argumentos&gt;, &lt;arg_resto&gt;, "
                  "&lt;sufijo_id&gt;, &lt;bloque&gt;"),
        "filas": [
            ("Atributos",
             "<b>nombre</b>: <i>heredado</i>.<br>"
             "<b>args</b>: <i>sintetizado</i> recorriendo la cola "
             "&lt;arg_resto&gt;.<br>"
             "<b>ultima</b>: <i>sintetizado</i> en &lt;bloque&gt;; indica si la "
             "última línea del bloque es una expresión o un enlace."),
            ("Acción de traducción",
             "<tt>code ← nombre \"(\" args \")\"</tt>, con los argumentos "
             "separados por coma. Una llamada vale igual como sentencia que "
             "como expresión, porque en Gleam todo es expresión.<br>"
             "<b>Cierre de bloque</b>: en Gleam todo bloque DEVUELVE un valor, "
             "así que no puede terminar en <tt>let</tt>. Si la última línea "
             "traducida es un enlace, la acción añade <tt>Nil</tt>, que es el "
             "valor unitario. Sin esto el código generado no compilaría."),
            ("Salida en Gleam",
             "<tt>sumar(1, 2)</tt> &nbsp;→&nbsp; <tt>sumar(1, 2)</tt><br>"
             "un bloque que termina en <tt>let x = 5</tt> recibe una línea "
             "<tt>Nil</tt> al final."),
        ],
    },
]
