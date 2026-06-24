"""
command_chain.py – Komut düzeyi çapraz-komut (cross-command) Markov zinciri deneyi.

Her sandbox-*-useractions.json = bir oturum. N-gram'lar oturum sınırını AŞMAZ.
İki varyant:
  • full  – tüm komut string'i durum olarak kullanılır
  • token – yalnızca ilk token (komut adı) durum olarak kullanılır

Ablasyon:
  k ∈ {1, 2, 3}   ×   λ ∈ {0, 0.005, 0.02}   +  baseline (en sık komut)

Çıktılar (python/eval/analysis/):
  command_level.csv      – tüm ablasyon sonuçları
  fig_command_k.png      – k vs Top-1/Top-5
  fig_command_decay.png  – λ vs Top-1/Top-5

Kullanım:
    python3 python/eval/command_chain.py
    python3 python/eval/command_chain.py --src data --out-dir python/eval/analysis
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import shlex
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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
DEFAULT_SRC     = os.path.join(_ROOT, "data")
DEFAULT_OUT_DIR = os.path.join(os.path.dirname(__file__), "analysis")


# ──────────────────────────────────────────────────────────────────────────────
# Veri yükleme
# ──────────────────────────────────────────────────────────────────────────────

Session = List[Tuple[int, str]]   # [(epoch, cmd), ...]


def _first_token(cmd: str) -> str:
    """Komutun ilk token'ını (komut adı) döndür."""
    try:
        toks = shlex.split(cmd, posix=False)
        return toks[0] if toks else cmd.split()[0]
    except Exception:
        parts = cmd.split()
        return parts[0] if parts else cmd


def load_sessions(src_dir: str) -> List[Tuple[int, str, Session]]:
    """
    Her sandbox-*-useractions.json = bir oturum.
    Döndürür: [(earliest_epoch, file_path, [(epoch, cmd), ...]), ...]
    Oturumlar kendi içinde timestamp'e göre sıralı; liste de böyledir.
    """
    pattern = os.path.join(src_dir, "**", "sandbox-*-useractions.json")
    files   = sorted(glob.glob(pattern, recursive=True))
    if not files:
        raise FileNotFoundError(f"Eşleşen JSON dosyası bulunamadı: {pattern}")

    sessions: List[Tuple[int, str, Session]] = []
    for fpath in files:
        entries: Session = []
        with open(fpath, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("cmd_type") != "bash-command":
                    continue
                cmd = obj.get("cmd", "").strip()
                if not cmd:
                    continue
                ts_str = obj.get("timestamp_str", "")
                epoch  = 0
                if ts_str:
                    try:
                        epoch = int(datetime.fromisoformat(
                            ts_str.replace("Z", "+00:00")).timestamp())
                    except (ValueError, TypeError):
                        epoch = 0
                entries.append((epoch, cmd))
        if not entries:
            continue
        entries.sort(key=lambda e: e[0])
        earliest = entries[0][0]
        sessions.append((earliest, fpath, entries))

    sessions.sort(key=lambda s: s[0])
    return sessions


# ──────────────────────────────────────────────────────────────────────────────
# Komut düzeyi Markov zinciri
# ──────────────────────────────────────────────────────────────────────────────

class CommandChain:
    """
    k-dereceli komut Markov zinciri.
    table[ctx_tuple] = Counter({sonraki_komut: ağırlıklı_frekans})
    Backoff: ctx uzunluğunu k'dan 1'e azaltarak arar.
    """

    def __init__(self, k: int = 2, token_mode: bool = False) -> None:
        self.k          = k
        self.token_mode = token_mode
        self.table: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)
        self.fallback: Counter = Counter()   # global komut frekansı

    def _norm(self, cmd: str) -> str:
        return _first_token(cmd) if self.token_mode else cmd

    def train_session(self, session: Session, weight: float = 1.0) -> None:
        """Bir oturumu ağırlıklı olarak eğit. Oturum sınırı AŞILMAZ."""
        normed = [self._norm(cmd) for _, cmd in session if cmd.strip()]
        for cmd in normed:
            self.fallback[cmd] += weight
        n = len(normed)
        for i in range(n - 1):
            nxt = normed[i + 1]
            # k'dan 1'e tüm bağlam uzunluklarını ekle
            for ctx_len in range(1, min(self.k, i + 1) + 1):
                ctx = tuple(normed[i - ctx_len + 1 : i + 1])
                self.table[ctx][nxt] += weight

    def predict(self, recent_cmds: List[str], top_k: int = 5) -> List[str]:
        """Son recent_cmds'e bakarak en olası sonraki komutu tahmin et."""
        normed = [self._norm(c) for c in recent_cmds]
        for ctx_len in range(min(self.k, len(normed)), 0, -1):
            ctx = tuple(normed[-ctx_len:])
            if ctx in self.table and self.table[ctx]:
                return [c for c, _ in self.table[ctx].most_common(top_k)]
        return [c for c, _ in self.fallback.most_common(top_k)]


class MostFrequentBaseline:
    """Bağlam gözetmeksizin en sık komutları öneren baseline."""

    def __init__(self, token_mode: bool = False) -> None:
        self.token_mode = token_mode
        self.fallback: Counter = Counter()

    def _norm(self, cmd: str) -> str:
        return _first_token(cmd) if self.token_mode else cmd

    def train_session(self, session: Session, weight: float = 1.0) -> None:
        for _, cmd in session:
            if cmd.strip():
                self.fallback[self._norm(cmd)] += weight

    def predict(self, recent_cmds: List[str], top_k: int = 5) -> List[str]:
        return [c for c, _ in self.fallback.most_common(top_k)]


# ──────────────────────────────────────────────────────────────────────────────
# Eğitim & Değerlendirme
# ──────────────────────────────────────────────────────────────────────────────

def _recency_weight(epoch: int, ref_epoch: int, lam: float) -> float:
    """exp(-λ · Δgün)"""
    if lam == 0.0 or epoch == 0 or ref_epoch == 0:
        return 1.0
    delta_days = max(0.0, (ref_epoch - epoch) / 86400.0)
    return math.exp(-lam * delta_days)


def train_model(model, sessions: List[Tuple[int, str, Session]],
                lam: float, ref_epoch: int) -> None:
    for earliest, _, session in sessions:
        w = _recency_weight(earliest, ref_epoch, lam)
        model.train_session(session, weight=w)


def evaluate_model(model, test_sessions: List[Tuple[int, str, Session]]) \
        -> Dict[str, float]:
    """
    Test oturumları üzerinde Top-1 ve Top-5 doğruluğu ölç.
    Her pozisyon için önceki min(k, pos) komutu bağlam olarak kullan.
    """
    top1_hits = 0
    top5_hits = 0
    total     = 0

    k = getattr(model, "k", 1)

    for _, _, session in test_sessions:
        normed = []
        for _, cmd in session:
            cmd = cmd.strip()
            if not cmd:
                continue
            normed.append(cmd)

        for i in range(1, len(normed)):
            ctx_cmds   = normed[max(0, i - k) : i]   # son k komut
            ground_true = normed[i]
            preds = model.predict(ctx_cmds, top_k=5)
            # token modunda ground_true'yu da normalleştir
            if hasattr(model, "token_mode") and model.token_mode:
                ground_true = _first_token(ground_true)

            total += 1
            if preds and preds[0] == ground_true:
                top1_hits += 1
            if ground_true in preds[:5]:
                top5_hits += 1

    return {
        "top1": top1_hits / total if total else 0.0,
        "top5": top5_hits / total if total else 0.0,
        "total": total,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Ablasyon
# ──────────────────────────────────────────────────────────────────────────────

def run_ablation(sessions: List[Tuple[int, str, Session]],
                 train_ratio: float = 0.8) \
        -> List[Dict]:
    """
    Tüm ablasyon konfigürasyonlarını çalıştır.
    Kronolojik split: ilk %80 oturum eğitim, son %20 test.
    """
    n_train = max(1, int(len(sessions) * train_ratio))
    train_sessions = sessions[:n_train]
    test_sessions  = sessions[n_train:]

    # Referans zamanı = eğitim setinin en geç timestamp'i
    ref_epoch = max((s[0] for s in train_sessions if s[0] > 0), default=0)

    ks    = [1, 2, 3]
    lams  = [0.0, 0.005, 0.02]
    modes = [("full", False), ("token", True)]

    results = []

    for mode_name, token_mode in modes:
        # Markov ablasyonu
        for k in ks:
            for lam in lams:
                model = CommandChain(k=k, token_mode=token_mode)
                train_model(model, train_sessions, lam, ref_epoch)
                metrics = evaluate_model(model, test_sessions)
                results.append({
                    "mod":     mode_name,
                    "config":  f"k={k}, λ={lam}",
                    "k":       k,
                    "lam":     lam,
                    "type":    "markov",
                    "top1":    metrics["top1"],
                    "top5":    metrics["top5"],
                    "total":   metrics["total"],
                    "n_ctx":   len(model.table),
                })
                top1p = metrics["top1"] * 100
                top5p = metrics["top5"] * 100
                print(f"  [{mode_name}] k={k} λ={lam:5.3f}  "
                      f"Top-1={top1p:5.1f}%  Top-5={top5p:5.1f}%  "
                      f"n={metrics['total']:,}", flush=True)

        # Baseline
        for lam in lams:
            model_bl = MostFrequentBaseline(token_mode=token_mode)
            train_model(model_bl, train_sessions, lam=0.0, ref_epoch=ref_epoch)
            metrics = evaluate_model(model_bl, test_sessions)
            results.append({
                "mod":     mode_name,
                "config":  f"baseline, λ={lam}",
                "k":       0,
                "lam":     lam,
                "type":    "baseline",
                "top1":    metrics["top1"],
                "top5":    metrics["top5"],
                "total":   metrics["total"],
                "n_ctx":   0,
            })
            top1p = metrics["top1"] * 100
            top5p = metrics["top5"] * 100
            print(f"  [{mode_name}] baseline λ={lam:5.3f}  "
                  f"Top-1={top1p:5.1f}%  Top-5={top5p:5.1f}%  "
                  f"n={metrics['total']:,}", flush=True)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Raporlama
# ──────────────────────────────────────────────────────────────────────────────

def save_csv(results: List[Dict], out_dir: str) -> None:
    path = os.path.join(out_dir, "command_level.csv")
    fields = ["mod", "config", "k", "lam", "type", "top1", "top5", "total", "n_ctx"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"  [chain] kaydedildi: {os.path.basename(path)}", flush=True)


def _markov_rows(results: List[Dict], mode: str, lam: float = 0.005):
    return sorted(
        [r for r in results if r["mod"] == mode
         and r["type"] == "markov" and r["lam"] == lam],
        key=lambda r: r["k"]
    )


def _decay_rows(results: List[Dict], mode: str, k: int = 3):
    return sorted(
        [r for r in results if r["mod"] == mode
         and r["type"] in ("markov", "baseline") and r["k"] == k],
        key=lambda r: r["lam"]
    )


def plot_k_comparison(results: List[Dict], out_dir: str) -> None:
    """
    Şekil: k değerine göre Top-1 ve Top-5 (λ=0.005 sabit).
    Full komut ve Token varyantı yan yana.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=False)

    for ax, mode, title in [
        (axes[0], "full",  "Tam Komut Dizisi"),
        (axes[1], "token", "Yalnızca Komut Adı (Token)"),
    ]:
        rows = _markov_rows(results, mode, lam=0.005)
        if not rows:
            continue
        ks      = [r["k"] for r in rows]
        top1    = [r["top1"] * 100 for r in rows]
        top5    = [r["top5"] * 100 for r in rows]

        x = np.arange(len(ks))
        w = 0.38
        ax.bar(x - w/2, top1, w, label="Top-1 Doğruluk",  color="#4c72b0", alpha=0.88)
        ax.bar(x + w/2, top5, w, label="Top-5 Doğruluk",  color="#dd8452", alpha=0.88)
        ax.set_xticks(x)
        ax.set_xticklabels([f"k={k}" for k in ks])
        ax.set_xlabel("Markov Bağlam Uzunluğu k")
        ax.set_ylabel("Doğruluk (%)")
        ax.set_title(title)
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)

    fig.suptitle("Komut Düzeyi Markov Zinciri — k Ablasyonu (λ=0.005)", fontsize=12)
    fig.tight_layout()
    path = os.path.join(out_dir, "fig_command_k.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [chain] kaydedildi: {os.path.basename(path)}", flush=True)


def plot_decay_comparison(results: List[Dict], out_dir: str) -> None:
    """
    Şekil: λ değerine göre Top-1 ve Top-5 (k=3 sabit).
    Full komut ve Token varyantı yan yana.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=False)

    for ax, mode, title in [
        (axes[0], "full",  "Tam Komut Dizisi"),
        (axes[1], "token", "Yalnızca Komut Adı (Token)"),
    ]:
        rows  = _decay_rows(results, mode, k=3)
        lams  = [r["lam"] for r in rows]
        top1  = [r["top1"] * 100 for r in rows]
        top5  = [r["top5"] * 100 for r in rows]

        ax.plot(lams, top1, "o-",  color="#4c72b0", linewidth=2,
                markersize=7, label="Top-1 Doğruluk")
        ax.plot(lams, top5, "s--", color="#dd8452", linewidth=2,
                markersize=7, label="Top-5 Doğruluk")
        ax.set_xlabel("Zaman Azalma Katsayısı λ")
        ax.set_ylabel("Doğruluk (%)")
        ax.set_title(title)
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        # λ ekseninde 3 nokta
        ax.set_xticks(lams)

    fig.suptitle("Komut Düzeyi Markov Zinciri — λ Ablasyonu (k=3)", fontsize=12)
    fig.tight_layout()
    path = os.path.join(out_dir, "fig_command_decay.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [chain] kaydedildi: {os.path.basename(path)}", flush=True)


def print_summary(results: List[Dict]) -> None:
    """Terminale Türkçe özet tablo yaz."""
    header = f"{'Mod':<8} {'Yapılandırma':<22} {'Top-1 (%)':>10} {'Top-5 (%)':>10} {'#Test':>8}"
    print("\n" + "─" * len(header))
    print(header)
    print("─" * len(header))
    for r in results:
        is_prop = (r["type"] == "markov" and r["k"] == 3 and r["lam"] == 0.005)
        mark = "★ " if is_prop else "  "
        print(f"{r['mod']:<8} {mark}{r['config']:<20} "
              f"{r['top1']*100:>10.1f} {r['top5']*100:>10.1f} "
              f"{int(r['total']):>8,}")
    print("─" * len(header))

    # k=1 vs k=2 vs k=3 fark analizi
    for mode in ("full", "token"):
        rows_lam = {r["k"]: r for r in results
                    if r["mod"] == mode and r["type"] == "markov"
                    and r["lam"] == 0.005}
        if len(rows_lam) < 2:
            continue
        print(f"\n[{mode}] k=1 vs k=3 Top-1 farkı: "
              f"{(rows_lam.get(3,{}).get('top1',0) - rows_lam.get(1,{}).get('top1',0))*100:+.2f} pp")
        print(f"[{mode}] k=1 vs k=3 Top-5 farkı: "
              f"{(rows_lam.get(3,{}).get('top5',0) - rows_lam.get(1,{}).get('top5',0))*100:+.2f} pp")

    # decay etki analizi (k=3)
    for mode in ("full", "token"):
        rows_k3 = {r["lam"]: r for r in results
                   if r["mod"] == mode and r["type"] == "markov" and r["k"] == 3}
        if 0.0 in rows_k3 and 0.005 in rows_k3:
            d = (rows_k3[0.005]["top1"] - rows_k3[0.0]["top1"]) * 100
            print(f"[{mode}] λ=0→0.005 Top-1 değişimi: {d:+.2f} pp "
                  f"({'etki var' if abs(d) > 0.1 else 'minimal etki'})")


def write_analysis_report(results: List[Dict], out_dir: str,
                           n_sessions: int, n_train: int, n_test: int) -> None:
    """analysis/ANALYSIS_REPORT.md oluştur."""
    lines: List[str] = [
        "# Komut Düzeyi Markov Zinciri — Analiz Raporu",
        "",
        f"**Veri seti:** Siber-güvenlik eğitim seti (Švábenský 2021)  ",
        f"**Toplam oturum:** {n_sessions}  ",
        f"**Eğitim oturumu:** {n_train} (%80)  ",
        f"**Test oturumu:** {n_test} (%20)  ",
        "",
        "---",
        "",
        "## Tablo 4.5 — Komut Düzeyi Ablasyon: k ve λ'ya Göre Doğruluk",
        "",
        "*Her satır: mod × k × λ konfigürasyonu. ★ = önerilen yapılandırma.*",
        "",
        "| Mod | Yapılandırma | Top-1 (%) | Top-5 (%) | #Test |",
        "|-----|:-------------|----------:|----------:|------:|",
    ]
    for r in results:
        mark = "★ " if (r["type"] == "markov" and r["k"] == 3 and r["lam"] == 0.005) else ""
        lines.append(
            f"| {r['mod']} | {mark}{r['config']} | "
            f"{r['top1']*100:.1f} | {r['top5']*100:.1f} | "
            f"{int(r['total']):,} |"
        )

    # Fark analizi
    full_rows  = {r["k"]: r for r in results
                  if r["mod"] == "full"  and r["type"] == "markov" and r["lam"] == 0.005}
    token_rows = {r["k"]: r for r in results
                  if r["mod"] == "token" and r["type"] == "markov" and r["lam"] == 0.005}

    def _diff(rows, k1, k2, metric):
        v1 = rows.get(k1, {}).get(metric, 0) * 100
        v2 = rows.get(k2, {}).get(metric, 0) * 100
        return v2 - v1

    full_decay  = {r["lam"]: r for r in results
                   if r["mod"] == "full"  and r["type"] == "markov" and r["k"] == 3}
    token_decay = {r["lam"]: r for r in results
                   if r["mod"] == "token" and r["type"] == "markov" and r["k"] == 3}

    def _decay_diff(rows, l1, l2, metric):
        v1 = rows.get(l1, {}).get(metric, 0) * 100
        v2 = rows.get(l2, {}).get(metric, 0) * 100
        return v2 - v1

    lines += [
        "",
        "---",
        "",
        "## Temel Bulgular",
        "",
        "### k Etkisi (λ=0.005 sabit)",
        f"| Karşılaştırma | Tam Komut Top-1 fark | Tam Komut Top-5 fark "
        f"| Token Top-1 fark | Token Top-5 fark |",
        "|:------|---:|---:|---:|---:|",
        f"| k=1 → k=2 | "
        f"{_diff(full_rows,1,2,'top1'):+.2f} pp | {_diff(full_rows,1,2,'top5'):+.2f} pp | "
        f"{_diff(token_rows,1,2,'top1'):+.2f} pp | {_diff(token_rows,1,2,'top5'):+.2f} pp |",
        f"| k=2 → k=3 | "
        f"{_diff(full_rows,2,3,'top1'):+.2f} pp | {_diff(full_rows,2,3,'top5'):+.2f} pp | "
        f"{_diff(token_rows,2,3,'top1'):+.2f} pp | {_diff(token_rows,2,3,'top5'):+.2f} pp |",
        f"| k=1 → k=3 | "
        f"{_diff(full_rows,1,3,'top1'):+.2f} pp | {_diff(full_rows,1,3,'top5'):+.2f} pp | "
        f"{_diff(token_rows,1,3,'top1'):+.2f} pp | {_diff(token_rows,1,3,'top5'):+.2f} pp |",
        "",
        "### λ Etkisi (k=3 sabit)",
        f"| Karşılaştırma | Tam Komut Top-1 fark | Tam Komut Top-5 fark "
        f"| Token Top-1 fark | Token Top-5 fark |",
        "|:------|---:|---:|---:|---:|",
        f"| λ=0 → λ=0.005 | "
        f"{_decay_diff(full_decay,0.0,0.005,'top1'):+.2f} pp | "
        f"{_decay_diff(full_decay,0.0,0.005,'top5'):+.2f} pp | "
        f"{_decay_diff(token_decay,0.0,0.005,'top1'):+.2f} pp | "
        f"{_decay_diff(token_decay,0.0,0.005,'top5'):+.2f} pp |",
        f"| λ=0.005 → λ=0.02 | "
        f"{_decay_diff(full_decay,0.005,0.02,'top1'):+.2f} pp | "
        f"{_decay_diff(full_decay,0.005,0.02,'top5'):+.2f} pp | "
        f"{_decay_diff(token_decay,0.005,0.02,'top1'):+.2f} pp | "
        f"{_decay_diff(token_decay,0.005,0.02,'top5'):+.2f} pp |",
        "",
        "---",
        "",
        "## Şekiller",
        "",
        "| Şekil No | Dosya | Açıklama |",
        "|----------|-------|---------|",
        "| Şekil 4.7 | `fig_command_k.png` | "
        "Markov bağlam uzunluğu k'ya göre Top-1 ve Top-5 doğruluğu (λ=0.005). |",
        "| Şekil 4.8 | `fig_command_decay.png` | "
        "Zaman azalma katsayısı λ'ya göre Top-1 ve Top-5 doğruluğu (k=3). |",
        "",
        "---",
        "",
        "*`python3 python/eval/command_chain.py` tarafından otomatik üretilmiştir.*",
    ]

    path = os.path.join(out_dir, "ANALYSIS_REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  [chain] kaydedildi: ANALYSIS_REPORT.md", flush=True)


# ──────────────────────────────────────────────────────────────────────────────
# Ana fonksiyon
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Komut düzeyi Markov zinciri deneyi",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--src",     default=DEFAULT_SRC,
                   help="sandbox-*-useractions.json dosyalarının kök dizini")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                   help="Çıktı dizini")
    p.add_argument("--train-ratio", type=float, default=0.8,
                   help="Eğitim oturumu oranı")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 60, flush=True)
    print("Komut Düzeyi Markov Zinciri Deneyi", flush=True)
    print("=" * 60, flush=True)
    print(f"\n[chain] Oturumlar yükleniyor: {args.src}", flush=True)

    sessions = load_sessions(args.src)
    n_sessions = len(sessions)
    n_train    = max(1, int(n_sessions * args.train_ratio))
    n_test     = n_sessions - n_train
    total_cmds = sum(len(s[2]) for s in sessions)

    print(f"[chain] {n_sessions} oturum, {total_cmds:,} bash komutu", flush=True)
    print(f"[chain] Eğitim: {n_train} oturum | Test: {n_test} oturum\n", flush=True)

    print("[chain] Ablasyon çalıştırılıyor …", flush=True)
    results = run_ablation(sessions, train_ratio=args.train_ratio)

    print("\n[chain] Özet:", flush=True)
    print_summary(results)

    print("\n[chain] Raporlar yazılıyor …", flush=True)
    save_csv(results, args.out_dir)
    plot_k_comparison(results, args.out_dir)
    plot_decay_comparison(results, args.out_dir)
    write_analysis_report(results, args.out_dir, n_sessions, n_train, n_test)

    print("\n" + "=" * 60, flush=True)
    print("Deney tamamlandı. Çıktı dizini:", args.out_dir, flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
