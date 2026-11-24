import json
import requests
import datetime
import sys

# Cargar la base de conocimiento
with open('data/base_conocimiento.json', 'r') as f:
    base_conocimiento = json.load(f)

def procesar_turno(mensaje: str, estado: dict | None = None, fecha_hoy: str | None = None) -> dict:
    """Procesa un mensaje del usuario."""
    if estado is None:
        estado = {}
    if fecha_hoy is None:
        today = datetime.date.today()
        fecha_hoy = today.strftime("%Y-%m-%d")
    
    # Prompt para Ollama
    prompt = f"""
    Eres un asistente de atención de RielSur. Tienes que detectar la intención del usuario y extraer los datos necesarios. 
    Los posibles intentos son: saludo, despedida, comprar_pasaje, consultar_horario, consultar_precio, cambiar_pasaje, devolver_pasaje, equipaje_mascotas, estado_tren, reclamo, fuera_de_alcance.
    Los datos que extraer son: origen, destino, fecha (AAAA-MM-DD), hora (HH:MM), pasajeros (entero), tarifa (adulto, estudiante, adulto_mayor, nino), clase (estandar, preferente), rut (formato 12345678-9), correo, codigo_reserva (formato RS-00000), nombre.
    Si el usuario solo entrega datos que el asistente le pidió, la intención es la del trámite en curso.
    Devuelve un JSON con 'intencion' y 'datos'.
    Mensaje del usuario: "{mensaje}"
    """
    
    # Enviar a Ollama
    url = "http://localhost:11434/api/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "qwen3:4b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        ollama_response = response.json()
        response_text = ollama_response.get("message", {}).get("content", "")
    except Exception as e:
        print(f"Error en Ollama: {e}")
        return {"intencion": "fuera_de_alcance", "datos": {}, "respuesta": "Error al procesar tu mensaje. Por favor, intenta nuevamente.", "estado": estado}
    
    # Parsear respuesta
    try:
        result = json.loads(response_text)
        intencion = result.get("intencion", "fuera_de_alcance")
        datos = result.get("datos", {})
    except Exception:
        intencion = "fuera_de_alcance"
        datos = {}
    
    # Actualizar estado
    estado_actualizado = estado.copy()
    for key, value in datos.items():
        if key in estado_actualizado:
            estado_actualizado[key] = value
    
    # Generar respuesta según intención
    respuesta = ""
    if intencion == "saludo":
        respuesta = "¡Hola! ¿En qué puedo ayudarte hoy?"
    elif intencion == "despedida":
        respuesta = "¡Hasta luego! Si necesitas más ayuda, contacta a RielSur en +56 2 2000 0000 o atencion@rielsur.cl."
    elif intencion == "comprar_pasaje":
        required_data = base_conocimiento["politicas"]["compra"]["datos_necesarios"]
        missing = [d for d in required_data if d not in datos]
        if missing:
            respuesta = f"Para comprar un pasaje necesito {', '.join(missing)}. ¿Podrías proporcionarlos?"
        else:
            respuesta = "¡Gracias por su compra! Tu pasaje será confirmado en 30 minutos. Recuerda revisar tu correo para el enlace de pago."
    elif intencion == "consultar_horario":
        respuesta = "El horario actual de RielSur es: [Listado de horarios en la base de conocimiento]."
    elif intencion == "consultar_precio":
        respuesta = "La tarifa por pasajero es: [Datos de tarifas en la base de conocimiento]."
    elif intencion == "cambiar_pasaje":
        respuesta = "Para cambiar un pasaje, necesito tu código de reserva, RUT y los datos del nuevo viaje."
    elif intencion == "devolver_pasaje":
        respuesta = "Para devolver un pasaje, necesito tu código de reserva y RUT."
    elif intencion == "equipaje_mascotas":
        respuesta = "El equipaje y mascotas están permitidos: [Información en base de conocimiento]."
    elif intencion == "estado_tren":
        respuesta = "El estado de los trenes se actualiza en www.rielsur.cl/estado y en el teléfono de atención (+56 2 2000 0000)."
    elif intencion == "reclamo":
        respuesta = "Para hacer un reclamo, necesito tu RUT, código de reserva y descripción del problema."
    elif intencion == "fuera_de_alcance":
        respuesta = "No entiendo tu mensaje. Por favor, describe tu consulta más claramente."
    
    return {
        "intencion": intencion,
        "datos": datos,
        "respuesta": respuesta,
        "estado": estado_actualizado
    }

if __name__ == "__main__":
    estado = {}
    print("¡Hola! Eres el asistente de RielSur. ¿En qué puedo ayudarte?")
    while True:
        try:
            mensaje = input("Tú: ").strip()
            if mensaje.lower() == "salir":
                print("¡Hasta luego! ¡Que tengas un buen viaje!")
                break
            result = procesar_turno(mensaje, estado)
            print(f"Asistente: {result['respuesta']}")
            estado = result["estado"]
        except KeyboardInterrupt:
            print("\n¡Hasta luego! ¡Que tengas un buen viaje!")
            sys.exit(0)
