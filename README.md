# Asistente de atención para RielSur

Proyecto del curso Procesamiento del Lenguaje Natural (UAI, 2026), opción 3 del enunciado: un chatbot en Python que atiende las consultas de los clientes de un servicio, identifica qué necesitan y qué datos entregan, y responde sin inventar información. Lo hice solo.

El servicio es RielSur, una empresa de trenes ficticia entre Santiago y Chillán. Todo lo que el asistente puede afirmar (estaciones, horarios, precios, políticas y cinco reservas de ejemplo) está en `data/base_conocimiento.json`. Solo uso modelos locales en Ollama: qwen3:4b y gemma3:4b.

- Informe completo: [`docs/informe.md`](docs/informe.md) (también en [PDF](docs/informe.pdf)).
- Presentación de 15 minutos: [`presentacion/presentacion.pptx`](presentacion/presentacion.pptx) (también en [PDF](presentacion/presentacion.pdf)).

## Etapas

1. **v0 con prompt engineering.** `scripts/generar_v0.py` le pide el chatbot a qwen3:4b con el prompt de `prompts/prompt_v0.md` y guarda la respuesta sin tocarla en `v0_cruda/qwen3_4b/`, con el prompt exacto, el razonamiento del modelo y los hashes.
2. **Ejecución de la v0 tal cual.** Corre, pero responde "No entiendo tu mensaje" a todo: manda `prompt` a `/api/chat`, que espera `messages`. El detalle está en `resultados/ejecucion_v0/reporte.md`.
3. **Explicación de la v0** parte por parte en [`docs/01_explicacion_v0.md`](docs/01_explicacion_v0.md), y una v0 corregida (`versiones/v0_corregida/`) que arregla solo sus cuatro errores para medir el diseño.
4. **Evaluación** con 62 conversaciones de prueba y 20 de validación; la metodología está en [`docs/02_evaluacion.md`](docs/02_evaluacion.md).
5. **Versiones simplificadas y comparación.** El asistente de `chatbot/` tiene piezas intercambiables: la intención se detecta con reglas, con TF-IDF + regresión logística o con un LLM; los datos se extraen con expresiones regulares o con un LLM; y la respuesta sale de plantillas o la redacta un LLM.
6. **Versión final:** qwen3:4b para la intención (salida JSON y el trámite en curso en el prompt), expresiones regulares para los datos y plantillas para responder. Si Ollama no responde, la intención la decide TF-IDF.

## Resultados

Conversaciones de prueba: 62 conversaciones, 153 turnos.

| Versión | Intención (accuracy) | Datos (F1) | Respuestas inventadas | Reconoce que no sabe (de 14) |
|---|---|---|---|---|
| v0 cruda | 0,065 | 0,000 | 0% | 0 |
| v0 corregida | 0,771 | 0,873 | 2% (revisión a mano) | 0 |
| Reglas + regex + plantillas | 0,922 | 1,000 | 0% | 13 |
| TF-IDF + regex + plantillas (liviana) | 0,876 | 1,000 | 0% | 10 |
| **qwen3:4b intención + regex + plantillas (final)** | 0,935 | 1,000 | 0% | 11 |
| qwen3:4b intención y datos | 0,935 | 0,867 | 1% | 11 |
| TF-IDF + gemma3:4b redacta | 0,876 | 1,000 | 45% (revisión a mano) | 14 |

En las 20 conversaciones de validación, escritas con el código ya cerrado, la versión final obtiene 0,915 en intención y 0,953 de F1 en datos, y la liviana 0,894 y 0,953; las reglas bajan de 0,922 a 0,766. La tabla completa está en `resultados/resumen.md`.

## Cómo usarlo

Necesita Python 3.10 o superior y Ollama.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3:4b
ollama pull gemma3:4b

# Conversar con la versión final (necesita Ollama con qwen3:4b; si no está, usa TF-IDF)
.venv/bin/python -m chatbot.asistente

# Evaluar una versión (v0, v0_corregida, reglas, tfidf, tfidf_sin_contexto,
# llm_intencion_regex, llm_nlu, llm_respuestas)
.venv/bin/python -m evaluacion.evaluar --sistema tfidf
.venv/bin/python -m evaluacion.evaluar --sistema tfidf --conversaciones data/conversaciones_validacion.json --salida resultados/validacion/tfidf

# Tabla y gráficos con todas las versiones
.venv/bin/python scripts/tabla_resultados.py
```

Todos los comandos se ejecutan desde la raíz del repositorio.

## Estructura

```
data/            base de conocimiento, conversaciones de prueba y validación, frases de entrenamiento
prompts/         prompt con el que se pidió la v0
v0_cruda/        la v0 tal como la entregó qwen3:4b
versiones/       v0 corregida (solo cuatro errores arreglados)
chatbot/         asistente por piezas: extracción, intención, contexto y respuestas
evaluacion/      evaluador, métricas y detector de respuestas inventadas
resultados/      predicciones y métricas de cada versión, revisión a mano y gráficos
scripts/         generación de la base, de la v0, de la tabla, del informe y de la presentación
docs/            explicación de la v0, metodología de evaluación e informe
presentacion/    presentación de 15 minutos
```
