# Paisascript - Analizador Léxico y Gramática

**Paisascript** es un lenguaje de programación de juguete (pseudocódigo) diseñado con la jerga y el sabor de la cultura paisa (Antioquia, Colombia). Este proyecto implementa un analizador léxico (Lexer) y define la gramática formal (BNF) para el lenguaje.

---

## 📋 Tabla de Contenidos
1. [Diccionario de Comandos](#-diccionario-de-comandos)
2. [Gramática del Lenguaje](#-gramática-del-lenguaje)
3. [Tipos de Datos](#-tipos-de-datos)
4. [Operadores](#-operadores)
5. [Ejemplos de Código](#-ejemplos-de-código)
6. [Analizador Léxico (Lexer)](#-analizador-léxico-lexer)

---

## 🗣️ Diccionario de Comandos

Paisascript sustituye las palabras reservadas tradicionales por expresiones típicas:

| Palabra Reservada | Paisascript | Función |
| :--- | :--- | :--- |
| `var / let` | `pille_pues` | Declaración y asignación de variables. |
| `scanf / input` | `escuche_pues` | Lectura de datos por consola. |
| `printf / print` | `hable_pues` | Impresión de datos en pantalla. |
| `switch / match` | `pillemos` | Estructura de control de flujo por coincidencia. |
| `=>` | `pa_que_lleve` | Operador de flecha para casos en el match. |
| `true` | `sizas` | Valor booleano verdadero. |
| `false` | `naranjas` | Valor booleano falso. |
| `default / else` | `_` | Comodín para casos no especificados. |

---

## 📐 Gramática del Lenguaje (BNF)

El lenguaje sigue una estructura formal definida en el archivo `gramatica_BNF_Paisascript.txt`. Los puntos clave son:

- **Instrucciones**: Un programa es una lista de instrucciones que pueden ser asignaciones, lecturas, impresiones o estructuras de control.
- **Estructura de Control**: Se utiliza `pillemos <expresion> { <casos> }` para evaluar múltiples condiciones.
- **Expresiones**:
  - **Aritméticas**: Soporta suma, resta, multiplicación y división con precedencia estándar.
  - **Lógicas**: Usa `y_tambien` (AND), `o_que` (OR) y `nanai` (NOT).
  - **Cadenas**: Utiliza el operador `<>` para la concatenación de cadenas.

---

## 💎 Tipos de Datos

1. **NUM_ENTERO**: Secuencias de dígitos (ej. `123`, `45`).
2. **CADENA_LITERAL**: Texto encerrado en comillas dobles (ej. `"Hola parcero"`).
3. **IDENTIFICADOR**: Nombres de variables que deben empezar con minúscula o guion bajo (ej. `mi_variable`, `edad`).
4. **BOOLEANOS**: `sizas` o `naranjas`.

---

## ⚡ Operadores

### Aritméticos
- `+`, `-`, `*`, `/`

### Relacionales (Comparación)
- `igualito`: Equivalente a `==`
- `distinto`: Equivalente a `!=`
- `>`, `<`, `>=`, `<=`

### Lógicos
- `y_tambien`: AND lógico
- `o_que`: OR lógico
- `nanai`: NOT lógico

### Especiales
- `<>`: Concatenación de cadenas.
- `=`: Asignación.

---

## 📝 Ejemplos de Código

### Ejemplo 1: Operaciones Básicas y Entrada/Salida
```text
escuche_pues(edad)
pille_pues calculo = (edad * 2) + 5
pille_pues mensaje = "El resultado es: " <> calculo
hable_pues(mensaje)
```

### Ejemplo 2: Estructura de Control (Match)
```text
pillemos resultado {
    10 pa_que_lleve hable_pues("Sacaste diez, ¡qué elegancia!")
    "error" pa_que_lleve hable_pues("Algo salió mal, mijo")
    _ pa_que_lleve hable_pues("No sé qué pasó ahí")
}
```

---

## ⚙️ Analizador Léxico (Lexer)

El archivo `lexer_paisascript.py` utiliza expresiones regulares para identificar cada token del código fuente. 

### Cómo ejecutarlo:
1. Asegúrate de tener Python instalado.
2. Ejecuta el script:
   ```bash
   python lexer_paisascript.py
   ```

### Salida del Lexer:
El analizador generará una tabla con el **Lexema** (el texto encontrado) y su **Tipo de Token** correspondiente:

```text
Lexema                    | Tipo de token
--------------------------------------------------
escuche_pues              | KW_LECTURA
(                         | PAR_ABRE
edad                      | IDENTIFICADOR
)                         | PAR_CIERRA
...
```

Si el analizador encuentra un carácter no permitido (como `@` o `#`), reportará un **ERROR LÉXICO** indicando la posición exacta.
