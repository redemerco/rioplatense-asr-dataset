"""
Concatena los manifest_<fuente>.jsonl de cada split en un único
data/{split}/manifest.jsonl (el formato que describe el README). Los
campos comunes son path/text/source/license/duration_s/transcript_type/
split; cada fuente puede tener columnas extra propias, eso queda tal cual.

Uso: python scripts/merge_manifests.py
"""
import glob
import subprocess

RSYNC_SSH = "ssh -o RemoteCommand=none -o RequestTTY=no"
NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"

for split in ("train", "test"):
    parts = sorted(glob.glob(f"data/{split}/manifest_*.jsonl"))
    if not parts:
        continue
    out_path = f"data/{split}/manifest.jsonl"
    with open(out_path, "w", encoding="utf-8") as out:
        for p in parts:
            with open(p, encoding="utf-8") as f:
                out.write(f.read())
    print(f"{out_path}: {len(parts)} fuentes -> {parts}")
    subprocess.run(["rsync", "-e", RSYNC_SSH, "-a", out_path,
                     f"{NAS_HOST}:{NAS_BASE}/{out_path}"], check=True)
