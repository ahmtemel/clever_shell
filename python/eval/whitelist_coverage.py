"""
whitelist_coverage.py – Her iki korpusta komutların yüzde kaçının ilk token'ı
beyaz listede (veya './' ile başlıyor) olduğunu hesaplar.

Çıktılar (analysis/):
    whitelist_coverage.csv    – her korpus için kapsam istatistikleri
    (stdout'a özet cümle yazdırır)

Kullanım:
    python3 python/eval/whitelist_coverage.py
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shlex
import sys
from collections import Counter
from datetime import datetime
from typing import List, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.markov_daemon import WHITELIST, parse_zsh_history
from python.eval.command_chain import _first_token

DEFAULT_SELF_HIST  = os.path.expanduser("~/.zsh_history")
DEFAULT_CYBER_HIST = os.path.join(os.path.dirname(__file__), "data", "cyber_history.txt")
DEFAULT_OUT        = os.path.join(os.path.dirname(__file__), "analysis")


def _first_tok(cmd: str) -> str:
    try:
        toks = shlex.split(cmd, posix=False)
        return toks[0] if toks else cmd.split()[0]
    except Exception:
        parts = cmd.split()
        return parts[0] if parts else cmd


def _in_whitelist(tok: str) -> bool:
    """Token beyaz listede veya ./ ile başlıyor mu?"""
    return tok in WHITELIST or tok.startswith("./")


def analyze_history(path: str, label: str) -> dict:
    """Bir history dosyasını analiz et."""
    if not os.path.isfile(path):
        return {"label": label, "total": 0, "whitelisted": 0, "pct": 0.0,
                "top_whitelisted": "", "top_not_whitelisted": ""}
    entries = parse_zsh_history(path)
    commands = [cmd for _, cmd in entries if cmd.strip()]
    total = len(commands)
    if total == 0:
        return {"label": label, "total": 0, "whitelisted": 0, "pct": 0.0,
                "top_whitelisted": "", "top_not_whitelisted": ""}

    wl_ctr  = Counter()
    nwl_ctr = Counter()
    n_whitelisted = 0
    for cmd in commands:
        tok = _first_tok(cmd)
        if _in_whitelist(tok):
            n_whitelisted += 1
            wl_ctr[tok] += 1
        else:
            nwl_ctr[tok] += 1

    pct = n_whitelisted / total * 100
    top_wl  = ", ".join(f"{t}({c})" for t, c in wl_ctr.most_common(5))
    top_nwl = ", ".join(f"{t}({c})" for t, c in nwl_ctr.most_common(5))

    return {
        "label":              label,
        "total":              total,
        "whitelisted":        n_whitelisted,
        "pct":                round(pct, 1),
        "top_whitelisted":    top_wl,
        "top_not_whitelisted": top_nwl,
    }


def save_csv(rows: List[dict], out_dir: str) -> None:
    path = os.path.join(out_dir, "whitelist_coverage.csv")
    fields = ["label", "total", "whitelisted", "pct",
              "top_whitelisted", "top_not_whitelisted"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [wl] kaydedildi: whitelist_coverage.csv", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Whitelist kapsam analizi",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--self-hist",  default=DEFAULT_SELF_HIST)
    p.add_argument("--cyber-hist", default=DEFAULT_CYBER_HIST)
    p.add_argument("--out-dir",    default=DEFAULT_OUT)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 55, flush=True)
    print("Whitelist Kapsam Analizi", flush=True)
    print("=" * 55, flush=True)
    print(f"\n[wl] Beyaz liste boyutu: {len(WHITELIST)} token", flush=True)

    rows = [
        analyze_history(args.self_hist,  "Kendi kabuk geçmişim"),
        analyze_history(args.cyber_hist, "Siber-güvenlik seti (Švábenský 2021)"),
    ]

    for r in rows:
        print(f"\n[wl] {r['label']}", flush=True)
        print(f"     Toplam komut     : {r['total']:,}", flush=True)
        print(f"     Whitelist'te     : {r['whitelisted']:,}  ({r['pct']:.1f}%)", flush=True)
        print(f"     İlk 5 WL token   : {r['top_whitelisted']}", flush=True)
        print(f"     İlk 5 WL-dışı    : {r['top_not_whitelisted']}", flush=True)

    save_csv(rows, args.out_dir)

    # Özet cümle
    print("\n=== ÖZET ===", flush=True)
    for r in rows:
        print(
            f"  {r['label']}: {r['total']:,} komutun %{r['pct']:.1f}'i "
            f"whitelist kapsamında ({r['whitelisted']:,}/{r['total']:,}).",
            flush=True,
        )
    print("=" * 55, flush=True)


if __name__ == "__main__":
    main()
