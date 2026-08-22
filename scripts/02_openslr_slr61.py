"""
Baja el corpus OpenSLR SLR61 (español argentino, CC-BY-SA 4.0, oraciones
leídas por voluntarios en Buenos Aires + mensajes meteorológicos), arma el
manifest y sincroniza al NAS. Corpus chico (~1.8GB en zips) así que se baja
entero de una, sin partir en lotes como Common Voice.

Uso: python scripts/02_openslr_slr61.py
"""
import glob
import json
import os
import subprocess
import zipfile

MIRROR = "https://openslr.trmal.net/resources/61"
FILES = {
    "es_ar_female.zip": "line_index_female.tsv",
    "es_ar_male.zip": "line_index_male.tsv",
    "es_weather_messages.zip": "es_ar_line_index_weather.tsv",
}
RAW_DIR = "raw_cache/slr61"
CLIPS_DIR = "data/train/clips_slr61"
MANIFEST_PATH = "data/train/manifest_slr61.jsonl"
NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"
RSYNC_SSH = "ssh -o RemoteCommand=none -o RequestTTY=no"


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)

    transcripts = {}
    for zip_name, tsv_name in FILES.items():
        zip_path = f"{RAW_DIR}/{zip_name}"
        tsv_path = f"{RAW_DIR}/{tsv_name}"
        if not os.path.exists(zip_path):
            print(f"descargando {zip_name}...", flush=True)
            run(["curl", "-sL", "--max-time", "900", "-o", zip_path, f"{MIRROR}/{zip_name}"])
        if not os.path.exists(tsv_path):
            run(["curl", "-sL", "--max-time", "60", "-o", tsv_path, f"{MIRROR}/{tsv_name}"])
        with open(tsv_path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                fid, text = line.split("\t", 1)
                transcripts[fid] = text
        print(f"extrayendo {zip_name}...", flush=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(RAW_DIR)

    wavs = glob.glob(f"{RAW_DIR}/**/*.wav", recursive=True)
    print(f"{len(wavs)} wavs extraídos, {len(transcripts)} transcripciones cargadas", flush=True)

    n_written = 0
    seen_fids = set()  # el zip de weather duplica ~90 ids ya presentes en female (mismo audio)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as mf:
        for wav_path in wavs:
            fid = os.path.splitext(os.path.basename(wav_path))[0]
            text = transcripts.get(fid)
            if text is None or fid in seen_fids:
                continue
            seen_fids.add(fid)
            dest = f"{CLIPS_DIR}/{fid}.wav"
            os.replace(wav_path, dest)
            dur_out = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", dest],
                capture_output=True, text=True,
            ).stdout.strip()
            mf.write(json.dumps({
                "path": dest,
                "text": text,
                "source": "openslr_61_argentinian_spanish",
                "license": "CC-BY-SA-4.0",
                "duration_s": float(dur_out) if dur_out else None,
                "transcript_type": "manual",
                "split": "train",
            }, ensure_ascii=False) + "\n")
            n_written += 1

    print(f"{n_written} clips escritos en {CLIPS_DIR}", flush=True)

    run(["ssh", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", NAS_HOST,
         f"mkdir -p {NAS_BASE}/{CLIPS_DIR}"])
    run(["rsync", "-e", RSYNC_SSH, "-a", f"{CLIPS_DIR}/", f"{NAS_HOST}:{NAS_BASE}/{CLIPS_DIR}/"])
    run(["rsync", "-e", RSYNC_SSH, "-a", MANIFEST_PATH, f"{NAS_HOST}:{NAS_BASE}/{MANIFEST_PATH}"])

    import shutil
    shutil.rmtree(RAW_DIR)
    shutil.rmtree(CLIPS_DIR)
    print("[DONE] SLR61 sincronizado al NAS y limpiado local.", flush=True)


if __name__ == "__main__":
    main()
