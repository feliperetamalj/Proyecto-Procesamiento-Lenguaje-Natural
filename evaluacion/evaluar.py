"""Corre un sistema sobre las conversaciones de prueba y calcula sus métricas.

Uso (desde la raíz del repo):
    python -m evaluacion.evaluar --sistema v0
    python -m evaluacion.evaluar --sistema v1 --ids C01 C02

Escribe en resultados/<sistema>/:
    predicciones.jsonl  un turno por línea, con lo que devolvió el sistema
    metricas.json       todas las métricas y el detalle de errores
    resumen.md          las cifras principales en una tabla

Las predicciones se guardan apenas termina cada conversación, así que si el
proceso se corta se puede seguir con --reanudar.
"""

import argparse
import json
import time
from pathlib import Path

from chatbot.base import Base
from evaluacion import metricas
from evaluacion.sistemas import adaptar, obtener

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONVERSACIONES = RAIZ / "data" / "conversaciones_prueba.json"


def correr_conversacion(procesar, conv, fecha_hoy):
    estado, salida = None, []
    for i, turno in enumerate(conv["turnos"], 1):
        t0 = time.time()
        error = None
        try:
            r = adaptar(procesar(turno["usuario"], estado, fecha_hoy), estado)
        except Exception as e:  # el error también es un resultado
            r = {"intencion": None, "datos": {}, "respuesta": "", "estado": estado}
            error = f"{type(e).__name__}: {e}"
        estado = r["estado"]
        salida.append({
            "id": f"{conv['id']}-{i}",
            "conversacion": conv["id"],
            "usuario": turno["usuario"],
            "intencion": r["intencion"],
            "datos": r["datos"],
            "respuesta": r["respuesta"],
            "segundos": round(time.time() - t0, 2),
            "error": error,
        })
    return salida


def calcular(conversaciones, predicciones, base):
    por_conv = {}
    for p in predicciones:
        por_conv.setdefault(p["conversacion"], []).append(p)
    pares, turnos_datos = [], []
    for conv in conversaciones:
        for gold, pred in zip(conv["turnos"], por_conv.get(conv["id"], [])):
            pares.append((gold["intencion"], pred["intencion"]))
            turnos_datos.append({"id": pred["id"], "datos_reales": gold["datos"], "datos_predichos": pred["datos"]})
    tiempos = [p["segundos"] for p in predicciones]
    return {
        "conversaciones": len(conversaciones),
        "turnos": len(pares),
        "errores_de_ejecucion": sum(1 for p in predicciones if p["error"]),
        "segundos_por_turno": sum(tiempos) / len(tiempos) if tiempos else 0.0,
        "intencion": metricas.metricas_intencion(pares),
        "intencion_por_tema": metricas.resumen_por_tema(conversaciones, por_conv),
        "datos": metricas.metricas_datos(turnos_datos, base),
        "respuestas": metricas.metricas_respuestas(conversaciones, por_conv, base),
    }


def resumen_md(nombre, m):
    filas = [
        ("Conversaciones / turnos", f"{m['conversaciones']} / {m['turnos']}"),
        ("Errores de ejecución", m["errores_de_ejecucion"]),
        ("Intención: accuracy", f"{m['intencion']['accuracy']:.3f}"),
        ("Intención: macro-F1", f"{m['intencion']['macro_f1']:.3f}"),
        ("Datos: precisión", f"{m['datos']['precision']:.3f}"),
        ("Datos: recall", f"{m['datos']['recall']:.3f}"),
        ("Datos: F1", f"{m['datos']['f1']:.3f}"),
        ("Respuestas con datos inventados", f"{m['respuestas']['tasa_inventadas']:.3f} ({m['respuestas']['respuestas_con_invento']})"),
        ("Respuestas evasivas (vacías o \"no entiendo\")", m["respuestas"]["respuestas_evasivas"]),
        ("Reconoce cuando no sabe", f"{m['respuestas']['abstencion_correcta']:.3f} de {m['respuestas']['preguntas_sin_informacion']}"),
        ("Datos esperados que menciona", f"{m['respuestas']['cobertura_menciones']:.3f}"),
        ("Segundos por turno", f"{m['segundos_por_turno']:.2f}"),
    ]
    lineas = [f"# Resultados: {nombre}", "", "| Métrica | Valor |", "|---|---|"]
    lineas += [f"| {a} | {b} |" for a, b in filas]
    return "\n".join(lineas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sistema", required=True)
    ap.add_argument("--ids", nargs="*", help="solo estas conversaciones")
    ap.add_argument("--reanudar", action="store_true")
    args = ap.parse_args()

    datos = json.loads(RUTA_CONVERSACIONES.read_text(encoding="utf-8"))
    conversaciones = [c for c in datos["conversaciones"] if not args.ids or c["id"] in args.ids]
    salida = RAIZ / "resultados" / args.sistema
    salida.mkdir(parents=True, exist_ok=True)
    ruta_pred = salida / "predicciones.jsonl"

    hechas = []
    if args.reanudar and ruta_pred.exists():
        hechas = [json.loads(l) for l in ruta_pred.read_text(encoding="utf-8").splitlines() if l.strip()]
    else:
        ruta_pred.write_text("", encoding="utf-8")
    listas = {p["conversacion"] for p in hechas}

    procesar = obtener(args.sistema)
    for conv in conversaciones:
        if conv["id"] in listas:
            continue
        t0 = time.time()
        turnos = correr_conversacion(procesar, conv, datos["fecha_hoy"])
        with ruta_pred.open("a", encoding="utf-8") as f:
            for t in turnos:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        hechas += turnos
        print(f"{conv['id']}: {len(turnos)} turnos en {time.time() - t0:.1f} s", flush=True)

    m = calcular(conversaciones, hechas, Base())
    (salida / "metricas.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (salida / "resumen.md").write_text(resumen_md(args.sistema, m), encoding="utf-8")
    print(resumen_md(args.sistema, m))


if __name__ == "__main__":
    main()
