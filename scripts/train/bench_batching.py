"""
Prueba/benchmark de batching real (batch_size>1) + DataLoader con
workers paralelos, comparado contra el baseline actual (batch_size=1 +
grad_accum). No toca el training real todavía — sólo mide steps/hora
para decidir si vale la pena el cambio.
"""
import argparse
import sys
import time

import soundfile as sf
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoProcessor, Qwen3ASRForConditionalGeneration

sys.path.insert(0, "scripts/train")
from finetune_lora import LORA_TARGETS, MODEL_DIR, load_rows

SR = 16000


class ManifestDataset(torch.utils.data.Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        audio, sr = sf.read(row["local_path"])
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return audio, row["text"]


def render_text(processor, transcript):
    messages = [
        {"role": "user", "content": [{"type": "audio", "audio": None}]},
        {"role": "assistant", "content": [{"type": "text", "text": f"language Spanish<asr_text>{transcript}"}]},
    ]
    return processor.apply_chat_template(messages, tokenize=False)


class Collator:
    """Clase (no closure) para que sea picklable con el start method
    'spawn'/'forkserver' que usa multiprocessing en Python 3.14 en macOS
    — cada worker carga su propio AutoProcessor la primera vez que se usa."""

    def __init__(self, model_dir):
        self.model_dir = model_dir
        self._processor = None

    def _proc(self):
        if self._processor is None:
            self._processor = AutoProcessor.from_pretrained(self.model_dir)
        return self._processor

    def __call__(self, batch):
        processor = self._proc()
        audios = [b[0] for b in batch]
        texts = [render_text(processor, b[1]) for b in batch]
        return processor(text=texts, audio=audios, output_labels=True, sampling_rate=SR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument("--n-steps", type=int, default=6)
    args = ap.parse_args()

    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    rows = load_rows("data/train/manifest.jsonl", "local_clips/train", 20.0, 0)
    rows = rows[: args.batch_size * (args.n_steps + 2)]

    dataset = ManifestDataset(rows)
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=args.batch_size, shuffle=False,
        collate_fn=Collator(MODEL_DIR), num_workers=args.num_workers,
    )

    model = Qwen3ASRForConditionalGeneration.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
    model.config.use_cache = False
    lora_cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                           target_modules=LORA_TARGETS, task_type="CAUSAL_LM")
    model = get_peft_model(model, lora_cfg)
    model.gradient_checkpointing_enable()
    model = model.to("mps")
    model.train()

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=1e-4)

    print(f"batch_size={args.batch_size} num_workers={args.num_workers}", flush=True)
    it = iter(loader)
    # descartar el primer batch (carga del DataLoader/warmup de MPS)
    warm = next(it)
    warm = {k: (v.to("mps") if hasattr(v, "to") else v) for k, v in warm.items()}
    warm["input_features"] = warm["input_features"].to(torch.bfloat16)
    out = model(**warm)
    out.loss.backward()
    torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
    opt.step()
    opt.zero_grad()

    times = []
    for i in range(args.n_steps):
        batch = next(it)
        t0 = time.time()
        batch = {k: (v.to("mps") if hasattr(v, "to") else v) for k, v in batch.items()}
        batch["input_features"] = batch["input_features"].to(torch.bfloat16)
        out = model(**batch)
        out.loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(trainable, max_norm=1.0)
        if torch.isfinite(grad_norm):
            opt.step()
        opt.zero_grad()
        torch.mps.synchronize()
        dt = time.time() - t0
        times.append(dt)
        print(f"  step {i}: {dt:.2f}s (loss={out.loss.item():.3f}, "
              f"{args.batch_size/dt:.3f} ejemplos/s)", flush=True)

    avg = sum(times) / len(times)
    examples_per_step = args.batch_size
    print(f"\npromedio: {avg:.2f}s/step, {examples_per_step/avg:.3f} ejemplos/s, "
          f"{3600/avg:.1f} steps/hora (steps de batch_size={args.batch_size})", flush=True)
    print(f"equivalente en 'steps de tamaño 1' (comparable al baseline grad_accum=8): "
          f"{3600*examples_per_step/avg:.1f} ejemplos/hora", flush=True)


if __name__ == "__main__":
    main()
