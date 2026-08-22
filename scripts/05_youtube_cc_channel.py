"""
Descarga episodios de un canal de YouTube con licencia CC-BY, los corta en
clips cortos usando los auto-captions (vía vtt_segment.py) y arma el
manifest. Verifica licencia por video (salteando los que no sean CC-BY) y
sincroniza al NAS por lotes, igual que los scripts anteriores.

Pensado para volumen: decodifica el audio del episodio UNA vez (a un
array numpy) y corta los clips en memoria en vez de invocar ffmpeg por
clip — con cientos de episodios, un ffmpeg por clip sería demasiado lento.

Uso:
  python scripts/05_youtube_cc_channel.py <channel_url_or_handle> <source_slug> [--limit N] [--ids-file archivo.txt]

  --ids-file: en vez de listar el canal, usar esta lista de video IDs
  (una por línea) — útil para una muestra ya elegida a mano.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from vtt_segment import make_segments, parse_words

SR = 16000
RAW_DIR = "raw_cache/yt_episode"
NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"
RSYNC_SSH = "ssh -o RemoteCommand=none -o RequestTTY=no"
MIN_FREE_GB = 3


def free_gb(path="."):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def sync_to_nas(local, remote, retries=3, wait_s=20):
    import time
    for attempt in range(1, retries + 1):
        r = subprocess.run(["rsync", "-e", RSYNC_SSH, "-a", local, remote])
        if r.returncode == 0:
            return True
        print(f"[WARN] rsync falló (intento {attempt}/{retries}) para {local}", flush=True)
        time.sleep(wait_s)
    print(f"[WARN] NAS no disponible, {local} queda local.", flush=True)
    return False


def get_video_ids(channel_url, limit):
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--playlist-end", str(limit), "--print", "%(id)s",
         f"{channel_url}/videos"],
        capture_output=True, text=True, timeout=120,
    )
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def process_video(vid, source_slug, clips_dir, manifest_path):
    os.makedirs(RAW_DIR, exist_ok=True)
    meta = subprocess.run(
        ["yt-dlp", "--print", "%(license)s|%(duration)s|%(channel)s|%(title)s",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=60,
    ).stdout.strip()
    if not meta or "|" not in meta:
        print(f"[{vid}] no se pudo leer metadata, salteo", flush=True)
        return 0
    license_, duration, channel, title = meta.split("|", 3)
    if "Creative Commons Attribution" not in license_:
        print(f"[{vid}] licencia no es CC-BY ('{license_}'), salteo", flush=True)
        return 0

    base = f"{RAW_DIR}/{vid}"
    r = subprocess.run(
        ["yt-dlp", "-f", "worstaudio[ext=m4a]/worstaudio", "-x", "--audio-format", "opus",
         "--audio-quality", "5", "--write-auto-sub", "--sub-lang", "es", "--sub-format", "vtt",
         "-o", f"{base}.%(ext)s", f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=1200,
    )
    vtt_path = f"{base}.es.vtt"
    audio_path = f"{base}.opus"
    if not (os.path.exists(vtt_path) and os.path.exists(audio_path)):
        print(f"[{vid}] faltó audio o subtítulos, salteo. stderr: {r.stderr[-300:]}", flush=True)
        for p in (vtt_path, audio_path):
            if os.path.exists(p):
                os.remove(p)
        return 0

    words = parse_words(open(vtt_path, encoding="utf-8").read())
    segments = make_segments(words)

    # decodificar el episodio entero UNA vez a 16kHz mono
    proc = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", audio_path, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
        capture_output=True,
    )
    audio = np.frombuffer(proc.stdout, dtype=np.float32)

    n_written = 0
    with open(manifest_path, "a", encoding="utf-8") as mf:
        for i, seg in enumerate(segments):
            start_i = int(seg["start"] * SR)
            end_i = int(seg["end"] * SR)
            if end_i <= start_i or end_i > len(audio):
                continue
            clip = audio[start_i:end_i]
            clip_name = f"{vid}_{i:04d}.flac"
            clip_path = f"{clips_dir}/{clip_name}"
            sf.write(clip_path, clip, SR)
            mf.write(json.dumps({
                "path": clip_path,
                "text": seg["text"],
                "source": source_slug,
                "license": "CC-BY-3.0",
                "duration_s": round(seg["end"] - seg["start"], 3),
                "transcript_type": "auto",
                "video_id": vid,
                "channel": channel,
                "split": "train",
            }, ensure_ascii=False) + "\n")
            n_written += 1

    os.remove(vtt_path)
    os.remove(audio_path)
    print(f"[{vid}] '{title[:50]}' -> {n_written} clips ({float(duration)/60:.0f} min)", flush=True)
    return n_written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel_url")
    ap.add_argument("source_slug")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--ids-file")
    args = ap.parse_args()

    clips_dir = f"data/train/clips_{args.source_slug}"
    manifest_path = f"data/train/manifest_{args.source_slug}.jsonl"
    os.makedirs(clips_dir, exist_ok=True)
    subprocess.run(["ssh", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", NAS_HOST,
                    f"mkdir -p {NAS_BASE}/{clips_dir}"])

    if args.ids_file:
        ids = [l.strip() for l in open(args.ids_file) if l.strip()]
    else:
        ids = get_video_ids(args.channel_url, args.limit)
    print(f"{len(ids)} videos a procesar", flush=True)

    SYNC_EVERY = 10
    since_sync = 0
    for vid in ids:
        done_marker = f"raw_cache/.done_yt_{args.source_slug}_{vid}"
        if os.path.exists(done_marker):
            print(f"[{vid}] ya procesado, salteo", flush=True)
            continue
        if free_gb() < MIN_FREE_GB:
            print(f"[STOP] menos de {MIN_FREE_GB}GB libres. Frenando.", flush=True)
            break
        try:
            process_video(vid, args.source_slug, clips_dir, manifest_path)
        except Exception as e:
            print(f"[{vid}] ERROR: {e}, salteo", flush=True)
            continue
        open(done_marker, "w").close()
        since_sync += 1

        if since_sync >= SYNC_EVERY:
            synced = sync_to_nas(f"{clips_dir}/", f"{NAS_HOST}:{NAS_BASE}/{clips_dir}/")
            sync_to_nas(manifest_path, f"{NAS_HOST}:{NAS_BASE}/{manifest_path}")
            if synced:
                shutil.rmtree(clips_dir)
                os.makedirs(clips_dir, exist_ok=True)
                since_sync = 0

    if since_sync:
        synced = sync_to_nas(f"{clips_dir}/", f"{NAS_HOST}:{NAS_BASE}/{clips_dir}/")
        sync_to_nas(manifest_path, f"{NAS_HOST}:{NAS_BASE}/{manifest_path}")
        if synced:
            shutil.rmtree(clips_dir)
            os.makedirs(clips_dir, exist_ok=True)

    print(f"[DONE] {args.source_slug} completo.", flush=True)


if __name__ == "__main__":
    main()
