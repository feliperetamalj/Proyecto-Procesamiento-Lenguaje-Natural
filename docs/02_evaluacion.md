# Cómo evalúo el asistente

El enunciado pide medir la calidad con al menos 50 conversaciones de prueba, revisando tres cosas: las intenciones detectadas, los datos extraídos y las respuestas inventadas. Esta es la forma en que lo hice.

## Conversaciones de prueba

`data/conversaciones_prueba.json` tiene 62 conversaciones con 153 turnos de usuario. Las escribí a mano para cubrir los once tipos de intención, con frases chilenas ("wena", "pa Rancagua", "uno no más") y con casos difíciles a propósito: un horario que no existe, una fecha a más de 30 días, ocho pasajes cuando el máximo es seis, una reserva que no existe, un RUT sin reservas, preguntas sobre wifi o el clima, y un destino fuera de la ruta.

Cada turno trae:

- `intencion`: lo que el usuario necesita en ese mensaje.
- `datos`: los datos que entrega en ese mensaje, ya normalizados (RUT sin puntos, fecha AAAA-MM-DD, estación con su nombre oficial).
- `sin_informacion`: si la pregunta no tiene respuesta en la base. Hay 14 turnos así.
- `debe_mencionar`: lo que una buena respuesta tiene que decir, por ejemplo el total de la compra o la hora de salida. Lo calculé con la base, no a ojo.

Las conversaciones son un guion fijo: el usuario no reacciona a lo que contesta el asistente. Es la forma estándar de evaluar fuera de línea y permite comparar versiones con exactamente los mismos mensajes.

### Criterios de anotación

Los fijé antes de evaluar mis versiones y los apliqué igual en todas las conversaciones:

- Un mensaje que solo trae datos pedidos ("15678901-1") lleva la intención del trámite en curso.
- `fecha` solo cuando el usuario nombra un día concreto ("mañana", "el viernes", "el 3 de diciembre"). "Un domingo" o "el fin de semana" no cuentan.
- `pasajeros` solo cuando hay una cantidad: "2 adultos", "somos tres", "uno no más". En "quiero un pasaje", "un" es un artículo y no se anota.
- `hora` es la de salida que el usuario elige. "Antes de las 3 de la tarde" es una restricción y no se anota.
- Una ciudad que no está en la ruta ("Puerto Montt") igual se anota como destino, porque el usuario la entregó.

## Conversaciones de validación

Escribí las 62 conversaciones de prueba antes de programar el asistente, pero después las usé para revisar errores. Eso infla las cifras: las reglas y las expresiones regulares terminan calzando con esas frases en particular.

Para tener una medida honesta escribí otras 20 conversaciones (`data/conversaciones_validacion.json`, 47 turnos) cuando el código ya estaba cerrado. Las subí al repositorio en un commit propio antes de evaluar con ellas, y no cambié nada del asistente después de ver los resultados.

## Métricas

El evaluador está en `evaluacion/`. Corre cada sistema turno a turno, pasando el estado de la conversación de un turno al siguiente, y guarda todo en `resultados/<sistema>/predicciones.jsonl`.

**Intención.** Accuracy por turno y macro-F1 sobre las once intenciones. Uso macro-F1 porque las intenciones no están balanceadas (hay 46 turnos de compra y 5 de estado del tren) y la accuracy sola premia acertar en la clase grande.

**Datos extraídos.** Comparo campo por campo los datos de cada turno con los anotados, después de normalizar ambos con la misma función (`chatbot/base.py`). Un valor correcto es un acierto; un valor de más es un falso positivo; un valor que falta es un falso negativo, y un valor equivocado cuenta como las dos cosas. Con eso calculo precisión, recall y F1.

**Respuestas inventadas.** Es la métrica más difícil de automatizar. El detector (`evaluacion/inventadas.py`) hace dos revisiones:

1. Saca de la respuesta los datos que se pueden comprobar: montos, horas, porcentajes, códigos de reserva, correos, páginas web y teléfonos. Cada uno tiene que existir en la base, poder calcularse con ella (por ejemplo, precio por pasajeros con descuento) o haberlo dicho el usuario. Los montos y las horas se aceptan solo para las estaciones de esa conversación, para que una cifra real de otra ruta no pase como válida.
2. En las 14 preguntas sin respuesta en la base, revisa si el asistente lo reconoce ("no tengo información", "no tenemos servicio a..."). Si en vez de eso asegura algo ("sí, hay wifi"), la respuesta cuenta como inventada.

La tasa de respuestas inventadas es el porcentaje de respuestas con al menos un problema de los dos tipos.

**Otras dos medidas.** "Reconoce que no sabe" es la proporción de esas 14 preguntas donde el asistente admite que no tiene la información. "Menciona lo esperado" es la proporción de datos de `debe_mencionar` que aparecen en la respuesta; mide si el asistente contesta lo que se le preguntó, que es lo que la tasa de inventos no ve (un asistente que nunca dice nada no inventa nada).

## Límites del detector

- No entiende el sentido de la frase. Si una respuesta dice "su pasaje será confirmado en 30 minutos" cuando la base dice que el enlace de pago vence en 30 minutos, el detector no lo marca, porque "30 minutos" no es un monto ni una hora. Encontré ese caso en la v0 leyendo las respuestas.
- La detección de afirmaciones en preguntas sin información usa patrones ("sí", "hay", "tenemos"). Para las versiones que redactan con un LLM revisé a mano esas respuestas.
- Que una cifra exista en la base no garantiza que sea la correcta para esa pregunta. Por eso también mido si la respuesta menciona el dato esperado.
