# Dataset de audio rioplatense para ASR

Dataset de audio en español rioplatense (Argentina + Uruguay) con
transcripción, para entrenar y evaluar ASR. Parte de la premisa de que el
cuello de botella real para mejorar ASR en rioplatense no es cómputo sino
falta de dataset — sobre todo un test set con transcripción confiable.

Ver `BRIEF.md` (brief original), `PROGRESS.md` (log de avance, qué se
investigó y bajó, y por qué) y `LICENSES.md` (procedencia y licencia exacta
de cada fuente incorporada — leer antes de asumir que algo se puede
redistribuir).

## Restricción de licencia

Sólo se incorpora contenido de licencia permisiva verificada por fuente
(CC0, CC-BY/CC-BY-SA, dominio público, o liberación explícita del dueño).
Nada de TV/radio con copyright, fútbol narrado, ni redes sociales sin
verificar. Ver el brief para el detalle completo.

## Objetivo completo

No es sólo el dataset: el proyecto incluye fine-tunear
[Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf) con LoRA
sobre este dataset y benchmarkearlo contra el modelo genérico (mismo test
set held-out, WER + CER + desglose por velocidad de habla). Ver
`PROGRESS.md` para el estado en vivo de esa parte.

## Estructura

```
data/
  train/    manifests (metadata + transcripción) para entrenamiento
  test/     manifests con transcripción verificada, held-out por hablante/split oficial
scripts/    descarga/filtrado por fuente (01-06), scripts/train/ (fine-tuning + evaluación)
```

El **audio real** (varios GB, licencias mixtas por fuente) vive en un NAS
propio, no en este repo — cada fila del manifest tiene el `path` relativo
que lo referencia. Los manifests (metadata + texto, sin binarios) sí están
acá, versionados.

Cada clip tiene su fila en `data/{split}/manifest.jsonl` con al menos:
`path`, `text`, `source`, `license`, `duration_s`, `transcript_type`
(`manual` | `validated` | `auto`).

## Estado actual

Ver `PROGRESS.md` — log cronológico de qué se investigó, bajó, decidió y
por qué, incluyendo los problemas reales encontrados en el camino (no
sólo lo que salió bien).

## Reproducir

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/<script>.py            # descarga/filtrado por fuente

python3 -m venv .venv-train && source .venv-train/bin/activate
pip install torch transformers accelerate peft datasets soundfile librosa
python scripts/train/finetune_lora.py --local-clips-dir <clips locales> --auto-resume
python scripts/train/evaluate.py --out results/baseline.json --tag baseline
python scripts/train/evaluate.py --lora-dir <checkpoint> --out results/finetuned.json --tag finetuned
python scripts/train/report.py results/baseline.json results/finetuned.json
```
