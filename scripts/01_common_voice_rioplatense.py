"""
Baja Common Voice 23.0 (es) shard por shard desde el mirror CC0 en HF
(bookbot/common_voice_23_0_es), se queda sólo con las filas cuyo campo
`accents` contiene "Rioplatense" (Argentina/Uruguay/este de Bolivia/Paraguay,
la categoría armonizada de Common Voice), escribe esos clips + manifest en
data/{split}/, sincroniza cada lote al NAS por rsync, y borra la copia local
para no comprometer el disco de la Mac (ver PROGRESS.md).

Uso: python scripts/01_common_voice_rioplatense.py
"""
import json
import os
import shutil
import subprocess
import time

BASE_URL = "https://huggingface.co/api/datasets/bookbot/common_voice_23_0_es/parquet/default/{split}/{i}.parquet"
SPLIT_SHARDS = {"test": 2, "train": 33}
RAW_SHARD = "raw_cache/cv_shard.parquet"
ACCENT_KEY = "Rioplatense"
NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"
RSYNC_SSH = "ssh -o RemoteCommand=none -o RequestTTY=no"
MIN_FREE_GB = 3


def free_gb(path="."):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def sync_to_nas(local, remote, retries=3, wait_s=20):
    """rsync con reintentos; si el NAS está caído no aborta el script entero
    (se queda con la copia local y sigue con el próximo shard)."""
    for attempt in range(1, retries + 1):
        r = subprocess.run(["rsync", "-e", RSYNC_SSH, "-a", local, remote])
        if r.returncode == 0:
            return True
        print(f"[WARN] rsync falló (intento {attempt}/{retries}, código {r.returncode}) "
              f"para {local} -> se reintenta en {wait_s}s", flush=True)
        time.sleep(wait_s)
    print(f"[WARN] NAS no disponible tras {retries} intentos, "
          f"{local} se queda local por ahora.", flush=True)
    return False


def main():
    import pyarrow.parquet as pq  # importado acá: primero queremos fallar rápido en el chequeo de disco

    for split, n_shards in SPLIT_SHARDS.items():
        out_dir = f"data/{split}"
        clips_dir = f"{out_dir}/clips"
        manifest_path = f"{out_dir}/manifest_common_voice.jsonl"
        os.makedirs(clips_dir, exist_ok=True)
        subprocess.run(["ssh", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", NAS_HOST,
                        f"mkdir -p {NAS_BASE}/{clips_dir}"])

        for i in range(n_shards):
            done_marker = f"raw_cache/.done_cv_{split}_{i}"
            if os.path.exists(done_marker):
                print(f"[{split} {i+1}/{n_shards}] ya procesado (marker existe), salteo", flush=True)
                continue
            if free_gb() < MIN_FREE_GB:
                print(f"[STOP] menos de {MIN_FREE_GB}GB libres en disco. Frenando acá.", flush=True)
                return

            url = BASE_URL.format(split=split, i=i)
            t0 = time.time()
            print(f"[{split} {i+1}/{n_shards}] descargando...", flush=True)
            for attempt in range(3):
                r = subprocess.run(["curl", "-sL", "--max-time", "600", "-o", RAW_SHARD, url])
                if r.returncode == 0:
                    break
                print(f"[WARN] descarga falló (intento {attempt+1}/3, código {r.returncode}), "
                      f"reintentando...", flush=True)
            else:
                print(f"[STOP] no se pudo descargar {url} tras 3 intentos.", flush=True)
                return

            table = pq.read_table(RAW_SHARD)
            df = table.to_pandas()
            mask = df["accents"].fillna("").str.contains(ACCENT_KEY)
            sub = df[mask]
            print(f"[{split} {i+1}/{n_shards}] {len(sub)}/{len(df)} filas Rioplatense "
                  f"({time.time()-t0:.0f}s descarga+lectura)", flush=True)

            n_written = 0
            with open(manifest_path, "a", encoding="utf-8") as mf:
                for _, row in sub.iterrows():
                    audio = row["audio"]
                    fname = audio["path"] or f"{row['sentence_id']}.mp3"
                    clip_path = f"{clips_dir}/{fname}"
                    with open(clip_path, "wb") as f:
                        f.write(audio["bytes"])
                    dur_out = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                         "-of", "csv=p=0", clip_path],
                        capture_output=True, text=True,
                    ).stdout.strip()
                    mf.write(json.dumps({
                        "path": clip_path,
                        "text": row["sentence"],
                        "source": "common_voice_23_0",
                        "license": "CC0-1.0",
                        "duration_s": float(dur_out) if dur_out else None,
                        "transcript_type": "validated",
                        "accent_raw": row["accents"],
                        "gender": row.get("gender"),
                        "up_votes": int(row["up_votes"]),
                        "down_votes": int(row["down_votes"]),
                        "split": split,
                    }, ensure_ascii=False) + "\n")
                    n_written += 1

            os.remove(RAW_SHARD)
            open(done_marker, "w").close()

            synced = True
            if n_written:
                synced = sync_to_nas(f"{clips_dir}/", f"{NAS_HOST}:{NAS_BASE}/{clips_dir}/")
            sync_to_nas(manifest_path, f"{NAS_HOST}:{NAS_BASE}/{manifest_path}")
            if synced:
                shutil.rmtree(clips_dir)
                os.makedirs(clips_dir, exist_ok=True)
                print(f"[{split} {i+1}/{n_shards}] sincronizado al NAS y limpiado local "
                      f"(libre: {free_gb():.1f}GB)", flush=True)
            else:
                print(f"[{split} {i+1}/{n_shards}] quedó local sin sincronizar "
                      f"(libre: {free_gb():.1f}GB)", flush=True)

    print("[DONE] Common Voice Rioplatense completo.", flush=True)


if __name__ == "__main__":
    main()
