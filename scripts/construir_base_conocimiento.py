"""Genera data/base_conocimiento.json para RielSur, la empresa de trenes ficticia
que atiende el asistente.

Los precios y horarios se calculan acá y no a mano, para que la tabla quede
consistente. Si se cambia una distancia o una tarifa, basta con volver a correr
este script.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "base_conocimiento.json"

# Estaciones de norte a sur: kilómetros y minutos de viaje desde Santiago.
ESTACIONES = [
    ("Santiago", 0, 0),
    ("Rancagua", 82, 50),
    ("San Fernando", 134, 80),
    ("Curicó", 185, 110),
    ("Talca", 249, 150),
    ("Linares", 300, 180),
    ("Parral", 342, 205),
    ("Chillán", 398, 240),
]

# Salidas desde la estación de origen de cada sentido.
SALIDAS = {
    "sur": {  # Santiago -> Chillán
        "lunes_a_viernes": ["07:30", "10:30", "14:00", "18:30"],
        "sabado_domingo_festivos": ["08:30", "13:00", "17:30"],
    },
    "norte": {  # Chillán -> Santiago
        "lunes_a_viernes": ["06:30", "10:00", "14:30", "18:00"],
        "sabado_domingo_festivos": ["09:00", "13:30", "18:00"],
    },
}

DESCUENTOS = {"adulto": 0.0, "estudiante": 0.30, "adulto_mayor": 0.40, "nino": 0.50}


def redondear_100(valor):
    return int(round(valor / 100.0)) * 100


def precio_estandar(km):
    return redondear_100(1500 + 22 * km)


def sumar_minutos(hora, minutos):
    base = datetime.strptime(hora, "%H:%M")
    return (base + timedelta(minutes=minutos)).strftime("%H:%M")


def digito_verificador(numero):
    """Dígito verificador del RUT chileno (módulo 11)."""
    suma, factor = 0, 2
    for d in reversed(str(numero)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def rut(numero):
    return f"{numero}-{digito_verificador(numero)}"


def tabla_tarifas():
    tarifas = []
    for i, (origen, km_o, _) in enumerate(ESTACIONES):
        for destino, km_d, _ in ESTACIONES[i + 1:]:
            estandar = precio_estandar(km_d - km_o)
            preferente = redondear_100(estandar * 1.6)
            tarifas.append({
                "tramo": [origen, destino],
                "estandar": estandar,
                "preferente": preferente,
            })
    return tarifas


def tabla_horarios():
    """Hora de paso por cada estación, para los dos sentidos."""
    horarios = {}
    total = ESTACIONES[-1][2]
    for sentido, por_dia in SALIDAS.items():
        horarios[sentido] = {}
        for tipo_dia, salidas in por_dia.items():
            servicios = []
            for salida in salidas:
                paradas = {}
                for nombre, _, minutos in ESTACIONES:
                    offset = minutos if sentido == "sur" else total - minutos
                    paradas[nombre] = sumar_minutos(salida, offset)
                servicios.append(paradas)
            horarios[sentido][tipo_dia] = servicios
    return horarios


def reservas_demo():
    """Reservas de ejemplo para probar cambios, devoluciones y reclamos."""
    base = [
        ("RS-10234", 12345678, "Santiago", "Talca", "2026-12-04", "10:30", 2, "adulto", "estandar"),
        ("RS-20871", 9876543, "Chillán", "Santiago", "2026-11-28", "09:00", 1, "adulto_mayor", "estandar"),
        ("RS-31502", 19456321, "Rancagua", "Curicó", "2026-11-26", "08:20", 1, "estudiante", "estandar"),
        ("RS-44120", 16783092, "Santiago", "Chillán", "2026-12-12", "17:30", 3, "adulto", "preferente"),
        ("RS-58077", 20114587, "Talca", "Santiago", "2026-11-25", "16:00", 2, "adulto", "estandar"),
    ]
    tarifas = {tuple(t["tramo"]): t for t in tabla_tarifas()}
    reservas = []
    for codigo, numero, origen, destino, fecha, hora, n, tarifa, clase in base:
        tramo = (origen, destino) if (origen, destino) in tarifas else (destino, origen)
        unitario = tarifas[tramo][clase] * (1 - DESCUENTOS[tarifa])
        reservas.append({
            "codigo": codigo,
            "rut": rut(numero),
            "origen": origen,
            "destino": destino,
            "fecha": fecha,
            "hora": hora,
            "pasajeros": n,
            "tarifa": tarifa,
            "clase": clase,
            "total": int(round(unitario)) * n,
        })
    return reservas


def construir():
    return {
        "empresa": {
            "nombre": "RielSur",
            "nota": "Empresa ficticia creada para este proyecto.",
            "ruta": "Santiago - Chillán",
            "telefono": "+56 2 2000 0000",
            "horario_telefono": "todos los días de 08:00 a 22:00",
            "correo": "atencion@rielsur.cl",
            "web": "www.rielsur.cl",
        },
        "estaciones": [
            {"nombre": n, "km_desde_santiago": km, "minutos_desde_santiago": m}
            for n, km, m in ESTACIONES
        ],
        "horarios": tabla_horarios(),
        "tarifas": {
            "moneda": "CLP",
            "nota": "Precio por pasajero y por tramo. La tarifa preferente no tiene descuento de estudiante.",
            "tramos": tabla_tarifas(),
            "descuentos": {
                "adulto": {"porcentaje": 0, "requisito": "sin requisito"},
                "estudiante": {"porcentaje": 30, "requisito": "TNE vigente; solo clase estándar"},
                "adulto_mayor": {"porcentaje": 40, "requisito": "60 años o más, con cédula de identidad"},
                "nino": {"porcentaje": 50, "requisito": "de 3 a 11 años"},
            },
            "menores_de_3": "viajan gratis en brazos de un adulto, sin asiento propio",
        },
        "politicas": {
            "compra": {
                "canales": ["web", "app", "boletería de cada estación"],
                "medios_de_pago": "débito o crédito en web y app; efectivo solo en boletería",
                "anticipacion_maxima_dias": 30,
                "maximo_pasajes_por_compra": 6,
                "datos_necesarios": ["origen", "destino", "fecha", "hora", "pasajeros", "tarifa", "clase", "rut", "correo"],
                "confirmacion": "el enlace de pago llega al correo del comprador y vence en 30 minutos",
            },
            "cambio": {
                "plazo": "hasta 2 horas antes de la salida",
                "cargo_por_pasaje": 1000,
                "diferencia_tarifa": "si el viaje nuevo es más caro se paga la diferencia; si es más barato no se devuelve",
                "cambios_permitidos": 1,
                "datos_necesarios": ["codigo_reserva", "rut", "fecha", "hora"],
            },
            "devolucion": {
                "tramos": [
                    {"anticipacion": "24 horas o más antes de la salida", "reembolso_porcentaje": 90},
                    {"anticipacion": "entre 24 y 2 horas antes de la salida", "reembolso_porcentaje": 50},
                    {"anticipacion": "menos de 2 horas antes o después de la salida", "reembolso_porcentaje": 0},
                ],
                "plazo_reembolso": "10 días hábiles, al mismo medio de pago",
                "datos_necesarios": ["codigo_reserva", "rut"],
            },
            "equipaje": {
                "incluido": "1 maleta de hasta 23 kg y 1 bolso de mano de hasta 8 kg por pasajero",
                "maleta_adicional": {"precio": 3000, "maximo": 1, "nota": "por tramo"},
                "bicicletas": "solo plegadas y en su funda, como maleta",
            },
            "mascotas": {
                "permitidas": "perros y gatos de hasta 8 kg en transportín cerrado",
                "precio_por_tramo": 2500,
                "maximo_por_pasajero": 1,
                "perros_de_asistencia": "viajan gratis",
            },
            "estado_tren": "el asistente no tiene información en tiempo real; el estado de cada servicio se publica en www.rielsur.cl/estado y en el teléfono de atención",
            "reclamos": {
                "datos_necesarios": ["rut", "codigo_reserva", "descripción"],
                "plazo_respuesta": "5 días hábiles, por correo",
            },
            "accesibilidad": "rampa y espacio para silla de ruedas en el coche 2; hay que avisar con 48 horas de anticipación",
            "servicios_a_bordo": "coche cafetería en todos los servicios",
        },
        "reservas": reservas_demo(),
    }


if __name__ == "__main__":
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(construir(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}")
