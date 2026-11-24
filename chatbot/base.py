"""Acceso a la base de conocimiento de RielSur y normalización de datos.

Todo lo que el asistente afirma (precios, horarios, políticas, reservas) sale de
las funciones de este módulo. El evaluador también las usa para saber qué datos
son verdaderos.
"""

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_BASE = RAIZ / "data" / "base_conocimiento.json"

INTENCIONES = [
    "saludo", "despedida", "comprar_pasaje", "consultar_horario", "consultar_precio",
    "cambiar_pasaje", "devolver_pasaje", "equipaje_mascotas", "estado_tren", "reclamo",
    "fuera_de_alcance",
]
CAMPOS = [
    "origen", "destino", "fecha", "hora", "pasajeros", "tarifa", "clase", "rut",
    "correo", "codigo_reserva", "nombre",
]
TARIFAS = ["adulto", "estudiante", "adulto_mayor", "nino"]
CLASES = ["estandar", "preferente"]


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def cargar_base(ruta=RUTA_BASE):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


class Base:
    """Envoltorio de consulta sobre el JSON."""

    def __init__(self, datos=None):
        self.datos = datos or cargar_base()
        self.estaciones = [e["nombre"] for e in self.datos["estaciones"]]
        self._por_clave = {sin_tildes(n).lower(): n for n in self.estaciones}
        self._tarifas = {tuple(t["tramo"]): t for t in self.datos["tarifas"]["tramos"]}
        self.reservas = {r["codigo"]: r for r in self.datos["reservas"]}
        self.descuentos = {k: v["porcentaje"] for k, v in self.datos["tarifas"]["descuentos"].items()}

    # Estaciones -----------------------------------------------------------
    def estacion(self, texto):
        """Devuelve el nombre oficial de una estación o None."""
        if not texto:
            return None
        return self._por_clave.get(sin_tildes(str(texto)).lower().strip())

    def sentido(self, origen, destino):
        i, j = self.estaciones.index(origen), self.estaciones.index(destino)
        return "sur" if j > i else "norte"

    # Precios --------------------------------------------------------------
    def precio_base(self, origen, destino, clase="estandar"):
        tramo = self._tarifas.get((origen, destino)) or self._tarifas.get((destino, origen))
        return tramo[clase] if tramo else None

    def precio_unitario(self, origen, destino, tarifa="adulto", clase="estandar"):
        base = self.precio_base(origen, destino, clase)
        if base is None:
            return None
        if tarifa == "estudiante" and clase == "preferente":
            return None  # la base no permite ese descuento
        return int(round(base * (100 - self.descuentos.get(tarifa, 0)) / 100))

    # Horarios -------------------------------------------------------------
    @staticmethod
    def tipo_dia(fecha_iso):
        if not fecha_iso:
            return "lunes_a_viernes"
        dia = date.fromisoformat(fecha_iso).weekday()
        return "sabado_domingo_festivos" if dia >= 5 else "lunes_a_viernes"

    def servicios(self, origen, destino, fecha_iso=None, tipo=None):
        """Lista de (salida en origen, llegada a destino) para una fecha o un tipo de día."""
        sentido = self.sentido(origen, destino)
        tabla = self.datos["horarios"][sentido][tipo or self.tipo_dia(fecha_iso)]
        return [(s[origen], s[destino]) for s in tabla]

    def minutos_viaje(self, origen, destino):
        minutos = {e["nombre"]: e["minutos_desde_santiago"] for e in self.datos["estaciones"]}
        return abs(minutos[destino] - minutos[origen])

    # Reservas -------------------------------------------------------------
    def reserva(self, codigo):
        return self.reservas.get(codigo) if codigo else None


# Normalización de valores, compartida por el chatbot y el evaluador --------

def normalizar_rut(texto):
    if texto is None:
        return None
    limpio = re.sub(r"[^0-9kK]", "", str(texto)).upper()
    if len(limpio) < 2:
        return None
    return f"{limpio[:-1]}-{limpio[-1]}"


def rut_valido(rut):
    rut = normalizar_rut(rut)
    if not rut:
        return False
    numero, dv = rut.split("-")
    if not numero.isdigit():
        return False
    suma, factor = 0, 2
    for d in reversed(numero):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    esperado = {11: "0", 10: "K"}.get(11 - suma % 11, str(11 - suma % 11))
    return dv == esperado


def normalizar_hora(texto):
    if texto is None:
        return None
    m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?", str(texto))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def normalizar_fecha(texto):
    if texto is None:
        return None
    texto = str(texto).strip()
    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            pass
    return texto


def normalizar_valor(campo, valor, base=None):
    """Lleva un valor a la forma que usan las anotaciones de prueba."""
    if valor is None or valor == "" or valor == []:
        return None
    if campo in ("origen", "destino"):
        if base is not None and base.estacion(valor):
            return base.estacion(valor)
        return str(valor).strip().title()
    if campo == "fecha":
        return normalizar_fecha(valor)
    if campo == "hora":
        return normalizar_hora(valor)
    if campo == "pasajeros":
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None
    if campo in ("tarifa", "clase"):
        v = sin_tildes(str(valor)).lower().strip().replace(" ", "_")
        equivalencias = {"nino": "nino", "ninos": "nino", "adultos": "adulto",
                         "estudiantes": "estudiante", "adulto_mayor": "adulto_mayor",
                         "tercera_edad": "adulto_mayor", "estandar": "estandar",
                         "economica": "estandar", "preferente": "preferente"}
        v = equivalencias.get(v, v)
        # Un valor fuera de la lista (por ejemplo "tne" que devuelve el LLM) se descarta.
        return v if v in (TARIFAS if campo == "tarifa" else CLASES) else None
    if campo == "rut":
        return normalizar_rut(valor)
    if campo == "correo":
        return str(valor).strip().lower()
    if campo == "codigo_reserva":
        return str(valor).strip().upper()
    if campo == "nombre":
        return " ".join(str(valor).split()).title()
    return valor
