# Dataset de audio rioplatense para ASR

Dataset de audio en español rioplatense (Argentina + Uruguay) con
transcripción, para entrenar y evaluar ASR. Nace de un pipeline de
transcripción de clases (`zoom-recorder`) donde se detectó que el cuello de
botella real para mejorar ASR en rioplatense no es cómputo sino falta de
dataset — sobre todo un test set con transcripción confiable.

Ver `BRIEF.md` (brief original), `PROGRESS.md` (log de avance, qué se
investigó y bajó, y por qué) y `LICENSES.md` (procedencia y licencia exacta
de cada fuente incorporada — leer antes de asumir que algo se puede
redistribuir).

## Restricción de licencia

Sólo se incorpora contenido de licencia permisiva verificada por fuente
(CC0, CC-BY/CC-BY-SA, dominio público, o liberación explícita del dueño).
Nada de TV/radio con copyright, fútbol narrado, ni redes sociales sin
verificar. Ver el brief para el detalle completo.

## Estructura

```
data/
  train/    clips + transcripción para entrenamiento (tolera ruido)
  test/     clips + transcripción verificada, para medir WER con confianza
scripts/    scripts de descarga/filtrado (uno por fuente)
raw_cache/  caché temporal de descargas en curso (no es dataset final)
logs/       logs de ejecución de scripts
```

Cada clip incorporado a `data/` tiene su fila en un manifest
(`data/train/manifest.jsonl` / `data/test/manifest.jsonl`) con al menos:
`path`, `text`, `source`, `license`, `duration_s`, `transcript_type`
(`manual` | `validated` | `auto`).

## Estado actual

Ver `PROGRESS.md` — incluye un bloqueante de espacio en disco activo en
esta máquina (sólo ~15GB libres), que limita cuánto se puede bajar acá sin
disco adicional.

## Reproducir / continuar la descarga

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/<script>.py
```
