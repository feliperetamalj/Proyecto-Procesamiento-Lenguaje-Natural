# Ejecución de la v0 sin cambios

- Fecha: 23 de noviembre de 2026, 23:10.
- Equipo: MacBook Air con Apple M4 y 16 GB de RAM, macOS 26.2.
- Python 3.13.14 con requests 2.34.2 (el resto del entorno está en `entorno.txt`).
- Generación: qwen3:4b en Ollama 0.40.17, con razonamiento activado. Produjo 9.166 tokens en 391 segundos y terminó sola (`done_reason: stop`). Los hashes de `respuesta_cruda.md` y de `chatbot_v0.py` coinciden con los de `metadata.json`.
- Revisión antes de ejecutar: el código solo lee `data/base_conocimiento.json` y llama a Ollama en localhost. No escribe archivos, no usa subprocess ni eval. Tampoco encontré instrucciones raras en la respuesta ni en el razonamiento.
- Comando: `.venv/bin/python v0_cruda/qwen3_4b/chatbot_v0.py`, desde la raíz del repo y con cinco mensajes de entrada (`consola.txt`).
- Resultado: corre sin errores, pero contesta "No entiendo tu mensaje. Por favor, describe tu consulta más claramente." a todos los mensajes.

## Por qué contesta siempre lo mismo

La v0 manda a `/api/chat` un campo `prompt`, que es el formato de `/api/generate`. El endpoint de chat espera `messages`. Sin mensajes, Ollama solo carga el modelo y devuelve un contenido vacío con `done_reason: "load"` (lo reproduje con curl en `diagnostico_ollama.txt`). El `json.loads("")` falla, el `except` lo ataja en silencio y la intención queda en `fuera_de_alcance`. De ahí sale la respuesta fija.

## Evaluación con las 62 conversaciones de prueba

La corrí con `python -m evaluacion.evaluar --sistema v0`. Los resultados completos están en `resultados/v0/`.

| Métrica | Valor |
|---|---|
| Turnos evaluados | 153 |
| Errores de ejecución | 0 |
| Intención: accuracy | 0,065 |
| Intención: macro-F1 | 0,011 |
| Datos: F1 | 0,000 |
| Respuestas con datos inventados | 0 |
| Respuestas evasivas | 153 de 153 |
| Reconoce cuando no sabe | 0 de 14 |

El 0,065 de accuracy son los 10 turnos cuya intención correcta era `fuera_de_alcance`, que es la que la v0 pone por defecto. Que no invente nada no es mérito: no responde nada.
