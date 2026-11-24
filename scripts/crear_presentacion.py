"""Arma la presentación de 15 minutos (presentacion/presentacion.pptx) con las
cifras que están en resultados/. Si se vuelve a evaluar algo, basta con correr
este script de nuevo.

Uso:
    python scripts/crear_presentacion.py
"""

import html
import json
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"
SALIDA = RAIZ / "presentacion" / "presentacion.pptx"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

AZUL = RGBColor(0x1F, 0x3A, 0x5F)
NARANJO = RGBColor(0xE0, 0x7A, 0x1F)
GRIS = RGBColor(0x55, 0x5F, 0x6B)
FUENTE = "Helvetica Neue"


def m(sistema, carpeta=RES):
    ruta = carpeta / sistema / "metricas.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def m_revision(sistema):
    ruta = RES / "revision_manual" / f"{sistema}.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def f3(x):
    return f"{x:.3f}".replace(".", ",")


def pct(x):
    return f"{x * 100:.0f}%"


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.vacio = self.prs.slide_layouts[6]
        self.html = []  # la misma presentación en HTML, para exportarla a PDF con Chrome

    def _texto(self, slide, x, y, w, h, texto, size=20, color=GRIS, bold=False, align=PP_ALIGN.LEFT):
        caja = slide.shapes.add_textbox(x, y, w, h)
        tf = caja.text_frame
        tf.word_wrap = True
        lineas = texto if isinstance(texto, list) else [texto]
        for i, linea in enumerate(lineas):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            run = p.add_run()
            run.text = linea
            run.font.size, run.font.bold, run.font.name = Pt(size), bold, FUENTE
            run.font.color.rgb = color
            p.space_after = Pt(10)
        return caja

    def _base(self, titulo, notas):
        s = self.prs.slides.add_slide(self.vacio)
        barra = s.shapes.add_shape(1, 0, 0, self.prs.slide_width, Inches(0.12))
        barra.fill.solid()
        barra.fill.fore_color.rgb = NARANJO
        barra.line.fill.background()
        self._texto(s, Inches(0.6), Inches(0.35), Inches(12), Inches(0.9), titulo, size=32, color=AZUL, bold=True)
        s.notes_slide.notes_text_frame.text = notas
        n = len(self.prs.slides)
        self._texto(s, Inches(12.3), Inches(7.0), Inches(0.8), Inches(0.4), str(n), size=12, align=PP_ALIGN.RIGHT)
        return s

    def portada(self, titulo, subtitulo, autor, notas):
        s = self.prs.slides.add_slide(self.vacio)
        fondo = s.shapes.add_shape(1, 0, 0, self.prs.slide_width, self.prs.slide_height)
        fondo.fill.solid()
        fondo.fill.fore_color.rgb = AZUL
        fondo.line.fill.background()
        blanco = RGBColor(0xFF, 0xFF, 0xFF)
        self._texto(s, Inches(0.9), Inches(2.3), Inches(11.5), Inches(1.4), titulo, size=44, color=blanco, bold=True)
        self._texto(s, Inches(0.9), Inches(3.7), Inches(11.5), Inches(1.0), subtitulo, size=22, color=RGBColor(0xF5, 0xC2, 0x8A))
        self._texto(s, Inches(0.9), Inches(5.6), Inches(11.5), Inches(1.0), autor, size=18, color=blanco)
        s.notes_slide.notes_text_frame.text = notas
        self.html.append(f"<section class='portada'><h1>{html.escape(titulo)}</h1><h2>{html.escape(subtitulo).replace(chr(10), '<br>')}</h2>"
                         f"<p>{html.escape(autor)}</p></section>")

    def vinetas(self, titulo, puntos, notas, size=22):
        s = self._base(titulo, notas)
        self._texto(s, Inches(0.8), Inches(1.5), Inches(11.8), Inches(5.4), [f"•  {p}" for p in puntos], size=size)
        items = "".join(f"<li>{html.escape(p)}</li>" for p in puntos)
        self._html(titulo, f"<ul style='font-size:{size * 1.33:.0f}px'>{items}</ul>")

    def tabla(self, titulo, encabezado, filas, notas, nota_pie=None, anchos=None):
        s = self._base(titulo, notas)
        alto = Inches(0.62) * (len(filas) + 1)
        forma = s.shapes.add_table(len(filas) + 1, len(encabezado), Inches(0.6), Inches(1.5), Inches(12.1), alto)
        t = forma.table
        if anchos:
            for i, a in enumerate(anchos):
                t.columns[i].width = Inches(a)
        for j, h in enumerate(encabezado):
            c = t.cell(0, j)
            c.text = h
            c.fill.solid()
            c.fill.fore_color.rgb = AZUL
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.bold, r.font.name = Pt(17), True, FUENTE
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for i, fila in enumerate(filas, 1):
            for j, v in enumerate(fila):
                c = t.cell(i, j)
                c.text = str(v)
                for p in c.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size, r.font.name = Pt(16), FUENTE
                        r.font.color.rgb = GRIS
                        r.font.bold = j == 0
        if nota_pie:
            self._texto(s, Inches(0.6), Inches(1.7) + alto, Inches(12), Inches(1.2), nota_pie, size=15)
        cab = "".join(f"<th>{html.escape(h)}</th>" for h in encabezado)
        cuerpo = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in f) + "</tr>" for f in filas)
        pie = f"<p class='pie'>{html.escape(nota_pie)}</p>" if nota_pie else ""
        self._html(titulo, f"<table><tr>{cab}</tr>{cuerpo}</table>{pie}")

    def imagen(self, titulo, ruta, notas, pie=None):
        s = self._base(titulo, notas)
        if ruta.exists():
            s.shapes.add_picture(str(ruta), Inches(0.9), Inches(1.4), width=Inches(11.5))
        if pie:
            self._texto(s, Inches(0.9), Inches(6.4), Inches(11.5), Inches(0.8), pie, size=15)
        img = f"<img src='{ruta.as_uri()}'>" if ruta.exists() else ""
        self._html(titulo, img + (f"<p class='pie'>{html.escape(pie)}</p>" if pie else ""))

    def _html(self, titulo, cuerpo):
        n = len(self.prs.slides)
        self.html.append(f"<section><div class='barra'></div><h1>{html.escape(titulo)}</h1>{cuerpo}<span class='n'>{n}</span></section>")

    def exportar_pdf(self):
        estilo = """
        @page { size: 1280px 720px; margin: 0; }
        body { margin: 0; font-family: 'Helvetica Neue', Arial, sans-serif; color: #555f6b; }
        section { width: 1280px; height: 720px; position: relative; box-sizing: border-box; padding: 34px 58px; page-break-after: always; overflow: hidden; }
        .barra { position: absolute; top: 0; left: 0; right: 0; height: 12px; background: #e07a1f; }
        h1 { color: #1f3a5f; font-size: 40px; margin: 10px 0 22px; }
        ul { padding-left: 22px; } li { margin-bottom: 12px; line-height: 1.3; }
        table { border-collapse: collapse; width: 100%; font-size: 21px; }
        th { background: #1f3a5f; color: white; text-align: left; padding: 10px; }
        td { border-bottom: 1px solid #dde2e8; padding: 10px; }
        td:first-child { font-weight: bold; }
        img { width: 1110px; display: block; margin: 0 auto; }
        .pie { font-size: 19px; margin-top: 14px; }
        .n { position: absolute; right: 30px; bottom: 18px; font-size: 15px; }
        .portada { background: #1f3a5f; padding: 220px 90px; }
        .portada h1 { color: white; font-size: 56px; } .portada h2 { color: #f5c28a; font-weight: normal; font-size: 28px; }
        .portada p { color: white; font-size: 24px; margin-top: 120px; }
        """
        ruta_html = SALIDA.with_suffix(".html")
        ruta_html.write_text(f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{estilo}</style></head>"
                             f"<body>{''.join(self.html)}</body></html>", encoding="utf-8")
        try:
            subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={SALIDA.with_suffix('.pdf')}", ruta_html.as_uri()],
                           check=True, capture_output=True, timeout=120)
        finally:
            ruta_html.unlink()

    def guardar(self):
        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        props = self.prs.core_properties
        props.title = "Asistente de atención para RielSur"
        props.author = props.last_modified_by = "Felipe Retamal"
        props.comments = ""
        self.prs.save(SALIDA)


def fila_sistema(nombre, x):
    if not x:
        return [nombre, "-", "-", "-", "-", "-"]
    r = x["respuestas"]
    return [nombre, f3(x["intencion"]["accuracy"]), f3(x["datos"]["f1"]), pct(r["tasa_inventadas"]),
            f"{round(r['abstencion_correcta'] * r['preguntas_sin_informacion'])} de {r['preguntas_sin_informacion']}",
            pct(r["cobertura_menciones"])]


def main():
    meta = json.loads((RAIZ / "v0_cruda" / "qwen3_4b" / "metadata.json").read_text(encoding="utf-8"))
    v0, v0c = m("v0"), m("v0_corregida")
    reglas, tfidf, sin_ctx = m("reglas"), m("tfidf"), m("tfidf_sin_contexto")
    llm_nlu, llm_int, llm_resp = m("llm_nlu"), m("llm_intencion_regex"), m("llm_respuestas")
    val = {k: m(k, RES / "validacion") for k in ("reglas", "tfidf", "tfidf_sin_contexto", "llm_nlu", "llm_intencion_regex", "llm_respuestas")}

    d = Deck()
    d.portada("Asistente de atención para RielSur",
              "Chatbot en Python con modelos locales\nProcesamiento del Lenguaje Natural · UAI · 2026",
              "Felipe Retamal",
              "Presento el proyecto 3 del enunciado: un asistente de atención en Python para una empresa de trenes. "
              "Lo hice solo. Voy a mostrar lo que generó la IA, cómo lo evalué, qué cambié y por qué.")

    d.vinetas("El problema", [
        "Lang-Chi pide un chatbot que atienda clientes chilenos de un servicio a elección.",
        "Elegí RielSur, una empresa de trenes ficticia entre Santiago y Chillán, con 8 estaciones.",
        "En cada mensaje el asistente debe detectar la intención (11 tipos), extraer los datos (11 campos: origen, fecha, RUT, correo...) y responder sin inventar.",
        "Solo modelos locales: qwen3:4b y gemma3:4b en Ollama, en un MacBook Air M4 de 16\u00a0GB.",
        "Toda la información verdadera está en una base de conocimiento: horarios, 28 tramos con precio, descuentos, políticas de cambio y devolución, equipaje, mascotas y 5 reservas de ejemplo.",
    ], "Elegí trenes porque tiene datos con estructura clara y porque es fácil saber si una respuesta es verdadera: "
       "un precio o un horario existe en la base o no existe. La base la genera un script, así que los precios son consistentes.")

    d.vinetas("Etapa 1: la v0 con prompt engineering", [
        "Un solo prompt a qwen3:4b: la tarea, las intenciones, los datos, la firma de procesar_turno y la base completa.",
        "El modelo razonó " + f"{meta['caracteres_razonamiento']:,}".replace(",", ".") + " caracteres y escribió 112 líneas de código. Tardó "
        + f"{meta['duracion_s'] / 60:.1f}".replace(".", ",") + " minutos (" + f"{meta['tokens_generados']:,}".replace(",", ".") + " tokens).",
        "La guardé sin tocar, con el prompt exacto, el razonamiento y los hashes, en un commit aparte.",
        "Diseño que propuso: el mismo LLM detecta intención y datos en JSON, y un if/elif elige una respuesta fija por intención.",
    ], "Lo importante acá es que la v0 está tal cual salió. El commit de la v0 solo tiene esos archivos y los hashes de "
       "metadata.json coinciden con los archivos. El razonamiento ocupó la mayor parte de los tokens.")

    d.tabla("Ejecutar la v0 tal cual", ["Qué revisé", "Resultado"], [
        ["Corre", "Sí, sin errores"],
        ["Responde", "\"No entiendo tu mensaje\" a los 153 turnos"],
        ["Causa", "Manda \"prompt\" a /api/chat, que espera \"messages\"; Ollama devuelve vacío"],
        ["Intención (accuracy)", f3(v0["intencion"]["accuracy"]) if v0 else "-"],
        ["Datos (F1)", f3(v0["datos"]["f1"]) if v0 else "-"],
        ["Reconoce que no sabe", "0 de 14"],
    ], "Corre sin caerse, pero un except silencioso esconde el error de la API. El 0,065 de accuracy son solo los turnos "
       "cuya intención correcta era fuera_de_alcance, que es lo que la v0 pone por defecto.", anchos=[3.5, 8.6])

    d.vinetas("La v0 por dentro: 4 errores y 2 problemas de diseño", [
        "Error 1: \"prompt\" en vez de \"messages\" en /api/chat.",
        "Error 2: json.loads directo, aunque el modelo a veces envuelve el JSON en un bloque de código o escribe \"intención\" con tilde.",
        "Error 3: el estado solo actualiza claves que ya existen; como parte vacío, nunca guarda nada.",
        "Error 4: los datos faltantes de la compra se buscan en el mensaje actual y no en el estado.",
        "Diseño: el prompt interno no recibe la fecha ni el trámite en curso, así que no puede resolver \"mañana\" ni mensajes como \"15678901-1\".",
        "Diseño: horarios, precios y equipaje responden con textos de relleno, por ejemplo \"[Listado de horarios en la base de conocimiento]\".",
    ], "Hice una v0 corregida que solo arregla los cuatro errores, para medir el diseño que propuso el modelo y no sus bugs. "
       "El detalle línea por línea está en docs/01_explicacion_v0.md.", size=19)

    rev_v0c = m_revision("v0_corregida")
    if v0c:
        filas_v0c = [
            ["Intención (accuracy)", f3(v0["intencion"]["accuracy"]), f3(v0c["intencion"]["accuracy"])],
            ["Datos (F1)", f3(v0["datos"]["f1"]), f3(v0c["datos"]["f1"])],
            ["Menciona lo esperado", pct(v0["respuestas"]["cobertura_menciones"]), pct(v0c["respuestas"]["cobertura_menciones"])],
        ]
        if rev_v0c:
            filas_v0c.append(["Inventadas (revisión a mano)", "0", f"{rev_v0c['inventadas']} de {rev_v0c['respuestas']}"])
        filas_v0c.append(["Segundos por turno", "<0,01", f"{v0c['segundos_por_turno']:.0f}"])
        d.tabla("La v0 corregida: el diseño del modelo, funcionando", ["Métrica", "v0 cruda", "v0 corregida"], filas_v0c,
                "Con los errores arreglados la v0 entiende mejor, pero sigue sin contestar: las respuestas son fijas y no usan la base. "
                "Cuando llega a cerrar una compra dice que el pasaje será confirmado en 30 minutos, y eso no está en la base: "
                "lo que vence en 30 minutos es el enlace de pago. El detector automático no lo ve porque el 30 sí aparece en la base. "
                "Además es lenta, porque qwen3:4b razona antes de cada respuesta.", anchos=[5, 3.5, 3.6])

    d.vinetas("Cómo lo evalué", [
        "62 conversaciones de prueba (153 turnos) escritas a mano, con intención, datos y lo que la respuesta debe mencionar.",
        "Casos difíciles a propósito: horario que no existe, 8 pasajes (máximo 6), reserva inexistente, wifi, clima, Puerto Montt.",
        "20 conversaciones de validación (47 turnos) escritas con el código cerrado y subidas antes de evaluar.",
        "Intención: accuracy y macro-F1. Datos: precisión, recall y F1 por campo.",
        "Respuestas inventadas: cada monto, hora, porcentaje, código, correo o teléfono debe existir en la base o poder calcularse; en las 14 preguntas sin respuesta, el asistente debe reconocer que no sabe.",
    ], "Las reglas las escribí mirando las conversaciones de prueba, así que ahí rinden de más. "
       "La validación muestra cuánto generaliza cada versión.", size=20)

    d.vinetas("Mi asistente: cuatro piezas intercambiables", [
        "Datos: expresiones regulares + lista de estaciones (RUT con dígito verificador, fechas relativas, \"las 7 y media\").",
        "Intención: reglas con palabras clave, TF-IDF + regresión logística (220 frases), o un LLM con salida JSON.",
        "Contexto: si el mensaje solo trae datos o confirma, sigue el trámite en curso; un RUT o correo después de una consulta pasa a compra.",
        "Respuesta: plantillas que sacan cada cifra de la base, o un LLM que redacta con la base en el prompt.",
        "Cada versión cambia una sola pieza, así se ve qué aporta cada una. Versión final: qwen3:4b (intención) + regex + contexto + plantillas.",
    ], "Esto responde a la etapa 2 del enunciado: comparar versiones simplificadas. Por ejemplo, el LLM que detecta intención "
       "lo comparo con TF-IDF, y el LLM que redacta lo comparo con plantillas.", size=20)

    filas = [
        fila_sistema("v0 corregida (LLM, sin contexto)", v0c),
        fila_sistema("Reglas + regex + plantillas", reglas),
        fila_sistema("TF-IDF sin contexto", sin_ctx),
        fila_sistema("TF-IDF + regex + plantillas (liviana)", tfidf),
        fila_sistema("qwen3:4b intención + regex (final)", llm_int),
        fila_sistema("qwen3:4b intención y datos", llm_nlu),
        fila_sistema("TF-IDF + gemma3:4b redacta", llm_resp),
    ]
    d.tabla("Resultados en las 62 conversaciones de prueba",
            ["Versión", "Intención", "Datos F1", "Inventadas", "Reconoce", "Menciona"], filas,
            "Las versiones con plantillas no inventan datos porque cada cifra sale de la base. La que redacta con gemma3:4b suena "
            "más natural, pero es la que más inventa: en la revisión a mano, 69 de 153 respuestas tienen algo falso. "
            "El mismo qwen3:4b de la v0, con un prompt mejor, es el que mejor detecta la intención.",
            nota_pie="Inventadas: según el detector automático. A mano: v0 corregida "
                     + (f"{rev_v0c['inventadas']} de {rev_v0c['respuestas']}" if rev_v0c else "-")
                     + ", gemma3:4b 69 de 153.",
            anchos=[4.6, 1.5, 1.5, 1.5, 1.5, 1.5])

    d.imagen("Prueba contra validación: quién generaliza", RES / "graficos" / "intencion.png",
             "Las reglas caen al pasar a conversaciones nuevas porque las escribí mirando las de prueba. TF-IDF y el LLM se mantienen: "
             "TF-IDF aprendió de frases que escribí aparte y el LLM no aprendió de ninguna de las dos.",
             pie=(f"La v0 corregida no tiene barra de validación: tarda {v0c['segundos_por_turno']:.0f} segundos por turno y nunca la ajusté con la prueba.  "
                  f"Reglas: {f3(reglas['intencion']['accuracy'])} → {f3(val['reglas']['intencion']['accuracy'])}.   "
                  f"TF-IDF: {f3(tfidf['intencion']['accuracy'])} → {f3(val['tfidf']['intencion']['accuracy'])}.   "
                  f"qwen3:4b: {f3(llm_int['intencion']['accuracy'])} → {f3(val['llm_intencion_regex']['intencion']['accuracy'])}.")
             if v0c and reglas and val["reglas"] and tfidf and val["tfidf"] and llm_int and val["llm_intencion_regex"] else None)

    d.imagen("Respuestas: decir lo correcto sin inventar", RES / "graficos" / "respuestas.png",
             "Verde es la proporción de datos esperados que la respuesta menciona; rojo, las respuestas con algo inventado. "
             "La v0 no inventa porque no dice nada. El LLM que redacta dice más cosas, pero inventa.",
             pie="Verde: datos esperados que menciona la respuesta. Rojo: respuestas con datos inventados según el detector automático. "
                 "A mano: gemma3 45%"
                 + (f" y v0 corregida {pct(rev_v0c['inventadas'] / rev_v0c['respuestas'])}." if rev_v0c else "."))

    revision = json.loads((RES / "revision_manual" / "llm_respuestas.json").read_text(encoding="utf-8"))
    cat = revision["por_categoria"]
    d.tabla(f"gemma3:4b redactando: {revision['inventadas']} de {revision['respuestas']} respuestas inventan algo",
            ["Tipo de error", "Respuestas", "Ejemplo"], [
                ["Precio", cat["precio"], "Santiago a Talca a $14.000 por pasajero (cuesta $7.000)"],
                ["Política", cat["politica"], "Exige avisar con 48 horas para llevar una mascota"],
                ["Horario", cat["horario"], "\"El primer tren sale a las 06:30\" (sale a las 07:30)"],
                ["Disponibilidad o fecha", cat["disponibilidad_o_fecha"], "Dice que el viaje de mañana \"ya ocurrió\""],
                ["Correo mal escrito", cat["correo_mal_escrito"], "atención@rielsur.cl, con tilde"],
                ["Acción que no ocurre", cat["accion_que_no_ocurre"], "Inventa un código de reserva nuevo, RS-98765"],
                ["Dato de la conversación", cat["dato_de_la_conversacion_erroneo"], "Cambia el destino de la reserva del cliente"],
            ],
            f"El detector automático encontró {revision['detector_automatico_marco']} de estas {revision['inventadas']}: no ve un precio equivocado "
            "que existe en otra parte de la base ni una política inventada sin números. Por eso revisé a mano. "
            "Lo que sí hace bien gemma3:4b es reconocer cuando no sabe: 14 de 14.",
            anchos=[3.2, 1.6, 7.3])

    puntos = [
        "La v0 tenía una idea razonable (LLM para entender, respuestas fijas para contestar), pero un error de API escondido por un except silencioso la dejó inútil.",
        "Recordar el trámite en curso es lo que más sube la intención: TF-IDF pasa de "
        + (f"{f3(sin_ctx['intencion']['accuracy'])} a {f3(tfidf['intencion']['accuracy'])}." if sin_ctx and tfidf else "-."),
        "El mismo qwen3:4b de la v0, con descripciones, el trámite en curso y salida JSON, es el mejor detector de intención: "
        + (f"{f3(llm_int['intencion']['accuracy'])} en prueba y {f3(val['llm_intencion_regex']['intencion']['accuracy'])} en validación." if llm_int and val["llm_intencion_regex"] else "-."),
        "TF-IDF con 220 frases queda cerca, sin GPU y en milisegundos. Las reglas a mano no generalizan.",
        "Para fechas, RUT y cifras ganan las reglas exactas y las plantillas: el LLM se equivoca en fechas relativas y, si redacta, inventa precios y políticas.",
    ]
    d.vinetas("Lo que aprendí", puntos, "La versión final usa qwen3:4b solo para la intención, regex para los datos y plantillas para responder; si Ollama no está, usa TF-IDF.", size=20)

    d.vinetas("Límites y siguientes pasos", [
        "Las conversaciones son un guion fijo: no prueban cómo reacciona un usuario real a cada respuesta.",
        "El detector de inventos no entiende el sentido; revisé a mano los casos dudosos.",
        "Faltan fechas como \"ayer\" o \"el 2 del otro mes\" y nombres sin \"me llamo\".",
        "Siguiente paso: usar el LLM solo cuando TF-IDF tenga poca confianza, para bajar la latencia, y redactar con LLM verificando cada cifra contra la base.",
    ], "Termino con lo que no alcancé y lo que haría después. Después de esto puedo mostrar una demo por consola: python -m chatbot.asistente.")

    d.guardar()
    d.exportar_pdf()
    print(f"Escritas {SALIDA.relative_to(RAIZ)} y su PDF, con {len(d.prs.slides)} diapositivas")


if __name__ == "__main__":
    main()
