"""Tres formas de detectar la intención, con la misma interfaz:

    clasificador.predecir(mensaje) -> (intencion, confianza)

- Reglas: palabras clave escritas a mano. Sirve de línea base.
- TfidfLR: TF-IDF de caracteres y palabras con regresión logística, entrenado
  con data/frases_entrenamiento.json (220 frases, 20 por intención).
- LLM: le pide la intención a un modelo local de Ollama en formato JSON.
"""

import json
import os
import re

from chatbot.base import INTENCIONES, RAIZ, sin_tildes


def limpiar(texto):
    texto = sin_tildes(texto).lower()
    texto = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", " correo ", texto)
    texto = re.sub(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dk]\b", " rut ", texto)
    texto = re.sub(r"\brs-?\d+\b", " codigo ", texto)
    texto = re.sub(r"\d+", " 0 ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def frases_entrenamiento():
    datos = json.loads((RAIZ / "data" / "frases_entrenamiento.json").read_text(encoding="utf-8"))
    textos, etiquetas = [], []
    for intencion, frases in datos["frases"].items():
        textos += frases
        etiquetas += [intencion] * len(frases)
    return textos, etiquetas


class Reglas:
    """Gana la primera regla que calce, en este orden. Las más específicas van
    primero: "cambiar" y "devolver" antes que "pasaje", que aparece en casi todo."""

    REGLAS = [
        ("reclamo", r"reclam|queja|pesim|molest|mala atencion|me cobraron|perdieron|no funcionaba|exijo"),
        ("estado_tren", r"atrasad|retras|demora(do)?\b|detuv|detenid|paro\b|huelga|suspend|funcionando|a la hora\b"),
        ("devolver_pasaje", r"devol|devuelv|reembols|anula|cancel"),
        ("cambiar_pasaje", r"cambi|modific|reprogram|posterg|adelant"),
        ("equipaje_mascotas", r"malet|equipaje|bolso|mochila|perro|gat[oa]\b|mascota|bicicleta|transportin|kilos?\b"),
        ("consultar_precio", r"cuanto (cuesta|sale|vale|es|cobran|pago)|precio|valor|tarifa|descuento|paga"),
        ("consultar_horario", r"hora|horario|sale el|salen|llega|demora|dura|primer tren|ultimo|para en|pasa por"),
        ("comprar_pasaje", r"compr|pasaje|boleto|reserv|sacar|viajar|asiento"),
        ("despedida", r"chao|adios|gracias|hasta luego|nos vemos"),
        ("saludo", r"^(hola|buenas|buenos|wena|alo)\b"),
    ]

    def predecir(self, mensaje):
        texto = sin_tildes(mensaje).lower()
        for intencion, patron in self.REGLAS:
            if re.search(patron, texto):
                return intencion, 1.0
        return "fuera_de_alcance", 0.0


class TfidfLR:
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion, Pipeline

        caracteres = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=1)
        palabras = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)
        self.modelo = Pipeline([
            ("tfidf", FeatureUnion([("car", caracteres), ("pal", palabras)])),
            ("lr", LogisticRegression(C=10, max_iter=2000)),
        ])
        textos, etiquetas = frases_entrenamiento()
        self.modelo.fit([limpiar(t) for t in textos], etiquetas)

    def predecir(self, mensaje):
        proba = self.modelo.predict_proba([limpiar(mensaje)])[0]
        i = proba.argmax()
        return self.modelo.classes_[i], float(proba[i])


DESCRIPCIONES = {
    "saludo": "el usuario saluda o pregunta con quién habla",
    "despedida": "el usuario se despide o agradece al final",
    "comprar_pasaje": "quiere comprar o reservar pasajes",
    "consultar_horario": "pregunta horarios, duración del viaje o paradas",
    "consultar_precio": "pregunta precios, tarifas o descuentos",
    "cambiar_pasaje": "quiere cambiar fecha u hora de un pasaje ya comprado, o pregunta por cambios",
    "devolver_pasaje": "quiere devolver o anular un pasaje, o pregunta por reembolsos",
    "equipaje_mascotas": "pregunta por equipaje, maletas, bicicletas o mascotas",
    "estado_tren": "pregunta si un tren va atrasado, detenido o funcionando",
    "reclamo": "quiere reclamar o quejarse de algo",
    "fuera_de_alcance": "cualquier otra cosa",
}


class LLM:
    """Clasifica (y opcionalmente extrae datos) con un modelo local.

    Le paso la intención del trámite en curso para que pueda resolver los
    mensajes que solo traen datos, como "15678901-1"."""

    def __init__(self, modelo="qwen3:4b", url=None):
        self.modelo = modelo
        self.url = url or os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def prompt(self, mensaje, intencion_previa, fecha_hoy):
        lista = "\n".join(f"- {k}: {v}" for k, v in DESCRIPCIONES.items())
        return (
            "Eres el módulo de comprensión de un asistente de venta de pasajes de tren en Chile.\n"
            f"Hoy es {fecha_hoy}. Intención del trámite en curso: {intencion_previa or 'ninguna'}.\n"
            "Si el mensaje solo entrega datos que se pidieron, la intención es la del trámite en curso.\n\n"
            f"Intenciones posibles:\n{lista}\n\n"
            "Datos posibles: origen, destino, fecha (AAAA-MM-DD), hora (HH:MM), pasajeros (entero), "
            "tarifa (adulto, estudiante, adulto_mayor, nino), clase (estandar, preferente), "
            "rut (12345678-9), correo, codigo_reserva (RS-00000), nombre. "
            "Incluye solo los datos que aparecen en este mensaje.\n\n"
            f"Mensaje: \"{mensaje}\"\n\n"
            'Responde solo con JSON: {"intencion": "...", "datos": {...}}'
        )

    def analizar(self, mensaje, intencion_previa=None, fecha_hoy=None):
        import requests

        cuerpo = {
            "model": self.modelo,
            "messages": [{"role": "user", "content": self.prompt(mensaje, intencion_previa, fecha_hoy)}],
            "stream": False,
            "think": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        r = requests.post(f"{self.url}/api/chat", json=cuerpo, timeout=120)
        r.raise_for_status()
        try:
            salida = json.loads(r.json()["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return "fuera_de_alcance", {}
        intencion = salida.get("intencion") or salida.get("intención")
        if intencion not in INTENCIONES:
            intencion = "fuera_de_alcance"
        datos = salida.get("datos") if isinstance(salida.get("datos"), dict) else {}
        return intencion, datos

    def predecir(self, mensaje, intencion_previa=None, fecha_hoy=None):
        intencion, _ = self.analizar(mensaje, intencion_previa, fecha_hoy)
        return intencion, 1.0
