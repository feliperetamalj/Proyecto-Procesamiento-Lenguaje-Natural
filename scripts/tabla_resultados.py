"""Junta las métricas de todas las versiones en una tabla y dos gráficos.

Uso:
    python scripts/tabla_resultados.py

Lee resultados/<sistema>/metricas.json (conversaciones de prueba) y
resultados/validacion/<sistema>/metricas.json, y escribe:
    resultados/resumen.md
    resultados/graficos/intencion.png
    resultados/graficos/respuestas.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"

SISTEMAS = [
    ("v0", "v0 cruda"),
    ("v0_corregida", "v0 corregida"),
    ("reglas", "Reglas + regex + plantillas"),
    ("tfidf_sin_contexto", "TF-IDF sin contexto"),
    ("tfidf", "TF-IDF + regex + plantillas (liviana)"),
    ("llm_intencion_regex", "qwen3:4b intención + regex + plantillas (final)"),
    ("llm_nlu", "qwen3:4b intención y datos"),
    ("llm_respuestas", "TF-IDF + gemma3:4b redacta"),
]


# Nombres cortos para el eje de los gráficos.
CORTOS = {
    "v0": "v0 cruda", "v0_corregida": "v0\ncorregida", "reglas": "Reglas", "tfidf_sin_contexto": "TF-IDF\nsin contexto",
    "tfidf": "TF-IDF\n(liviana)", "llm_intencion_regex": "qwen3 intención\n(final)", "llm_nlu": "qwen3\nintención y datos",
    "llm_respuestas": "gemma3\nredacta",
}


def cargar(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def fila(nombre, m):
    r = m["respuestas"]
    return (f"| {nombre} | {m['intencion']['accuracy']:.3f} | {m['intencion']['macro_f1']:.3f} | "
            f"{m['datos']['f1']:.3f} | {r['tasa_inventadas']:.3f} | "
            f"{r['abstencion_correcta']:.2f} | {r['cobertura_menciones']:.3f} | {m['segundos_por_turno']:.2f} |")


def tabla(carpeta):
    encabezado = ["| Versión | Intención acc. | Intención macro-F1 | Datos F1 | Resp. inventadas | Reconoce que no sabe | Menciona lo esperado | s/turno |",
                  "|---|---|---|---|---|---|---|---|"]
    filas = []
    for clave, nombre in SISTEMAS:
        m = cargar(carpeta / clave / "metricas.json")
        if m:
            filas.append(fila(nombre, m))
    return "\n".join(encabezado + filas)


def grafico(carpeta_prueba, carpeta_val, salida):
    nombres, prueba, val = [], [], []
    for clave, nombre in SISTEMAS:
        mp = cargar(carpeta_prueba / clave / "metricas.json")
        mv = cargar(carpeta_val / clave / "metricas.json")
        if mp:
            nombres.append(CORTOS[clave])
            prueba.append(mp["intencion"]["accuracy"])
            val.append(mv["intencion"]["accuracy"] if mv else 0)
    x = range(len(nombres))
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar([i - 0.2 for i in x], prueba, width=0.4, label="Prueba (62 conv.)", color="#2f6db5")
    ax.bar([i + 0.2 for i in x], val, width=0.4, label="Validación (20 conv.)", color="#f0a030")
    ax.set_xticks(list(x))
    ax.set_xticklabels(nombres, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Accuracy de intención")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.1f}".replace(".", ",")))
    for i, (a, b) in enumerate(zip(prueba, val)):
        ax.text(i - 0.2, a + 0.01, f"{a:.2f}".replace(".", ","), ha="center", fontsize=8)
        if b:
            ax.text(i + 0.2, b + 0.01, f"{b:.2f}".replace(".", ","), ha="center", fontsize=8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2, frameon=False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(salida, dpi=150)
    plt.close(fig)


def grafico_respuestas(carpeta, salida):
    nombres, inventadas, menciones = [], [], []
    for clave, nombre in SISTEMAS:
        m = cargar(carpeta / clave / "metricas.json")
        if m:
            nombres.append(CORTOS[clave])
            inventadas.append(m["respuestas"]["tasa_inventadas"])
            menciones.append(m["respuestas"]["cobertura_menciones"])
    x = range(len(nombres))
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar([i - 0.2 for i in x], menciones, width=0.4, label="Menciona el dato esperado", color="#3a9a5b")
    ax.bar([i + 0.2 for i in x], inventadas, width=0.4, label="Respuestas con datos inventados", color="#c8423b")
    ax.set_xticks(list(x))
    ax.set_xticklabels(nombres, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y * 100:.0f}%"))
    for i, (a, b) in enumerate(zip(menciones, inventadas)):
        ax.text(i - 0.2, a + 0.01, f"{a * 100:.0f}%", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.01, f"{b * 100:.0f}%", ha="center", fontsize=8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2, frameon=False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(salida, dpi=150)
    plt.close(fig)


def main():
    (RES / "graficos").mkdir(parents=True, exist_ok=True)
    texto = [
        "# Resumen de resultados",
        "",
        "Generado con `python scripts/tabla_resultados.py`.",
        "",
        "## Conversaciones de prueba (62 conversaciones, 153 turnos)",
        "",
        tabla(RES),
        "",
        "## Conversaciones de validación (20 conversaciones, 47 turnos)",
        "",
        tabla(RES / "validacion"),
        "",
    ]
    (RES / "resumen.md").write_text("\n".join(texto), encoding="utf-8")
    grafico(RES, RES / "validacion", RES / "graficos" / "intencion.png")
    grafico_respuestas(RES, RES / "graficos" / "respuestas.png")
    print("\n".join(texto))


if __name__ == "__main__":
    main()
