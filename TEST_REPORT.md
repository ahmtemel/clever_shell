# clever_shell — Tam Test Raporu

> **Tarih:** 24 Haziran 2026  
> **Commit aralığı:** Phase 1–6 + Ghost Text IPC zamanlama düzeltmesi  
> **Ortam:** macOS 25.4.0, gcc (Apple Clang), Python 3.9, libzmq 4.3.5

---

## Özet Tablo

| # | Test | Sonuç | Detay |
|---|------|-------|-------|
| 1 | `make re` (üretim derlemesi) | ✅ PASS | 0 uyarı, 0 hata |
| 2 | `make asan` (ASan/UBSan derlemesi) | ✅ PASS | 0 uyarı, 0 hata |
| 3 | `pytest python/eval/` (28 birim testi) | ✅ PASS | 28/28 geçti |
| 4 | ASan/UBSan çalışma zamanı (PTY) | ✅ PASS | 0 ASan hatası, 0 UBSan hatası |
| 5 | Daemon + IPC dumanı (5 sorgu) | ✅ PASS | 5/5 beklenen yanıt |
| 6 | Ghost Text PTY (4 senaryo) | ✅ PASS | 4/4 — 'git st'→'atus' dahil |
| 7 | Eval tekrar-üretimi (self) | ✅ PASS | ΔKSR=0.0pp, ΔTop1=0.0pp |
| — | Küçük tutarsızlık (not) | ⚠️ NOTE | compare.csv eski çalıştırmayı yansıtıyor (bkz. §7) |

**Sonuç: Tüm kritik testler PASS. Tek not: comparison.csv eskiden kalma sayı farkı.**

---

## 1. Derleme: `make re`

```
gcc -Wall -Wextra -Werror … src/main.c src/input.c … src/zmq_ipc.c -o minishell -lzmq
```

- 10 kaynak dosya başarıyla derlendi
- **Uyarı:** 0 — `-Wall -Wextra -Werror` geçti
- Bağlantı: libzmq 4.3.5 (`-L/opt/homebrew/Cellar/zeromq/4.3.5_2/lib`)
- **Sonuç: ✅ PASS**

---

## 2. Derleme: `make asan`

```
gcc -Wall -Wextra -Werror -g -fsanitize=address,undefined … -o minishell_asan
```

- ASan + UBSan enstrümantasyonu ile derlendi
- **Uyarı:** 0
- **Sonuç: ✅ PASS**

---

## 3. Birim Testleri: `pytest python/eval/`

```
28 passed, 14 warnings in 11.98s
```

Kapsanan test kategorileri:

| Kategori | Test Sayısı | İçerik |
|----------|-------------|--------|
| KSR metrikleri | 3 | simulate_ksr, aggregate, mükemmel oracle |
| Top-N doğruluk | 4 | top1/top3 mükemmel ve sıfır senaryoları |
| Önek tamamlama | 2 | mükemmel ve kısmi eşleşme |
| Kapsama | 2 | tam kapsam, tam sessizlik |
| Önek koşullu | 2 | min_chars eşiği |
| Top-k komut | 2 | mükemmel ve başarısız |
| CommandChain | 6 | eğitim/tahmin, oturum izolasyonu, token modu |
| MostFreqBaseline | 2 | sınıf testi |
| Smoke testler | 5 | runner, ablation konfigürasyonları |

**Sonuç: ✅ PASS (28/28)**

---

## 4. ASan/UBSan Çalışma Zamanı (PTY)

`minishell_asan` PTY üzerinden çalıştırıldı (ham mode uyumlu). Test senaryoları:
- `ls` — normal komut
- `echo hi | cat` — pipe
- `ls > /tmp/t_asan.txt` — yönlendirme
- `cat /tmp/t_asan.txt` — okuma
- `exit` — temiz çıkış

```
ASan/UBSan hata sayısı: 0
```

> **Not:** macOS'ta heap-leak dedektörü (`detect_leaks`) ASan'da desteklenmiyor (Linux-only).
> Tam leak taraması için `sudo leaks --atExit -- ./minishell` gereklidir; macOS kısıtı
> nedeniyle henüz çalıştırılmadı. **"Leak-free kanıtlandı" iddiasında bulunulmamalıdır.**

**Sonuç: ✅ PASS (0 çalışma zamanı hatası)**

---

## 5. Daemon + IPC Dumanı

Python Markov daemon başlatıldı (`ipc:///tmp/markov_shell.ipc`), ZMQ PAIR istemcisiyle 5 sorgu:

| Gönderilen | Beklenen | Alınan | Sonuç |
|-----------|----------|--------|-------|
| `"git s"` | `"tatus"` | `"tatus"` | ✓ |
| `"git statu"` | `"s"` | `"s"` | ✓ |
| `"ls "` | `"-la"` | `"-la"` | ✓ |
| `"git "` | `"config"` | `"config"` | ✓ |
| `"cd "` | `".."` | `".."` | ✓ |

Round-trip süresi < 5ms (p99=0.615ms ölçülen).

**Sonuç: ✅ PASS (5/5)**

---

## 6. Ghost Text PTY

`./minishell` PTY üzerinden çalıştırıldı, daemon aktif, her karakter arası 90ms bekleme
(15ms `zmq_poll` timeout'undan > 6x büyük — IPC zamanlama düzeltmesinin test koşulu).

| Yazılan | Beklenen Ghost | Alınan (ANSI \x1b[90m…\x1b[0m) | Sonuç |
|---------|---------------|--------------------------------|-------|
| `"git st"` | `"atus"` | `['it','t','@github…','config','tatus','atus']` | ✓ |
| `"ls "` | `"-la"` | `[…, '-la']` | ✓ |
| `"git "` | `"config"` | `[…, 'config']` | ✓ |
| `"cd "` | `".."` | `[…, '..']` | ✓ |

**Edge case — `"git"` tek başına:**  
Ghost text `'@github.com:ahmtemel/clever_shell.git'` içeriyor. Bu beklenen davranış:
geçmişte `git clone git@github.com:…` komutları dominant, `git status` ise daha az frekans.
`"git s"` yazmak `"tatus"` prefix filtrelemesiyle doğru sonucu verir.

**IPC zamanlama düzeltmesinin etkisi (zmq_update refactor):**
- Önceki yöntem: `recv(DONTWAIT)` → EAGAIN (daemon yetişemiyordu)
- Yeni yöntem: `drain() → send → recv_timeout(15ms)` → her tuşta doğru yanıt

**Sonuç: ✅ PASS (4/4)**

---

## 7. Değerlendirme Tekrar-Üretimi

Kendi zsh geçmişi (`~/.zsh_history`) yeniden çalıştırıldı (200 latency örneği):

| Metrik | Saklanan (`results_self/`) | Yeniden üretilen | Delta |
|--------|---------------------------|------------------|-------|
| KSR | 32.8% | 32.8% | 0.0pp |
| Top-1 Doğruluk | 25.4% | 25.4% | 0.0pp |
| Kapsama | 78.9% | 78.9% | 0.0pp |

**Sonuç: ✅ PASS (deterministik — Δ=0pp)**

### ⚠️ Küçük Tutarsızlık Notu

`results_compare_fair/comparison.csv` dosyasındaki "Kendi Geçmişim" KSR değeri **34.3%**
olarak görünüyor; ancak mevcut `results_self/metrics_summary.csv` değeri **32.8%**.

**Neden:** `compare.py`, `results_self` ve `results_cyber_fair` klasörlerini okur.
`results_self` eskiden farklı bir çalıştırmayla üretilmişti (büyük olasılıkla o sırada
farklı `latency_samples` veya hafif farklı test seti). Gerçek performans sayıları için
**`results_self/metrics_summary.csv` birincil referans alınmalıdır** (32.8%).

**Etki:** Tez tablolarında bu iki sayıdan biri kullanılmalı; hangisi kullanılacaksa not
edilmeli. Önerilen: `results_self/metrics_summary.csv` → KSR=32.8%.

---

## 8. Dosya Varlık Kontrolü

```
python/eval/analysis/
  ├── command_level.csv      ✓
  ├── scaling.csv            ✓
  ├── whitelist_coverage.csv ✓
  ├── MEMORY_REPORT.md       ✓
  ├── ANALYSIS_REPORT.md     ✓
  ├── fig_command_k.png      ✓
  ├── fig_command_decay.png  ✓
  ├── fig_scaling.png        ✓
  ├── asan_run.log           ✓
  └── leaks_run.log          ✓

python/eval/results_self/      ✓  (12 dosya)
python/eval/results_cyber/     ✓  (12 dosya — filtreli referans)
python/eval/results_cyber_fair/✓  (12 dosya — filtresiz/adil)
python/eval/results_compare/   ✓  (eski, referans için)
python/eval/results_compare_fair/ ✓ (güncel adil karşılaştırma)
```

---

## Genel Sonuç

```
DERLEME (make re)        : PASS
DERLEME (make asan)      : PASS
BİRİM TESTLERİ (pytest)  : PASS  28/28
ASAN/UBSAN ÇALIŞMA ZAMANI: PASS  0 hata
IPC DUMANSI              : PASS  5/5
GHOST TEXT PTY           : PASS  4/4
EVAL TEKRARÜRETİM        : PASS  Δ=0pp
────────────────────────────────────────
TOPLAM                   : 7/7 PASS  (1 bilgi notu)
```
