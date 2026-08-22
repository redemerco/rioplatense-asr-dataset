"""
Baja el corpus VoxForge español (mirror ciempiess/voxforge_spanish en HF,
GPLv3, atribución: Carlos Daniel Hernández Mena / proyecto CIEMPIESS) shard
por shard, se queda sólo con las filas `country == "argentina"`, escribe
clips + manifest en data/train/, sincroniza al NAS y borra la copia local.
Mismo patrón que 01_common_voice_rioplatense.py (ver ese script para más
detalle de las decisiones de resiliencia/reintentos).

Uso: python scripts/03_voxforge_argentina.py
"""
import json
import os
import shutil
import subprocess
import time

BASE_URL = "https://huggingface.co/api/datasets/ciempiess/voxforge_spanish/parquet/voxforge_spanish/train/{i}.parquet"
N_SHARDS = 8
RAW_SHARD = "raw_cache/vf_shard.parquet"
CLIPS_DIR = "data/train/clips_voxforge"
MANIFEST_PATH = "data/train/manifest_voxforge.jsonl"
NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"
RSYNC_SSH = "ssh -o RemoteCommand=none -o RequestTTY=no"
MIN_FREE_GB = 3


def free_gb(path="."):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def sync_to_nas(local, remote, retries=3, wait_s=20):
    for attempt in range(1, retries + 1):
        r = subprocess.run(["rsync", "-e", RSYNC_SSH, "-a", local, remote])
        if r.returncode == 0:
            return True
        print(f"[WARN] rsync falló (intento {attempt}/{retries}) para {local}, "
              f"reintento en {wait_s}s", flush=True)
        time.sleep(wait_s)
    print(f"[WARN] NAS no disponible tras {retries} intentos, {local} queda local.", flush=True)
    return False


def main():
    import pyarrow.parquet as pq

    os.makedirs(CLIPS_DIR, exist_ok=True)
    subprocess.run(["ssh", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", NAS_HOST,
                    f"mkdir -p {NAS_BASE}/{CLIPS_DIR}"])

    for i in range(N_SHARDS):
        done_marker = f"raw_cache/.done_vf_{i}"
        if os.path.exists(done_marker):
            print(f"[{i+1}/{N_SHARDS}] ya procesado, salteo", flush=True)
            continue
        if free_gb() < MIN_FREE_GB:
            print(f"[STOP] menos de {MIN_FREE_GB}GB libres. Frenando.", flush=True)
            return

        url = BASE_URL.format(i=i)
        t0 = time.time()
        print(f"[{i+1}/{N_SHARDS}] descargando...", flush=True)
        for attempt in range(3):
            r = subprocess.run(["curl", "-sL", "--max-time", "600", "-o", RAW_SHARD, url])
            if r.returncode == 0:
                break
            print(f"[WARN] descarga falló (intento {attempt+1}/3), reintentando...", flush=True)
        else:
            print(f"[STOP] no se pudo descargar {url} tras 3 intentos.", flush=True)
            return

        df = pq.read_table(RAW_SHARD).to_pandas()
        sub = df[df["country"].fillna("").str.lower() == "argentina"]
        print(f"[{i+1}/{N_SHARDS}] {len(sub)}/{len(df)} filas Argentina "
              f"({time.time()-t0:.0f}s descarga+lectura)", flush=True)

        n_written = 0
        with open(MANIFEST_PATH, "a", encoding="utf-8") as mf:
            for _, row in sub.iterrows():
                audio = row["audio"]
                fname = audio["path"] or f"{row['audio_id']}.wav"
                clip_path = f"{CLIPS_DIR}/{fname}"
                with open(clip_path, "wb") as f:
                    f.write(audio["bytes"])
                mf.write(json.dumps({
                    "path": clip_path,
                    "text": row["normalized_text"],
                    "source": "voxforge_spanish_ciempiess",
                    "license": "GPL-3.0",
                    "duration_s": float(row["duration"]),
                    "transcript_type": "manual",
                    "gender": row.get("gender"),
                    "split": "train",
                }, ensure_ascii=False) + "\n")
                n_written += 1

        os.remove(RAW_SHARD)
        open(done_marker, "w").close()

        synced = True
        if n_written:
            synced = sync_to_nas(f"{CLIPS_DIR}/", f"{NAS_HOST}:{NAS_BASE}/{CLIPS_DIR}/")
        sync_to_nas(MANIFEST_PATH, f"{NAS_HOST}:{NAS_BASE}/{MANIFEST_PATH}")
        if synced:
            shutil.rmtree(CLIPS_DIR)
            os.makedirs(CLIPS_DIR, exist_ok=True)
            print(f"[{i+1}/{N_SHARDS}] sincronizado y limpiado local "
                  f"(libre: {free_gb():.1f}GB)", flush=True)
        else:
            print(f"[{i+1}/{N_SHARDS}] quedó local sin sincronizar "
                  f"(libre: {free_gb():.1f}GB)", flush=True)

    print("[DONE] VoxForge Argentina completo.", flush=True)


if __name__ == "__main__":
    main()
