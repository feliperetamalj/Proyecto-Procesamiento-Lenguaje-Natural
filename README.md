# Asistente de atención para RielSur

Proyecto del curso Procesamiento del Lenguaje Natural (UAI, 2026), opción 3 del enunciado: un chatbot en Python que atiende las consultas de los clientes de un servicio, identifica qué necesitan y qué datos entregan, y responde sin inventar información. Lo hice solo.

El servicio es RielSur, una empresa de trenes ficticia entre Santiago y Chillán, con paradas en Rancagua, San Fernando, Curicó, Talca, Linares y Parral. Todo lo que el asistente puede afirmar (estaciones, horarios, precios, políticas y cinco reservas de ejemplo) está en `data/base_conocimiento.json`. Solo uso modelos locales en Ollama: qwen3:4b y gemma3:4b.

- Informe completo: [`docs/informe.md`](docs/informe.md) (también en [PDF](docs/informe.pdf)).
- Presentación de 15 minutos: [`presentacion/presentacion.pptx`](presentacion/presentacion.pptx) (también en [PDF](presentacion/presentacion.pdf)).

## 1. Cómo correr el chatbot

### Requisitos

- Python 3.10 o superior. La v0 usa la sintaxis `dict | None`, que no existe en versiones anteriores. Lo probé con Python 3.13 y 3.14 en macOS.
- [Ollama](https://ollama.com) con el modelo qwen3:4b, que ocupa unos 2,5 GB. gemma3:4b (3,3 GB) solo hace falta para evaluar la versión donde un LLM redacta las respuestas.
- Todo lo desarrollé en un MacBook Air con chip M4 y 16 GB de RAM, sin GPU dedicada.

### Instalación

```
git clone https://github.com/feliperetamalj/Proyecto-Procesamiento-Lenguaje-Natural.git
cd Proyecto-Procesamiento-Lenguaje-Natural
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3:4b
ollama pull gemma3:4b      # opcional, solo para la versión llm_respuestas
```

Ollama tiene que estar abierto, ya sea la aplicación o `ollama serve` en otra terminal. Para comprobar que responde: `curl http://localhost:11434/api/version`.

### Conversar con el asistente

Desde la raíz del repositorio:

```
.venv/bin/python -m chatbot.asistente
```

Se abre una conversación por consola. Escriba sus mensajes después de `Usted:` y escriba `salir` para terminar.

Algunas cosas que conviene saber:

- Hay que usar `python -m` desde la raíz. Si ejecuta `chatbot/asistente.py` directamente, Python no encuentra el paquete `chatbot`.
- El primer mensaje tarda unos segundos más porque Ollama carga el modelo en memoria. Después, cada turno tarda cerca de 1,7 segundos en el MacBook Air.
- Si Ollama no está abierto o no tiene qwen3:4b, el asistente igual funciona: la intención la decide un clasificador TF-IDF (la versión liviana) y responde al instante, con algo menos de precisión.
- Las fechas relativas ("mañana", "el viernes") se calculan desde la fecha del computador.

Una conversación de ejemplo, hecha el martes 24 de noviembre de 2026:

```
Usted: Hola
RielSur: Hola, soy el asistente virtual de RielSur. Puedo ayudarle a comprar pasajes, ver horarios y precios, cambiar o devolver pasajes y resolver dudas de equipaje, mascotas o reclamos. ¿Qué necesita?
Usted: ¿Cuánto sale un pasaje de Santiago a Talca?
RielSur: El pasaje adulto de Santiago a Talca cuesta: clase estándar: $7.000; clase preferente: $11.200.
Usted: Quiero comprar 2 pasajes para el viernes
RielSur: El viernes 27 de noviembre los trenes de Santiago a Talca salen a las 07:30, 10:30, 14:00 y 18:30. ¿Cuál prefiere?
Usted: A las 9
RielSur: No hay un tren que salga de Santiago a las 09:00 el viernes 27 de noviembre. Ese día salen a las 07:30, 10:30, 14:00 y 18:30. ¿Cuál prefiere?
Usted: El de las 10:30, adultos, clase estándar
RielSur: Para terminar la compra necesito el RUT y el correo de quien compra.
Usted: Mi rut es 17.234.567-0 y mi correo camila.rojas@gmail.com
RielSur: Resumen de su compra: 2 pasajes adulto en clase estándar, de Santiago a Talca, el viernes 27 de noviembre a las 10:30 (llega a las 13:00). Valor por pasaje: $7.000. Total: $14.000. El enlace de pago llegará a camila.rojas@gmail.com y vence en 30 minutos.
Usted: ¿Tienen wifi?
RielSur: No tengo información sobre eso. Puedo ayudarle con pasajes, horarios, precios, cambios, devoluciones, equipaje, mascotas y reclamos. Para otras consultas puede llamar al +56 2 2000 0000 o escribir a atencion@rielsur.cl.
```

### Qué se le puede preguntar

Estos mensajes los probé con la versión final:

| Tema | Mensaje de ejemplo |
|---|---|
| Horarios | ¿A qué hora salen trenes de Santiago a Chillán el viernes? |
| Precios | ¿Cuánto sale un pasaje de Santiago a Talca? y después ¿Y cuánto cuesta en clase preferente? |
| Compra | Quiero comprar un pasaje de Santiago a Talca para el 5 de diciembre (y responder lo que pregunte) |
| Cambio | Necesito cambiar mi reserva RS-10234 para el 6 de diciembre (pide el RUT: 12.345.678-5) |
| Devolución | Quiero devolver el pasaje RS-20871, rut 9.876.543-3 |
| Mascotas | ¿Puedo llevar a mi perro en el tren? |
| Reclamo | Quiero hacer un reclamo, el tren llegó 40 minutos tarde |
| Fuera de tema | ¿Quién ganó el partido de ayer? |

El asistente recuerda lo que el cliente ya dijo y pide solo lo que falta. En una compra necesita origen, destino, fecha, hora, cantidad de pasajeros, tarifa, clase, RUT y correo, y el cliente los puede dar en cualquier orden y en varios mensajes.

Para probar cambios y devoluciones están estas reservas de ejemplo:

| Código | RUT | Viaje | Fecha y hora | Pasajes | Total |
|---|---|---|---|---|---|
| RS-10234 | 12.345.678-5 | Santiago a Talca | 4 de diciembre, 10:30 | 2 adulto, estándar | $14.000 |
| RS-20871 | 9.876.543-3 | Chillán a Santiago | 28 de noviembre, 09:00 | 1 adulto mayor, estándar | $6.180 |
| RS-31502 | 19.456.321-3 | Rancagua a Curicó | 26 de noviembre, 08:20 | 1 estudiante, estándar | $2.660 |
| RS-44120 | 16.783.092-7 | Santiago a Chillán | 12 de diciembre, 17:30 | 3 adulto, preferente | $49.500 |
| RS-58077 | 20.114.587-2 | Talca a Santiago | 25 de noviembre, 16:00 | 2 adulto, estándar | $14.000 |

El reembolso de una devolución depende de cuánto falte para el viaje según la fecha del computador: 90% con 24 horas o más, 50% entre 24 y 2 horas, y nada con menos de 2 horas o si el tren ya salió.

### Usar otra versión desde Python

La consola usa la versión final. Para conversar con otra configuración se puede crear el asistente a mano:

```python
from chatbot.asistente import Asistente

asistente = Asistente(intenciones="tfidf")   # versión liviana, no necesita Ollama
r = asistente.procesar_turno("¿Cuánto sale un pasaje de Santiago a Talca?")
print(r["intencion"], r["datos"])
print(r["respuesta"])
r = asistente.procesar_turno("¿Y en clase preferente?", r["estado"])   # el estado lleva la memoria
print(r["respuesta"])
```

Las opciones son `intenciones` ("llm", "tfidf" o "reglas"), `extraccion` ("regex" o "llm"), `respuestas` ("plantillas" o "llm") y `contexto` (True o False).

## 2. Qué hice, etapa por etapa

El enunciado pide cuatro etapas. Cada paso quedó en su propio commit, así que `git log --reverse --oneline` muestra el orden en que lo hice.

### Etapa 1: la v0, hecha por la IA solo con un prompt

1. Generé la base de conocimiento con `scripts/construir_base_conocimiento.py`. Los precios salen de una fórmula por kilómetro y los horarios de los minutos de viaje desde Santiago, así que son consistentes entre sí: 8 estaciones, horarios de días hábiles y de fin de semana en los dos sentidos, 28 tramos con precio estándar y preferente, cuatro tarifas, las políticas del servicio y 5 reservas de ejemplo.
2. Escribí un solo prompt, `prompts/prompt_v0.md`. Le pide a qwen3:4b un chatbot en un archivo que detecte una de 11 intenciones, extraiga 11 tipos de datos, responda solo con la base, recuerde los datos de turnos anteriores y tenga la función `procesar_turno` con la firma que uso para evaluar. Al final va la base completa.
3. `scripts/generar_v0.py` le envió ese prompt a qwen3:4b una sola vez, con razonamiento activado y espacio para 24.000 tokens. El modelo razonó 31.940 caracteres y escribió un archivo de 112 líneas en 6,5 minutos (9.166 tokens). No agregó la explicación que le pedí después del código.
4. La respuesta quedó sin tocar en `v0_cruda/qwen3_4b/`, junto con el prompt exacto, el razonamiento y los hashes SHA-256 en `metadata.json`. El commit `d855a42` contiene solo esos archivos.

### Ejecutar la v0 tal como salió

La ejecuté desde la raíz del repositorio. Corre sin errores, pero responde "No entiendo tu mensaje. Por favor, describe tu consulta más claramente." a todo. La causa está en la llamada a Ollama: manda el texto en un campo `prompt` al endpoint `/api/chat`, que espera una lista `messages`. Ollama devuelve un contenido vacío, `json.loads` falla y un `except` silencioso deja la intención en `fuera_de_alcance`. Lo reproduje con curl en `resultados/ejecucion_v0/diagnostico_ollama.txt`, y el reporte completo está en `resultados/ejecucion_v0/reporte.md`.

### Etapa 2: explicar el código y comparar versiones simplificadas

1. Recorrí la v0 parte por parte en [`docs/01_explicacion_v0.md`](docs/01_explicacion_v0.md). Tiene cuatro errores de programación: el campo `prompt`, la lectura del JSON, un estado que nunca guarda nada y una revisión de datos faltantes que mira el mensaje y no el estado. También tiene dos problemas de diseño: el prompt interno no recibe la fecha ni el trámite en curso, y las respuestas de horarios, precios y equipaje son textos de relleno como "[Listado de horarios en la base de conocimiento]". Además, cuando cree que la compra está completa dice "Tu pasaje será confirmado en 30 minutos", que no está en la base.
2. Hice `versiones/v0_corregida/chatbot.py`, una copia que arregla solo esos cuatro errores, marcados con `CORRECCIÓN`. Así medí el diseño que propuso el modelo y no sus errores: la intención sube a 0,771, pero el asistente sigue sin contestar lo que se le pregunta y tarda 96 segundos por turno porque qwen3:4b razona antes de cada respuesta.
3. Armé mi propio asistente en `chatbot/`, con cuatro piezas intercambiables: extracción de datos, detección de intención, contexto y respuesta. Para cada pieza comparé una versión con LLM contra una más simple, cambiando una sola pieza a la vez:

| Versión | Intención | Datos | Contexto | Respuesta |
|---|---|---|---|---|
| `reglas` | Palabras clave | Regex | Sí | Plantillas |
| `tfidf` (liviana) | TF-IDF + regresión logística | Regex | Sí | Plantillas |
| `tfidf_sin_contexto` | TF-IDF + regresión logística | Regex | No | Plantillas |
| `llm_intencion_regex` (final) | qwen3:4b | Regex | Sí | Plantillas |
| `llm_nlu` | qwen3:4b | qwen3:4b | Sí | Plantillas |
| `llm_respuestas` | TF-IDF + regresión logística | Regex | Sí | gemma3:4b redacta |

### La evaluación

El enunciado pide al menos 50 conversaciones de prueba. La metodología completa está en [`docs/02_evaluacion.md`](docs/02_evaluacion.md).

- Escribí 62 conversaciones de prueba (153 turnos) en `data/conversaciones_prueba.json`. Cada turno trae la intención correcta, los datos que entrega y, cuando corresponde, lo que la respuesta tiene que mencionar. Incluyen casos difíciles a propósito: un horario que no existe, una fecha a más de 30 días, ocho pasajes cuando el máximo es seis, una reserva inexistente y 14 preguntas que la base no responde.
- Las reglas las escribí mirando esas conversaciones, así que ahí rinden de más. Para medir sin ese sesgo escribí otras 20 conversaciones de validación (47 turnos) cuando el código ya estaba cerrado, las subí en un commit propio (`439d0d2`) antes de evaluar con ellas y no cambié nada después de ver los resultados.
- Mido la intención con accuracy y macro-F1, y los datos con precisión, recall y F1 campo por campo.
- Para las respuestas inventadas, un detector (`evaluacion/inventadas.py`) saca de cada respuesta los montos, horas, porcentajes, códigos, correos, páginas y teléfonos, y revisa que estén en la base, se puedan calcular con ella o los haya dicho el usuario. En las preguntas sin respuesta en la base revisa que el asistente reconozca que no sabe.
- El detector no entiende el sentido de la frase, así que revisé a mano las respuestas de la v0 corregida, de la versión final y de la versión donde redacta gemma3:4b. Esas revisiones están en `resultados/revision_manual/`.
- También mido cuántos de los datos esperados menciona la respuesta, porque un asistente que no dice nada tampoco inventa nada.

### La versión final

La versión final es la configuración por defecto de `chatbot/asistente.py`: qwen3:4b detecta la intención con salida JSON, sin razonamiento y con el trámite en curso en el prompt; las expresiones regulares extraen los datos, y las plantillas responden con cifras sacadas de la base. Es la mejor detectando la intención en prueba y en validación, la que más veces menciona lo que el cliente necesita saber y no inventa datos. Si Ollama no responde, la intención la decide TF-IDF.

### Etapas 3 y 4: repositorio y presentación

Este repositorio guarda todo el proceso: la v0 cruda, la corregida, el asistente, las conversaciones, las predicciones y métricas de cada versión, y las revisiones a mano. La presentación de 15 minutos está en `presentacion/`, con 14 diapositivas y notas para cada una.

## 3. Cómo funciona el asistente

```
mensaje del cliente
   |
   v
1. Datos (extraccion.py)       regex: estaciones, fechas, horas, pasajeros, tarifa, clase, RUT, correo, código
2. Intención (intenciones.py)  qwen3:4b en Ollama con salida JSON; si falla, TF-IDF
3. Contexto (asistente.py)     si el mensaje solo trae datos o confirma, sigue el trámite en curso
4. Estado                      suma los datos a los de turnos anteriores
5. Respuesta (respuestas.py)   plantillas que toman cada cifra de la base (base.py)
   |
   v
{"intencion", "datos", "respuesta", "estado"}
```

La idea es separar la comprensión de la respuesta. El LLM puede equivocarse al entender qué quiere el cliente, pero nunca escribe una cifra: cada precio, horario y política de la respuesta sale de `data/base_conocimiento.json` a través de `chatbot/base.py`.

- `chatbot/base.py` lee la base y tiene las funciones de normalización que comparten el asistente y el evaluador: RUT con dígito verificador, fechas, horas, tarifas y clases.
- `chatbot/extraccion.py` saca los datos con expresiones regulares. Entiende RUT con o sin puntos, fechas como "mañana", "el viernes" o "el 3 de diciembre", horas como "las 7 y media" o "las 6 de la tarde", y cantidades como "somos dos" o "uno no más".
- `chatbot/intenciones.py` tiene los tres clasificadores con la misma interfaz. Las reglas son palabras clave en orden. TF-IDF combina n-gramas de caracteres (2 a 5) y de palabras (1 y 2) con una regresión logística entrenada con las 220 frases de `data/frases_entrenamiento.json`, escritas aparte de las conversaciones de prueba; se entrena en menos de un segundo. El LLM recibe una descripción de cada intención, la fecha de hoy y el trámite en curso, y responde en JSON (`format: "json"`, `think: false`, temperatura 0).
- `chatbot/asistente.py` une las piezas. Su regla de contexto es la que más mejora la intención: si el mensaje solo trae datos ("15678901-1", "Estándar") o es una confirmación ("ok, dale"), sigue el trámite anterior, y si después de una consulta llega un RUT o un correo, pasa al trámite que estaba en curso o, si no había ninguno, a la compra.
- `chatbot/respuestas.py` tiene una plantilla por intención. La de compra revisa en orden si falta algo o algo está mal (una estación sin servicio, más de 6 pasajes, una fecha pasada o a más de 30 días, un horario que no existe, un RUT inválido) y pide lo siguiente que falta, hasta llegar al resumen con el total.

## 4. Resultados

Conversaciones de prueba (62 conversaciones, 153 turnos):

| Versión | Intención (accuracy) | Datos (F1) | Respuestas inventadas | Reconoce que no sabe (de 14) | Menciona lo esperado | Segundos por turno |
|---|---|---|---|---|---|---|
| v0 cruda | 0,065 | 0,000 | 0% | 0 | 0% | <0,01 |
| v0 corregida | 0,771 | 0,873 | 2% (revisión a mano) | 0 | 2% | 96 |
| Reglas + regex + plantillas | 0,922 | 1,000 | 0% | 13 | 92% | <0,01 |
| TF-IDF sin contexto | 0,634 | 1,000 | 0% | 10 | 67% | <0,01 |
| TF-IDF + regex + plantillas (liviana) | 0,876 | 1,000 | 0% | 10 | 88% | <0,01 |
| **qwen3:4b intención + regex + plantillas (final)** | 0,935 | 1,000 | 0% | 11 | 97% | 1,69 |
| qwen3:4b intención y datos | 0,935 | 0,867 | 1% | 11 | 73% | 4,90 |
| TF-IDF + gemma3:4b redacta | 0,876 | 1,000 | 45% (revisión a mano) | 14 | 35% | 8,28 |

Conversaciones de validación (20 conversaciones, 47 turnos, escritas con el código ya cerrado):

| Versión | Intención (prueba → validación) | Datos F1 (prueba → validación) |
|---|---|---|
| Reglas + regex + plantillas | 0,922 → 0,766 | 1,000 → 0,953 |
| TF-IDF + regex + plantillas (liviana) | 0,876 → 0,894 | 1,000 → 0,953 |
| **qwen3:4b intención + regex + plantillas (final)** | 0,935 → 0,915 | 1,000 → 0,953 |
| qwen3:4b intención y datos | 0,935 → 0,915 | 0,867 → 0,824 |

La tabla completa, con macro-F1 y todas las columnas, está en `resultados/resumen.md`. Los tiempos son del MacBook Air.

Lo que muestran las comparaciones:

- Recordar el trámite en curso es lo que más mejora la intención. Sin contexto, TF-IDF falla en todos los mensajes que solo traen datos; con la regla de contexto sube de 0,634 a 0,876.
- Las reglas a mano rinden bien en las conversaciones con que las escribí, pero en validación pierden 16 puntos. TF-IDF, entrenado con frases escritas aparte, se mantiene.
- El mismo qwen3:4b de la v0, con un prompt mejor (descripción de cada intención, trámite en curso y salida JSON sin razonamiento), es el mejor detector de intención que probé y baja de 96 a 1,69 segundos por turno.
- Para los datos ganan las expresiones regulares. Cuando qwen3:4b extrae los datos se equivoca sobre todo en fechas: convierte "el viernes" en el día de hoy o pone el año equivocado. También cambia dígitos del RUT.
- Las plantillas no pueden inventar una cifra. gemma3:4b redactando suena más natural y reconoce las 14 preguntas sin respuesta, pero en la revisión a mano 69 de sus 153 respuestas afirman algo falso: precios, horarios, políticas y hasta un código de reserva. El detector automático solo vio 20 de esas 69.

## 5. Cómo evaluar y reproducir las cifras

Todos los comandos se ejecutan desde la raíz del repositorio.

```
# Evaluar una versión con las conversaciones de prueba
.venv/bin/python -m evaluacion.evaluar --sistema tfidf

# Evaluar con las conversaciones de validación
.venv/bin/python -m evaluacion.evaluar --sistema tfidf \
    --conversaciones data/conversaciones_validacion.json --salida resultados/validacion/tfidf

# Recalcular las métricas sin volver a correr el sistema
.venv/bin/python -m evaluacion.evaluar --sistema tfidf --solo-metricas

# Tabla y gráficos con todas las versiones
.venv/bin/python scripts/tabla_resultados.py
```

Los sistemas disponibles son `v0`, `v0_corregida`, `reglas`, `tfidf`, `tfidf_sin_contexto`, `llm_intencion_regex`, `llm_nlu` y `llm_respuestas` (están en `evaluacion/sistemas.py`).

- Cada evaluación escribe en `resultados/<sistema>/` las predicciones turno a turno (`predicciones.jsonl`), todas las métricas con el detalle de cada error (`metricas.json`) y un resumen (`resumen.md`). Si ya hay resultados, los reemplaza.
- Las conversaciones tienen la fecha de hoy fija en el archivo (24 de noviembre de 2026), así que "mañana" o "el viernes" dan siempre la misma fecha y las cifras se pueden reproducir.
- Las versiones sin LLM terminan en segundos. Con LLM tardan varios minutos: unos 4 la final, 13 `llm_nlu` y 21 `llm_respuestas`. `v0_corregida` tarda unas cuatro horas.
- El evaluador guarda cada conversación apenas termina. Si se corta, se puede seguir con `--reanudar`.
- `scripts/exportar_informe.py` vuelve a generar el PDF del informe y `scripts/crear_presentacion.py` la presentación. Los dos usan Google Chrome sin interfaz para el PDF.
- `scripts/generar_v0.py --modelo qwen3:4b` es el script que pidió la v0. No sobrescribe la v0 que ya existe, y una generación nueva daría otro código.

## 6. Estructura del repositorio

```
data/            base de conocimiento, conversaciones de prueba y validación, frases de entrenamiento
prompts/         prompt con el que se pidió la v0
v0_cruda/        la v0 tal como la entregó qwen3:4b, con el prompt, el razonamiento y los hashes
versiones/       v0 corregida (solo cuatro errores arreglados)
chatbot/         asistente por piezas: base, extracción, intención, contexto y respuestas
evaluacion/      evaluador, métricas y detector de respuestas inventadas
resultados/      predicciones y métricas de cada versión, ejecución de la v0, revisión a mano y gráficos
scripts/         generación de la base, de la v0, de la tabla, del informe y de la presentación
docs/            explicación de la v0, metodología de evaluación e informe
presentacion/    presentación de 15 minutos
```

## 7. Limitaciones conocidas

- Las conversaciones de prueba son un guion fijo: el usuario no reacciona a lo que contesta el asistente. Sirven para comparar versiones, pero no reemplazan pruebas con personas.
- Las anotaciones las escribí yo solo, sin una segunda persona que revisara los criterios.
- El asistente no está conectado a un sistema de reservas. Cuando dice que registró un cambio o un reclamo, eso solo queda en el estado de la conversación.
- Cuando el LLM se equivoca de intención, la respuesta es verdadera pero no contesta la pregunta. Por ejemplo, "¿Tienen wifi a bordo?" y "¿Puedo pagar con Mach?" reciben la política de equipaje, y "¿Hay vagón comedor?" recibe una pregunta por las estaciones, aunque la base dice que hay coche cafetería.
- Después del resumen de una compra, "ok, confirmo" vuelve a mostrar el resumen en vez de cerrar la compra, como sí hace el cambio de pasaje.
- La extracción con reglas no cubre todo: "ayer", "es solo él", "quiero comprar 2 para el viernes" (sin la palabra "pasajes") o un nombre sin "me llamo". Tampoco conoce los festivos, así que un festivo en día hábil usa el horario de lunes a viernes.
- Como siguiente paso probaría un sistema híbrido, con TF-IDF primero y el LLM solo cuando la confianza sea baja, y un LLM que redacte sobre la respuesta de la plantilla con una verificación automática de que cada cifra coincida con la base.
