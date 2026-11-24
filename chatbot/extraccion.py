"""Extracción de datos con expresiones regulares y una lista de estaciones.

No usa modelos: cada campo tiene su patrón. Es la parte más fácil de explicar y
de corregir, porque cuando falla se ve exactamente qué regla no calzó.
"""

import re
from datetime import date, timedelta

from chatbot.base import normalizar_rut, sin_tildes

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
NUMEROS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
           "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}
NUM = r"(\d{1,2}|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
PERSONAS = r"(pasajes?|boletos?|asientos?|personas?|pasajeros?|adultos?|estudiantes?|ninos?)"

# Si la palabra anterior a "de <estación>" es una de estas, la estación no es el origen.
NO_ORIGEN = {"estacion", "boleteria", "restaurante", "clima", "tiempo", "hotel", "ciudad"}

RE_RUT = re.compile(r"\b(\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK])\b")
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RE_CODIGO = re.compile(r"\bRS-?(\d{5})\b", re.I)
RE_CIUDAD = re.compile(r"\b(?:a|hasta|hacia)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)")
RE_NOMBRE = re.compile(r"(?i:me llamo|mi nombre es|se llama|soy)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})")


def _numero(palabra):
    return int(palabra) if palabra.isdigit() else NUMEROS.get(palabra)


def _palabra_anterior(texto, inicio):
    previas = texto[:inicio].split()
    return previas[-1] if previas else ""


class Extractor:
    def __init__(self, base):
        self.base = base
        nombres = sorted(base.estaciones, key=len, reverse=True)  # "San Fernando" antes que otras
        self.est = "(" + "|".join(sin_tildes(n).lower() for n in nombres) + ")"

    def extraer(self, mensaje, fecha_hoy):
        texto = sin_tildes(mensaje).lower()
        datos = self._ruta(texto, mensaje)
        campos = {
            "fecha": self._fecha(texto, date.fromisoformat(fecha_hoy)),
            "hora": self._hora(texto),
            "pasajeros": self._pasajeros(texto),
            "tarifa": self._tarifa(texto),
            "clase": self._clase(texto),
        }
        datos.update({k: v for k, v in campos.items() if v})
        m = RE_CORREO.search(mensaje)
        if m:
            datos["correo"] = m.group(0).lower()
        m = RE_RUT.search(RE_CORREO.sub(" ", mensaje))
        if m:
            datos["rut"] = normalizar_rut(m.group(1))
        m = RE_CODIGO.search(mensaje)
        if m:
            datos["codigo_reserva"] = f"RS-{m.group(1)}"
        m = RE_NOMBRE.search(mensaje)
        if m:
            datos["nombre"] = m.group(1)
        return datos

    # Origen y destino ---------------------------------------------------
    def _ruta(self, texto, original):
        est, datos = self.est, {}
        m = re.search(rf"\b(?:de|desde)\s+{est}\s+(?:a|al|hasta|hacia|para|pa)\s+{est}\b", texto)
        if m:
            return {"origen": self.base.estacion(m.group(1)), "destino": self.base.estacion(m.group(2))}

        m = re.search(rf"\b(?:desde|saliendo de|sale de|parte de)\s+{est}\b", texto)
        if not m:
            for c in re.finditer(rf"\bde\s+{est}\b", texto):
                if _palabra_anterior(texto, c.start()) not in NO_ORIGEN:
                    m = c
                    break
        if m:
            datos["origen"] = self.base.estacion(m.group(1))

        m = re.search(rf"\b(?:a|al|hasta|hacia|para|pa)\s+{est}\b", texto)
        if m:
            datos["destino"] = self.base.estacion(m.group(1))
        else:
            # Ciudades fuera de la ruta ("a Puerto Montt"): se guardan igual para
            # poder decirle al cliente que ese destino no existe.
            m = RE_CIUDAD.search(original)
            if m and sin_tildes(m.group(1)).lower() not in DIAS:
                datos["destino"] = m.group(1)
        return datos

    # Fecha ---------------------------------------------------------------
    def _fecha(self, texto, hoy):
        """Junta todas las fechas del mensaje y prefiere la que va después de "para"
        o "al" ("cambiarlo de mañana para el jueves" -> jueves)."""
        candidatos = []

        for m in re.finditer(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+del?\s+(\d{4}))?", texto):
            dia, mes = int(m.group(1)), MESES.index(m.group(2)) + 1
            anio = int(m.group(3)) if m.group(3) else hoy.year + (mes < hoy.month)
            candidatos.append((m.start(), self._fecha_valida(anio, mes, dia)))
        for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", texto):
            dia, mes = int(m.group(1)), int(m.group(2))
            anio = int(m.group(3)) if m.group(3) else hoy.year + (mes < hoy.month)
            candidatos.append((m.start(), self._fecha_valida(anio + (2000 if anio < 100 else 0), mes, dia)))
        for m in re.finditer(r"\bpasado manana\b", texto):
            candidatos.append((m.start(), (hoy + timedelta(days=2)).isoformat()))
        for m in re.finditer(r"\bmanana\b", texto):
            anterior = _palabra_anterior(texto, m.start())
            if anterior not in ("la", "pasado"):  # "en la mañana" es la parte del día
                candidatos.append((m.start(), (hoy + timedelta(days=1)).isoformat()))
        for m in re.finditer(r"\bhoy\b", texto):
            candidatos.append((m.start(), hoy.isoformat()))
        # "el viernes" cuenta, pero no "el sábado 5 de diciembre": ahí manda la fecha explícita.
        for m in re.finditer(r"\b(?:el|del|este|al)\s+(?:proximo\s+)?(" + "|".join(DIAS) + r")\b(?!\s+\d)", texto):
            delta = (DIAS.index(m.group(1)) - hoy.weekday()) % 7 or 7
            candidatos.append((m.start(), (hoy + timedelta(days=delta)).isoformat()))

        candidatos = sorted(c for c in candidatos if c[1])
        if not candidatos:
            return None
        for inicio, fecha in candidatos:
            if _palabra_anterior(texto, inicio) in ("para", "al"):
                return fecha
        return candidatos[0][1]

    @staticmethod
    def _fecha_valida(anio, mes, dia):
        try:
            return date(anio, mes, dia).isoformat()
        except ValueError:
            return None

    # Hora ----------------------------------------------------------------
    def _hora(self, texto):
        """Hora de salida. Ignora las que van después de "antes de" o "después de",
        porque esas son restricciones y no un tren elegido."""
        patron = (r"\b(?:las\s+)?(\d{1,2}):(\d{2})\b"
                  r"|\blas\s+(\d{1,2})(\s+y\s+media|\s+y\s+cuarto)?(?:\s+de\s+la\s+(manana|tarde|noche))?")
        for m in re.finditer(patron, texto):
            previo = texto[:m.start()][-16:]
            if re.search(r"(antes|despues) de (las )?$", previo):
                continue
            if m.group(1):
                h, mi = int(m.group(1)), int(m.group(2))
            else:
                h = int(m.group(3))
                mi = (30 if "media" in m.group(4) else 15) if m.group(4) else 0
                if m.group(5) in ("tarde", "noche") and h < 12:
                    h += 12
            if h <= 23 and mi <= 59:
                return f"{h:02d}:{mi:02d}"
        return None

    # Pasajeros, tarifa y clase --------------------------------------------
    def _pasajeros(self, texto):
        for m in re.finditer(rf"\b{NUM}\s+(?:\w+\s+)?{PERSONAS}\b", texto):
            if m.group(1) in ("un", "una") and m.group(2).startswith(("pasaje", "boleto", "asiento")):
                continue  # "un pasaje" es un artículo, no una cantidad
            return _numero(m.group(1))
        m = re.search(rf"\b(?:somos|son)\s+{NUM}\b", texto)
        if m:
            return _numero(m.group(1))
        if re.search(r"(?:^|\b(?:compra(?:me|r)?|quiero|necesito|dame|saca(?:me|r)?)\s+)(uno|una)\b", texto.strip()):
            return 1
        return None

    def _tarifa(self, texto):
        if re.search(r"\b(estudiantes?|tne|universitari[oa]s?)\b", texto):
            return "estudiante"
        if re.search(r"\b(adultos? mayor(es)?|tercera edad|jubilad[oa]s?)\b", texto):
            return "adulto_mayor"
        m = re.search(r"\b(\d{1,3})\s+anos\b", texto)
        if m:
            edad = int(m.group(1))
            if edad >= 60:
                return "adulto_mayor"
            if 3 <= edad <= 11:
                return "nino"
        if re.search(r"\bninos?\b", texto):
            return "nino"
        if re.search(r"\badultos?\b", texto):
            return "adulto"
        return None

    def _clase(self, texto):
        if re.search(r"\bpreferente\b", texto):
            return "preferente"
        if re.search(r"\b(estandar|economica)\b", texto):
            return "estandar"
        return None
