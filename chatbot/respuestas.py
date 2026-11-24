"""Respuestas con plantillas. Cada cifra sale de la base de conocimiento a través
de chatbot.base, así que el asistente no puede decir un precio u horario que no
exista. Cuando falta información, lo dice y da el contacto.
"""

import re
from datetime import date, timedelta

from chatbot.base import rut_valido, sin_tildes

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
NOMBRE_TARIFA = {"adulto": "adulto", "estudiante": "estudiante", "adulto_mayor": "adulto mayor", "nino": "niño"}
NOMBRE_CLASE = {"estandar": "estándar", "preferente": "preferente"}


def pesos(n):
    return "$" + f"{n:,}".replace(",", ".")


def fecha_larga(iso):
    d = date.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def enumerar(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def minutos_a_texto(m):
    h, mi = divmod(m, 60)
    if h and mi:
        return f"{h} horas y {mi} minutos" if h > 1 else f"1 hora y {mi} minutos"
    return f"{h} horas" if h else f"{mi} minutos"


class Plantillas:
    def __init__(self, base):
        self.base = base
        d = base.datos
        self.empresa = d["empresa"]
        self.politicas = d["politicas"]
        self.contacto = f"llamar al {self.empresa['telefono']} o escribir a {self.empresa['correo']}"
        nombres = sorted(base.estaciones, key=len, reverse=True)
        self.re_est = "(" + "|".join(sin_tildes(n).lower() for n in nombres) + ")"

    # ------------------------------------------------------------------
    def responder(self, intencion, mensaje, estado, fecha_hoy):
        texto = sin_tildes(mensaje).lower()
        metodo = getattr(self, intencion, self.fuera_de_alcance)
        return metodo(texto, estado, fecha_hoy)

    def saludo(self, texto, estado, hoy):
        return ("Hola, soy el asistente virtual de RielSur. Puedo ayudarle a comprar pasajes, ver horarios y precios, "
                "cambiar o devolver pasajes y resolver dudas de equipaje, mascotas o reclamos. ¿Qué necesita?")

    def despedida(self, texto, estado, hoy):
        return "Gracias por escribir a RielSur. Que tenga buen viaje."

    # Compra ---------------------------------------------------------------
    def comprar_pasaje(self, texto, estado, hoy):
        d = estado["datos"]
        b = self.base
        maximo = self.politicas["compra"]["maximo_pasajes_por_compra"]
        anticipacion = self.politicas["compra"]["anticipacion_maxima_dias"]

        for campo in ("origen", "destino"):
            if d.get(campo) and not b.estacion(d[campo]):
                ciudad = d.pop(campo)
                return (f"RielSur solo tiene trenes entre Santiago y Chillán, con paradas en {enumerar(b.estaciones[1:-1])}. "
                        f"No tenemos servicio a {ciudad}.")
        if d.get("origen") and d.get("origen") == d.get("destino"):
            d.pop("destino")
            return "El origen y el destino son la misma estación. ¿Hacia dónde viaja?"
        if d.get("pasajeros") and d["pasajeros"] > maximo:
            n = d.pop("pasajeros")
            return (f"Se pueden comprar hasta {maximo} pasajes por compra. Para {n} pasajeros tendría que hacer más de una compra. "
                    "¿Con cuántos pasajes partimos?")
        if d.get("fecha"):
            dias = (date.fromisoformat(d["fecha"]) - date.fromisoformat(hoy)).days
            if dias < 0:
                d.pop("fecha")
                return "Esa fecha ya pasó. ¿Para qué día quiere viajar?"
            if dias > anticipacion:
                fecha = d.pop("fecha")
                apertura = date.fromisoformat(fecha) - timedelta(days=anticipacion)
                return (f"Los pasajes se venden con un máximo de {anticipacion} días de anticipación, así que para el "
                        f"{fecha_larga(fecha)} la venta abre el {fecha_larga(apertura.isoformat())}.")
        if d.get("tarifa") == "estudiante" and d.get("clase") == "preferente":
            d.pop("clase")
            return ("El descuento de estudiante es solo para clase estándar. ¿Prefiere estándar con descuento "
                    "o preferente a precio adulto?")

        if not (d.get("origen") and d.get("destino")):
            falta = "desde qué estación" if d.get("destino") else "hacia qué estación" if d.get("origen") else "entre qué estaciones"
            return f"¿{falta[0].upper() + falta[1:]} viaja? Tenemos trenes entre {enumerar(b.estaciones)}."
        o, de = d["origen"], d["destino"]
        if not d.get("fecha"):
            return f"¿Para qué fecha quiere viajar de {o} a {de}?"
        salidas = [s for s, _ in b.servicios(o, de, d["fecha"])]
        if d.get("hora") and d["hora"] not in salidas:
            hora = d.pop("hora")
            return (f"No hay un tren que salga de {o} a las {hora} el {fecha_larga(d['fecha'])}. "
                    f"Ese día salen a las {enumerar(salidas)}. ¿Cuál prefiere?")
        if not d.get("hora"):
            return f"El {fecha_larga(d['fecha'])} los trenes de {o} a {de} salen a las {enumerar(salidas)}. ¿Cuál prefiere?"
        if not d.get("pasajeros"):
            return "¿Cuántos pasajeros son?"
        if not d.get("tarifa"):
            return "¿Con qué tarifa viajan: adulto, estudiante (con TNE), adulto mayor o niño (de 3 a 11 años)?"
        if not d.get("clase"):
            est = b.precio_unitario(o, de, d["tarifa"], "estandar")
            pref = b.precio_unitario(o, de, "adulto" if d["tarifa"] == "estudiante" else d["tarifa"], "preferente")
            return f"¿Clase estándar ({pesos(est)} por pasaje) o preferente ({pesos(pref)} por pasaje)?"
        if d.get("rut") and not rut_valido(d["rut"]):
            rut = d.pop("rut")
            return f"El RUT {rut} no es válido. ¿Me lo puede revisar?"
        if not d.get("rut") or not d.get("correo"):
            pide = [x for x, c in (("el RUT", "rut"), ("el correo", "correo")) if not d.get(c)]
            return f"Para terminar la compra necesito {enumerar(pide)} de quien compra."

        unitario = b.precio_unitario(o, de, d["tarifa"], d["clase"])
        total = unitario * d["pasajeros"]
        llegada = dict(b.servicios(o, de, d["fecha"]))[d["hora"]]
        n = d["pasajeros"]
        estado["compra_lista"] = True
        return (f"Resumen de su compra: {n} pasaje{'s' if n > 1 else ''} {NOMBRE_TARIFA[d['tarifa']]} en clase "
                f"{NOMBRE_CLASE[d['clase']]}, de {o} a {de}, el {fecha_larga(d['fecha'])} a las {d['hora']} "
                f"(llega a las {llegada}). Valor por pasaje: {pesos(unitario)}. Total: {pesos(total)}. "
                f"El enlace de pago llegará a {d['correo']} y vence en 30 minutos.")

    # Horarios -------------------------------------------------------------
    def consultar_horario(self, texto, estado, hoy):
        b, d = self.base, estado["datos"]
        o, de = d.get("origen"), d.get("destino")
        if (o and not b.estacion(o)) or (de and not b.estacion(de)):
            return self.comprar_pasaje(texto, estado, hoy)
        m = re.search(r"(?:para en|pasa por|parada en|se detiene en)\s+" + self.re_est, texto)
        parada = b.estacion(m.group(1)) if m else None

        if re.search(r"cuanto (se )?(demora|tarda|dura)|cuanto tiempo|duracion", texto):
            if o and de:
                return f"El viaje de {o} a {de} dura {minutos_a_texto(b.minutos_viaje(o, de))}."
            return "¿Entre qué estaciones? Así le digo cuánto dura el viaje."
        if parada and not d.get("hora"):
            return f"Sí. Todos los trenes entre Santiago y Chillán paran en {parada}."
        if not (o and de):
            return f"¿Entre qué estaciones quiere ver los horarios? Tenemos trenes entre {enumerar(b.estaciones)}."

        fecha = d.get("fecha")
        tipos = [b.tipo_dia(fecha)] if fecha else ["lunes_a_viernes", "sabado_domingo_festivos"]
        if not fecha and re.search(r"dia de semana|dias de semana|habil", texto):
            tipos = ["lunes_a_viernes"]
        partes = []
        for tipo in tipos:
            servicios = b.servicios(o, de, tipo=tipo)
            if parada and d.get("hora"):
                for s in b.datos["horarios"][b.sentido(o, de)][tipo]:
                    if s[o] == d["hora"]:
                        return f"El tren que sale de {o} a las {d['hora']} pasa por {parada} a las {s[parada]}."
            elegidos = self._filtrar(texto, servicios)
            estado["ultimo_servicio"] = elegidos[-1] if re.search(r"ultimo", texto) else elegidos[0]
            cuando = f"El {fecha_larga(fecha)}" if fecha else ("De lunes a viernes" if tipo == "lunes_a_viernes" else "Sábados, domingos y festivos")
            if re.search(r"\bllega|llegada|llegar", texto):
                detalle = enumerar(f"el de las {s} llega a {de} a las {l}" for s, l in elegidos)
                partes.append(f"{cuando}, {detalle}.")
            else:
                partes.append(f"{cuando}, los trenes de {o} a {de} salen a las {enumerar(s for s, _ in elegidos)}.")
        return " ".join(partes)

    def _filtrar(self, texto, servicios):
        m = re.search(r"antes de las (\d{1,2})(?::(\d{2}))?(?: de la (tarde|noche))?", texto)
        if m:
            h = int(m.group(1)) + (12 if m.group(3) and int(m.group(1)) < 12 else 0)
            limite = f"{h:02d}:{m.group(2) or '00'}"
            filtrados = [s for s in servicios if s[1] <= limite]
            return filtrados or servicios
        if re.search(r"\bprimer", texto):
            return servicios[:1]
        if re.search(r"\bultimo", texto):
            return servicios[-1:]
        if re.search(r"en la tarde|por la tarde", texto):
            return [s for s in servicios if "12:00" <= s[0] < "20:00"] or servicios
        if re.search(r"en la manana|por la manana", texto):
            return [s for s in servicios if s[0] < "12:00"] or servicios
        if re.search(r"en la noche|por la noche", texto):
            return [s for s in servicios if s[0] >= "19:00"] or servicios
        return servicios

    # Precios --------------------------------------------------------------
    def consultar_precio(self, texto, estado, hoy):
        b, d = self.base, estado["datos"]
        desc = b.datos["tarifas"]["descuentos"]
        if re.search(r"bebe|guagua|menor(es)? de 3|\b[12] anos?\b", texto):
            return f"Los menores de 3 años {b.datos['tarifas']['menores_de_3']}, así que no pagan."
        o, de = d.get("origen"), d.get("destino")
        if (o and not b.estacion(o)) or (de and not b.estacion(de)):
            return self.comprar_pasaje(texto, estado, hoy)
        if not (o and de):
            if d.get("tarifa") and d["tarifa"] != "adulto":
                t = d["tarifa"]
                return (f"Sí. La tarifa {NOMBRE_TARIFA[t]} tiene {desc[t]['porcentaje']}% de descuento "
                        f"({desc[t]['requisito']}).")
            return ("¿Entre qué estaciones? Hay descuentos de 30% para estudiantes con TNE (solo clase estándar), "
                    "40% para adultos mayores y 50% para niños de 3 a 11 años.")
        tarifa = d.get("tarifa") or "adulto"
        clases = [d["clase"]] if d.get("clase") else ["estandar", "preferente"]
        n = d.get("pasajeros") or 1
        partes = []
        for clase in clases:
            unitario = b.precio_unitario(o, de, tarifa, clase)
            if unitario is None:
                partes.append(f"la tarifa {NOMBRE_TARIFA[tarifa]} no aplica en clase {NOMBRE_CLASE[clase]}")
                continue
            texto_precio = f"clase {NOMBRE_CLASE[clase]}: {pesos(unitario)}"
            if n > 1:
                texto_precio += f" por pasaje, {pesos(unitario * n)} por {n} pasajes"
            partes.append(texto_precio)
        titulo = f"El pasaje {NOMBRE_TARIFA[tarifa]} de {o} a {de} cuesta"
        extra = ""
        if tarifa != "adulto":
            extra = f" Incluye el {desc[tarifa]['porcentaje']}% de descuento ({desc[tarifa]['requisito']})."
        return f"{titulo}: {'; '.join(partes)}.{extra}"

    # Cambios --------------------------------------------------------------
    def cambiar_pasaje(self, texto, estado, hoy):
        pol = self.politicas["cambio"]
        cargo = pol["cargo_por_pasaje"]
        d = estado["datos"]
        reserva = self.base.reserva(d.get("codigo_reserva"))
        if re.search(r"hasta cuando|hasta que hora|plazo|hasta que momento", texto):
            return f"Se puede cambiar {pol['plazo']}. Cada pasaje admite un solo cambio."
        if re.search(r"ya (lo )?cambie|otra vez|segunda vez|una vez", texto):
            return "Cada pasaje se puede cambiar una sola vez, así que un pasaje ya cambiado no admite otro cambio."
        if re.search(r"cuanto (me )?(cobran|cuesta|sale|vale)|cargo|costo", texto) and not d.get("fecha"):
            if reserva:
                n = reserva["pasajeros"]
                return (f"El cambio cuesta {pesos(cargo)} por pasaje: {pesos(cargo * n)} por sus {n} pasajes. "
                        f"Además, {pol['diferencia_tarifa']}.")
            return f"El cambio cuesta {pesos(cargo)} por pasaje. Además, {pol['diferencia_tarifa']}."

        falta_reserva = self._validar_reserva(d, reserva)
        if falta_reserva:
            return falta_reserva
        if re.search(r"mismo horario|misma hora", texto) and not d.get("hora"):
            d["hora"] = reserva["hora"]
        if not d.get("fecha") or d["fecha"] == reserva["fecha"] and not d.get("hora"):
            return (f"Encontré la reserva {reserva['codigo']}: {reserva['origen']} a {reserva['destino']}, el "
                    f"{fecha_larga(reserva['fecha'])} a las {reserva['hora']}. ¿Para qué fecha y hora la quiere cambiar?")
        salidas = [s for s, _ in self.base.servicios(reserva["origen"], reserva["destino"], d["fecha"])]
        if not d.get("hora") or d["hora"] not in salidas:
            if d.get("hora"):
                d.pop("hora")
            return (f"El {fecha_larga(d['fecha'])} los trenes de {reserva['origen']} a {reserva['destino']} salen a las "
                    f"{enumerar(salidas)}. ¿Cuál prefiere?")
        n = reserva["pasajeros"]
        if estado.get("cambio_propuesto") == [d["fecha"], d["hora"]] and re.search(r"\b(ok|dale|si|confirmo|ya|listo|bueno)\b", texto):
            return (f"Listo. Dejé registrado el cambio de la reserva {reserva['codigo']} al {fecha_larga(d['fecha'])} "
                    f"a las {d['hora']}.")
        estado["cambio_propuesto"] = [d["fecha"], d["hora"]]
        return (f"La reserva {reserva['codigo']} ({reserva['origen']} a {reserva['destino']}, {n} pasaje{'s' if n > 1 else ''}) "
                f"pasaría al {fecha_larga(d['fecha'])} a las {d['hora']}. El cambio cuesta {pesos(cargo)} por pasaje, "
                f"{pesos(cargo * n)} en total; como el tramo y la clase no cambian, no hay diferencia de tarifa. ¿Confirma el cambio?")

    def _validar_reserva(self, d, reserva):
        if not d.get("codigo_reserva"):
            return "¿Me indica el código de reserva (empieza con RS y tiene cinco números) y el RUT de quien compró?"
        if not reserva:
            return (f"No encuentro la reserva {d['codigo_reserva']}. Revise el código, por favor. "
                    f"Si el problema sigue, puede llamar al {self.empresa['telefono']}.")
        if not d.get("rut"):
            return f"Encontré la reserva {reserva['codigo']}. Para continuar necesito el RUT de quien compró."
        if d["rut"] != reserva["rut"]:
            return f"El RUT {d['rut']} no coincide con el de la reserva {reserva['codigo']}. ¿Me lo puede revisar?"
        return None

    # Devoluciones ---------------------------------------------------------
    def devolver_pasaje(self, texto, estado, hoy):
        pol = self.politicas["devolucion"]
        tramos = pol["tramos"]
        d = estado["datos"]
        m = re.search(r"(\d+)\s+horas?\s+antes", texto)
        if m and not d.get("codigo_reserva"):
            horas = int(m.group(1))
            pct = tramos[0]["reembolso_porcentaje"] if horas >= 24 else tramos[1]["reembolso_porcentaje"] if horas >= 2 else 0
            return (f"Si la pide {horas} horas antes de la salida, le devolvemos el {pct}% del valor. "
                    f"El reembolso llega en {pol['plazo_reembolso']}.")
        if re.search(r"en cuanto tiempo|cuando (me )?llega|plazo|cuantos dias", texto):
            return f"El reembolso llega en {pol['plazo_reembolso']}."
        if re.search(r"perdi|no tengo el codigo|olvide", texto) and not d.get("codigo_reserva"):
            if d.get("rut"):
                encontradas = [r for r in self.base.reservas.values() if r["rut"] == d["rut"]]
                if encontradas:
                    d["codigo_reserva"] = encontradas[0]["codigo"]
                else:
                    return (f"No encuentro reservas asociadas al RUT {d['rut']}. Para buscarla de otra forma puede llamar al "
                            f"{self.empresa['telefono']}.")
            else:
                return "Sin el código puedo buscar la reserva con el RUT de quien compró. ¿Me lo indica?"
        if not d.get("codigo_reserva") and d.get("rut"):
            encontradas = [r for r in self.base.reservas.values() if r["rut"] == d["rut"]]
            if not encontradas:
                return (f"No encuentro reservas asociadas al RUT {d['rut']}. Para buscarla de otra forma puede llamar al "
                        f"{self.empresa['telefono']}.")
            d["codigo_reserva"] = encontradas[0]["codigo"]
        reserva = self.base.reserva(d.get("codigo_reserva"))
        falta = self._validar_reserva(d, reserva)
        if falta:
            return falta
        total = reserva["total"]
        dias = (date.fromisoformat(reserva["fecha"]) - date.fromisoformat(hoy)).days
        viaje = f"{reserva['origen']} a {reserva['destino']}, {fecha_larga(reserva['fecha'])} a las {reserva['hora']}"
        if dias >= 2:
            pct = tramos[0]["reembolso_porcentaje"]
            return (f"La reserva {reserva['codigo']} ({viaje}) se puede devolver con un reembolso del {pct}%: "
                    f"{pesos(int(round(total * pct / 100)))} de {pesos(total)}. Llega en {pol['plazo_reembolso']}.")
        if dias == 1:
            p1, p2 = tramos[0]["reembolso_porcentaje"], tramos[1]["reembolso_porcentaje"]
            return (f"La reserva {reserva['codigo']} es para mañana ({viaje}). Si faltan 24 horas o más para la salida, "
                    f"le devolvemos el {p1}% ({pesos(int(round(total * p1 / 100)))}); si faltan entre 24 y 2 horas, "
                    f"el {p2}% ({pesos(int(round(total * p2 / 100)))}). Llega en {pol['plazo_reembolso']}.")
        if dias == 0:
            p2 = tramos[1]["reembolso_porcentaje"]
            return (f"La reserva {reserva['codigo']} es para hoy ({viaje}). Hasta 2 horas antes de la salida le devolvemos "
                    f"el {p2}% ({pesos(int(round(total * p2 / 100)))}); después ya no hay reembolso.")
        return f"La reserva {reserva['codigo']} era para el {fecha_larga(reserva['fecha'])}; un pasaje de un viaje que ya salió no tiene reembolso."

    # Equipaje y mascotas -----------------------------------------------------
    def equipaje_mascotas(self, texto, estado, hoy):
        eq, mas = self.politicas["equipaje"], self.politicas["mascotas"]
        partes = []
        if re.search(r"asistencia|guia|lazarillo", texto):
            partes.append(f"Los perros de asistencia {mas['perros_de_asistencia']}.")
        elif re.search(r"perr|gat[oa]|mascota|transportin", texto):
            kilos = re.search(r"(\d+)\s*(kg|kilos?)", texto)
            if kilos and int(kilos.group(1)) > 8:
                partes.append(f"Solo pueden viajar {mas['permitidas']}, así que una mascota de {kilos.group(1)} kg no puede ir. "
                              f"La excepción son los perros de asistencia, que {mas['perros_de_asistencia']}.")
            elif re.search(r"transportin|jaula", texto) and not re.search(r"cuanto", texto):
                partes.append(f"Sí. Se aceptan {mas['permitidas']}.")
            else:
                partes.append(f"Sí. Se aceptan {mas['permitidas']}. Cuesta {pesos(mas['precio_por_tramo'])} por tramo "
                              f"y se permite {mas['maximo_por_pasajero']} mascota por pasajero.")
        if re.search(r"bicicleta|bici\b", texto):
            partes.append(f"Las bicicletas se aceptan {eq['bicicletas']}.")
        if re.search(r"extra|adicional|otra maleta|segunda maleta|dos maletas", texto):
            ad = eq["maleta_adicional"]
            partes.append(f"Una maleta adicional cuesta {pesos(ad['precio'])} {ad['nota']}, y se puede llevar solo {ad['maximo']}.")
        elif not partes or re.search(r"malet|equipaje|bolso|cuanto.*llevar", texto):
            partes.append(f"Cada pasajero puede llevar sin costo {eq['incluido'].replace(' por pasajero', '')}.")
        return " ".join(partes)

    # Estado del tren ----------------------------------------------------------
    def estado_tren(self, texto, estado, hoy):
        return ("No tengo información en tiempo real sobre el estado de los trenes. Puede revisarlo en "
                f"www.rielsur.cl/estado o llamando al {self.empresa['telefono']} ({self.empresa['horario_telefono']}).")

    # Reclamos -----------------------------------------------------------------
    def reclamo(self, texto, estado, hoy):
        plazo = self.politicas["reclamos"]["plazo_respuesta"]
        d = estado["datos"]
        if re.search(r"cuando (me )?(responden|contestan)|plazo|cuanto (se )?demoran", texto):
            return f"La respuesta llega en un plazo máximo de {plazo}."
        estado.setdefault("reclamo", texto)
        if d.get("codigo_reserva") and not self.base.reserva(d["codigo_reserva"]):
            return f"No encuentro la reserva {d['codigo_reserva']}. ¿Me la puede revisar?"
        if not d.get("rut"):
            return ("Lamento lo ocurrido. Para registrar el reclamo necesito su RUT y, si lo tiene, el código de reserva. "
                    "Si quiere, deje también un correo para responderle.")
        ref = f" asociado a la reserva {d['codigo_reserva']}" if d.get("codigo_reserva") else ""
        return f"Registré su reclamo{ref}. Le responderemos en un plazo máximo de {plazo}."

    # Fuera de alcance ------------------------------------------------------------
    def fuera_de_alcance(self, texto, estado, hoy):
        b = self.base
        destino = estado.get("datos_turno", {}).get("destino")
        if destino and not b.estacion(destino):
            return (f"RielSur solo vende pasajes de tren entre Santiago y Chillán, así que no tenemos servicio a {destino}. "
                    f"Para otras consultas puede escribir a {self.empresa['correo']}.")
        if re.search(r"silla de ruedas|movilidad reducida|accesib", texto):
            return f"Sí. Hay {self.politicas['accesibilidad']}."
        if re.search(r"efectivo|tarjeta|medios? de pago|como (se )?pag", texto):
            return f"Se puede pagar con {self.politicas['compra']['medios_de_pago']}."
        if re.search(r"cafeteria", texto) and not re.search(r"vegan|vegetarian|menu|sin gluten", texto):
            return f"Sí, hay {self.politicas['servicios_a_bordo']}."
        if re.search(r"comida|vegan|vegetarian|menu|sin gluten", texto):
            return (f"No tengo información sobre el menú. Lo que sé es que hay {self.politicas['servicios_a_bordo']}. "
                    f"Para más detalles puede escribir a {self.empresa['correo']}.")
        return ("No tengo información sobre eso. Puedo ayudarle con pasajes, horarios, precios, cambios, devoluciones, "
                f"equipaje, mascotas y reclamos. Para otras consultas puede {self.contacto}.")
