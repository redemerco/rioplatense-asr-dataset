"""
Evalúa un modelo (base o base+LoRA) contra el test set held-out. Métricas:
WER, CER, desglose por velocidad de habla (proxy de dificultad: palabras
por segundo de la referencia — sin eso no hay forma automática de saber
qué clip es "difícil"), y tiempo de inferencia por clip.

Uso:
  python scripts/train/evaluate.py --lora-dir models/qwen3-asr-rioplatense-lora \
    --out results/finetuned.json --tag finetuned
  python scripts/train/evaluate.py --out results/baseline.json --tag baseline
  (sin --lora-dir corre el modelo base sin fine-tunear)
"""
import argparse
import json
import re
import time

import soundfile as sf
import torch
from peft import PeftModel
from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

MODEL_DIR = "models/Qwen3-ASR-1.7B-hf"


def normalize_words(text):
    text = text.lower()
    text = re.sub(r"[^\wáéíóúüñ\s]", " ", text, flags=re.UNICODE)
    return text.split()


def edit_distance(ref, hyp):
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[n][m]


def wer(ref_text, hyp_text):
    ref, hyp = normalize_words(ref_text), normalize_words(hyp_text)
    return edit_distance(ref, hyp) / max(len(ref), 1)


def cer(ref_text, hyp_text):
    ref = re.sub(r"\s+", " ", ref_text.lower().strip())
    hyp = re.sub(r"\s+", " ", hyp_text.lower().strip())
    return edit_distance(list(ref), list(hyp)) / max(len(ref), 1)


def load_test_rows(manifest_path, local_clips_dir):
    import os
    rows = []
    for line in open(manifest_path, encoding="utf-8"):
        d = json.loads(line)
        fname = d["path"].split("/")[-1]
        source_subdir = d["path"].split("/")[-2]
        local_path = os.path.join(local_clips_dir, source_subdir, fname)
        if not os.path.exists(local_path):
            print(f"[WARN] no encontrado localmente: {local_path}, salteo", flush=True)
            continue
        d["local_path"] = local_path
        rows.append(d)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-manifest", default="data/test/manifest.jsonl")
    ap.add_argument("--local-clips-dir", default="local_clips/test")
    ap.add_argument("--lora-dir", default=None, help="si se pasa, carga el adaptador LoRA sobre el modelo base")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    model = Qwen3ASRForConditionalGeneration.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
    if args.lora_dir:
        model = PeftModel.from_pretrained(model, args.lora_dir)
        model = model.merge_and_unload()
    model = model.to("mps")
    model.eval()

    rows = load_test_rows(args.test_manifest, args.local_clips_dir)
    if args.limit:
        rows = rows[:args.limit]
    print(f"{len(rows)} clips de test a evaluar (tag={args.tag})", flush=True)

    results = []
    for i, row in enumerate(rows):
        audio, sr = sf.read(row["local_path"])
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        inputs = processor.apply_transcription_request(audio=audio, language="Spanish")
        inputs = inputs.to("mps", torch.bfloat16)

        t0 = time.time()
        with torch.no_grad():
            output_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)
        infer_s = time.time() - t0

        generated = output_ids[:, inputs["input_ids"].shape[1]:]
        hyp = processor.decode(generated, return_format="transcription_only")[0]
        ref = row["text"]

        w = wer(ref, hyp)
        c = cer(ref, hyp)
        ref_words = normalize_words(ref)
        wps = len(ref_words) / row["duration_s"] if row.get("duration_s") else None

        results.append({
            "path": row["path"], "source": row.get("source"), "ref": ref, "hyp": hyp,
            "wer": w, "cer": c, "duration_s": row.get("duration_s"),
            "words_per_second": wps, "infer_s": infer_s,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(rows)} evaluados...", flush=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"tag": args.tag, "lora_dir": args.lora_dir, "results": results}, f,
                   ensure_ascii=False, indent=2)
    print(f"[DONE] resultados guardados en {args.out}", flush=True)


if __name__ == "__main__":
    main()
