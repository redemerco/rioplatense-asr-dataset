"""
Fine-tuning LoRA de Qwen3-ASR-1.7B-hf sobre el dataset rioplatense.

Notas de diseño (ver PROGRESS.md para el detalle completo):
- Esta Mac tiene 8GB de RAM total — memoria es el recurso crítico, no
  cómputo. LoRA (congela el modelo base, entrena sólo adaptadores chicos)
  + gradient checkpointing son necesarios, no opcionales, para que esto
  entre en memoria.
- El audio se lee de una copia LOCAL de los clips (bajada del NAS antes
  de arrancar) — leer del NAS por sample durante el training sería un
  cuello de botella de red innecesario.
- Un solo ejemplo por forward/backward (batch_size=1) + gradient
  accumulation para el batch efectivo — la memoria no da para más y en
  MPS no hay multi-GPU para paralelizar.
- Se sigue el formato de fine-tuning documentado por el propio model card
  de Qwen3-ASR: transcripción objetivo en el turno del asistente como
  "language Spanish<asr_text>{texto}", `output_labels=True` en el
  processor (enmascara automáticamente audio y padding).

Uso:
  python scripts/train/finetune_lora.py \
    --train-manifest data/train/manifest.jsonl \
    --local-clips-dir /path/a/clips/locales \
    --output-dir models/qwen3-asr-rioplatense-lora \
    --max-examples 6000 --epochs 2
"""
import argparse
import json
import os
import random
import time

import soundfile as sf
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

MODEL_DIR = "models/Qwen3-ASR-1.7B-hf"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load_rows(manifest_path, local_clips_dir, max_dur_s, max_examples, seed=13):
    rows = []
    for line in open(manifest_path, encoding="utf-8"):
        d = json.loads(line)
        if d.get("duration_s") and d["duration_s"] > max_dur_s:
            continue
        fname = d["path"].split("/")[-1]
        source_subdir = d["path"].split("/")[-2]  # ej. clips_slr61, clips_snac_podcast
        local_path = os.path.join(local_clips_dir, source_subdir, fname)
        if not os.path.exists(local_path):
            continue
        d["local_path"] = local_path
        rows.append(d)
    random.Random(seed).shuffle(rows)
    if max_examples:
        rows = rows[:max_examples]
    return rows


class ManifestDataset(torch.utils.data.Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        return self.rows[idx]


def build_inputs(row, processor):
    audio, sr = sf.read(row["local_path"])
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    transcript = row["text"]
    messages = [
        {"role": "user", "content": [{"type": "audio", "audio": audio}]},
        {"role": "assistant", "content": [{"type": "text", "text": f"language Spanish<asr_text>{transcript}"}]},
    ]
    text = processor.apply_chat_template(messages, tokenize=False)
    inputs = processor(text=text, audio=[audio], output_labels=True, sampling_rate=16000)
    return inputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-manifest", default="data/train/manifest.jsonl")
    ap.add_argument("--local-clips-dir", required=True)
    ap.add_argument("--output-dir", default="models/qwen3-asr-rioplatense-lora")
    ap.add_argument("--max-examples", type=int, default=6000)
    ap.add_argument("--max-duration-s", type=float, default=15.0)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--save-every-steps", type=int, default=200)
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    log_path = os.path.join(args.output_dir, "train_log.jsonl")

    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    rows = load_rows(args.train_manifest, args.local_clips_dir, args.max_duration_s, args.max_examples)
    print(f"{len(rows)} ejemplos de entrenamiento (tras filtrar por duración <= "
          f"{args.max_duration_s}s y max_examples={args.max_examples})", flush=True)

    model = Qwen3ASRForConditionalGeneration.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
    model.config.use_cache = False
    lora_cfg = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_r * 2, lora_dropout=0.05,
        target_modules=LORA_TARGETS, task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()
    model.gradient_checkpointing_enable()
    model = model.to("mps")
    model.train()

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)

    step = 0
    t_start = time.time()
    with open(log_path, "a", encoding="utf-8") as logf:
        for epoch in range(args.epochs):
            random.Random(epoch).shuffle(rows)
            accum_loss = 0.0
            opt.zero_grad()
            for i, row in enumerate(rows):
                try:
                    inputs = build_inputs(row, processor)
                except Exception as e:
                    print(f"[WARN] fallo procesando {row.get('path')}: {e}", flush=True)
                    continue
                inputs = {k: (v.to("mps") if hasattr(v, "to") else v) for k, v in inputs.items()}
                inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)

                out = model(**inputs)
                loss = out.loss / args.grad_accum
                loss.backward()
                accum_loss += out.loss.item()

                if (i + 1) % args.grad_accum == 0:
                    opt.step()
                    opt.zero_grad()
                    step += 1
                    if step % args.log_every == 0:
                        avg_loss = accum_loss / args.grad_accum / args.log_every
                        elapsed = time.time() - t_start
                        rec = {"epoch": epoch, "step": step, "example": i, "loss": avg_loss,
                               "elapsed_s": round(elapsed, 1)}
                        logf.write(json.dumps(rec) + "\n")
                        logf.flush()
                        print(f"[epoch {epoch} step {step}] loss={avg_loss:.4f} "
                              f"({i+1}/{len(rows)} ejemplos, {elapsed/60:.1f} min)", flush=True)
                        accum_loss = 0.0
                    if step % args.save_every_steps == 0:
                        ckpt_dir = f"{args.output_dir}/checkpoint-{step}"
                        model.save_pretrained(ckpt_dir)
                        print(f"[checkpoint guardado en {ckpt_dir}]", flush=True)

            ckpt_dir = f"{args.output_dir}/checkpoint-epoch{epoch}-step{step}"
            model.save_pretrained(ckpt_dir)
            print(f"[epoch {epoch} completa, checkpoint guardado en {ckpt_dir}]", flush=True)

    final_dir = f"{args.output_dir}/checkpoint-final-step{step}"
    model.save_pretrained(final_dir)
    print(f"[DONE] entrenamiento completo -> {final_dir}", flush=True)


if __name__ == "__main__":
    main()
