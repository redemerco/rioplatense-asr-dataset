"""
Arma la tabla comparativa final a partir de los JSON de evaluate.py de
dos corridas (baseline y fine-tuned sobre el mismo test set).

Desglose por dificultad: uso palabras/segundo de la referencia como proxy
de velocidad de habla (no hay otra forma automática de saber qué clip es
"difícil"). El corte entre "normal" y "rápida" se define por el propio
percentil 75 de la distribución del test set (no un número inventado a
mano), así se adapta a los datos reales en vez de un umbral arbitrario.

Uso: python scripts/train/report.py results/baseline.json results/finetuned.json
"""
import json
import statistics
import sys


def load(path):
    return json.load(open(path, encoding="utf-8"))


def summarize(results, label):
    wers = [r["wer"] for r in results]
    cers = [r["cer"] for r in results]
    times = [r["infer_s"] for r in results]
    print(f"\n== {label} (n={len(results)}) ==")
    print(f"WER medio: {statistics.mean(wers)*100:.2f}%  (mediana {statistics.median(wers)*100:.2f}%)")
    print(f"CER medio: {statistics.mean(cers)*100:.2f}%  (mediana {statistics.median(cers)*100:.2f}%)")
    print(f"Tiempo de inferencia medio: {statistics.mean(times):.2f}s/clip")
    return statistics.mean(wers), statistics.mean(cers), statistics.mean(times)


def summarize_by_difficulty(results, label, wps_cutoff):
    normal = [r for r in results if (r.get("words_per_second") or 0) <= wps_cutoff]
    rapida = [r for r in results if (r.get("words_per_second") or 0) > wps_cutoff]
    for bucket, name in [(normal, "habla normal"), (rapida, "habla rápida/densa")]:
        if not bucket:
            continue
        wers = [r["wer"] for r in bucket]
        print(f"  {label} — {name} (n={len(bucket)}): "
              f"WER medio {statistics.mean(wers)*100:.2f}%")


def main():
    baseline_path, finetuned_path = sys.argv[1], sys.argv[2]
    base = load(baseline_path)
    fine = load(finetuned_path)

    all_wps = [r["words_per_second"] for r in base["results"] if r.get("words_per_second")]
    wps_cutoff = statistics.quantiles(all_wps, n=4)[2]  # percentil 75
    print(f"Corte habla normal/rápida (percentil 75 de palabras/seg del test set): {wps_cutoff:.2f}")

    b_wer, b_cer, b_time = summarize(base["results"], "BASELINE (genérico)")
    summarize_by_difficulty(base["results"], "baseline", wps_cutoff)

    f_wer, f_cer, f_time = summarize(fine["results"], "FINE-TUNED (rioplatense)")
    summarize_by_difficulty(fine["results"], "fine-tuned", wps_cutoff)

    print(f"\n== Comparación ==")
    print(f"WER: {b_wer*100:.2f}% -> {f_wer*100:.2f}%  "
          f"({'mejora' if f_wer < b_wer else 'empeora'} {abs(b_wer-f_wer)*100:.2f} puntos, "
          f"{abs(b_wer-f_wer)/max(b_wer,1e-9)*100:.1f}% relativo)")
    print(f"CER: {b_cer*100:.2f}% -> {f_cer*100:.2f}%  "
          f"({'mejora' if f_cer < b_cer else 'empeora'} {abs(b_cer-f_cer)*100:.2f} puntos)")
    print(f"Tiempo de inferencia: {b_time:.2f}s -> {f_time:.2f}s/clip")


if __name__ == "__main__":
    main()
