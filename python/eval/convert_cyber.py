"""
convert_cyber.py – Siber-güvenlik JSONL veri setini zsh genişletilmiş history
formatına dönüştürür.

Kaynak: Švábenský et al. (2021) – sandbox-*-useractions.json dosyaları.
Çıktı formatı: ": <epoch>:0;<cmd>"  (parse_zsh_history tarafından doğrudan okunur,
böylece recency-decay ablasyonu gerçek zaman damgasına göre çalışır.)

Kullanım:
    python3 python/eval/convert_cyber.py
    python3 python/eval/convert_cyber.py --src data --out python/eval/data/cyber_history.txt
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Repo kökü
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_SRC = os.path.join(_ROOT, "data")
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "data", "cyber_history.txt")


# ── Tek dosyadan bash komutlarını oku ─────────────────────────────────────────

def _load_file(path: str) -> List[Tuple[int, str]]:
    """
    JSONL dosyasından (satır başına bir JSON nesnesi) bash komutlarını oku.

    Döndürür:
        [(epoch_saniye, komut_str), ...]  – yalnızca cmd_type=="bash-command"
    """
    entries: List[Tuple[int, str]] = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if obj.get("cmd_type") != "bash-command":
                continue
            cmd = obj.get("cmd", "").strip()
            if not cmd:
                continue
            ts_str: Optional[str] = obj.get("timestamp_str")
            epoch: int = 0
            if ts_str:
                try:
                    # ISO 8601; Python 3.9 "Z" suffix'ini tanımaz → +00:00'a çevir
                    ts_norm = ts_str.replace("Z", "+00:00")
                    epoch = int(datetime.fromisoformat(ts_norm).timestamp())
                except (ValueError, TypeError):
                    epoch = 0
            entries.append((epoch, cmd))
    return entries


# ── Ana dönüştürücü ───────────────────────────────────────────────────────────

def convert(src_dir: str, out_path: str) -> None:
    """
    *src_dir* altındaki tüm sandbox-*-useractions.json dosyalarını bulur,
    bash komutlarını kronolojik sıraya koyar ve *out_path*'e yazar.

    Oturumlar (dosyalar):
      1. Her dosya içi  → timestamp'e göre sıralanır.
      2. Dosyalar arası → her dosyanın en erken timestamp'ine göre sıralanır.
    """
    pattern = os.path.join(src_dir, "**", "sandbox-*-useractions.json")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        print(f"[convert] UYARI: {pattern} ile eşleşen dosya bulunamadı.", flush=True)
        sys.exit(1)

    # Her dosyanın içeriğini yükle + dosya içi sıralama
    sessions: List[Tuple[int, str, List[Tuple[int, str]]]] = []
    per_folder: Dict[str, int] = defaultdict(int)
    total_skipped = 0

    for fpath in files:
        entries = _load_file(fpath)
        if not entries:
            continue
        entries.sort(key=lambda e: e[0])  # dosya içi kronolojik sıra
        earliest = entries[0][0]
        folder = os.path.basename(os.path.dirname(fpath))
        per_folder[folder] += len(entries)
        total_skipped += 0  # already filtered in _load_file
        sessions.append((earliest, fpath, entries))

    # Dosyalar arası sıralama: en erken timestamp'e göre
    sessions.sort(key=lambda s: s[0])

    # Düz liste
    all_entries: List[Tuple[int, str]] = []
    for _, _, entries in sessions:
        all_entries.extend(entries)

    # Çıktı dizini oluştur
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as fh:
        for epoch, cmd in all_entries:
            # Zsh genişletilmiş format: ": <epoch>:0;<cmd>"
            # Eğer epoch=0 (timestamp okunamazsa) boş bırakmak yerine 0 yazılır
            fh.write(f": {epoch}:0;{cmd}\n")

    # Özet
    total = len(all_entries)
    print(f"\n[convert] Dönüştürme tamamlandı", flush=True)
    print(f"  Bulunan JSONL dosyası : {len(files)}", flush=True)
    print(f"  Kullanılan oturum     : {len(sessions)}", flush=True)
    print(f"  Toplam bash komutu    : {total:,}", flush=True)
    print(f"  Çıktı dosyası         : {out_path}", flush=True)
    print(f"\n  Klasör başına komut sayısı:", flush=True)
    for folder, cnt in sorted(per_folder.items(), key=lambda x: -x[1]):
        print(f"    {folder:<40s} {cnt:>5,} komut", flush=True)
    print(f"\n  İlk 5 satır:", flush=True)
    with open(out_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= 5:
                break
            print(f"    {line.rstrip()}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Siber-güvenlik JSONL veri setini zsh history formatına çevirir.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--src", default=DEFAULT_SRC,
                   help="sandbox-*-useractions.json dosyalarını içeren kök dizin.")
    p.add_argument("--out", default=DEFAULT_OUT,
                   help="Çıktı zsh history dosyasının yolu.")
    args = p.parse_args()
    convert(args.src, args.out)


if __name__ == "__main__":
    main()
