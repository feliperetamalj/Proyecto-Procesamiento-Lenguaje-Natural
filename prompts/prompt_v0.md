Eres un desarrollador experto en Python y en procesamiento de lenguaje natural.

Necesito un asistente de atención (chatbot) en Python para RielSur, una empresa de trenes ficticia que une Santiago y Chillán. El asistente conversa por consola, en español de Chile, con clientes que quieren comprar pasajes o hacer consultas.

En cada mensaje del usuario el asistente debe:

1. Detectar la intención del usuario. Tiene que ser una de estas: saludo, despedida, comprar_pasaje, consultar_horario, consultar_precio, cambiar_pasaje, devolver_pasaje, equipaje_mascotas, estado_tren, reclamo, fuera_de_alcance. Si el usuario solo entrega datos que el asistente le pidió, la intención es la del trámite en curso.
2. Extraer los datos que el usuario entrega en ese mensaje: origen, destino, fecha (AAAA-MM-DD), hora (HH:MM), pasajeros (entero), tarifa (adulto, estudiante, adulto_mayor, nino), clase (estandar, preferente), rut (formato 12345678-9), correo, codigo_reserva (formato RS-00000) y nombre. Las fechas relativas como "mañana" o "el viernes" se calculan a partir de la fecha de hoy.
3. Responder usando solo la información de la base de conocimiento. Si algo no está en la base, debe decir que no tiene esa información y dar el teléfono o el correo de contacto. Nunca debe inventar precios, horarios, políticas ni datos de reservas.
4. Recordar los datos de los turnos anteriores y pedir los que falten para completar una compra, un cambio o una devolución.

Restricciones:

- Solo puedes usar modelos locales. Usa Ollama en http://localhost:11434 con el modelo qwen3:4b (endpoint /api/chat). No uses APIs externas.
- Todo en un solo archivo, chatbot_v0.py, usando la biblioteca estándar de Python y requests.
- La base de conocimiento está en data/base_conocimiento.json. Su contenido va al final de este mensaje.
- La fecha de hoy llega como parámetro; si no llega, usa la fecha del sistema.
- El archivo debe tener esta función, que voy a usar para evaluar el chatbot con conversaciones de prueba:

```python
def procesar_turno(mensaje: str, estado: dict | None = None, fecha_hoy: str | None = None) -> dict:
    """Procesa un mensaje del usuario.

    Devuelve {"intencion": str, "datos": dict, "respuesta": str, "estado": dict}.
    "datos" tiene solo los datos extraídos de este mensaje.
    "estado" se vuelve a pasar en el turno siguiente de la misma conversación.
    """
```

- Si el archivo se ejecuta directamente (python chatbot_v0.py), debe abrir una conversación por consola que termine cuando el usuario escriba "salir".

Entrega el código completo en un solo bloque ```python``` y, después del código, una explicación breve de cómo funciona.

Base de conocimiento (data/base_conocimiento.json):

```json
{{BASE_CONOCIMIENTO}}
```
