"""Registro de sistemas que se pueden evaluar.

Cada sistema es una función procesar_turno(mensaje, estado, fecha_hoy) que
devuelve un dict con intencion, datos, respuesta y estado. El adaptador de la
v0 no cambia nada del archivo original: solo lo importa y traduce su salida si
usa otros nombres de clave.
"""

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _cargar_modulo(ruta, nombre):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _primera(d, claves, defecto=None):
    for k in claves:
        if isinstance(d, dict) and d.get(k) is not None:
            return d[k]
    return defecto


def adaptar(resultado, estado_anterior):
    if not isinstance(resultado, dict):
        return {"intencion": None, "datos": {}, "respuesta": str(resultado), "estado": estado_anterior}
    datos = _primera(resultado, ["datos", "entidades", "slots", "data"], {})
    return {
        "intencion": _primera(resultado, ["intencion", "intención", "intent"]),
        "datos": datos if isinstance(datos, dict) else {},
        "respuesta": _primera(resultado, ["respuesta", "response", "texto"], ""),
        "estado": _primera(resultado, ["estado", "state"], estado_anterior),
    }


def sistema_v0():
    ruta = RAIZ / "v0_cruda" / "qwen3_4b" / "chatbot_v0.py"
    modulo = _cargar_modulo(ruta, "chatbot_v0")
    return modulo.procesar_turno


def sistema_asistente(config):
    from chatbot.asistente import Asistente
    return Asistente(**config).procesar_turno


# Configuraciones que se comparan en el informe. Cada una cambia una sola pieza
# respecto de la anterior, para que se vea qué aporta cada cambio.
CONFIGURACIONES = {
    "reglas": {"intenciones": "reglas", "extraccion": "regex", "respuestas": "plantillas"},
    "tfidf": {"intenciones": "tfidf", "extraccion": "regex", "respuestas": "plantillas"},
    "llm_nlu": {"intenciones": "llm", "extraccion": "llm", "respuestas": "plantillas"},
    "llm_respuestas": {"intenciones": "tfidf", "extraccion": "regex", "respuestas": "llm"},
    "v1": {"intenciones": "tfidf", "extraccion": "regex", "respuestas": "plantillas", "contexto": True},
}


def obtener(nombre):
    if nombre == "v0":
        return sistema_v0()
    if nombre in CONFIGURACIONES:
        return sistema_asistente(CONFIGURACIONES[nombre])
    raise SystemExit(f"Sistema desconocido: {nombre}")
