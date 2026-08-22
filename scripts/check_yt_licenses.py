"""
Utilidad de validación: para una lista de video IDs de YouTube, chequea
licencia + idioma + duración vía yt-dlp (con timeout por video, así uno
que cuelgue no traba todo el lote). Sólo lectura de metadata, no descarga
audio. Uso: python scripts/check_yt_licenses.py archivo_de_ids.txt
"""
import subprocess
import sys

ids_file = sys.argv[1]
with open(ids_file) as f:
    ids = [line.strip() for line in f if line.strip()]

for vid in ids:
    try:
        r = subprocess.run(
            ["yt-dlp", "--print", "%(license)s|%(duration)s|%(language)s|%(title).60s",
             f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True, text=True, timeout=30,
        )
        out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "ERROR"
    except subprocess.TimeoutExpired:
        out = "TIMEOUT"
    print(f"{vid}|{out}", flush=True)
