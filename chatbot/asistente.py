"""Asistente de atención de RielSur.

Cada turno pasa por cuatro pasos:
    1. extraer los datos del mensaje (regex o LLM);
    2. detectar la intención (reglas, TF-IDF o LLM);
    3. resolver la intención con el contexto: si el mensaje solo trae datos,
       sigue el trámite en curso;
    4. responder (plantillas con datos de la base, o un LLM que redacta).

Las piezas se eligen al crear el asistente, así puedo comparar versiones
cambiando una sola a la vez. La configuración por defecto es la versión final:
qwen3:4b para la intención, regex para los datos, contexto y plantillas. Si
Ollama no responde, la intención la decide TF-IDF.

Uso por consola:
    python -m chatbot.asistente
"""

import copy
import json
import re
from datetime import date

from chatbot.base import Base, CAMPOS, normalizar_valor, sin_tildes
from chatbot.extraccion import Extractor
from chatbot.intenciones import LLM, Reglas, TfidfLR
from chatbot.respuestas import Plantillas

UMBRAL_CONFIANZA = 0.5
# Trámites que piden datos en varios turnos.
TRANSACCIONES = {"comprar_pasaje", "cambiar_pasaje", "devolver_pasaje", "reclamo"}
TRAMITES = TRANSACCIONES | {"consultar_horario", "consultar_precio"}
# Datos que solo se piden para una transacción, nunca para una consulta.
DATOS_TRANSACCION = {"rut", "correo", "codigo_reserva"}
CONFIRMACION = re.compile(r"^(ok|okey|ya|si|dale|listo|bueno|confirmo|de acuerdo|perfecto)([\s,.!]+(dale|ok|ya|si|confirmo))*[\s.!]*$")
# Palabras que no cambian el sentido de un mensaje que solo trae datos.
RELLENO = set("""
y e o a al de del el la los las un una uno en para por con mi mis su es son somos soy me se le lo
rut correo mail email codigo reserva clase tarifa pasaje pasajes pasajero pasajeros nombre llamo llama ella el
no mas nomas solo ya ok entonces porfa favor si que ese esa dia tren de las desde hasta pa sale
""".split())


class Asistente:
    def __init__(self, intenciones="llm", extraccion="regex", respuestas="plantillas", contexto=True,
                 modelo_llm="qwen3:4b", modelo_respuestas="gemma3:4b"):
        self.base = Base()
        self.extractor = Extractor(self.base)
        self.plantillas = Plantillas(self.base)
        self.modo_intenciones, self.modo_extraccion = intenciones, extraccion
        self.contexto = contexto
        self.llm = LLM(modelo_llm) if "llm" in (intenciones, extraccion) else None
        # Con el LLM, TF-IDF queda de respaldo por si Ollama no está disponible.
        self.clasificador = {"reglas": Reglas, "tfidf": TfidfLR, "llm": TfidfLR}[intenciones]()
        self.redactor = RedactorLLM(self.base, modelo_respuestas) if respuestas == "llm" else None

    # ------------------------------------------------------------------
    def procesar_turno(self, mensaje, estado=None, fecha_hoy=None):
        estado = copy.deepcopy(estado) if estado else {"intencion": None, "datos": {}, "historial": []}
        fecha_hoy = fecha_hoy or date.today().isoformat()
        previa = estado.get("intencion")

        intencion_llm, datos_llm = None, None
        if self.llm:
            try:
                intencion_llm, datos_llm = self.llm.analizar(mensaje, previa if self.contexto else None, fecha_hoy)
            except Exception:  # Ollama apagado o sin el modelo: seguimos sin LLM
                intencion_llm, datos_llm = None, None
        if self.modo_extraccion == "llm" and datos_llm is not None:
            datos = {k: normalizar_valor(k, v, self.base) for k, v in datos_llm.items() if k in CAMPOS}
            datos = {k: v for k, v in datos.items() if v is not None}
        else:
            datos = self.extractor.extraer(mensaje, fecha_hoy)

        if self.modo_intenciones == "llm" and intencion_llm:
            intencion, confianza = intencion_llm, 1.0
        else:
            intencion, confianza = self.clasificador.predecir(mensaje)
        if self.contexto:
            intencion = self.resolver_contexto(mensaje, intencion, confianza, datos, previa, estado.get("tramite"))
        if intencion in TRANSACCIONES:
            estado["tramite"] = intencion

        estado["datos"].update(datos)
        estado["datos_turno"] = datos
        estado["intencion"] = intencion
        if self.redactor:
            respuesta = self.redactor.redactar(mensaje, intencion, estado, fecha_hoy)
        else:
            respuesta = self.plantillas.responder(intencion, mensaje, estado, fecha_hoy)
        estado["historial"] = (estado.get("historial", []) + [["usuario", mensaje], ["asistente", respuesta]])[-8:]
        return {"intencion": intencion, "datos": datos, "respuesta": respuesta, "estado": estado}

    def resolver_contexto(self, mensaje, intencion, confianza, datos, previa, tramite):
        """Si el mensaje solo entrega datos o confirma algo, sigue el trámite anterior."""
        if previa not in TRAMITES:
            return intencion
        texto = sin_tildes(mensaje).lower().strip()
        if CONFIRMACION.match(texto):
            return previa
        if not datos:
            return intencion
        seguir = previa
        # Un RUT, un correo o un código después de una consulta significan que el
        # cliente pasó a una transacción: la que estaba en curso o una compra.
        if previa not in TRANSACCIONES and set(datos) & DATOS_TRANSACCION:
            seguir = tramite or "comprar_pasaje"
        if intencion in ("saludo", "despedida", "fuera_de_alcance"):
            return seguir
        # Trae datos y el clasificador duda: lo más probable es que siga el mismo trámite.
        if confianza < UMBRAL_CONFIANZA:
            return seguir
        return seguir if self._solo_datos(texto, datos) else intencion

    def _solo_datos(self, texto, datos):
        """True si, al quitar los datos y las palabras de relleno, casi no queda nada."""
        for v in datos.values():
            for parte in re.split(r"[\s-]+", sin_tildes(str(v)).lower()):
                texto = texto.replace(parte, " ")
        texto = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+|\d+[.:\-/]?\d*|[^\w\s]", " ", texto)
        palabras = [p for p in texto.split() if p not in RELLENO and len(p) > 2]
        return len(palabras) <= 1


class RedactorLLM:
    """Redacta la respuesta con un LLM local que recibe la base completa.

    Es la alternativa a las plantillas: la respuesta suena más natural, pero el
    modelo puede inventar. Sirve para medir cuánto."""

    def __init__(self, base, modelo="gemma3:4b", url="http://localhost:11434"):
        self.modelo, self.url = modelo, url
        compacta = json.dumps(base.datos, ensure_ascii=False, separators=(",", ":"))
        self.sistema = (
            "Eres el asistente de atención al cliente de RielSur, una empresa de trenes entre Santiago y Chillán. "
            "Respondes en español de Chile, con trato de usted, en dos o tres oraciones. "
            "Usa solo la información de esta base de conocimiento. Si la respuesta no está en la base, di que no tienes "
            "esa información y da el teléfono o el correo de contacto. No inventes precios, horarios, políticas ni reservas.\n\n"
            f"Base de conocimiento (JSON):\n{compacta}"
        )

    def redactar(self, mensaje, intencion, estado, fecha_hoy):
        import requests

        datos = {k: v for k, v in estado["datos"].items()}
        contexto = (f"Hoy es {fecha_hoy}. Intención detectada: {intencion}. "
                    f"Datos que entregó el cliente hasta ahora: {json.dumps(datos, ensure_ascii=False)}.")
        mensajes = [{"role": "system", "content": self.sistema}]
        for rol, texto in estado.get("historial", [])[-6:]:
            mensajes.append({"role": "user" if rol == "usuario" else "assistant", "content": texto})
        mensajes.append({"role": "user", "content": f"{contexto}\n\nMensaje del cliente: {mensaje}"})
        cuerpo = {"model": self.modelo, "messages": mensajes, "stream": False,
                  "options": {"temperature": 0, "num_ctx": 8192}}
        r = requests.post(f"{self.url}/api/chat", json=cuerpo, timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


def main():
    asistente = Asistente()
    estado = None
    print("Asistente de RielSur. Escriba 'salir' para terminar.")
    while True:
        try:
            mensaje = input("Usted: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if mensaje.lower() == "salir":
            break
        r = asistente.procesar_turno(mensaje, estado)
        estado = r["estado"]
        print(f"RielSur: {r['respuesta']}")


if __name__ == "__main__":
    main()
