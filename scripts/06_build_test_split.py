"""
Separa un subconjunto de hablantes de SLR61 y VoxForge para el test set
held-out (nunca van a estar en train). Common Voice ya viene con su
propio split oficial (se deja como está). Snac Podcast / futuras fuentes
de YouTube CC quedan enteras en train — su transcripción es auto-caption,
no verificada, así que no sirve como referencia confiable para medir WER
(mezclaría los errores del ASR de YouTube con los del modelo que estamos
evaluando).

Selección de hablantes held-out: determinística (hash del speaker id),
no aleatoria con seed — así es reproducible sin tener que guardar estado.

Uso: python scripts/06_build_test_split.py
"""
import hashlib
import json
import subprocess

NAS_HOST = "nas"
NAS_BASE = "/srv/dev-disk-by-uuid-540a82c6-6a24-41c4-9779-5f4a8e1634ce/Remoto/Proyectos/rioplatense-asr-dataset"
SSH = ["ssh", "-o", "RemoteCommand=none", "-o", "RequestTTY=no", NAS_HOST]

# fracción de hablantes reservados para test, por fuente
HOLDOUT_FRACS = {"slr61": 0.11, "voxforge": 0.09}


def speaker_of_slr61(path):
    fname = path.split("/")[-1]
    parts = fname.split("_")
    return parts[0] + "_" + parts[1]


def speaker_of_voxforge(path):
    fname = path.split("/")[-1]
    parts = fname.split("_")
    return parts[1] + "_" + parts[2]


def is_holdout(speaker_id, frac):
    h = int(hashlib.sha256(speaker_id.encode()).hexdigest(), 16)
    return (h % 1000) / 1000 < frac


def split_source(name, manifest_path, speaker_fn, clips_dirname):
    train_rows, test_rows = [], []
    holdout_speakers = set()
    for line in open(manifest_path, encoding="utf-8"):
        d = json.loads(line)
        spk = speaker_fn(d["path"])
        if is_holdout(spk, HOLDOUT_FRACS[name]):
            holdout_speakers.add(spk)
            d["split"] = "test"
            test_rows.append(d)
        else:
            train_rows.append(d)

    print(f"{name}: {len(holdout_speakers)} hablantes held-out, "
          f"{len(test_rows)} clips test / {len(train_rows)} clips train", flush=True)

    with open(manifest_path, "w", encoding="utf-8") as f:
        for d in train_rows:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    test_manifest_path = f"data/test/manifest_{name}.jsonl"
    with open(test_manifest_path, "w", encoding="utf-8") as f:
        for d in test_rows:
            new_path = d["path"].replace(f"data/train/{clips_dirname}",
                                          f"data/test/{clips_dirname}_test")
            d["path"] = new_path
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    # mover los archivos de audio correspondientes en el NAS (train -> test)
    filenames = [d["path"].split("/")[-1] for d in test_rows]
    src_dir = f"{NAS_BASE}/data/train/{clips_dirname}"
    dst_dir = f"{NAS_BASE}/data/test/{clips_dirname}_test"
    subprocess.run(SSH + [f"mkdir -p {dst_dir}"], check=True)
    # mover en un solo comando remoto para no hacer N round-trips de ssh
    move_script = " && ".join(f'mv "{src_dir}/{fn}" "{dst_dir}/{fn}"' for fn in filenames)
    if move_script:
        r = subprocess.run(SSH + [move_script])
        if r.returncode != 0:
            print(f"[WARN] algún mv falló para {name}, revisar a mano", flush=True)

    return test_manifest_path


def main():
    split_source("slr61", "data/train/manifest_slr61.jsonl", speaker_of_slr61, "clips_slr61")
    split_source("voxforge", "data/train/manifest_voxforge.jsonl", speaker_of_voxforge, "clips_voxforge")
    print("[DONE] split de test armado.", flush=True)


if __name__ == "__main__":
    main()
