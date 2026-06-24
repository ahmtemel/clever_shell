"""
compare.py – İki run_eval sonucunu karşılaştıran rapor üreticisi.

Kullanım:
    python3 python/eval/compare.py \\
        --dir-a python/eval/results_self   --label-a "Kendi Geçmişim" \\
        --dir-b python/eval/results_cyber  --label-b "Siber-Güvenlik Seti" \\
        --out   python/eval/results_compare

Üretilen dosyalar (results_compare/):
    comparison.csv               – Türkçe başlıklı metrik karşılaştırma CSV
    comparison.md                – Tablo 4.X Markdown
    fig_compare.png              – Gruplu bar chart
    decay_ablation.csv           – λ ablasyon karşılaştırma CSV
    decay_ablation.md            – Tablo 4.X Markdown
    COMPARE_REPORT.md            – Tüm tabloları ve şekil referanslarını içeren özet
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── matplotlib global ayarları ────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":     "serif",
    "font.size":       11,
    "axes.titlesize":  12,
    "axes.labelsize":  11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "figure.dpi":      150,
    "savefig.dpi":     150,
})

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ── CSV okuma yardımcısı ───────────────────────────────────────────────────────

def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _proposed_row(csv_path: str) -> Optional[Dict[str, Any]]:
    """CSV'den 'proposed' satırını bul ve sayısal değerlere çevir."""
    rows = _read_csv(csv_path)
    for r in rows:
        if "proposed" in r.get("name", "").lower():
            return {k: _to_float(v) for k, v in r.items()}
    # Bulunamazsa ilk satır
    if rows:
        return {k: _to_float(v) for k, v in rows[0].items()}
    return None


def _to_float(v: str) -> Any:
    try:
        return float(v)
    except (ValueError, TypeError):
        return v


def _decay_rows(csv_path: str) -> List[Dict[str, Any]]:
    """λ ablasyon satırlarını döndür (group==decay veya proposed)."""
    rows = _read_csv(csv_path)
    result = []
    for r in rows:
        group = r.get("group", "")
        if group in ("decay", "proposed"):
            result.append({k: _to_float(v) for k, v in r.items()})
    return sorted(result, key=lambda r: float(r.get("decay", 0) or 0))


# ── Karşılaştırma metrikleri ──────────────────────────────────────────────────

# (csv_key, Türkçe etiket, biçim)
METRIC_DEFS = [
    ("metric_ksr",             "Tuş Tasarrufu Oranı (KSR %)",           "pct"),
    ("metric_top1_acc",        "Doğruluk@1 (%)",                        "pct"),
    ("metric_top3_acc",        "Doğruluk@3 (%)",                        "pct"),
    ("metric_prefix_cond_acc", "Önek-Koşullu Tamamlama Doğ. (≥2 kar.%)", "pct"),
    ("metric_topk_cmd_acc",    "Top-5 Komut Kabul Oranı (%)",           "pct"),
    ("metric_coverage",        "Kapsama (%)",                           "pct"),
    ("lat_p99_ms",             "Gecikme p99 (ms)",                      "f3"),
]


def _fmt(v: Any, fmt: str) -> str:
    if not isinstance(v, float):
        return str(v)
    if fmt == "pct":
        return f"{v * 100:.1f}"
    if fmt == "f3":
        return f"{v:.3f}"
    return str(v)


# ── CSV kaydetme ──────────────────────────────────────────────────────────────

def save_comparison_csv(
    row_a: Dict,
    row_b: Dict,
    label_a: str,
    label_b: str,
    path: str,
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Metrik", label_a, label_b])
        for key, label, fmt in METRIC_DEFS:
            va = row_a.get(key, "")
            vb = row_b.get(key, "")
            writer.writerow([label, _fmt(va, fmt), _fmt(vb, fmt)])
    print(f"  [compare] kaydedildi: {os.path.basename(path)}", flush=True)


def save_decay_csv(
    rows_a: List[Dict],
    rows_b: List[Dict],
    label_a: str,
    label_b: str,
    path: str,
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "λ",
            f"KSR — {label_a} (%)",
            f"Doğruluk@1 — {label_a} (%)",
            f"KSR — {label_b} (%)",
            f"Doğruluk@1 — {label_b} (%)",
        ])
        decays = sorted(set(
            [float(r.get("decay", 0) or 0) for r in rows_a] +
            [float(r.get("decay", 0) or 0) for r in rows_b]
        ))
        by_decay_a = {float(r.get("decay", 0) or 0): r for r in rows_a}
        by_decay_b = {float(r.get("decay", 0) or 0): r for r in rows_b}
        for d in decays:
            ra = by_decay_a.get(d, {})
            rb = by_decay_b.get(d, {})
            writer.writerow([
                d,
                _fmt(ra.get("metric_ksr", ""),   "pct"),
                _fmt(ra.get("metric_top1_acc", ""), "pct"),
                _fmt(rb.get("metric_ksr", ""),   "pct"),
                _fmt(rb.get("metric_top1_acc", ""), "pct"),
            ])
    print(f"  [compare] kaydedildi: {os.path.basename(path)}", flush=True)


# ── Şekil 4.X – Karşılaştırma bar chart ──────────────────────────────────────

def plot_comparison(
    row_a: Dict,
    row_b: Dict,
    label_a: str,
    label_b: str,
    out_dir: str,
) -> None:
    """
    Şekil 4.5 – Veri seti karşılaştırması: önerilen modelin her iki korpustaki
    performansı (gruplu yatay bar chart).
    """
    metric_labels = [
        "KSR (%)",
        "Doğruluk@1 (%)",
        "Doğruluk@3 (%)",
        "Önek-Koş. (%)",
        "Top-5 Komut (%)",
        "Kapsama (%)",
    ]
    keys = [
        "metric_ksr",
        "metric_top1_acc",
        "metric_top3_acc",
        "metric_prefix_cond_acc",
        "metric_topk_cmd_acc",
        "metric_coverage",
    ]
    vals_a = np.array([float(row_a.get(k, 0) or 0) * 100 for k in keys])
    vals_b = np.array([float(row_b.get(k, 0) or 0) * 100 for k in keys])

    x = np.arange(len(metric_labels))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.bar(x - w/2, vals_a, w, label=label_a, color="#4c72b0", alpha=0.88)
    ax.bar(x + w/2, vals_b, w, label=label_b, color="#55a868", alpha=0.88)
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, fontsize=10)
    ax.set_ylabel("Puan (%)", fontsize=11)
    ax.set_xlabel("Metrik", fontsize=11)
    ax.legend(fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.45)
    ax.set_axisbelow(True)
    fig.tight_layout()
    path = os.path.join(out_dir, "fig_compare.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [compare] kaydedildi: {os.path.basename(path)}", flush=True)


def plot_decay_comparison(
    rows_a: List[Dict],
    rows_b: List[Dict],
    label_a: str,
    label_b: str,
    out_dir: str,
) -> None:
    """
    Şekil 4.6 – Zaman azalma katsayısı λ'ya göre KSR: iki veri seti karşılaştırması.
    Siber sette timestamp var olduğu için decay artık gerçek etki gösterebilir.
    """
    def _series(rows):
        rows_s = sorted(rows, key=lambda r: float(r.get("decay", 0) or 0))
        return (
            [float(r.get("decay", 0) or 0) for r in rows_s],
            [float(r.get("metric_ksr", 0) or 0) * 100 for r in rows_s],
            [float(r.get("metric_top1_acc", 0) or 0) * 100 for r in rows_s],
        )

    da, ksr_a, acc_a = _series(rows_a)
    db, ksr_b, acc_b = _series(rows_b)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
    for ax, decays, ksr, acc1, label, color in [
        (axes[0], da, ksr_a, acc_a, label_a, "#1f77b4"),
        (axes[1], db, ksr_b, acc_b, label_b, "#2ca02c"),
    ]:
        ax2 = ax.twinx()
        ax.plot(decays, ksr,  "o-",  color=color, linewidth=2,
                markersize=7, label="KSR")
        ax2.plot(decays, acc1, "s--", color="#d62728", linewidth=2,
                 markersize=7, label="Doğruluk@1")
        ax.set_xlabel("Zaman Azalma Katsayısı λ", fontsize=11)
        ax.set_ylabel("KSR (%)", color=color, fontsize=10)
        ax2.set_ylabel("Doğruluk@1 (%)", color="#d62728", fontsize=10)
        ax.tick_params(axis="y", labelcolor=color)
        ax2.tick_params(axis="y", labelcolor="#d62728")
        ax.set_title(label, fontsize=11)
        lines1, lbl1 = ax.get_legend_handles_labels()
        lines2, lbl2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, lbl1 + lbl2, loc="best", fontsize=8)
        ax.yaxis.grid(True, linestyle="--", alpha=0.35)
        ax.set_axisbelow(True)
    fig.suptitle("Zaman Azalma Katsayısı λ — İki Veri Setinde Etkisi", fontsize=12)
    fig.tight_layout()
    path = os.path.join(out_dir, "fig_decay_compare.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [compare] kaydedildi: {os.path.basename(path)}", flush=True)


# ── COMPARE_REPORT.md ─────────────────────────────────────────────────────────

def write_compare_report(
    row_a: Dict,
    row_b: Dict,
    rows_decay_a: List[Dict],
    rows_decay_b: List[Dict],
    label_a: str,
    label_b: str,
    out_dir: str,
) -> None:
    lines: List[str] = [
        "# clever_shell — Veri Seti Karşılaştırma Raporu",
        "",
        f"**Veri seti A:** {label_a}  ",
        f"**Veri seti B:** {label_b}  ",
        "",
        "---",
        "",
        "## Tablo 4.3 — Veri Seti Karşılaştırması: Önerilen Modelin İki Korpustaki Başarımı",
        "",
        f"*Önerilen yapılandırma (k=3, λ=0,005, geri-alma etkin). "
        f"Satırlar: metrikler. Sütunlar: veri seti.*",
        "",
        f"| Metrik | {label_a} | {label_b} |",
        "|--------|" + "------:|" * 2,
    ]
    for key, label, fmt in METRIC_DEFS:
        va = row_a.get(key, "")
        vb = row_b.get(key, "")
        lines.append(f"| {label} | {_fmt(va, fmt)} | {_fmt(vb, fmt)} |")

    lines += [
        "",
        "---",
        "",
        "## Tablo 4.4 — Zaman Azalma (λ) Ablasyonu: İki Veri Setinde Karşılaştırma",
        "",
        "*Timestamp var olan siber sette λ artışı ile recency etkisinin gözlemlenmesi.*",
        "",
        f"| λ | KSR — {label_a} (%) | Doğruluk@1 — {label_a} (%) "
        f"| KSR — {label_b} (%) | Doğruluk@1 — {label_b} (%) |",
        "|--:|--------------------:|---------------------------:|"
        "--------------------:|---------------------------:|",
    ]
    decays = sorted(set(
        [float(r.get("decay", 0) or 0) for r in rows_decay_a] +
        [float(r.get("decay", 0) or 0) for r in rows_decay_b]
    ))
    by_a = {float(r.get("decay", 0) or 0): r for r in rows_decay_a}
    by_b = {float(r.get("decay", 0) or 0): r for r in rows_decay_b}
    for d in decays:
        ra = by_a.get(d, {})
        rb = by_b.get(d, {})
        mark_a = "**" if ra.get("proposed") else ""
        mark_b = "**" if rb.get("proposed") else ""
        lines.append(
            f"| {d} "
            f"| {mark_a}{_fmt(ra.get('metric_ksr',''), 'pct')}{mark_a} "
            f"| {mark_a}{_fmt(ra.get('metric_top1_acc',''), 'pct')}{mark_a} "
            f"| {mark_b}{_fmt(rb.get('metric_ksr',''), 'pct')}{mark_b} "
            f"| {mark_b}{_fmt(rb.get('metric_top1_acc',''), 'pct')}{mark_b} |"
        )

    # Bulgular
    ksr_a = float(row_a.get("metric_ksr", 0) or 0) * 100
    ksr_b = float(row_b.get("metric_ksr", 0) or 0) * 100
    acc_a = float(row_a.get("metric_top1_acc", 0) or 0) * 100
    acc_b = float(row_b.get("metric_top1_acc", 0) or 0) * 100
    pc_a  = float(row_a.get("metric_prefix_cond_acc", 0) or 0) * 100
    pc_b  = float(row_b.get("metric_prefix_cond_acc", 0) or 0) * 100
    top5_a = float(row_a.get("metric_topk_cmd_acc", 0) or 0) * 100
    top5_b = float(row_b.get("metric_topk_cmd_acc", 0) or 0) * 100

    # Decay etki analizi
    decay_ksr_a = {float(r.get("decay", 0) or 0): float(r.get("metric_ksr", 0) or 0)*100
                   for r in rows_decay_a}
    decay_ksr_b = {float(r.get("decay", 0) or 0): float(r.get("metric_ksr", 0) or 0)*100
                   for r in rows_decay_b}
    decay_effect_a = decay_ksr_a.get(0.0, 0) - decay_ksr_a.get(0.005, 0)
    decay_effect_b = decay_ksr_b.get(0.0, 0) - decay_ksr_b.get(0.005, 0)

    lines += [
        "",
        "---",
        "",
        "## Temel Bulgular",
        "",
        f"### KSR Karşılaştırması",
        f"- **{label_a}:** KSR = {ksr_a:.1f}%, Doğruluk@1 = {acc_a:.1f}%",
        f"- **{label_b}:** KSR = {ksr_b:.1f}%, Doğruluk@1 = {acc_b:.1f}%",
        f"- Fark: {ksr_b - ksr_a:+.1f}% KSR, {acc_b - acc_a:+.1f}% Doğruluk@1",
        "",
        f"### Önek-Koşullu Tamamlama ve Top-5 Komut",
        f"- **{label_a}:** Önek-Koşullu = {pc_a:.1f}%, Top-5 Komut = {top5_a:.1f}%",
        f"- **{label_b}:** Önek-Koşullu = {pc_b:.1f}%, Top-5 Komut = {top5_b:.1f}%",
        "",
        f"### Zaman Azalma (λ) Etkisi",
        f"- **{label_a}'nda** λ=0→0.005 KSR değişimi: {decay_effect_a:+.2f}% (küçük etki — eski zsh geçmişinde geniş zaman aralığı)",
        f"- **{label_b}'nde** λ=0→0.005 KSR değişimi: {decay_effect_b:+.2f}% "
        f"({'timestamp mevcut — decay gerçek etki gösteriyor' if abs(decay_effect_b) > 0.1 else 'küçük etki'})",
        "",
        "---",
        "",
        "## Şekiller",
        "",
        "| Şekil No | Dosya | Açıklama (başlık ALTTA) |",
        "|----------|-------|-------------------------|",
        "| Şekil 4.5 | `fig_compare.png` | "
        "Önerilen modelin iki veri setindeki performans karşılaştırması (gruplu bar chart). |",
        "| Şekil 4.6 | `fig_decay_compare.png` | "
        "Zaman azalma katsayısı λ'nın iki veri setindeki etkisi. |",
        "",
        "---",
        "",
        "*`python3 python/eval/compare.py` tarafından otomatik üretilmiştir.*",
    ]

    path = os.path.join(out_dir, "COMPARE_REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [compare] kaydedildi: COMPARE_REPORT.md", flush=True)


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def compare(
    dir_a: str,
    dir_b: str,
    label_a: str,
    label_b: str,
    out_dir: str,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    csv_a = os.path.join(dir_a, "metrics_summary.csv")
    csv_b = os.path.join(dir_b, "metrics_summary.csv")

    for p in (csv_a, csv_b):
        if not os.path.isfile(p):
            print(f"[compare] HATA: bulunamadı: {p}", flush=True)
            sys.exit(1)

    row_a        = _proposed_row(csv_a) or {}
    row_b        = _proposed_row(csv_b) or {}
    decay_rows_a = _decay_rows(csv_a)
    decay_rows_b = _decay_rows(csv_b)

    save_comparison_csv(row_a, row_b, label_a, label_b,
                        os.path.join(out_dir, "comparison.csv"))
    save_decay_csv(decay_rows_a, decay_rows_b, label_a, label_b,
                   os.path.join(out_dir, "decay_ablation.csv"))
    plot_comparison(row_a, row_b, label_a, label_b, out_dir)
    plot_decay_comparison(decay_rows_a, decay_rows_b, label_a, label_b, out_dir)
    write_compare_report(row_a, row_b, decay_rows_a, decay_rows_b,
                         label_a, label_b, out_dir)


def main() -> None:
    eval_dir = os.path.dirname(__file__)
    p = argparse.ArgumentParser(
        description="İki run_eval sonucunu karşılaştır",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--dir-a",   default=os.path.join(eval_dir, "results_self"),
                   help="İlk run_eval çıktı dizini")
    p.add_argument("--dir-b",   default=os.path.join(eval_dir, "results_cyber"),
                   help="İkinci run_eval çıktı dizini")
    p.add_argument("--label-a", default="Kendi Geçmişim")
    p.add_argument("--label-b", default="Siber-Güvenlik Seti")
    p.add_argument("--out",     default=os.path.join(eval_dir, "results_compare"),
                   help="Karşılaştırma çıktı dizini")
    args = p.parse_args()
    compare(args.dir_a, args.dir_b, args.label_a, args.label_b, args.out)
    print("\n[compare] Karşılaştırma tamamlandı.", flush=True)


if __name__ == "__main__":
    main()
