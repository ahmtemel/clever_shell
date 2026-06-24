"""
run_eval.py – Değerlendirme pipeline'ının tek giriş noktası.

Kullanım:
    python -m python.eval.run_eval [--history PATH] [--out-dir DIR] [--label STR] ...

Tüm olasılıksal işlemler seed=42 ile deterministiktir.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.eval.ablation import get_configs
from python.eval.data     import load_split
from python.eval.report   import generate_all
from python.eval.runner   import evaluate_config

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="clever_shell değerlendirme hattı",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--history", default=None, metavar="PATH",
        help="Zsh/bash history dosyasının yolu. "
             "Verilmezse otomatik bulunur (~/.zsh_history → ~/.bash_history → fixture).",
    )
    p.add_argument(
        "--out-dir", dest="out_dir", default=RESULTS_DIR, metavar="DIR",
        help="CSV, LaTeX, PNG ve REPORT.md için çıktı dizini.",
    )
    # Geriye uyumluluk: eski --out argümanı da çalışsın
    p.add_argument(
        "--out", dest="out_dir", metavar="DIR",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--label", default=None, metavar="STR",
        help="REPORT.md başlığı ve tablo açıklamalarında kullanılacak veri seti etiketi. "
             "Varsayılan: history dosyasının yolu.",
    )
    p.add_argument(
        "--train-ratio", type=float, default=0.8, metavar="F",
        help="Eğitim için kullanılacak geçmiş girdisi oranı (kronolojik split).",
    )
    p.add_argument(
        "--latency-samples", type=int, default=1000, metavar="N",
        help="Gecikme ölçümü için config başına predict_suffix çağrısı.",
    )
    p.add_argument(
        "--no-filter", action="store_true",
        help="Eğitim seti üzerinde is_valid_command + frekans filtresini devre dışı bırak.",
    )
    return p.parse_args()


def run(
    history_path=None,
    out_dir=RESULTS_DIR,
    label=None,
    train_ratio=0.8,
    latency_samples=1000,
    filter_train=True,
) -> list:
    """
    Pipeline'ı programatik olarak çalıştır (compare.py tarafından kullanılabilir).
    Tüm config sonuçlarını döndürür.
    """
    print("=" * 60, flush=True)
    print("clever_shell Değerlendirme Hattı", flush=True)
    print("=" * 60, flush=True)

    # ── Veri ──────────────────────────────────────────────────────────────────
    display_path = history_path or "(otomatik algılandı)"
    print(f"\n[eval] Geçmiş yükleniyor: {display_path}", flush=True)
    train_entries, test_entries, test_commands = load_split(
        path=history_path,
        train_ratio=train_ratio,
        filter_train=filter_train,
    )
    print(
        f"[eval] eğitim={len(train_entries)}, "
        f"test_girdisi={len(test_entries)}, "
        f"geçerli_test_komutu={len(test_commands)}",
        flush=True,
    )

    if not test_commands:
        print("[eval] UYARI: filtreleme sonrası geçerli test komutu yok; "
              "metrikler sıfır olacak.  --no-filter deneyin.", flush=True)

    dataset_label = label or display_path
    dataset_stats = {
        "n_train":      len(train_entries),
        "n_test":       len(test_entries),
        "n_test_cmds":  len(test_commands),
        "history_file": dataset_label,
    }

    # Recency ağırlıkları tüm config'lerde aynı olsun diye tek referans zamanı
    now = time.time()

    # ── Ablasyon döngüsü ───────────────────────────────────────────────────────
    configs = get_configs()
    print(f"\n[eval] {len(configs)} ablasyon konfigürasyonu çalıştırılıyor …\n",
          flush=True)

    all_results = []
    t_total = time.monotonic()

    for i, cfg in enumerate(configs, 1):
        name = cfg["name"]
        print(f"  [{i}/{len(configs)}] {name}", end=" … ", flush=True)
        t0 = time.monotonic()
        try:
            result = evaluate_config(
                config=cfg,
                train_entries=train_entries,
                test_commands=test_commands,
                now=now,
                n_latency_samples=latency_samples,
            )
            result["proposed"] = cfg.get("proposed", False)
            result["group"]    = cfg.get("group", "")
            all_results.append(result)
            dt  = time.monotonic() - t0
            ksr = result.get("metric_ksr", 0)
            acc = result.get("metric_top1_acc", 0)
            print(f"tamam ({dt:.1f}s) | KSR={ksr*100:.1f}% Doğruluk@1={acc*100:.1f}%",
                  flush=True)
        except Exception as exc:
            print(f"HATA: {exc}", flush=True)
            import traceback
            traceback.print_exc()

    elapsed = time.monotonic() - t_total
    print(f"\n[eval] Tüm konfigürasyonlar {elapsed:.1f}s'de tamamlandı", flush=True)

    # ── Rapor ──────────────────────────────────────────────────────────────────
    print(f"\n[eval] Raporlar yazılıyor: {out_dir}", flush=True)
    os.makedirs(out_dir, exist_ok=True)
    generate_all(all_results, out_dir, dataset_stats=dataset_stats)

    print("\n[eval] Tamamlandı. Çıktı dosyaları:", flush=True)
    for fname in sorted(os.listdir(out_dir)):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            print(f"  {fname:40s}  {size:>8,} bayt", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("Değerlendirme tamamlandı. Sonuçlar:", out_dir, flush=True)
    print("=" * 60, flush=True)

    return all_results


def main() -> None:
    args = _parse_args()
    run(
        history_path=args.history,
        out_dir=args.out_dir,
        label=args.label,
        train_ratio=args.train_ratio,
        latency_samples=args.latency_samples,
        filter_train=not args.no_filter,
    )


if __name__ == "__main__":
    main()
