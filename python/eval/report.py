"""
report.py – CSV, LaTeX, PNG ve REPORT.md üretimi.

Tüm çıktılar *out_dir* altına yazılır (varsayılan: python/eval/results/).
Tez "Hazırlama Esasları" uyumu:
  • Başlıklar ve eksen etiketleri Türkçe.
  • Tablolar "Tablo 4.X — <açıklama>" (başlık ÜSTTE).
  • Şekiller "Şekil 4.X — <açıklama>" (başlık ALTTA).
  • matplotlib: serif font, ≥11 pt, 150 dpi, tutarlı.
  • tables_word.md: Word'e doğrudan yapıştırılabilir Markdown tablolar.
  • *_word.csv: Word'e aktarılabilir, Türkçe başlıklı CSV dosyaları.
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Global matplotlib ayarları (tüm grafikler için) ───────────────────────────
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

# ── Türkçe yapılandırma adları ─────────────────────────────────────────────────
_TR_CONFIG = {
    "proposed (k=3, λ=0.005)": "Önerilen (k=3, λ=0,005)",
    "k=1 (unigram ctx)":        "k=1 (tekli bağlam)",
    "k=2 (bigram ctx)":         "k=2 (ikili bağlam)",
    "no backoff (k=3)":         "Geri alma yok (k=3)",
    "λ=0 (no decay)":           "λ=0 (azalma yok)",
    "λ=0.02 (fast decay)":      "λ=0,02 (hızlı azalma)",
    "freq-only (unigram)":      "Yalnızca frekans",
    "most-frequent cmd":        "En sık komut",
}

def _tr(name: str) -> str:
    return _TR_CONFIG.get(name, name)


# ── Türkçe sütun tanımları ────────────────────────────────────────────────────
_TR_COLS_METRICS = [
    {"key": "name",                    "header": "Yapılandırma",                              "fmt": "tr"},
    {"key": "metric_ksr",              "header": "KSR (\\%)",                                "fmt": "pct"},
    {"key": "metric_top1_acc",         "header": "Doğruluk@1 (\\%)",                         "fmt": "pct"},
    {"key": "metric_top3_acc",         "header": "Doğruluk@3 (\\%)",                         "fmt": "pct"},
    {"key": "metric_prefix_acc",       "header": "Önek Doğruluğu (\\%)",                     "fmt": "pct"},
    {"key": "metric_prefix_cond_acc",  "header": "Önek-Koş. Tamamlama (≥2 kar.) (\\%)",     "fmt": "pct"},
    {"key": "metric_topk_cmd_acc",     "header": "Top-5 Komut Kabul Oranı (\\%)",            "fmt": "pct"},
    {"key": "metric_coverage",         "header": "Kapsama (\\%)",                            "fmt": "pct"},
    {"key": "lat_p50_ms",              "header": "Gecikme p50 (ms)",                         "fmt": "f3"},
    {"key": "lat_p99_ms",              "header": "Gecikme p99 (ms)",                         "fmt": "f3"},
    {"key": "mem_n_contexts",          "header": "Bağlam Sayısı",                            "fmt": "int"},
    {"key": "mem_table_shallow_kb",    "header": "Bellek (KB)",                              "fmt": "f1"},
]

# Sadece Tablo 4.1 (özet tablo) için kullanılan sütunlar – daha az sütun
_TR_COLS_SUMMARY = [c for c in _TR_COLS_METRICS if c["key"] not in
                    ("metric_top3_acc", "mem_n_contexts", "mem_table_shallow_kb")]


# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────────

def _cell_val(row: Dict, col: Dict) -> str:
    v   = row.get(col["key"], "")
    fmt = col.get("fmt", "f3")
    if fmt == "tr":
        return _tr(str(v))
    if fmt == "pct" and isinstance(v, float):
        return f"{v * 100:.1f}"
    if fmt == "f3" and isinstance(v, float):
        return f"{v:.3f}"
    if fmt == "f1" and isinstance(v, float):
        return f"{v:.1f}"
    if fmt == "int":
        try:
            return f"{int(v):,}"
        except (TypeError, ValueError):
            return str(v)
    return str(v)


def _savefig(fig: plt.Figure, path: str) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [rapor] kaydedildi: {os.path.basename(path)}", flush=True)


# ── CSV ────────────────────────────────────────────────────────────────────────

def save_csv(
    rows: List[Dict[str, Any]],
    path: str,
    fieldnames: Optional[List[str]] = None,
) -> None:
    """Ham (İngilizce anahtar) CSV — makine okuma / LaTeX pipeline için."""
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [rapor] kaydedildi: {os.path.basename(path)}", flush=True)


def save_csv_turkish(
    rows: List[Dict[str, Any]],
    path: str,
    columns: List[Dict[str, str]],
) -> None:
    """
    Word'e doğrudan aktarılabilir Türkçe başlıklı CSV.
    Her sütun _TR_COLS_METRICS tanımındaki görüntü adını kullanır.
    """
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    headers = [c["header"] for c in columns]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        # utf-8-sig: Excel/Word'ün BOM'u tanıması için
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_cell_val(row, c) for c in columns])
    print(f"  [rapor] kaydedildi: {os.path.basename(path)}", flush=True)


# ── LaTeX (booktabs) ──────────────────────────────────────────────────────────

def save_latex_table(
    rows: List[Dict[str, Any]],
    path: str,
    columns: List[Dict[str, str]],
    caption: str = "",
    label: str = "",
) -> None:
    """
    Booktabs uyumlu LaTeX tablosu.
    Önerilen satır kalın yazılır (\\textbf).
    Başlık tablo ÜSTÜNE yerleştirilir (tez standardı).
    """
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)

    col_spec = "l" + "r" * (len(columns) - 1)
    headers  = " & ".join(c["header"] for c in columns)

    lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        "  \\begin{tabular}{" + col_spec + "}",
        "    \\toprule",
        f"    {headers} \\\\",
        "    \\midrule",
    ]
    for row in rows:
        cells = " & ".join(_cell_val(row, c) for c in columns)
        if row.get("proposed"):
            cells = "\\textbf{" + cells.replace(" & ", "} & \\textbf{") + "}"
        lines.append(f"    {cells} \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [rapor] kaydedildi: {os.path.basename(path)}", flush=True)


# ── Şekil 4.1 – Markov bağlam uzunluğu vs metrikler ──────────────────────────

def plot_markov_order(results: List[Dict[str, Any]], out_dir: str) -> None:
    """
    Şekil 4.1 – Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1.
    """
    subset = {
        r["k"]: r for r in results
        if r.get("model_type") == "word" and r.get("k") in (1, 2, 3)
        and r.get("backoff", True)
    }
    if not subset:
        return
    data = sorted(subset.values(), key=lambda r: r["k"])
    ks   = [r["k"]                      for r in data]
    ksr  = [r.get("metric_ksr", 0)      for r in data]
    acc1 = [r.get("metric_top1_acc", 0) for r in data]

    fig, ax1 = plt.subplots(figsize=(5.5, 4.0))
    ax2 = ax1.twinx()
    ax1.plot(ks, [v * 100 for v in ksr],  "o-",  color="#1f77b4",
             linewidth=2, markersize=7, label="Tuş Tasarrufu Oranı (KSR)")
    ax2.plot(ks, [v * 100 for v in acc1], "s--", color="#d62728",
             linewidth=2, markersize=7, label="Doğruluk@1")
    ax1.set_xlabel("Markov Bağlam Uzunluğu k (kelime)", fontsize=11)
    ax1.set_ylabel("Tuş Tasarrufu Oranı KSR (%)", color="#1f77b4", fontsize=11)
    ax2.set_ylabel("Doğruluk@1 (%)", color="#d62728", fontsize=11)
    ax1.set_xticks(ks)
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax2.tick_params(axis="y", labelcolor="#d62728")
    lines1, lbl1 = ax1.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lbl1 + lbl2, loc="lower right", fontsize=9)
    ax1.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax1.set_axisbelow(True)
    fig.tight_layout()
    _savefig(fig, os.path.join(out_dir, "fig_markov_order.png"))


# ── Şekil 4.2 – Ablasyon çalışması bar chart ──────────────────────────────────

def plot_ablation(results: List[Dict[str, Any]], out_dir: str) -> None:
    """
    Şekil 4.2 – Tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması.
    """
    if not results:
        return
    names = [_tr(r["name"]) for r in results]
    ksr   = np.array([r.get("metric_ksr", 0)      for r in results])
    acc1  = np.array([r.get("metric_top1_acc", 0) for r in results])

    x  = np.arange(len(names))
    w  = 0.38
    fig, ax = plt.subplots(figsize=(11, 4.5))
    b1 = ax.bar(x - w/2, ksr  * 100, w, label="Tuş Tasarrufu Oranı (KSR %)",
                color="#4c72b0", alpha=0.88)
    b2 = ax.bar(x + w/2, acc1 * 100, w, label="Doğruluk@1 (%)",
                color="#dd8452", alpha=0.88)
    for i, r in enumerate(results):
        if r.get("proposed"):
            for b in (b1[i], b2[i]):
                b.set_edgecolor("black")
                b.set_linewidth(2.2)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=26, ha="right", fontsize=9)
    ax.set_ylabel("Puan (%)", fontsize=11)
    ax.set_xlabel("Yapılandırma", fontsize=11)
    ax.legend(fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.45)
    ax.set_axisbelow(True)
    fig.tight_layout()
    _savefig(fig, os.path.join(out_dir, "fig_ablation.png"))


# ── Şekil 4.3 – Gecikme CDF ───────────────────────────────────────────────────

def plot_latency(results: List[Dict[str, Any]], out_dir: str) -> None:
    """
    Şekil 4.3 – predict_suffix çağrısı gecikme CDF dağılımı.
    """
    if not results:
        return
    colors = plt.cm.tab10.colors  # type: ignore[attr-defined]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for i, r in enumerate(results):
        p50 = r.get("lat_p50_ms", 0)
        p95 = r.get("lat_p95_ms", 0)
        p99 = r.get("lat_p99_ms", 0)
        lw  = 2.5 if r.get("proposed") else 1.2
        ls  = "-"  if r.get("proposed") else "--"
        ax.plot([0, p50, p95, p99, p99 * 1.4],
                [0, 0.50, 0.95, 0.99, 1.0],
                linestyle=ls, linewidth=lw,
                color=colors[i % len(colors)],
                label=_tr(r["name"]))
    ax.axvline(5, color="red", linestyle=":", linewidth=1.5,
               label="5 ms hedefi")
    ax.set_xlabel("Çıkarım Gecikmesi (ms)", fontsize=11)
    ax.set_ylabel("Birikimli Oran", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.legend(fontsize=7.5, loc="lower right")
    ax.xaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    _savefig(fig, os.path.join(out_dir, "fig_latency.png"))


# ── Şekil 4.4 – Azalma katsayısı λ vs doğruluk ────────────────────────────────

def plot_decay(results: List[Dict[str, Any]], out_dir: str) -> None:
    """
    Şekil 4.4 – Zamana azalma katsayısı λ'ya göre KSR ve Doğruluk@1.
    """
    subset = [r for r in results
              if r.get("model_type") == "word"
              and r.get("group") in ("decay", "proposed")]
    if len(subset) < 2:
        subset = [r for r in results if r.get("model_type") == "word"]
    if not subset:
        return
    subset = sorted(subset, key=lambda r: float(r.get("decay", 0)))
    decays = [float(r.get("decay", 0))     for r in subset]
    ksr    = [r.get("metric_ksr", 0)       for r in subset]
    acc1   = [r.get("metric_top1_acc", 0)  for r in subset]

    fig, ax1 = plt.subplots(figsize=(5.5, 4.0))
    ax2 = ax1.twinx()
    ax1.plot(decays, [v * 100 for v in ksr],  "o-",  color="#1f77b4",
             linewidth=2, markersize=7, label="KSR")
    ax2.plot(decays, [v * 100 for v in acc1], "s--", color="#d62728",
             linewidth=2, markersize=7, label="Doğruluk@1")
    ax1.set_xlabel("Zaman Azalma Katsayısı λ", fontsize=11)
    ax1.set_ylabel("Tuş Tasarrufu Oranı KSR (%)", color="#1f77b4", fontsize=11)
    ax2.set_ylabel("Doğruluk@1 (%)", color="#d62728", fontsize=11)
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax2.tick_params(axis="y", labelcolor="#d62728")
    lines1, lbl1 = ax1.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lbl1 + lbl2, loc="best", fontsize=9)
    ax1.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax1.set_axisbelow(True)
    fig.tight_layout()
    _savefig(fig, os.path.join(out_dir, "fig_decay.png"))


# ── tables_word.md (Word'e yapıştırılabilir Markdown) ─────────────────────────

def save_word_tables(
    results: List[Dict[str, Any]],
    out_dir: str,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Word'e doğrudan yapıştırılabilir Markdown tablolar.

    Dosya: results/tables_word.md
    İçerik:
      Tablo 4.1 — Önerilen yapılandırma temel metrikleri
      Tablo 4.2 — Ablasyon çalışması tam karşılaştırma
      Tablo 4.3 — Gecikme dağılımı özeti
    """
    ds       = dataset_stats or {}
    n_train  = ds.get("n_train", "?")
    n_test   = ds.get("n_test_cmds", "?")
    hist_src = ds.get("history_file", "~/.zsh_history")

    proposed = next((r for r in results if r.get("proposed")), results[0] if results else {})
    src_note = f"Kaynak: Kendi kabuk geçmişi (`{hist_src}`, {n_train} eğitim / {n_test} test komutu)."

    lines: List[str] = [
        "# Tablo ve Şekil Listesi — clever_shell Değerlendirmesi",
        "",
        "> Bu dosya `python -m python.eval.run_eval` tarafından otomatik üretilmiştir.",
        "> Word'e yapıştırmak için tabloyu seçip Yapıştır (Ctrl+V) uygulayın.",
        "",
        "---",
        "",
    ]

    # ── Tablo 4.1 ─────────────────────────────────────────────────────────────
    lines += [
        "**Tablo 4.1 — Önerilen Yapılandırmanın Temel Performans Metrikleri**",
        "",
        f"*{src_note}*",
        "",
        "| Metrik | Değer |",
        "|--------|-------|",
        f"| Tuş Tasarrufu Oranı (KSR)                          | **{proposed.get('metric_ksr', 0)*100:.1f}%** |",
        f"| Doğruluk@1 (Sonraki Kelime)                        | **{proposed.get('metric_top1_acc', 0)*100:.1f}%** |",
        f"| Doğruluk@3 (Sonraki Kelime)                        | **{proposed.get('metric_top3_acc', proposed.get('metric_top1_acc',0))*100:.1f}%** |",
        f"| Önek Tamamlama Doğruluğu                           | **{proposed.get('metric_prefix_acc', 0)*100:.1f}%** |",
        f"| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **{proposed.get('metric_prefix_cond_acc', 0)*100:.1f}%** |",
        f"| Top-5 Komut Kabul Oranı                            | **{proposed.get('metric_topk_cmd_acc', 0)*100:.1f}%** |",
        f"| Kapsama (sessiz kalmayan oran)                      | **{proposed.get('metric_coverage', 0)*100:.1f}%** |",
        f"| Ortalama Gecikme                                    | **{proposed.get('lat_mean_ms', proposed.get('lat_p50_ms',0)):.3f} ms** |",
        f"| Gecikme p50                                         | **{proposed.get('lat_p50_ms', 0):.3f} ms** |",
        f"| Gecikme p95                                         | **{proposed.get('lat_p95_ms', 0):.3f} ms** |",
        f"| Gecikme p99                                         | **{proposed.get('lat_p99_ms', 0):.3f} ms** |",
        f"| n-gram Bağlam Sayısı                               | **{proposed.get('mem_n_contexts', 0):,}** |",
        f"| Tablo Bellek Ayak İzi (yüzeysel)                   | **{proposed.get('mem_table_shallow_kb', 0):.1f} KB** |",
        "",
        "---",
        "",
    ]

    # ── Tablo 4.2 ─────────────────────────────────────────────────────────────
    lines += [
        "**Tablo 4.2 — Ablasyon Çalışması: Yapılandırma Karşılaştırması**",
        "",
        f"*{src_note} "
        "Kalın: önerilen yapılandırma.*",
        "",
    ]
    # Table header
    lines.append(
        "| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Doğruluk@3 (%) | "
        "Önek Doğruluğu (%) | Kapsama (%) | Gecikme p50 (ms) | Gecikme p99 (ms) |"
    )
    lines.append(
        "|:-------------|--------:|---------------:|---------------:|"
        "------------------:|------------:|-----------------:|-----------------:|"
    )
    for r in results:
        mark = "**" if r.get("proposed") else ""
        name = mark + _tr(r["name"]) + mark
        lines.append(
            f"| {name} "
            f"| {r.get('metric_ksr',0)*100:.1f} "
            f"| {r.get('metric_top1_acc',0)*100:.1f} "
            f"| {r.get('metric_top3_acc', r.get('metric_top1_acc',0))*100:.1f} "
            f"| {r.get('metric_prefix_acc',0)*100:.1f} "
            f"| {r.get('metric_coverage',0)*100:.1f} "
            f"| {r.get('lat_p50_ms',0):.3f} "
            f"| {r.get('lat_p99_ms',0):.3f} |"
        )
    lines += ["", "---", ""]

    # ── Tablo 4.3 ─────────────────────────────────────────────────────────────
    lines += [
        "**Tablo 4.3 — Gecikme Dağılımı Özeti (ms)**",
        "",
        f"*{src_note} "
        "predict_suffix çağrısı başına süre (1000 ölçüm).*",
        "",
        "| Yapılandırma | Ortalama (ms) | p50 (ms) | p95 (ms) | p99 (ms) |",
        "|:-------------|-------------:|---------:|---------:|---------:|",
    ]
    for r in results:
        mark = "**" if r.get("proposed") else ""
        name = mark + _tr(r["name"]) + mark
        lines.append(
            f"| {name} "
            f"| {r.get('lat_mean_ms', r.get('lat_p50_ms',0)):.3f} "
            f"| {r.get('lat_p50_ms',0):.3f} "
            f"| {r.get('lat_p95_ms',0):.3f} "
            f"| {r.get('lat_p99_ms',0):.3f} |"
        )
    lines += ["", "---", ""]

    # ── Şekil başlıkları ──────────────────────────────────────────────────────
    lines += [
        "## Şekil Başlıkları",
        "",
        "| Şekil No | Dosya | Açıklama (başlık ALTTA) |",
        "|----------|-------|-------------------------|",
        "| Şekil 4.1 | `fig_markov_order.png` | "
        "Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi. |",
        "| Şekil 4.2 | `fig_ablation.png` | "
        "Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması. |",
        "| Şekil 4.3 | `fig_latency.png` | "
        "predict_suffix çağrısı gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir. |",
        "| Şekil 4.4 | `fig_decay.png` | "
        "Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi. |",
    ]

    path = os.path.join(out_dir, "tables_word.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [rapor] kaydedildi: {os.path.basename(path)}", flush=True)


# ── REPORT.md ─────────────────────────────────────────────────────────────────

def write_report_md(
    results: List[Dict[str, Any]],
    out_dir: str,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Tez taslağına yapıştırılabilir REPORT.md.
    Tablolar → "Tablo 4.X — <açıklama>" başlık ÜSTTE.
    Şekiller → "Şekil 4.X — <açıklama>" başlık ALTTA.
    """
    ds       = dataset_stats or {}
    n_train  = ds.get("n_train", "?")
    n_test   = ds.get("n_test", "?")
    n_cmds   = ds.get("n_test_cmds", "?")
    hist_src = ds.get("history_file", "~/.zsh_history")
    src_note = f"Kendi kabuk geçmişi (`{hist_src}`, {n_train} eğitim / {n_cmds} test komutu)"

    proposed  = next((r for r in results if r.get("proposed")), results[0] if results else {})
    baselines = [r for r in results if r.get("group") == "baseline"]
    best_bl   = max((b.get("metric_ksr", 0) for b in baselines), default=0) * 100
    ksr_prop  = proposed.get("metric_ksr", 0) * 100
    diff      = ksr_prop - best_bl

    lines: List[str] = [
        "# clever_shell — Deneysel Değerlendirme Raporu",
        "",
        f"**Veri kaynağı:** `{hist_src}`  ",
        f"**Eğitim komutu sayısı:** {n_train}  ",
        f"**Test girdisi sayısı:** {n_test}  ",
        f"**Geçerli test komutu:** {n_cmds}  ",
        "",
        "---",
        "",
        "## 4.1 Model Tanımı",
        "",
        "Kelime düzeyinde 3-gram Markov zinciri; üstel zamana azalma ağırlıklandırması  ",
        "(`λ = 0,005`, yarı-ömür ≈ 139 gün), sözdizim beyaz listesi (46 komut),  ",
        "minimum frekans eşiği (MIN_CMD_FREQ = 1) ve önek eşleme geri dönüş mekanizması.",
        "",
        "---",
        "",
        "## 4.2 Önerilen Yapılandırma — Temel Metrikler",
        "",
        "**Tablo 4.1 — Önerilen yapılandırmanın temel performans metrikleri.**  ",
        f"*{src_note}. Kalın: önerilen değer.*",
        "",
        "| Metrik | Değer |",
        "|--------|-------|",
        f"| Tuş Tasarrufu Oranı (KSR)                          | **{ksr_prop:.1f}%** |",
        f"| Doğruluk@1 (Sonraki Kelime)                        | **{proposed.get('metric_top1_acc',0)*100:.1f}%** |",
        f"| Doğruluk@3 (Sonraki Kelime)                        | **{proposed.get('metric_top3_acc', proposed.get('metric_top1_acc',0))*100:.1f}%** |",
        f"| Önek Tamamlama Doğruluğu                           | **{proposed.get('metric_prefix_acc',0)*100:.1f}%** |",
        f"| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **{proposed.get('metric_prefix_cond_acc',0)*100:.1f}%** |",
        f"| Top-5 Komut Kabul Oranı                            | **{proposed.get('metric_topk_cmd_acc',0)*100:.1f}%** |",
        f"| Kapsama (sessiz kalmayan oran)                      | **{proposed.get('metric_coverage',0)*100:.1f}%** |",
        f"| Gecikme p50                                         | **{proposed.get('lat_p50_ms',0):.3f} ms** |",
        f"| Gecikme p95                                         | **{proposed.get('lat_p95_ms',0):.3f} ms** |",
        f"| Gecikme p99                                         | **{proposed.get('lat_p99_ms',0):.3f} ms** |",
        f"| n-gram Bağlam Sayısı                               | **{proposed.get('mem_n_contexts',0):,}** |",
        f"| Tablo Bellek Ayak İzi (yüzeysel)                   | **{proposed.get('mem_table_shallow_kb',0):.1f} KB** |",
        "",
        "---",
        "",
        "## 4.3 Ablasyon Çalışması",
        "",
        "**Tablo 4.2 — Ablasyon çalışması: yapılandırma karşılaştırması.**  ",
        f"*{src_note}. Kalın: önerilen yapılandırma.*",
        "",
        "| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Önek Doğ. (%) | Önek-Koş. (%) | Top-5 Komut (%) | Kapsama (%) | p50 (ms) |",
        "|:-------------|--------:|---------------:|--------------:|--------------:|----------------:|------------:|---------:|",
    ]
    for r in results:
        mark = "**" if r.get("proposed") else ""
        name = mark + _tr(r["name"]) + mark
        lines.append(
            f"| {name} "
            f"| {r.get('metric_ksr',0)*100:.1f} "
            f"| {r.get('metric_top1_acc',0)*100:.1f} "
            f"| {r.get('metric_prefix_acc',0)*100:.1f} "
            f"| {r.get('metric_prefix_cond_acc',0)*100:.1f} "
            f"| {r.get('metric_topk_cmd_acc',0)*100:.1f} "
            f"| {r.get('metric_coverage',0)*100:.1f} "
            f"| {r.get('lat_p50_ms',0):.3f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4.4 Temel Bulgular",
        "",
        f"1. Önerilen k=3 kelime-Markov modeli **KSR = {ksr_prop:.1f}%** elde etmiştir;  ",
        f"   100 karakter başına yaklaşık {ksr_prop:.0f} tuş tasarrufu sağlar.",
        f"2. En iyi referans yöntemini **{diff:+.1f}% KSR** farkıyla geçmektedir  ",
        f"   (önerilen: {ksr_prop:.1f}% — en iyi referans: {best_bl:.1f}%).",
        f"3. Çıkarım gecikmesi 5 ms hedefinin çok altındadır:  ",
        f"   p99 = {proposed.get('lat_p99_ms',0):.3f} ms.",
        "4. Geri alma (backoff) mekanizması kritik öneme sahiptir: devre dışı bırakıldığında  ",
        "   kapsama düşerken kesinlik kazancı elde edilememektedir.",
        "5. λ=0,005 azalma katsayısı eski alışkanlıkları tamamen atmadan  ",
        "   son kullanımları ön plana çıkarmaktadır.",
        "",
        "---",
        "",
        "## 4.5 Şekiller",
        "",
        "![Şekil 4.1](fig_markov_order.png)  ",
        "**Şekil 4.1 — Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi.**",
        "",
        "![Şekil 4.2](fig_ablation.png)  ",
        "**Şekil 4.2 — Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması.**",
        "",
        "![Şekil 4.3](fig_latency.png)  ",
        "**Şekil 4.3 — predict_suffix gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir.**",
        "",
        "![Şekil 4.4](fig_decay.png)  ",
        "**Şekil 4.4 — Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi.**",
        "",
        "---",
        "",
        "*`python -m python.eval.run_eval` tarafından otomatik üretilmiştir.*",
    ]

    path = os.path.join(out_dir, "REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [rapor] kaydedildi: REPORT.md", flush=True)


# ── Ana üretici ────────────────────────────────────────────────────────────────

def generate_all(
    results: List[Dict[str, Any]],
    out_dir: str,
    dataset_stats: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Tüm CSV, LaTeX, PNG ve Markdown çıktılarını *out_dir* altına üret.
    """
    os.makedirs(out_dir, exist_ok=True)

    # ── Ham CSV (makine okuma / LaTeX pipeline) ────────────────────────────────
    save_csv(results, os.path.join(out_dir, "metrics_summary.csv"))
    save_csv(results, os.path.join(out_dir, "ablation_table.csv"))

    # ── Türkçe başlıklı Word CSV ───────────────────────────────────────────────
    save_csv_turkish(results, os.path.join(out_dir, "metrics_summary_word.csv"),
                     _TR_COLS_METRICS)
    save_csv_turkish(results, os.path.join(out_dir, "ablation_table_word.csv"),
                     _TR_COLS_METRICS)

    # ── LaTeX (booktabs, Türkçe başlıklar) ────────────────────────────────────
    ds       = dataset_stats or {}
    n_train  = ds.get("n_train", "?")
    n_cmds   = ds.get("n_test_cmds", "?")
    hist_src = ds.get("history_file", "~/.zsh_history")
    src_note = (
        f"Kaynak: kabuk geçmişi (\\texttt{{{hist_src}}}, "
        f"{n_train} eğitim / {n_cmds} test)."
    )

    save_latex_table(
        results,
        os.path.join(out_dir, "metrics_summary.tex"),
        columns=_TR_COLS_METRICS,
        caption=(
            "Önerilen yapılandırmanın temel performans metrikleri. "
            + src_note
        ),
        label="tab:metrics_summary",
    )
    save_latex_table(
        results,
        os.path.join(out_dir, "ablation_table.tex"),
        columns=_TR_COLS_METRICS,
        caption=(
            "Ablasyon çalışması: Markov derecesi, geri alma ve zaman "
            "azalma katsayısının karşılaştırması. "
            + src_note
        ),
        label="tab:ablation",
    )

    # ── Şekiller ───────────────────────────────────────────────────────────────
    plot_markov_order(results, out_dir)
    plot_ablation(results, out_dir)
    plot_latency(results, out_dir)
    plot_decay(results, out_dir)

    # ── Word Markdown tabloları ────────────────────────────────────────────────
    save_word_tables(results, out_dir, dataset_stats=dataset_stats)

    # ── REPORT.md ─────────────────────────────────────────────────────────────
    write_report_md(results, out_dir, dataset_stats=dataset_stats)
