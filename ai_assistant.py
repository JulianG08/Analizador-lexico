"""
Módulo: ai_assistant.py
Descripción: Integración con OpenAI para detección de errores sintácticos
y sugerencias inteligentes adaptadas al contexto del compilador Paisascript.
"""
import os
from pathlib import Path

# El paquete `openai` es OPCIONAL: la app debe poder arrancar y ejecutar el
# analisis lexico, sintactico y semantico aunque no se haya instalado (o no se
# quiera usar) la integracion con IA del bonus.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# `python-dotenv` tambien es opcional: si no esta, se usan solo las variables
# de entorno del sistema o los Secrets de Streamlit.
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

# Indica si la integracion con IA esta disponible en este entorno.
OPENAI_DISPONIBLE = OpenAI is not None

# Carga las variables definidas en el archivo .env al entorno de Python
load_dotenv(override=True)

# Streamlit es opcional: este modulo debe poder importarse desde un script
# suelto o desde una prueba sin que exista una sesion de Streamlit.
try:
    import streamlit as st
except ImportError:
    st = None

# Directorio raíz del proyecto para ubicar la gramática
RAIZ = Path(__file__).parent


def leer_secreto(nombre, defecto=None):
    """Lee una variable de configuracion, en este orden de prioridad:

    1. st.secrets  -> lo que se escribe en "Secrets" de Streamlit Cloud
                      (y, en local, en .streamlit/secrets.toml)
    2. os.environ  -> variables de entorno del sistema o del archivo .env

    Asi el mismo codigo funciona desplegado y en la maquina local sin
    cambiar una linea: basta con definir el nombre en el sitio que
    corresponda. Devuelve `defecto` si no aparece en ninguno de los dos.
    """
    # 1. Secrets de Streamlit. El acceso se envuelve porque, si no hay
    # archivo de secretos, Streamlit lanza una excepcion en vez de devolver
    # vacio; ese caso no es un error, solo significa "seguir buscando".
    if st is not None:
        try:
            if nombre in st.secrets:
                return str(st.secrets[nombre])
        except Exception:
            pass

    # 2. Entorno del proceso, que ya incluye lo cargado desde .env
    return os.getenv(nombre, defecto)


def limpiar_api_key(key):
    """Limpia la clave de posibles prefijos o caracteres accidentales."""
    if not key:
        return None
    key = key.replace("OPENAI_API_KEY=", "")
    key = key.replace("'", "").replace('"', '').strip()
    return key


def hay_api_key_configurada():
    """Indica si existe una clave utilizable sin que el usuario escriba nada.

    La usa la interfaz para mostrar el estado de la conexion en la barra
    lateral sin tener que instanciar el cliente.
    """
    return limpiar_api_key(leer_secreto("OPENAI_API_KEY")) is not None


def origen_api_key():
    """Devuelve de donde sale la clave: 'secrets', 'entorno' o None.

    Sirve unicamente para informar al usuario en la interfaz.
    """
    if st is not None:
        try:
            if "OPENAI_API_KEY" in st.secrets and limpiar_api_key(str(st.secrets["OPENAI_API_KEY"])):
                return "secrets"
        except Exception:
            pass
    if limpiar_api_key(os.getenv("OPENAI_API_KEY")):
        return "entorno"
    return None


MENSAJE_SIN_PAQUETE = (
    "⚠️ La integración con IA no está disponible en este entorno porque falta "
    "el paquete `openai`. El analizador léxico, sintáctico y semántico funciona "
    "con normalidad. Para habilitar el bonus ejecute: "
    "`pip install openai python-dotenv`."
)

MENSAJE_SIN_CLAVE = (
    "⚠️ No se ha configurado una API Key de OpenAI válida o la variable de "
    "entorno está vacía."
)


def obtener_cliente_openai(api_key=None):
    """
    Inicializa el cliente de OpenAI.
    Si no se pasa una clave explícita, la busca en los Secrets de Streamlit
    y, en su defecto, en las variables de entorno.

    Devuelve None si el paquete `openai` no está instalado o si no hay clave:
    la interfaz debe seguir funcionando sin la integración de IA.
    """
    if not OPENAI_DISPONIBLE:
        return None

    if not api_key:
        api_key = leer_secreto("OPENAI_API_KEY")

    api_key_limpia = limpiar_api_key(api_key)

    if not api_key_limpia:
        return None

    return OpenAI(api_key=api_key_limpia)

def cargar_gramatica():
    """Lee el archivo de la gramática BNF para dárselo como contexto a la IA."""
    ruta_gramatica = RAIZ / "gramatica_BNF_Paisascript.txt"
    if ruta_gramatica.exists():
        return ruta_gramatica.read_text(encoding="utf-8")
    return "Gramática BNF no disponible localmente."

def analizar_error_con_ia(codigo_fuente, error_detectado, api_key=None):
    """
    Envía el fragmento de código, el error y la gramática BNF de Paisascript 
    a OpenAI para obtener una explicación y sugerencias de corrección precisas.
    """
    if not OPENAI_DISPONIBLE:
        return MENSAJE_SIN_PAQUETE

    cliente = obtener_cliente_openai(api_key)

    if not cliente:
        return MENSAJE_SIN_CLAVE

    # Cargamos la gramática para que la IA conozca las reglas exactas del lenguaje
    gramatica_bn = cargar_gramatica()

    prompt_sistema = (
        "Eres un asistente experto en compiladores, análisis sintáctico y en el lenguaje de programación 'Paisascript'. "
        "Tu objetivo es ayudar a estudiantes a corregir errores de sintaxis en su código fuente de forma clara, amigable y dando una sugerencia concreta.\n\n"
        "A continuación se presenta la gramática oficial en formato BNF de Paisascript que debes utilizar estrictamente como referencia para evaluar el código:\n"
        f"```\n{gramatica_bn}\n```"
    )

    prompt_usuario = f"""
    Analiza el siguiente código fuente en Paisascript que presentó un fallo en el compilador:
    
    CÓDIGO FUENTE:
    {codigo_fuente}
    
    ERROR DETECTADO / ESTADO DEL PARSER:
    {error_detectado}
    
    Por favor, responde estructuradamente con:
    1. 🔍 **¿Qué falló?** (Explicación breve del error sintáctico o léxico basándote en la gramática BNF).
    2. 💡 **Sugerencia de corrección** (Cómo debe ajustarse el código para que cumpla con la gramática de Paisascript).
    """

    try:
        # El modelo tambien es configurable por Secrets / entorno; si no se
        # define en ninguno de los dos se usa el valor por defecto.
        response = cliente.chat.completions.create(
            model=leer_secreto("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ocurrió un error al comunicarse con la API de OpenAI: {str(e)}"


# =============================================================================
#  BONUS QUIZ 4 — MODALIDAD A: IA COMO CAPA ADICIONAL DE VALIDACIÓN SEMÁNTICA
# =============================================================================
#
# Los errores que detectan las reglas semánticas clásicas (SEM-1 a SEM-8,
# implementadas en analizador_semantico.py) se envían a un modelo de lenguaje
# junto con el código fuente y la tabla de símbolos. El modelo NO reemplaza
# las reglas: solo enriquece el diagnóstico con una explicación en lenguaje
# natural y una propuesta de corrección concreta. Ambas capas coexisten.

def _tabla_simbolos_a_texto(tabla_simbolos):
    """Resume la tabla de símbolos para dársela como contexto a la IA."""
    if tabla_simbolos is None:
        return "(no disponible)"
    try:
        filas = tabla_simbolos.filas()
    except Exception:
        return str(tabla_simbolos)

    if not filas:
        return "(vacía)"

    lineas = ["Ámbito | Lexema | Tipo | Categoría | Fila | Columna | Detalle"]
    for fila in filas:
        lineas.append(
            " | ".join(str(fila.get(clave, "")) for clave in (
                "Ámbito", "Lexema", "Tipo", "Categoría",
                "Fila", "Columna", "Detalle",
            ))
        )
    return "\n".join(lineas)


def analizar_error_semantico_con_ia(codigo_fuente, errores_semanticos,
                                    tabla_simbolos=None, api_key=None):
    """
    Modalidad A del bonus: capa adicional de validación semántica con IA.

    Recibe el código fuente, los errores semánticos detectados por las reglas
    clásicas (SEM-1 .. SEM-8) y la tabla de símbolos construida por
    `analizador_semantico.AnalizadorSemantico`. Devuelve una explicación y una
    sugerencia de corrección en lenguaje natural.

    Esta función NO sustituye el análisis clásico: solo lo complementa.
    """
    if not OPENAI_DISPONIBLE:
        return MENSAJE_SIN_PAQUETE

    cliente = obtener_cliente_openai(api_key)

    if not cliente:
        return MENSAJE_SIN_CLAVE

    gramatica_bn = cargar_gramatica()

    if errores_semanticos:
        errores_texto = "\n".join(
            f"- {error}" for error in errores_semanticos
        )
    else:
        errores_texto = "(no se detectaron errores semánticos por las reglas clásicas)"

    tabla_texto = _tabla_simbolos_a_texto(tabla_simbolos)

    prompt_sistema = (
        "Eres un asistente experto en compiladores y en el lenguaje 'Paisascript', "
        "un lenguaje imperativo con palabras reservadas paisas que se compila a Gleam. "
        "Su análisis semántico ya detectó errores con reglas de atributos clásicas "
        "(declaración vs tipo de la expresión, uso de identificadores no declarados, "
        "operandos incompatibles, condiciones que deben ser siono y aridad/tipos en "
        "llamadas a función). Tu tarea es EXPLICAR esos errores y PROPONER una "
        "corrección concreta, sin contradecir el diagnóstico de las reglas clásicas.\n\n"
        "Reglas del lenguaje relevantes:\n"
        "- Tipos: numerito (Int), quebradito (Float), cuento (String), siono (Bool).\n"
        "- Estático y fuerte: numerito y quebradito NO se mezclan implícitamente.\n"
        "- Inmutable con shadowing: 'pille_pues' crea un enlace nuevo; no hay reasignación.\n"
        "- 'escuche_pues(x)' declara/inicializa x leyendo de consola.\n"
        "- 'entregue_pues' retorna el valor de una función.\n\n"
        "Gramática BNF oficial de Paisascript:\n"
        f"```\n{gramatica_bn}\n```"
    )

    prompt_usuario = f"""
    CÓDIGO FUENTE EN PAISASCRIPT:
    {codigo_fuente}

    ERRORES SEMÁNTICOS DETECTADOS POR LAS REGLAS CLÁSICAS:
    {errores_texto}

    TABLA DE SÍMBOLOS CONSTRUIDA POR EL COMPILADOR:
    {tabla_texto}

    Responde de forma estructurada y breve, en español:
    1. 🔍 **Causa**: explica por qué cada error viola una regla semántica.
    2. 🛠️ **Corrección propuesta**: muestra el fragmento corregido en Paisascript
       (usando los tipos y palabras reservadas reales del lenguaje).
    3. 📌 **Regla aplicada**: indica si corresponde a declaración/tipos,
       identificador no declarado, operandos incompatibles, condición no booleana
       o llamada a función.
    """

    try:
        response = cliente.chat.completions.create(
            model=leer_secreto("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ocurrió un error al comunicarse con la API de OpenAI: {str(e)}"


# =============================================================================
#  BONUS ENTREGA FINAL — MODALIDAD C: VALIDACIÓN + OPTIMIZACIÓN DEL CÓDIGO
#  GENERADO POR LA FASE SDT
# =============================================================================
#
# A diferencia del bonus del Quiz 4 (que enriquecía los errores semánticos del
# código FUENTE), aquí el objeto de estudio es el código DESTINO: el texto
# Gleam que produjo `traductor_sdt.py`. El modelo hace dos tareas sobre él:
#
#   1. Validación: ¿es sintáctica y semánticamente correcto en Gleam?
#   2. Optimización: ¿qué se podría escribir de forma más idiomática?
#
# Es una capa ADICIONAL. El compilador produce su salida sin ella; si no hay
# paquete, clave o red, la interfaz lo indica y todo lo demás sigue igual.

# El prompt se expone como constante para poder documentarlo en el PDF y
# mostrarlo en la interfaz: el enunciado pide describir el prompt utilizado.
PROMPT_VALIDACION_GLEAM = """Eres un revisor experto del lenguaje Gleam.

El código de abajo fue GENERADO automáticamente por un compilador que traduce
desde Paisascript (un lenguaje imperativo con jerga paisa) hacia Gleam. El
compilador ya garantizó que el programa fuente es léxica, sintáctica y
semánticamente válido; lo que hay que revisar es la calidad del código destino.

Responde en español, en dos secciones y sin rodeos:

1. ✅ VALIDEZ — ¿compila en Gleam? Revisa en particular:
   - que no se mezclen Int y Float (Gleam usa `+` y `+.` como operadores
     DISTINTOS, lo mismo con `-` `*` `/` y los relacionales);
   - que todo bloque termine en una expresión y nunca en un `let`;
   - que cada módulo usado (`io.`, `int.`, `list.`, ...) esté importado;
   - que todas las ramas de un mismo `case` devuelvan el mismo tipo;
   - que las funciones recursivas reciban todas las variables que usan.
   Si encuentras un problema, cita la línea y explica por qué rompe.
   Si no encuentras ninguno, dilo claramente.

2. ⚡ OPTIMIZACIÓN — propón mejoras concretas e idiomáticas de Gleam
   (uso de `|>`, `list.fold` en vez de recursión manual, nombres más claros,
   simplificaciones). Muestra el fragmento reescrito.

No inventes problemas para rellenar: si el código está bien, dilo."""


def validar_codigo_generado(codigo_gleam, codigo_fuente=None, api_key=None):
    """Bonus (Modalidad C): valida y propone mejoras sobre la salida del SDT.

    Recibe el código Gleam que produjo la fase SDT y, opcionalmente, el
    programa Paisascript del que salió, para que el modelo pueda contrastar
    intención y resultado.

    Devuelve el texto de la respuesta, o un mensaje explicativo si la
    integración no está disponible. Nunca lanza: es una capa opcional y no
    debe tumbar al compilador.
    """
    if not OPENAI_DISPONIBLE:
        return MENSAJE_SIN_PAQUETE

    cliente = obtener_cliente_openai(api_key)
    if not cliente:
        return MENSAJE_SIN_CLAVE

    if not (codigo_gleam or "").strip():
        return ("No hay código generado que validar. El compilador solo "
                "produce salida cuando no hay errores en ninguna fase.")

    partes = []
    if codigo_fuente:
        partes.append("PROGRAMA FUENTE EN PAISASCRIPT:\n"
                      f"```\n{codigo_fuente}\n```\n")
    partes.append("CÓDIGO GLEAM GENERADO POR LA FASE SDT:\n"
                  f"```gleam\n{codigo_gleam}\n```")
    prompt_usuario = "\n".join(partes)

    try:
        respuesta = cliente.chat.completions.create(
            model=leer_secreto("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": PROMPT_VALIDACION_GLEAM},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        return respuesta.choices[0].message.content
    except Exception as e:                                      # noqa: BLE001
        return f"❌ Ocurrió un error al comunicarse con la API de OpenAI: {e}"
