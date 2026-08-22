"""
Diagnóstico puntual: reproduce el mismo orden de datos que usó el
entrenamiento (mismo shuffle seed) y corre sólo el forward (sin
backward/optimizer) sobre los primeros N ejemplos para encontrar cuál
produce loss NaN/Inf.
"""
import random
import sys

import torch
from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

sys.path.insert(0, "scripts/train")
from finetune_lora import build_inputs, load_rows

MODEL_DIR = "models/Qwen3-ASR-1.7B-hf"

rows = load_rows("data/train/manifest.jsonl", "local_clips/train", 20.0, 0)
random.Random(0).shuffle(rows)
rows = rows[:170]

processor = AutoProcessor.from_pretrained(MODEL_DIR)
model = Qwen3ASRForConditionalGeneration.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
model = model.to("mps")
model.eval()

for i, row in enumerate(rows):
    try:
        inputs = build_inputs(row, processor)
    except Exception as e:
        print(f"[{i}] ERROR procesando {row['path']}: {e}")
        continue
    inputs = {k: (v.to("mps") if hasattr(v, "to") else v) for k, v in inputs.items()}
    inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)
    with torch.no_grad():
        out = model(**inputs)
    loss_val = out.loss.item()
    flag = ""
    if loss_val != loss_val or loss_val in (float("inf"), float("-inf")):
        flag = " <<<< NaN/Inf"
        n_labels = (inputs["labels"] != -100).sum().item()
        print(f"[{i}] path={row['path']} dur={row.get('duration_s')} "
              f"text={row['text']!r} n_labels_validos={n_labels} loss={loss_val}{flag}")
    else:
        print(f"[{i}] loss={loss_val:.4f} ({row['path'].split('/')[-1]})")
