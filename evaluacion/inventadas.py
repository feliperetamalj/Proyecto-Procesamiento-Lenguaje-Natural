"""Detector de respuestas inventadas.

La idea es simple: saco de cada respuesta los datos que se pueden comprobar
(montos, horas, porcentajes, códigos de reserva, correos, páginas web y
teléfonos) y reviso que cada uno exista en la base de conocimiento, se pueda
calcular con ella o lo haya dicho el usuario. Lo que no cumple nada de eso
cuenta como inventado.

Para que una cifra correcta de otra ruta no pase como válida, los montos y las
horas se aceptan solo para las estaciones que aparecen en la conversación.

También reviso las preguntas que no tienen respuesta en la base: ahí lo
correcto es reconocer que no hay información.
"""

import re
from itertools import combinations

from chatbot.base import normalizar_hora, sin_tildes

RE_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
RE_FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
RE_HORA = re.compile(r"\b(\d{1,2}):(\d{2})\b")
RE_DINERO = [
    re.compile(r"\$\s*(\d{1,3}(?:[.,]\d{3})+|\d+)"),
    re.compile(r"\bclp\s*\$?\s*(\d{1,3}(?:[.,]\d{3})+|\d+)", re.I),
    re.compile(r"\b(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:pesos|clp)\b", re.I),
    re.compile(r"\b(\d{1,3}(?:\.\d{3})+)\b"),
]
RE_PORCENTAJE = re.compile(r"\b(\d{1,3})\s*(?:%|por\s*ciento)", re.I)
RE_CODIGO = re.compile(r"\bRS-?\d{3,6}\b", re.I)
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RE_WEB = re.compile(r"\b(?:https?://)?(?:www\.)?[a-z0-9-]+\.(?:cl|com|org|net)(?:/[\w/-]*)?", re.I)
RE_TELEFONO = re.compile(r"\+?\d{2}\s?\d\s?\d{4}\s?\d{4}|\b600\s?\d{3}\s?\d{4}\b|\b\d{3}\s\d{3}\s\d{3,4}\b")

PATRONES_ABSTENCION = [
    r"no (tengo|tenemos|cuento con|contamos con|dispongo de|manejo) (esa |esta |la |informacion|datos|acceso)",
    r"no (tengo|tenemos) informacion",
    r"no (tengo|tenemos) (esa|ese) (informacion|dato)",
    r"no puedo (confirmar|informar|verificar|responder|entregar|saber|ver)",
    r"no (esta|aparece|figura) en (mi|la|nuestra) (base|informacion)",
    r"(fuera de|no esta dentro de) (mi|nuestro) alcance",
    r"no (tenemos|hay|contamos con|ofrecemos) (servicio|trenes|tren|ruta|recorrido|venta)",
    r"solo (opera|cubre|une|recorre|va|atiende|vende|tenemos)",
    r"en tiempo real",
    r"no (se|sabria) (decir|si|cual)",
    r"no me es posible",
]


def _numero(texto):
    return int(re.sub(r"[.,]", "", texto))


def _limpiar(texto):
    """Quita RUT y fechas para que no se confundan con montos u horas."""
    texto = RE_RUT.sub(" ", texto)
    return RE_FECHA.sub(" ", texto)


def extraer_hechos(respuesta):
    texto = _limpiar(respuesta or "")
    hechos = []
    for regex in RE_DINERO:
        for m in regex.finditer(texto):
            hechos.append(("dinero", _numero(m.group(1)), m.group(0)))
    for m in RE_HORA.finditer(texto):
        # "2:30 horas" es una duración, no una hora de salida.
        if re.match(r"\s*(h\b|hrs|horas)", texto[m.end():]):
            continue
        hechos.append(("hora", normalizar_hora(m.group(0)), m.group(0)))
    for m in RE_PORCENTAJE.finditer(texto):
        hechos.append(("porcentaje", int(m.group(1)), m.group(0)))
    for m in RE_CODIGO.finditer(texto):
        codigo = m.group(0).upper()
        if "-" not in codigo:
            codigo = codigo[:2] + "-" + codigo[2:]
        hechos.append(("codigo", codigo, m.group(0)))
    correos = set()
    for m in RE_CORREO.finditer(texto):
        correos.add(m.group(0).lower())
        hechos.append(("correo", m.group(0).lower(), m.group(0)))
    for m in RE_WEB.finditer(texto):
        web = m.group(0).lower()
        if any(web in c for c in correos):
            continue
        web = re.sub(r"^https?://", "", web).rstrip("/")
        if not web.startswith("www."):
            web = "www." + web
        hechos.append(("web", web, m.group(0)))
    for m in RE_TELEFONO.finditer(texto):
        hechos.append(("telefono", re.sub(r"\D", "", m.group(0))[-8:], m.group(0)))
    # Un mismo monto puede calzar con dos patrones; me quedo con uno.
    vistos, unicos = set(), []
    for h in hechos:
        if (h[0], h[1]) not in vistos:
            vistos.add((h[0], h[1]))
            unicos.append(h)
    return unicos


def hechos_permitidos(conversacion, base):
    """Conjunto de valores verificables que una respuesta puede usar en esta conversación."""
    datos = base.datos
    estaciones, reservas = set(), []
    for turno in conversacion["turnos"]:
        for campo in ("origen", "destino"):
            nombre = base.estacion(turno["datos"].get(campo))
            if nombre:
                estaciones.add(nombre)
        r = base.reserva(turno["datos"].get("codigo_reserva"))
        if r:
            reservas.append(r)
            estaciones.update([r["origen"], r["destino"]])

    dinero = {0}
    cargos = [datos["politicas"]["cambio"]["cargo_por_pasaje"],
              datos["politicas"]["equipaje"]["maleta_adicional"]["precio"],
              datos["politicas"]["mascotas"]["precio_por_tramo"]]
    for c in cargos:
        dinero.update(c * n for n in range(1, 9))
    # Cualquier precio unitario de la tabla vale, aunque sea de otra ruta.
    for t in datos["tarifas"]["tramos"]:
        for clase in ("estandar", "preferente"):
            for desc in base.descuentos.values():
                dinero.add(int(round(t[clase] * (100 - desc) / 100)))
    # Totales por cantidad de pasajeros, solo para los tramos de esta conversación.
    for o, d in combinations(sorted(estaciones), 2):
        for clase in ("estandar", "preferente"):
            for tarifa in base.descuentos:
                unitario = base.precio_unitario(o, d, tarifa, clase)
                if unitario is None:
                    unitario = int(round(base.precio_base(o, d, clase) * (100 - base.descuentos[tarifa]) / 100))
                dinero.update(unitario * n for n in range(1, 9))
    for r in reservas:
        for tramo in datos["politicas"]["devolucion"]["tramos"]:
            dinero.add(int(round(r["total"] * tramo["reembolso_porcentaje"] / 100)))
        dinero.add(r["total"])
        dinero.add(r["total"] // r["pasajeros"])

    relevantes = estaciones or set(base.estaciones)
    horas = {"08:00", "22:00"}
    for sentido in datos["horarios"].values():
        for servicios in sentido.values():
            for s in servicios:
                horas.update(h for est, h in s.items() if est in relevantes)
    horas.update(r["hora"] for r in reservas)

    porcentajes = {0, 100} | set(base.descuentos.values())
    porcentajes |= {t["reembolso_porcentaje"] for t in datos["politicas"]["devolucion"]["tramos"]}

    codigos = set(base.reservas)
    correos = {datos["empresa"]["correo"]}
    webs = {datos["empresa"]["web"], "www.rielsur.cl/estado"}
    telefonos = {re.sub(r"\D", "", datos["empresa"]["telefono"])[-8:]}

    # Lo que dijo el usuario también se puede repetir.
    for turno in conversacion["turnos"]:
        for tipo, valor, _ in extraer_hechos(turno["usuario"]):
            {"dinero": dinero, "hora": horas, "porcentaje": porcentajes, "codigo": codigos,
             "correo": correos, "web": webs, "telefono": telefonos}[tipo].add(valor)
        for m in re.finditer(r"\b\d+\b", turno["usuario"]):
            dinero.add(int(m.group(0)))
        for campo in ("hora",):
            if turno["datos"].get(campo):
                horas.add(turno["datos"][campo])
        if turno["datos"].get("correo"):
            correos.add(turno["datos"]["correo"])
        if turno["datos"].get("codigo_reserva"):
            codigos.add(turno["datos"]["codigo_reserva"])

    return {"dinero": dinero, "hora": horas, "porcentaje": porcentajes, "codigo": codigos,
            "correo": correos, "web": webs, "telefono": telefonos}


def no_respaldados(respuesta, permitidos):
    return [(tipo, texto) for tipo, valor, texto in extraer_hechos(respuesta)
            if valor not in permitidos[tipo]]


PATRONES_EVASIVA = [r"no (te |le )?entiendo", r"no (te |le )?entendi", r"no comprendo", r"reformul",
                    r"mas claramente", r"(puedes|podrias|puede|podria) repetir"]


def reconoce_que_no_sabe(respuesta):
    texto = sin_tildes(respuesta or "").lower()
    return any(re.search(p, texto) for p in PATRONES_ABSTENCION)


PATRONES_AFIRMA = [r"^\W*si\b", r"\bsi, (hay|tenemos|tiene|cuenta|ofrecemos|puede)", r"\b(hay|tenemos|ofrecemos|contamos con|cuentan? con|dispone de|disponemos de|incluye)\b",
                   r"\b(esta|estan|va|viene) (atrasad|a la hora|funcionando|operando|normal)", r"\bno hay (retras|paro|atras)"]


def afirma_algo(respuesta):
    """Detecta si la respuesta asegura algo ("sí, hay wifi", "el tren va a la hora").

    Miro solo el comienzo: si la respuesta parte con una pregunta, el asistente
    está pidiendo datos y no contestando."""
    texto = sin_tildes(respuesta or "").lower().strip()
    oraciones = re.findall(r"[^.?!]+[.?!]?", texto)
    if not oraciones or oraciones[0].strip().endswith("?"):
        return False
    inicio = " ".join(oraciones[:2])
    return any(re.search(p, inicio) for p in PATRONES_AFIRMA)


def es_evasiva(respuesta):
    """Respuesta vacía o que solo pide repetir: no ayuda, pero tampoco inventa."""
    texto = sin_tildes(respuesta or "").lower().strip()
    return not texto or any(re.search(p, texto) for p in PATRONES_EVASIVA)
