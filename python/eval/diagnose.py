#!/usr/bin/env python3
"""
diagnose.py  –  clever_shell tahmin hattı uçtan-uca teşhis.

Bölümler:
  A) Model eğitim teşhisi (gerçek ~/.zsh_history ile)
  B) IPC uçtan-uca teşhis (daemon çalışıyorsa)
  C) Özet rapor

Kullanım:
    python3 python/eval/diagnose.py
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import time
import types

# ── ZMQ STUB: markov_daemon'u zmq olmadan import edebilmek için ──────────────
_zmq_stub = types.ModuleType("zmq")
_zmq_stub.Context      = type("Context",  (), {"instance": lambda: None})
_zmq_stub.Poller       = type("Poller",   (), {"register": lambda *a, **kw: None,
                                               "poll":     lambda *a, **kw: {}})
_zmq_stub.PAIR         = 0
_zmq_stub.DONTWAIT     = 1
_zmq_stub.POLLIN       = 1
_zmq_stub.ZMQError     = Exception
_zmq_stub.error        = types.ModuleType("zmq.error")
_zmq_stub.error.Again  = BlockingIOError
sys.modules.setdefault("zmq",       _zmq_stub)
sys.modules.setdefault("zmq.error", _zmq_stub.error)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.markov_daemon import (
    WordMarkovChain,
    build_chain,
    is_valid_command,
    parse_zsh_history,
    apply_frequency_floor,
    CONTEXT_LEN,
    MIN_CMD_FREQ,
    RECENCY_DECAY,
    WHITELIST,
)

HISTORY_PATH = os.path.expanduser("~/.zsh_history")
DIVIDER      = "─" * 64


def section(title: str) -> None:
    print(f"\n{'═'*64}")
    print(f"  {title}")
    print('═'*64)


# ═══════════════════════════════════════════════════════════════
# A) MODEL EĞİTİM TEŞHİSİ
# ═══════════════════════════════════════════════════════════════
section("A) MODEL EĞİTİM TEŞHİSİ")

# A1. History dosyası formatı
print(f"\n[A1] Dosya: {HISTORY_PATH}")
if not os.path.isfile(HISTORY_PATH):
    print("  ✗ DOSYA BULUNAMADI")
    sys.exit(1)

raw_lines = open(HISTORY_PATH, encoding="utf-8", errors="replace").readlines()
print(f"  Ham satır sayısı: {len(raw_lines):,}")

print("\n  İlk 8 satır (ham):")
for i, ln in enumerate(raw_lines[:8]):
    print(f"    {i+1}: {repr(ln.rstrip())}")

# format tespiti
extended = sum(1 for ln in raw_lines if ln.startswith(": "))
print(f"\n  Genişletilmiş format (': epoch:0;cmd') satır sayısı: {extended:,}")
plain    = sum(1 for ln in raw_lines if not ln.startswith(": ") and ln.strip())
print(f"  Düz format satır sayısı: {plain:,}")

# A2. Ham grep: git status
git_status_raw = sum(1 for ln in raw_lines if "git status" in ln)
git_any_raw    = sum(1 for ln in raw_lines if "git" in ln)
print(f"\n  Ham arama: 'git status' içeren satır: {git_status_raw}")
print(f"  Ham arama: 'git' içeren satır: {git_any_raw}")
if git_status_raw == 0:
    print("  ⚠  ~/.zsh_history'de 'git status' SIFIR satır — model bunu öğrenemez!")

# A3. parse_zsh_history ile parse
print(f"\n[A2] parse_zsh_history çıktısı")
all_entries = parse_zsh_history(HISTORY_PATH)
print(f"  Parsed entry sayısı: {len(all_entries):,}")

valid_entries = [(ts, cmd) for ts, cmd in all_entries if is_valid_command(cmd)]
print(f"  is_valid_command geçen: {len(valid_entries):,}")

floored = apply_frequency_floor(valid_entries, min_freq=MIN_CMD_FREQ)
print(f"  apply_frequency_floor sonrası (min_freq={MIN_CMD_FREQ}): {len(floored):,}")

# git ile başlayan komutlar
git_valid = [cmd for _, cmd in valid_entries if cmd.strip().startswith("git")]
print(f"\n  Whitelist-valid 'git *' komutları: {len(git_valid)}")
for cmd in git_valid[:20]:
    print(f"    {repr(cmd)}")
if len(git_valid) == 0:
    print("  ⚠  Hiç 'git *' komutu yok → WHITELIST veya is_valid_command'dan geçemiyor")

# A4. build_chain ile model kur
print(f"\n[A3] build_chain ile model eğitimi (k={CONTEXT_LEN}, λ={RECENCY_DECAY})")
build_result = build_chain(HISTORY_PATH, k=CONTEXT_LEN)
# build_chain bir tuple döndürüyor: (chain, stats) – kontrol et
if isinstance(build_result, tuple):
    model, stats = build_result
    print(f"  build_chain dönüş tipi: tuple  stats={stats}")
else:
    model = build_result
n_contexts = sum(len(v) for v in model.table.values())
print(f"  model.table bağlam sayısı: {len(model.table):,}")
print(f"  Toplam (bağlam, sonraki-token) çifti: {n_contexts:,}")
print(f"  fallback_counter boyutu: {len(model.fallback_counter):,}")

# A5. ('git',) bağlamı
key_git = ("git",)
git_ctx = model.table.get(key_git, {})
print(f"\n[A4] model.table[{key_git}] (git'ten sonra gelebilecek kelimeler):")
if git_ctx:
    for word, score in sorted(git_ctx.items(), key=lambda x: -x[1])[:20]:
        print(f"    '{word}': {score:.4f}")
else:
    print("  ⚠  BOŞ — model 'git' bağlamından hiçbir şey öğrenmemiş")

status_score = git_ctx.get("status", 0)
print(f"\n  'status' skoru: {status_score:.4f}  {'✓ VAR' if status_score > 0 else '✗ YOK'}")

# A6. fallback_counter
print(f"\n[A5] fallback_counter (ilk 10 en sık komut):")
for cmd, cnt in sorted(model.fallback_counter.items(), key=lambda x: -x[1])[:10]:
    print(f"    {repr(cmd)}: {cnt:.4f}")
git_fb = {k: v for k, v in model.fallback_counter.items() if k.startswith("git")}
print(f"\n  fallback_counter'da 'git *' ile başlayan: {len(git_fb)}")
for cmd, cnt in sorted(git_fb.items(), key=lambda x: -x[1])[:10]:
    print(f"    {repr(cmd)}: {cnt:.4f}")

# A7. predict_suffix test girdileri
print(f"\n[A6] predict_suffix test sonuçları:")
test_inputs = [
    "git s",
    "git st",
    "git statu",
    "git ",
    "gi",
    "git c",
    "git p",
    "ls ",
    "cd ",
    "make",
]
for buf in test_inputs:
    result = model.predict_suffix(buf)
    print(f"  predict_suffix({repr(buf):>14}) → {repr(result)}")


# ═══════════════════════════════════════════════════════════════
# B) IPC UÇTAN-UCA TEŞHİSİ
# ═══════════════════════════════════════════════════════════════
section("B) IPC UÇTAN-UCA TEŞHİSİ")

ipc_path   = "/tmp/markov_shell.ipc"
ipc_exists = os.path.exists(ipc_path)
print(f"\n  /tmp/markov_shell.ipc mevcut: {'EVET' if ipc_exists else 'HAYIR'}")

try:
    result = subprocess.run(["pgrep", "-f", "markov_daemon"], capture_output=True, text=True)
    pids = result.stdout.strip()
    print(f"  pgrep -f markov_daemon: {'ÇALIŞIYOR pid=' + pids if pids else 'ÇALIŞMIYOR'}")
except Exception as e:
    print(f"  pgrep hatası: {e}")

if ipc_exists and pids:
    print("\n  Daemon çalışıyor → ZMQ PAIR istemci testi başlıyor …")
    # Stub'ı geçici olarak devre dışı bırakıp gerçek pyzmq'yu yükle
    _stub_backup   = sys.modules.pop("zmq",       None)
    _stube_backup  = sys.modules.pop("zmq.error", None)
    try:
        import zmq as _zmq_real      # gerçek pyzmq
        # stub'ı geri yükle (markov_daemon için)
        if _stub_backup:
            sys.modules["zmq"]       = _stub_backup
        if _stube_backup:
            sys.modules["zmq.error"] = _stube_backup

        ctx  = _zmq_real.Context()
        sock = ctx.socket(_zmq_real.PAIR)
        sock.connect(f"ipc://{ipc_path}")
        time.sleep(0.1)    # bağlantı kurulsun

        test_sends = ["git s", "git statu", "git ", "ls "]
        for buf in test_sends:
            try:
                sock.send_string(buf, flags=_zmq_real.DONTWAIT)
            except _zmq_real.ZMQError:
                pass
            time.sleep(0.15)    # daemon'un işlemesi için bekle
            poller = _zmq_real.Poller()
            poller.register(sock, _zmq_real.POLLIN)
            ready = dict(poller.poll(600))
            if ready.get(sock) == _zmq_real.POLLIN:
                reply = sock.recv_string(flags=_zmq_real.DONTWAIT)
                print(f"  ← send({repr(buf):>14})  reply: {repr(reply)}")
            else:
                print(f"  ← send({repr(buf):>14})  reply: [600ms ZAMAN AŞIMI — cevap yok]")
        sock.close()
        ctx.term()
    except ImportError:
        print("  ⚠  gerçek pyzmq import edilemedi — sadece stub var; pyzmq kur: pip install pyzmq")
        if _stub_backup:   sys.modules["zmq"]       = _stub_backup
        if _stube_backup:  sys.modules["zmq.error"] = _stube_backup
    except Exception as e:
        import traceback
        print(f"  ZMQ testi hatası: {e}")
        traceback.print_exc()
        if _stub_backup:   sys.modules["zmq"]       = _stub_backup
        if _stube_backup:  sys.modules["zmq.error"] = _stube_backup
else:
    if not ipc_exists:
        print("  Soket yok → daemon hiç başlatılmamış veya başka bir yerde bekliyor.")
    if not pids:
        print("  Daemon süreci çalışmıyor.")


# ═══════════════════════════════════════════════════════════════
# C) ÖZET RAPOR
# ═══════════════════════════════════════════════════════════════
section("C) ÖZET RAPOR")

history_format = "genişletilmiş (: epoch:0;cmd)" if extended > 0 else "DÜZMETIN (zaman damgasız)"
print(f"""
  [1] MODEL (bağlam sayısı, git bağlamı)
      Toplam bağlam: {len(model.table):,}
      model.table[('git',)] → {'BOŞ ⚠' if not git_ctx else f"{len(git_ctx)} token, 'status' skoru={status_score:.4f}"}
      fallback git* komut sayısı: {len(git_fb)}

  [2] predict_suffix GERÇEk ÇIKTILAR
      'git s'    → {repr(model.predict_suffix('git s'))}
      'git statu'→ {repr(model.predict_suffix('git statu'))}
      'git '     → {repr(model.predict_suffix('git '))}

  [3] ~/.zsh_history DURUM
      Toplam satır: {len(raw_lines):,}
      Format: {history_format}
      Ham 'git status' satır sayısı: {git_status_raw}
      Ham 'git' satır sayısı: {git_any_raw}
      Whitelist-valid 'git *' komut sayısı: {len(git_valid)}

  [4] IPC
      /tmp/markov_shell.ipc: {'mevcut' if ipc_exists else 'YOK'}
      Daemon süreci: {'çalışıyor pid=' + pids if pids else 'KAPALI'}
""")

if git_status_raw == 0:
    print("  KÖK NEDEN → ~/.zsh_history'de 'git status' hiç yok.")
    print("  ÇÖZÜM: birkaç kez 'git status' çalıştır, daemon'u yeniden başlat.")
elif len(git_valid) == 0:
    print("  KÖK NEDEN → 'git status' history'de var ama whitelist/parse filtresi geçiremiyor.")
elif status_score == 0:
    print("  KÖK NEDEN → Komut parse edildi ama table[('git',)]['status'] eksik → build_chain hatası.")
else:
    print("  Model 'status'u biliyor. Sorun IPC/render katmanında.")
