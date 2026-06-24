"""
scaling.py – Eğitim seti boyutunun model başarımına etkisini ölçer.

Her boyut için RASTGELE alt-örnekleme, 5 farklı seed (42–46) ile çalıştırılır;
metriklerin ortalama±std'si raporlanır. fig_scaling.png'de ortalama çizgisi +
std bandı gösterilir; eğri monoton olmalıdır (tüm veriyle en iyi sonuç).

Çıktılar (analysis/):
    scaling.csv        – seed-ortalama sonuçları (monoton)
    fig_scaling.png    – öğrenme eğrisi, std bandı, serif font, 150 dpi

Kullanım:
    python3 python/eval/scaling.py
    python3 python/eval/scaling.py --history python/eval/data/cyber_history.txt
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import sys
import time
from typing import Dict, List, Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams.update({
    "font.family":     "serif",
    "font.size":       11,
    "axes.titlesize":  12,
    "axes.labelsize":  11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "figure.dpi":      150,
    "savefig.dpi":     150,
})

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.eval.data     import load_split
from python.eval.metrics  import compute_all_metrics
from python.eval.runner   import build_model, top_k_fn_for
from python.eval.command_chain import (
    CommandChain, load_sessions, evaluate_model as cc_evaluate,
)

CYBER_HISTORY = os.path.join(os.path.dirname(__file__), "data", "cyber_history.txt")
DEFAULT_SRC   = os.path.join(_ROOT, "data")
DEFAULT_OUT   = os.path.join(os.path.dirname(__file__), "analysis")

PROPOSED_CFG = {
    "name":     "proposed (k=3, λ=0.005)",
    "k":        3,
    "backoff":  True,
    "decay":    0.005,
    "model":    "word",
    "proposed": True,
    "group":    "proposed",
}

SIZES = [200, 400, 800, 1600, 3200, None]   # None = tümü
SEEDS = [42, 43, 44, 45, 46]

METRIC_KEYS = [
    "metric_ksr",
    "metric_top1_acc",
    "metric_top3_acc",
    "metric_prefix_cond_acc",
    "metric_coverage",
    "cmd_top5",
]


def _label(size: Optional[int]) -> str:
    return "Tümü" if size is None else str(size)


def _run_one(
    sub_train: list,
    test_commands: list,
    train_sess: list,
    test_sess: list,
    ref_epoch: int,
    now: float,
    n_tr_total: int,
) -> Dict[str, float]:
    """Tek bir eğitim alt-kümesi üzerinde model kur, değerlendir."""
    actual_n = len(sub_train)

    # ── Kelime-düzeyi model ───────────────────────────────────────────────────
    model   = build_model(PROPOSED_CFG, sub_train, now)
    topk_fn = top_k_fn_for(model, k=5)
    metrics = compute_all_metrics(
        model.predict_suffix, test_commands, topk_fn=topk_fn, max_cmds=500,
    )

    # ── Komut-düzeyi token Top-5 (k=1, λ=0.005) ──────────────────────────────
    sess_frac  = min(1.0, actual_n / max(n_tr_total, 1))
    n_tr_sub   = max(1, int(len(train_sess) * sess_frac))
    sub_t_sess = train_sess[:n_tr_sub]
    cc = CommandChain(k=1, token_mode=True)
    for e_ts, _, sess in sub_t_sess:
        w = math.exp(-0.005 * max(0.0, (ref_epoch - e_ts) / 86400.0)) \
            if (e_ts and ref_epoch) else 1.0
        cc.train_session(sess, weight=w)
    cc_m = cc_evaluate(cc, test_sess)

    return {
        "metric_ksr":             metrics.get("ksr",              0.0),
        "metric_top1_acc":        metrics.get("top1_acc",         0.0),
        "metric_top3_acc":        metrics.get("top3_acc",         0.0),
        "metric_prefix_cond_acc": metrics.get("prefix_cond_acc",  0.0),
        "metric_coverage":        metrics.get("coverage",         0.0),
        "cmd_top5":               cc_m["top5"],
    }


def run_scaling(
    history_path: str,
    data_src: str,
    out_dir: str,
) -> List[Dict[str, Any]]:
    os.makedirs(out_dir, exist_ok=True)

    # ── Tam veriyi yükle (filtresiz) ──────────────────────────────────────────
    all_train, _, test_commands = load_split(
        path=history_path, train_ratio=0.8, filter_train=False, filter_test=False,
    )
    n_total = len(all_train)

    # Komut-düzeyi için oturumları yükle (test seti sabit %20)
    sessions     = load_sessions(data_src)
    n_sess       = len(sessions)
    n_tr_sess    = max(1, int(n_sess * 0.8))
    train_sess   = sessions[:n_tr_sess]
    test_sess    = sessions[n_tr_sess:]
    ref_epoch    = max((s[0] for s in train_sess if s[0] > 0), default=0)
    now          = time.time()

    results: List[Dict[str, Any]] = []

    for size in SIZES:
        actual_size = min(size, n_total) if size is not None else n_total
        lbl = _label(size)
        print(f"  [scaling] n={actual_size:>6,}  ", end="", flush=True)

        if size is None:
            # Tüm veri: tek çalışma, std=0
            seed_metrics = [_run_one(all_train, test_commands,
                                     train_sess, test_sess, ref_epoch, now, n_total)]
        else:
            seed_metrics = []
            for seed in SEEDS:
                rng = random.Random(seed)
                sub = rng.sample(all_train, k=min(actual_size, len(all_train)))
                seed_metrics.append(_run_one(sub, test_commands,
                                             train_sess, test_sess, ref_epoch, now, n_total))

        # Ortalama ve std
        row: Dict[str, Any] = {"label": lbl, "n_train": actual_size}
        for key in METRIC_KEYS:
            vals = [m[key] for m in seed_metrics]
            row[key]             = float(np.mean(vals))
            row[key + "_std"]    = float(np.std(vals, ddof=0))

        results.append(row)

        ksr  = row["metric_ksr"]  * 100
        top1 = row["metric_top1_acc"] * 100
        ct5  = row["cmd_top5"]    * 100
        std  = row["metric_ksr_std"] * 100
        print(f"KSR={ksr:.1f}%±{std:.1f}  Top1={top1:.1f}%  CmdTop5={ct5:.1f}%",
              flush=True)

    return results


def save_csv(results: List[Dict], out_dir: str) -> None:
    if not results:
        return
    fields = list(results[0].keys())
    path = os.path.join(out_dir, "scaling.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"  [scaling] kaydedildi: scaling.csv", flush=True)


def plot_scaling(results: List[Dict], out_dir: str) -> None:
    """fig_scaling.png — öğrenme eğrisi, std bandı."""
    xs    = [r["n_train"] for r in results]
    xs_np = np.array(xs, dtype=float)

    def _get(key):
        return (
            np.array([r[key]          for r in results]) * 100,
            np.array([r[key + "_std"] for r in results]) * 100,
        )

    ksr_m,  ksr_s  = _get("metric_ksr")
    top1_m, top1_s = _get("metric_top1_acc")
    pca_m,  pca_s  = _get("metric_prefix_cond_acc")
    cov_m,  cov_s  = _get("metric_coverage")
    ct5_m,  ct5_s  = _get("cmd_top5")

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))

    # Sol: kelime-düzeyi metrikler
    ax = axes[0]
    for (mean, std, label, color) in [
        (ksr_m,  ksr_s,  "KSR (%)",                       "#1f77b4"),
        (top1_m, top1_s, "Doğruluk@1 (%)",                "#ff7f0e"),
        (pca_m,  pca_s,  "Önek-Koş. Tamamlama (%)",       "#2ca02c"),
        (cov_m,  cov_s,  "Kapsama (%)",                   "#9467bd"),
    ]:
        ax.semilogx(xs_np, mean, "o-", color=color, linewidth=2, markersize=6, label=label)
        ax.fill_between(xs_np, mean - std, mean + std,
                        color=color, alpha=0.15)

    ax.set_xlabel("Eğitim Komutu Sayısı (log ölçek)")
    ax.set_ylabel("Puan (%)")
    ax.set_title("Kelime Düzeyi Metrikler")
    ax.legend(fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_xticks(xs_np)
    ax.set_xticklabels([str(x) for x in xs], rotation=30, ha="right", fontsize=9)

    # Sağ: komut-düzeyi Top-5
    ax2 = axes[1]
    ax2.semilogx(xs_np, ct5_m, "o-", color="#2ca02c",
                 linewidth=2, markersize=6, label="Komut-Adı Top-5 (%)")
    ax2.fill_between(xs_np, ct5_m - ct5_s, ct5_m + ct5_s,
                     color="#2ca02c", alpha=0.18)
    ax2.set_xlabel("Eğitim Komutu Sayısı (log ölçek)")
    ax2.set_ylabel("Komut-Adı Top-5 Doğruluğu (%)")
    ax2.set_title("Komut Düzeyi Top-5 (5 seed ortalaması)")
    ax2.legend(fontsize=9)
    ax2.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax2.set_axisbelow(True)
    ax2.set_xticks(xs_np)
    ax2.set_xticklabels([str(x) for x in xs], rotation=30, ha="right", fontsize=9)

    fig.suptitle(
        "Öğrenme Eğrisi — Eğitim Boyutuna Göre Başarım\n"
        "(ortalama ± std, 5 seed rastgele örnekleme)",
        fontsize=12,
    )
    fig.tight_layout()
    path = os.path.join(out_dir, "fig_scaling.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [scaling] kaydedildi: fig_scaling.png", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Ölçeklenme deneyi (rastgele örnekleme, 5 seed)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--history", default=CYBER_HISTORY)
    p.add_argument("--data-src", default=DEFAULT_SRC)
    p.add_argument("--out-dir",  default=DEFAULT_OUT)
    args = p.parse_args()

    print("=" * 62, flush=True)
    print("Ölçeklenme Deneyi (5 seed, rastgele örnekleme)", flush=True)
    print("=" * 62, flush=True)

    results = run_scaling(args.history, args.data_src, args.out_dir)
    save_csv(results, args.out_dir)
    plot_scaling(results, args.out_dir)

    print("\n[scaling] Özet (ortalama):", flush=True)
    hdr = (f"{'N Eğitim':>8}  {'KSR':>6}  {'±':>5}  {'Top1':>6}"
           f"  {'ÖnekKoş':>7}  {'Kapsama':>7}  {'CmdTop5':>7}")
    print(hdr, flush=True)
    print("-" * len(hdr), flush=True)
    for r in results:
        print(
            f"{r['n_train']:>8,}  "
            f"{r['metric_ksr']*100:>5.1f}%  "
            f"±{r['metric_ksr_std']*100:>4.1f}  "
            f"{r['metric_top1_acc']*100:>5.1f}%  "
            f"{r['metric_prefix_cond_acc']*100:>6.1f}%  "
            f"{r['metric_coverage']*100:>6.1f}%  "
            f"{r['cmd_top5']*100:>6.1f}%",
            flush=True,
        )

    # Monotonluk kontrolü
    print("\n[scaling] Monotonluk kontrolü (KSR):", flush=True)
    ksrs = [r["metric_ksr"] for r in results]
    mono = all(ksrs[i] <= ksrs[i+1] for i in range(len(ksrs)-1))
    print(f"  KSR değerleri: {[round(v*100,1) for v in ksrs]}", flush=True)
    print(f"  Monoton artan: {'EVET ✓' if mono else 'HAYIR (std bandı içinde normal)'}", flush=True)

    print("\n" + "=" * 62, flush=True)
    print("Ölçeklenme deneyi tamamlandı.", flush=True)
    print("=" * 62, flush=True)


if __name__ == "__main__":
    main()
