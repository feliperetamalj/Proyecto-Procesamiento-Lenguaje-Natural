# La v0 explicada por partes

La v0 es el archivo `v0_cruda/qwen3_4b/chatbot_v0.py`, tal como lo escribió qwen3:4b con el prompt de `prompts/prompt_v0.md`. Tiene 112 líneas. Acá la recorro en orden, digo qué hace cada parte y qué problema tiene. Los números de línea son los del archivo original.

## 1. Carga de la base de conocimiento (líneas 1 a 8)

Importa `json`, `requests`, `datetime` y `sys`, y abre `data/base_conocimiento.json` al importar el módulo. La ruta es relativa, así que solo funciona si el programa se ejecuta desde la raíz del repo. Tampoco indica `encoding="utf-8"`; en macOS no falla porque esa es la codificación por defecto, pero en Windows los tildes de la base se leerían mal.

La base se carga entera, pero el resto del código casi no la usa: solo lee `politicas.compra.datos_necesarios` (línea 68).

## 2. Firma de `procesar_turno` (líneas 10 a 16)

Respeta la firma que pedí en el prompt. Usa `dict | None`, una sintaxis que exige Python 3.10 o superior; con el Python 3.9 que trae macOS el archivo ni siquiera se importa. Por eso todo el proyecto corre con Python 3.13 en un entorno virtual.

Calcula `fecha_hoy` si no llega, pero después nunca la usa. El prompt que arma en la línea 19 no incluye la fecha, así que el modelo no tiene cómo convertir "mañana" o "el viernes" en una fecha concreta, que era una de las cosas que pedía el enunciado.

## 3. El prompt interno (líneas 19 a 26)

Es la parte de procesamiento de lenguaje: le pide al mismo qwen3:4b que detecte la intención y extraiga los datos de un mensaje y que devuelva un JSON. Copia casi literal las listas de intenciones y datos de mi prompt. Es un enfoque *zero-shot*: no da ejemplos ni describe qué significa cada intención.

Tiene dos problemas de diseño:

- Incluye la regla "si el usuario solo entrega datos que el asistente le pidió, la intención es la del trámite en curso", pero no le pasa al modelo cuál es el trámite en curso. El modelo ve un mensaje como "15678901-1" sin ningún contexto y no tiene forma de cumplir esa regla.
- No pide un formato estricto. qwen3:4b razona antes de contestar y a veces envuelve el JSON en un bloque de código o escribe la clave con tilde (`"intención"`), y el código no lo contempla.

## 4. Llamada a Ollama (líneas 29 a 44)

Acá está el error que hace que la v0 no funcione. Manda el texto en el campo `prompt`, que es el formato de `/api/generate`, pero lo envía a `/api/chat`, que espera una lista `messages`. Ollama no reclama: carga el modelo y responde con un contenido vacío y `done_reason: "load"` (está reproducido en `resultados/ejecucion_v0/diagnostico_ollama.txt`).

Además, `requests.post` no tiene `timeout`. Si Ollama se queda pegado, el programa espera para siempre.

## 5. Lectura del JSON (líneas 47 a 53)

Hace `json.loads` sobre la respuesta y, si falla, deja la intención en `fuera_de_alcance` sin avisar. Con el contenido vacío de la sección anterior, falla siempre. Ese `except` silencioso es el que esconde el error: el programa no se cae, pero tampoco hace nada útil.

## 6. Actualización del estado (líneas 55 a 59)

La idea es buena: guardar los datos de cada turno para no pedirlos de nuevo. Pero solo actualiza las claves que ya existen en el estado. Como el estado parte vacío, nunca se guarda nada. Es un error de una línea (`if key in estado_actualizado`) que anula el requisito 4 del prompt.

## 7. Respuestas por intención (líneas 62 a 89)

Es un `if/elif` con una respuesta fija por intención. Las de despedida y estado del tren están bien y usan datos reales de la base (teléfono, correo y página de estado). El resto tiene problemas:

- En horarios, precios y equipaje deja textos de relleno como `[Listado de horarios en la base de conocimiento]`. El modelo describió lo que había que poner en vez de escribir el código que lo busca.
- En la compra, revisa los datos que faltan mirando solo el mensaje actual (`datos`) y no el estado acumulado (línea 69). Aunque el estado funcionara, la compra nunca se completaría.
- Cuando cree que la compra está completa, responde "¡Gracias por su compra! Tu pasaje será confirmado en 30 minutos". La base dice otra cosa: el enlace de pago llega al correo y vence en 30 minutos. Es una respuesta inventada, aunque mi detector no la marca porque no tiene montos ni horas.
- Mezcla "tú" y "usted" ("Gracias por su compra", "Tu pasaje").

## 8. Bucle de consola (líneas 98 a 112)

Cumple lo pedido: conversa hasta que el usuario escribe "salir" y pasa el estado de un turno al siguiente. El saludo inicial dice "¡Hola! Eres el asistente de RielSur", que le habla al usuario como si él fuera el asistente.

## Resumen

| Parte | Funciona | Problema principal |
|---|---|---|
| Carga de la base | Sí | Ruta relativa, casi no se usa |
| Firma | Sí, con Python 3.10+ | `fecha_hoy` no se usa |
| Prompt interno | No se llega a usar | Sin contexto ni ejemplos |
| Llamada a Ollama | No | `prompt` en vez de `messages` |
| Lectura del JSON | No | `except` silencioso |
| Estado | No | Solo actualiza claves existentes |
| Respuestas | En parte | Textos de relleno y una respuesta inventada |
| Consola | Sí | Saludo mal redactado |

Para separar los errores de programación del diseño, hice `versiones/v0_corregida/chatbot.py`: la misma v0 con cuatro correcciones mínimas, marcadas con `CORRECCIÓN` en el código (el campo `messages`, la lectura del JSON, la actualización del estado y la revisión de datos faltantes). El resto, incluido el prompt y las respuestas fijas, quedó igual. Sus resultados están en el informe (`docs/informe.md`).
