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
import glob
import json
import os
import random
import re
import time

import soundfile as sf
import torch
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

MODEL_DIR = "models/Qwen3-ASR-1.7B-hf"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def find_latest_checkpoint(output_dir):
    """Busca el checkpoint-<N> (o epoch/final) con mayor step dentro de output_dir."""
    candidates = glob.glob(f"{output_dir}/checkpoint-*")
    best_step, best_dir = -1, None
    for c in candidates:
        m = re.search(r"step(\d+)$", c) or re.search(r"checkpoint-(\d+)$", c)
        if m:
            step = int(m.group(1))
            if step > best_step:
                best_step, best_dir = step, c
    return best_dir, best_step


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
    ap.add_argument("--auto-resume", action="store_true",
                     help="si hay checkpoints en output-dir, seguir desde el de mayor step "
                          "en vez de arrancar de cero (para reinicios tras un crash)")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    log_path = os.path.join(args.output_dir, "train_log.jsonl")

    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    rows = load_rows(args.train_manifest, args.local_clips_dir, args.max_duration_s, args.max_examples)
    print(f"{len(rows)} ejemplos de entrenamiento (tras filtrar por duración <= "
          f"{args.max_duration_s}s y max_examples={args.max_examples})", flush=True)

    base_model = Qwen3ASRForConditionalGeneration.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
    base_model.config.use_cache = False

    resume_dir, start_step = (None, 0)
    if args.auto_resume:
        found_dir, found_step = find_latest_checkpoint(args.output_dir)
        if found_dir:
            resume_dir, start_step = found_dir, found_step
        # si no hay checkpoint todavía, resume_dir/start_step quedan en (None, 0)

    if resume_dir:
        print(f"[RESUME] retomando desde {resume_dir} (step {start_step})", flush=True)
        model = PeftModel.from_pretrained(base_model, resume_dir, is_trainable=True)
    else:
        lora_cfg = LoraConfig(
            r=args.lora_r, lora_alpha=args.lora_r * 2, lora_dropout=0.05,
            target_modules=LORA_TARGETS, task_type="CAUSAL_LM",
        )
        model = get_peft_model(base_model, lora_cfg)
    model.print_trainable_parameters()
    model.gradient_checkpointing_enable()
    model = model.to("mps")
    model.train()

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable_params, lr=args.lr)

    steps_per_epoch = len(rows) // args.grad_accum
    total_steps = steps_per_epoch * args.epochs
    if start_step >= total_steps:
        print(f"[DONE] ya se alcanzaron los {total_steps} steps objetivo (resume_step={start_step}).",
              flush=True)
        return

    epoch = start_step // steps_per_epoch
    rng = random.Random(epoch)
    rng.shuffle(rows)
    pos = (start_step * args.grad_accum) % len(rows)

    step = start_step
    t_start = time.time()
    accum_loss = 0.0
    opt.zero_grad()
    with open(log_path, "a", encoding="utf-8") as logf:
        while step < total_steps:
            if pos >= len(rows):
                epoch += 1
                rng = random.Random(epoch)
                rng.shuffle(rows)
                pos = 0

            row = rows[pos]
            pos += 1
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

            if pos % args.grad_accum == 0:
                grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
                if torch.isfinite(grad_norm):
                    opt.step()
                else:
                    print(f"[WARN] grad_norm no finito ({grad_norm.item()}) en step {step+1}, "
                          f"salteando este update para no corromper los pesos.", flush=True)
                opt.zero_grad()
                step += 1
                if step % args.log_every == 0:
                    avg_loss = accum_loss / args.grad_accum / args.log_every
                    elapsed = time.time() - t_start
                    rec = {"epoch": epoch, "step": step, "elapsed_s": round(elapsed, 1),
                           "loss": avg_loss}
                    logf.write(json.dumps(rec) + "\n")
                    logf.flush()
                    print(f"[epoch {epoch} step {step}/{total_steps}] loss={avg_loss:.4f} "
                          f"({elapsed/3600:.2f}h transcurridas)", flush=True)
                    accum_loss = 0.0
                if step % args.save_every_steps == 0 or step == total_steps:
                    ckpt_dir = f"{args.output_dir}/checkpoint-step{step}"
                    model.save_pretrained(ckpt_dir)
                    print(f"[checkpoint guardado en {ckpt_dir}]", flush=True)

    print(f"[DONE] entrenamiento completo -> {args.output_dir}/checkpoint-step{step}", flush=True)


if __name__ == "__main__":
    main()
