"""
Módulo: ai_assistant.py
Descripción: Integración con OpenAI para detección de errores sintácticos
y sugerencias inteligentes adaptadas al contexto del compilador Paisascript.
"""
import os
from openai import OpenAI

def obtener_cliente_openai(api_key=None):
    """
    Inicializa el cliente de OpenAI. 
    Si no se pasa una clave explícita, intenta buscarla en las variables de entorno.
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        
    if not api_key:
        return None
        
    return OpenAI(api_key=api_key)

def analizar_error_con_ia(codigo_fuente, error_detectado, api_key=None):
    """
    Envía el fragmento de código y el error al modelo de OpenAI para obtener 
    una explicación amigable y sugerencias de corrección.
    """
    cliente = obtener_cliente_openai(api_key)
    
    if not cliente:
        return "⚠️ No se ha configurado una API Key de OpenAI válida o la variable de entorno está vacía."

    prompt_sistema = (
        "Eres un asistente experto en compiladores, análisis sintáctico y en el lenguaje de programación 'Paisascript'. "
        "Tu objetivo es ayudar a estudiantes a corregir errores de sintaxis en su código fuente de forma clara, amigable y dando una sugerencia concreta."
    )

    prompt_usuario = f"""
    Analiza el siguiente código fuente en Paisascript que presentó un fallo en el compilador:
    
    CÓDIGO FUENTE:
    {codigo_fuente}
    
    ERROR DETECTADO / ESTADO DEL PARSER:
    {error_detectado}
    
    Por favor, responde estructuradamente con:
    1. 🔍 **¿Qué falló?** (Explicación breve del error sintáctico o léxico).
    2. 💡 **Sugerencia de corrección** (Cómo debe ajustarse el código para que sea válido).
    """

    try:
        response = cliente.chat.completions.create(
            model="gpt-4o-mini",
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
