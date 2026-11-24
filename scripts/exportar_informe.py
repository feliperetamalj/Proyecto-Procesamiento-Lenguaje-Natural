"""Convierte docs/informe.md en docs/informe.pdf usando Chrome sin interfaz.

Uso:
    python scripts/exportar_informe.py
"""

import subprocess
import tempfile
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

ESTILO = """
@page { size: A4; margin: 2cm 2cm 2.2cm 2cm; }
body { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #222; }
h1 { color: #1f3a5f; font-size: 22pt; border-bottom: 3px solid #e07a1f; padding-bottom: 6px; }
h2 { color: #1f3a5f; font-size: 15pt; margin-top: 26px; }
h3 { color: #1f3a5f; font-size: 12pt; }
h2, h3 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9.5pt; page-break-inside: avoid; }
th { background: #1f3a5f; color: white; padding: 6px; text-align: left; }
td { border-bottom: 1px solid #ddd; padding: 5px 6px; }
tr:nth-child(even) td { background: #f6f8fb; }
code { background: #f1f3f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background: #f1f3f5; padding: 10px; border-radius: 4px; font-size: 8.5pt; white-space: pre-wrap; }
img { max-width: 100%; }
blockquote { border-left: 3px solid #e07a1f; margin-left: 0; padding-left: 12px; color: #555; }
"""


def main():
    md = (RAIZ / "docs" / "informe.md").read_text(encoding="utf-8")
    cuerpo = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html = f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{ESTILO}</style></head><body>{cuerpo}</body></html>"
    # El HTML va en docs/ para que las rutas relativas de las imágenes funcionen.
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=RAIZ / "docs", delete=False, encoding="utf-8") as f:
        f.write(html)
        temporal = Path(f.name)
    salida = RAIZ / "docs" / "informe.pdf"
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={salida}", temporal.as_uri()], check=True, capture_output=True, timeout=120)
    finally:
        temporal.unlink()
    print(f"Escrito {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
