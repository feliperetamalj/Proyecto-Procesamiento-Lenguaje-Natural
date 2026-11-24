"""Métricas del asistente: intención, datos extraídos y respuestas."""

import re
from collections import Counter, defaultdict

from chatbot.base import CAMPOS, INTENCIONES, normalizar_valor, sin_tildes
from evaluacion.inventadas import es_evasiva, hechos_permitidos, no_respaldados, reconoce_que_no_sabe


def _patron_mencion(esperado):
    """Regex tolerante para buscar un dato esperado dentro de una respuesta."""
    e = sin_tildes(esperado).lower()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", e):  # monto: 7.000, 7000, 7,000
        partes = e.split(".")
        return r"(?<![\d.,])" + r"[.,]?".join(partes) + r"(?![\d])"
    if re.fullmatch(r"\d{2}:\d{2}", e):  # hora: 07:30 o 7:30
        h, m = e.split(":")
        return r"(?<!\d)0?" + str(int(h)) + ":" + m
    if re.fullmatch(r"\d+", e):
        return r"(?<!\d)" + e + r"(?!\d)"
    return re.escape(e)


def menciona(respuesta, esperado):
    texto = sin_tildes(respuesta or "").lower()
    opciones = esperado if isinstance(esperado, list) else [esperado]
    return any(re.search(_patron_mencion(o), texto) for o in opciones)


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def metricas_intencion(pares):
    """pares: lista de (real, predicha)."""
    total = len(pares)
    aciertos = sum(r == p for r, p in pares)
    por_clase = {}
    for c in INTENCIONES:
        tp = sum(r == c and p == c for r, p in pares)
        fp = sum(r != c and p == c for r, p in pares)
        fn = sum(r == c and p != c for r, p in pares)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        por_clase[c] = {"precision": prec, "recall": rec, "f1": f1(prec, rec), "soporte": tp + fn}
    presentes = [c for c in INTENCIONES if por_clase[c]["soporte"]]
    matriz = Counter((r, p) for r, p in pares)
    return {
        "accuracy": aciertos / total if total else 0.0,
        "macro_f1": sum(por_clase[c]["f1"] for c in presentes) / len(presentes) if presentes else 0.0,
        "por_clase": por_clase,
        "confusion": {f"{r} -> {p}": n for (r, p), n in sorted(matriz.items()) if r != p},
    }


def metricas_datos(turnos, base):
    """Compara campo por campo los datos extraídos en cada turno."""
    tp, fp, fn = Counter(), Counter(), Counter()
    errores = []
    for t in turnos:
        real = {k: normalizar_valor(k, v, base) for k, v in t["datos_reales"].items()}
        pred = {}
        for k, v in (t.get("datos_predichos") or {}).items():
            if k in CAMPOS:
                nv = normalizar_valor(k, v, base)
                if nv is not None:
                    pred[k] = nv
        for campo in CAMPOS:
            r, p = real.get(campo), pred.get(campo)
            if r is not None and p == r:
                tp[campo] += 1
            else:
                if p is not None:
                    fp[campo] += 1
                if r is not None:
                    fn[campo] += 1
                if p is not None or r is not None:
                    errores.append({"id": t["id"], "campo": campo, "real": r, "predicho": p})
    por_campo = {}
    for c in CAMPOS:
        prec = tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else 0.0
        rec = tp[c] / (tp[c] + fn[c]) if tp[c] + fn[c] else 0.0
        por_campo[c] = {"precision": prec, "recall": rec, "f1": f1(prec, rec), "soporte": tp[c] + fn[c]}
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    prec = TP / (TP + FP) if TP + FP else 0.0
    rec = TP / (TP + FN) if TP + FN else 0.0
    return {"precision": prec, "recall": rec, "f1": f1(prec, rec), "por_campo": por_campo, "errores": errores}


def metricas_respuestas(conversaciones, turnos_por_conv, base):
    con_inventos, total_resp = 0, 0
    detalle_inventos = []
    sin_info_total, sin_info_ok, evasivas = 0, 0, 0
    menciones_total, menciones_ok = 0, 0
    turnos_con_mencion, turnos_mencion_ok = 0, 0
    por_tipo = Counter()
    for conv in conversaciones:
        permitidos = hechos_permitidos(conv, base)
        for gold, pred in zip(conv["turnos"], turnos_por_conv.get(conv["id"], [])):
            resp = pred.get("respuesta") or ""
            total_resp += 1
            malos = no_respaldados(resp, permitidos)
            if es_evasiva(resp):
                evasivas += 1
            if gold.get("sin_informacion"):
                sin_info_total += 1
                if reconoce_que_no_sabe(resp):
                    sin_info_ok += 1
                elif not es_evasiva(resp):
                    # Contestó algo que la base no dice.
                    malos = malos + [("responde_sin_informacion", "")]
            if malos:
                con_inventos += 1
                for tipo, _ in malos:
                    por_tipo[tipo] += 1
                detalle_inventos.append({"id": pred["id"], "usuario": gold["usuario"], "respuesta": resp, "no_respaldado": malos})
            esperados = gold.get("debe_mencionar") or []
            if esperados:
                turnos_con_mencion += 1
                oks = [menciona(resp, e) for e in esperados]
                menciones_total += len(oks)
                menciones_ok += sum(oks)
                turnos_mencion_ok += all(oks)
    return {
        "respuestas": total_resp,
        "tasa_inventadas": con_inventos / total_resp if total_resp else 0.0,
        "respuestas_con_invento": con_inventos,
        "inventos_por_tipo": dict(por_tipo),
        "respuestas_evasivas": evasivas,
        "abstencion_correcta": sin_info_ok / sin_info_total if sin_info_total else 0.0,
        "preguntas_sin_informacion": sin_info_total,
        "cobertura_menciones": menciones_ok / menciones_total if menciones_total else 0.0,
        "turnos_con_mencion_completa": turnos_mencion_ok / turnos_con_mencion if turnos_con_mencion else 0.0,
        "detalle_inventos": detalle_inventos,
    }


def resumen_por_tema(conversaciones, turnos_por_conv):
    """Accuracy de intención agrupada por el tema de la conversación."""
    grupos = defaultdict(list)
    for conv in conversaciones:
        for gold, pred in zip(conv["turnos"], turnos_por_conv.get(conv["id"], [])):
            grupos[conv["tema"]].append(gold["intencion"] == pred.get("intencion"))
    return {k: sum(v) / len(v) for k, v in sorted(grupos.items())}
