"""Pide la primera versión del chatbot a un modelo local de Ollama y guarda la
respuesta sin tocarla.

Uso:
    python3 scripts/generar_v0.py --modelo qwen3:4b

Queda todo en v0_cruda/<modelo>/:
    prompt_enviado.md   el mensaje exacto que recibió el modelo
    razonamiento.md     el "thinking" del modelo, si lo devuelve
    respuesta_cruda.md  la respuesta tal como llegó
    chatbot_v0.py       el primer bloque ```python``` de la respuesta, copiado byte a byte
    metadata.json       parámetros, tiempos, tokens y hashes

Solo usa la biblioteca estándar para no depender de nada instalado.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL = "http://localhost:11434"


def sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def armar_prompt():
    plantilla = (RAIZ / "prompts" / "prompt_v0.md").read_text(encoding="utf-8")
    base = json.loads((RAIZ / "data" / "base_conocimiento.json").read_text(encoding="utf-8"))
    # Va compacta para que ocupe menos contexto; el contenido es el mismo.
    compacta = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    return plantilla.replace("{{BASE_CONOCIMIENTO}}", compacta)


def digest_modelo(modelo):
    with urllib.request.urlopen(f"{URL}/api/tags", timeout=10) as r:
        for m in json.load(r)["models"]:
            if m["name"] == modelo:
                return m.get("digest")
    return None


def llamar(modelo, prompt, opciones, pensar):
    cuerpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "think": pensar,
        "options": opciones,
    }
    req = urllib.request.Request(
        f"{URL}/api/chat",
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    pensamiento, contenido, final = [], [], {}
    ultimo_aviso = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        for linea in r:
            if not linea.strip():
                continue
            parte = json.loads(linea)
            msg = parte.get("message", {})
            pensamiento.append(msg.get("thinking", ""))
            contenido.append(msg.get("content", ""))
            if parte.get("done"):
                final = parte
            if time.time() - ultimo_aviso > 30:
                largo = sum(map(len, pensamiento)) + sum(map(len, contenido))
                print(f"  ... {largo} caracteres recibidos", flush=True)
                ultimo_aviso = time.time()
    return "".join(pensamiento), "".join(contenido), final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen3:4b")
    ap.add_argument("--num-ctx", type=int, default=32768)
    ap.add_argument("--num-predict", type=int, default=24000)
    ap.add_argument("--sin-razonamiento", action="store_true")
    ap.add_argument("--forzar", action="store_true", help="sobrescribe una v0 ya generada")
    args = ap.parse_args()

    destino = RAIZ / "v0_cruda" / args.modelo.replace(":", "_")
    if (destino / "respuesta_cruda.md").exists() and not args.forzar:
        sys.exit(f"Ya existe {destino}/respuesta_cruda.md. La v0 se genera una sola vez.")
    destino.mkdir(parents=True, exist_ok=True)

    prompt = armar_prompt()
    opciones = {"num_ctx": args.num_ctx, "num_predict": args.num_predict}
    pensar = not args.sin_razonamiento

    print(f"Pidiendo la v0 a {args.modelo}...", flush=True)
    inicio = datetime.now().astimezone()
    t0 = time.time()
    pensamiento, contenido, final = llamar(args.modelo, prompt, opciones, pensar)
    duracion = time.time() - t0

    (destino / "prompt_enviado.md").write_text(prompt, encoding="utf-8")
    (destino / "respuesta_cruda.md").write_text(contenido, encoding="utf-8")
    if pensamiento:
        (destino / "razonamiento.md").write_text(pensamiento, encoding="utf-8")

    bloque = re.search(r"```python[^\n]*\n(.*?)```", contenido, re.S)
    codigo = bloque.group(1) if bloque else None
    if codigo is not None:
        (destino / "chatbot_v0.py").write_text(codigo, encoding="utf-8")

    metadata = {
        "modelo": args.modelo,
        "digest_modelo": digest_modelo(args.modelo),
        "think": pensar,
        "opciones": opciones,
        "inicio": inicio.isoformat(timespec="seconds"),
        "duracion_s": round(duracion, 1),
        "tokens_prompt": final.get("prompt_eval_count"),
        "tokens_generados": final.get("eval_count"),
        "motivo_termino": final.get("done_reason"),
        "caracteres_razonamiento": len(pensamiento),
        "caracteres_respuesta": len(contenido),
        "hay_bloque_python": codigo is not None,
        "sha256_prompt": sha256(prompt),
        "sha256_respuesta": sha256(contenido),
        "sha256_codigo": sha256(codigo) if codigo is not None else None,
    }
    (destino / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    if codigo is None:
        print("La respuesta no trae un bloque ```python```.")


if __name__ == "__main__":
    main()
