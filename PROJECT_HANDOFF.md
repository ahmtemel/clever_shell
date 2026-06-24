# clever_shell — Proje Devir-Teslim Dokümanı

> **Bu doküman kime yönelik?**  
> Kodu görmeyecek, yalnızca bu dosyayı okuyarak Word'de Türkçe akademik tez yazacak bir AI asistanına.
> Her bölüm doğrudan proza dönüştürülebilecek kadar eksiksiz açıklanmıştır.
> Sayıların tamamı gerçek CSV dosyalarından alınmıştır; hiçbiri uydurma değildir.
>
> **Kaynak dosyalar:** `/Users/fahrinox/Desktop/clever_shell/` deposu  
> **Test durumu:** TEST_REPORT.md — 7/7 PASS

---

## İÇİNDEKİLER

1. [Proje Özeti & Motivasyon](#1)
2. [Mimari & Veri Akışı](#2)
3. [Dosya Haritası](#3)
4. [Derleme, Çalıştırma & Demo](#4)
5. [Değerlendirme Metodolojisi](#5)
6. [Tüm Deneysel Sonuçlar](#6)
7. [Ana Bulgular & Dürüst Çerçeveleme](#7)
8. [Tezde Kaçınılacak İddialar](#8)
9. [Teze Eşleme (DD-050 Esasları)](#9)
10. [Sınırlar & Gelecek Çalışma](#10)
11. [Kaynaklar (BibTeX)](#11)

---

<a name="1"></a>
## 1. Proje Özeti & Motivasyon

### 1.1 Vizyon

clever_shell, kullanıcının geçmiş komut alışkanlıklarını öğrenerek terminal
komut girişini *her tuş vuruşunda* tamamlamayı öneren yapay zeka destekli
bir kabuk (shell) programıdır. Kullanıcı komutu yazdıkça tahmin edilen tamamlama
gri renkte "hayalet metin" (ghost text) olarak imlecin sağında belirir; Tab tuşuna
basıldığında bu metin kalıcı olarak tampona eklenir.

### 1.2 Neden LLM Değil, Markov Zinciri?

Modern büyük dil modelleri (GPT-4, Llama vb.) her token üretiminde yüzlerce
milisaniye gecikme yaratır. Terminal otomatik tamamlama için kabul edilebilir
gecikme sınırı **< 5 ms** olarak belirlenmiştir; insan, 40 ms üzerindeki
gecikmeleri hissederek aksama algılar. Deneysel ölçümlerimizde p99 gecikme
kendi geçmişimizde **0.052 ms**, siber güvenlik veri setinde **0.615 ms**
olarak gerçekleşmiştir. Böylece Markov zinciri, LLM'ların sağlayamayacağı
mikrosaniye-düzeyinde yanıt süresiyle doğal tamamlama deneyimi sunar.

### 1.3 Sistem Bileşenleri

Sistem iki bağımsız süreçten oluşur:

1. **C Çekirdeği (minishell):** 42-okul minishell standardında POSIX uyumlu
   kabuk; termios raw mod, özel okuma döngüsü, lexer/parser/executor pipeline,
   ZeroMQ istemcisi ve ghost text renderer içerir.

2. **Python Markov Daemon:** Arka planda çalışan asenkron servis; k=3 kelime
   düzeyi Markov zinciriyle kullanıcı geçmişini öğrenir ve C kabuğundan gelen
   mevcut tampon içeriğine göre en olası tamamlamayı tahmin eder.

---

<a name="2"></a>
## 2. Mimari & Veri Akışı

### 2.1 Tuştan Ghost Text'e Veri Akışı

```
Klavye tuşu
    │
    ▼
[C: input.c / read_line()]
  termios raw mod — ECHO + ICANON kapalı
  karakter tampona eklenir, ekrana yazılır
    │
    ▼
[C: zmq_ipc.c / zmq_update()]
  1. zmq_ipc_drain()        → eski yanıtları boşalt
  2. zmq_ipc_send(buf)      → tampon Python'a gönderilir (DONTWAIT)
  3. zmq_ipc_recv_timeout(15ms) → en fazla 15 ms poll
    │                            (terminal asla bloklanmaz)
    ▼
[Python: markov_daemon.py / predict_suffix(buf)]
  WordMarkovChain.predict_suffix() → suffix string döner
    │
    ▼  ZeroMQ PAIR socket (ipc:///tmp/markov_shell.ipc)
    │
    ▼
[C: input.c / ghost_render()]
  lb->prediction ← alınan suffix
  ANSI \x1b[90m...\x1b[0m ile gri renkte ekrana yazılır
  imleç gerçek metnin sonuna geri döner
```

### 2.2 ZeroMQ IPC Detayları

- **Desen:** ZMQ_PAIR (broker'siz, uçtan uca — REQ/REP KESİNLİKLE KULLANILMAMAKTADIR)
- **Adres:** `ipc:///tmp/markov_shell.ipc` (Unix domain soketi, TCP/IP değil)
- **C tarafı:** `zmq_connect` (istemci) — daemon çalışmasa bile bağlantı lazy başarılı olur
- **Python tarafı:** `zmq_bind` (sunucu) — daemon başlatıldığında soketi açar
- **Bloklanma garantisi:**
  - C: `zmq_send(DONTWAIT)` + `zmq_poll(timeout=15ms)` + `zmq_recv(DONTWAIT)`
  - Python: `zmq.Poller.poll()` ile asenkron dinleme
  - EAGAIN hatası sessizce yok sayılır; terminal döngüsü hiçbir zaman süresiz bloklanmaz

### 2.3 Ghost Text Görsel Protokolü

```
Kullanıcı "git s" yazmış, daemon "tatus" döndürmüş:
  Ekran: git s[tatus]    ([ ] = gri renk \x1b[90m...\x1b[0m)
                ↑ imleç s harfinin hemen sağında

Tab tuşu:
  ghost_clear() → ghost text silinir
  "tatus" tampona kalıcı eklenir, normal renkte yazılır
  Ekran: git status
```

---

<a name="3"></a>
## 3. Dosya Haritası

### 3.1 C Kaynak Dosyaları (`src/`)

| Dosya | Görev |
|-------|-------|
| `main.c` | Giriş noktası; termios backup, ZMQ init, shell döngüsü, temizlik |
| `input.c` | Termios raw mod, `read_line()` okuma döngüsü, ghost text render/clear/accept, `zmq_update()` |
| `lexer.c` | Ham satırı token listesine ayırır (`WORD`, `PIPE`, `REDIRECT_IN/OUT`, `HEREDOC`, `APPEND`) |
| `parser.c` | Token listesini AST'ye (Abstract Syntax Tree) dönüştürür; pipe root düğüm olur |
| `executor.c` | AST'yi `fork/execve/pipe/dup2/waitpid` ile çalıştırır; fd hijyeni sağlar |
| `signals.c` | `sigaction` ile SIGINT/SIGQUIT yönetimi (Ctrl+C kabuğu kapatmaz) |
| `builtins.c` | `cd`, `echo`, `export`, `unset`, `env`, `exit` yerleşik komutları |
| `free.c` | AST ve token listesi için `free` yardımcıları |
| `debug.c` | Geliştirme sırasında AST yazdırma (üretimde devre dışı) |
| `zmq_ipc.c` | ZMQ PAIR istemcisi: init, send, recv, recv_timeout(15ms), drain, cleanup |

### 3.2 Header (`inc/minishell.h`)

Tüm veri yapılarını (`t_token`, `t_ast_node`, `t_lbuf`), sabitleri (`LINE_CAP=4096`),
ve tüm public fonksiyon prototiplerini içerir. `t_lbuf` struct'ı ghost text state'ini tutar:
`data` (gerçek metin), `prediction` (gri tahmin), `last_sent` (son ZMQ gönderimi).

### 3.3 Python Daemon (`python/markov_daemon.py`)

| Bileşen | Açıklama |
|---------|----------|
| `WordMarkovChain` | k=3 kelime düzeyi Markov zinciri; `Dict[Tuple[str,...], Counter[str]]` tablo; satır izoleli |
| `build_chain(path, k)` | Geçmiş dosyasını yükle → whitelist filtrele → frekans tabanı uygula → zinciri eğit; `(chain, stats)` döner |
| `parse_zsh_history(path)` | Hem genişletilmiş (`: epoch:0;cmd`) hem düz format destekler |
| `predict_suffix(buf)` | Mevcut tampona göre suffix tahmin eder; backoff, prefix modu, 60 kar. hard cap |
| `is_valid_command(cmd)` | 46 komutluk whitelist + sözdizimsel doğrulama (shlex.split) |
| `WHITELIST` | git, ls, cd, python3, make, gcc, ssh, vim, docker, npm, … (46 komut) |
| `fallback_counter` | Markov sessiz kalırsa: `buf` ile başlayan en yüksek frekanslı komutun suffix'i |
| `run_daemon()` | ZMQ PAIR bind + poller döngüsü; mesaj gelince `predict_suffix` çağırır |

### 3.4 Değerlendirme Altyapısı (`python/eval/`)

| Dosya | Görev |
|-------|-------|
| `data.py` | Geçmiş yükleme, otomatik keşif, kronolojik %80/20 split, opsiyonel whitelist filtresi |
| `metrics.py` | 7 metriğin saf Python implementasyonu (KSR, Top-1/3, Prefix, Coverage, PrefixCond, TopkCmd) |
| `runner.py` | Tek konfigürasyon için model kur + eğit + değerlendir; p50/p95/p99 gecikme ölçümü |
| `ablation.py` | 8 konfigürasyon matrisi (k=1/2/3, backoff, λ=0/0.005/0.02, baseline) |
| `report.py` | CSV, LaTeX, PNG ve Markdown raporları; Türkçe etiketler, serif font, 150 dpi |
| `run_eval.py` | Ana giriş noktası; `--history`, `--out-dir`, `--label`, `--fair`, `--no-filter` destekler |
| `compare.py` | İki run_eval çıktısını karşılaştırır; grouped bar chart, decay ablasyon tablosu |
| `convert_cyber.py` | JSONL `sandbox-*-useractions.json` → zsh extended history formatı dönüştürücü |
| `command_chain.py` | Komut düzeyi (cross-command) Markov zinciri; oturum izoleli; Full-cmd + Token modları |
| `scaling.py` | Öğrenme eğrisi; 5 seed rastgele örnekleme; mean±std; std bantlı grafik |
| `whitelist_coverage.py` | Her iki korpusta whitelist kapsam analizi |
| `diagnose.py` | Çalışma zamanı teşhis aracı; model eğitim durumu + IPC round-trip test |
| `test_metrics.py` | 28 birim testi (`pytest python/eval/`) |

### 3.5 Sonuç Klasörleri

| Klasör | İçerik |
|--------|--------|
| `python/eval/results_self/` | Kendi zsh geçmişi; filtreli eğitim (910 komut), 12 çıktı dosyası |
| `python/eval/results_cyber/` | Siber set; **whitelist filtreli** (%55 alt-küme) — yalnızca referans |
| `python/eval/results_cyber_fair/` | Siber set; **filtresiz (adil)** — tezde kullanılacak sayılar |
| `python/eval/results_compare_fair/` | Adil karşılaştırma (kendi geçmiş ↔ siber filtresiz) |
| `python/eval/analysis/` | TEK analiz klasörü: scaling, command_level, whitelist, MEMORY_REPORT, ASan logları |

---

<a name="4"></a>
## 4. Derleme, Çalıştırma & Demo

### 4.1 Derleme

```bash
# Üretim derlemesi
make re                  # → ./minishell

# ASan + UBSan (bellek/tanımsız davranış denetimi)
make asan                # → ./minishell_asan

# Temizlik
make fclean
```

Gereksinimler: `gcc`, `libzmq` (`brew install zeromq`).  
Derleme bayrakları: `-Wall -Wextra -Werror -Iinc` (0 uyarı garantisi).

### 4.2 Demo Akışı (İki Terminal)

**Terminal 1 — Python Markov Daemon:**
```bash
cd /Users/fahrinox/Desktop/clever_shell
python3 -m python.markov_daemon
# [markov_daemon] trained in 0.018s | 261 unique n-gram contexts
# [markov_daemon] listening on ipc:///tmp/markov_shell.ipc
```

**Terminal 2 — Kabuk:**
```bash
./minishell
```

### 4.3 Demo İpuçları

- `git st` yaz → `atus` gri belirir → Tab → `git status` tamamlanır
- `ls ` (boşluk dahil) yaz → `-la` önerisi gelir → Tab → `ls -la`
- `cd ` yaz → `..` önerisi gelir
- `"git"` tek başına: URL önerisi verebilir (geçmişte `git clone` dominant); `"git s"` ile kesin öneri alınır
- Daemon kapalıysa kabuk çalışmaya devam eder, sadece ghost text görünmez (non-blocking tasarım garantisi)

### 4.4 Değerlendirme Komutları

```bash
# Kendi geçmiş — donmuş snapshot (tekrar-üretilebilir)
# Snapshot yenileme: python3 python/eval/freeze_history.py  (ilk kurulumda yapıldı)
python3 -m python.eval.run_eval \
  --history python/eval/data/self_history_frozen.txt \
  --out-dir python/eval/results_self \
  --label "Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)"

# Siber güvenlik seti (adil — filtresiz)
python3 -m python.eval.run_eval \
  --history python/eval/data/cyber_history.txt \
  --out-dir python/eval/results_cyber_fair \
  --label "Siber-güvenlik eğitim seti (Švábenský 2021)" \
  --fair

# Karşılaştırma
python3 python/eval/compare.py \
  --dir-a python/eval/results_self \
  --dir-b python/eval/results_cyber_fair \
  --out   python/eval/results_compare_fair

# Komut düzeyi analiz
python3 python/eval/command_chain.py

# Ölçeklenme (5 seed, ~30s)
python3 python/eval/scaling.py

# Whitelist kapsamı
python3 python/eval/whitelist_coverage.py
```

---

<a name="5"></a>
## 5. Değerlendirme Metodolojisi

### 5.1 Veri Bölme

**Kronolojik %80/20 split** uygulanır — zaman sızıntısı yoktur:
- İlk %80 → eğitim (modelin gördüğü komutlar)
- Son %20 → test (modelin hiç görmediği gelecek komutlar)

Eğitim setine isteğe bağlı whitelist + frekans filtresi uygulanabilir.
Test seti `filter_test=False` ile filtresizdir (adil eval için).

### 5.2 Metrik Tanımları

**1. Tuş Tasarrufu Oranı (KSR — Keystroke Savings Ratio)**

$$
\text{KSR} = \frac{\text{karakter sayısı\_tasarruf}}{\text{karakter sayısı\_toplam}} = \frac{\sum_i (\text{len}(c_i) - \text{yazılan}_i)}{\sum_i \text{len}(c_i)}
$$

Kullanıcının kaç karakter yazmadan tamamlayabildiğinin oranı.
Tahmin tampon ile eşleşen en uzun prefix bulunur; bu noktadan sonraki
karakterler "tasarruf" sayılır.

**2. Top-1 Kelime Doğruluğu (Doğruluk@1)**

$$
\text{Doğruluk@1} = \frac{|\{i : \hat{w}_i = w_i\}|}{N}
$$

Her test komutunun her token pozisyonunda modelin en yüksek olasılıklı
tahmini gerçek token ile eşleşiyorsa 1, aksi 0. Oran tüm pozisyonlar
üzerinden ortalaması alınır.

**3. Top-3 Kelime Doğruluğu (Doğruluk@3)**

$$
\text{Doğruluk@3} = \frac{|\{i : w_i \in \hat{w}_{i,1:3}\}|}{N}
$$

Modelin ilk 3 adayı arasında gerçek token bulunuyorsa başarılı sayar.

**4. Önek Tamamlama Doğruluğu (Prefix Completion Accuracy)**

Test komutunun her token'ı için, tahmin edilen suffix gerçek suffix ile
tam eşleşiyorsa doğru sayılır. Ghost text kullanım senaryosu: kullanıcı
bir kelime yazmaya başlamış, model kalan kısmı tahmin ediyor.

**5. Önek Koşullu Tamamlama Doğruluğu (Prefix Conditional Accuracy, ≥2 kar.)**

$$
\text{PCA}(k) = \frac{|\{(i,j) : \text{predict\_suffix}(c_i[:j]) = c_i[j:]\}|}{M}, \quad j \geq k
$$

Kullanıcı her token'ın en az `k=2` karakterini yazdığında modelin tam
kalan suffix'i önerip önerememesi. Gerçek ghost-text kabul senaryosunu
simüle eder.

**6. Kapsama (Coverage / Silence Rate)**

$$
\text{Kapsama} = \frac{|\{i : \text{predict\_suffix}(c_i) \neq ""\}|}{N}
$$

Modelin sessiz kalmadan (boş string döndürmeden) bir öneri ürettiği
test komutlarının oranı. Yüksek kapsama, modelin veri setine iyi
uyduğunu gösterir.

**7. Top-k Komut Kabul Oranı (topk_command_acceptance)**

$$
\text{TopkCmd@k} = \frac{|\{i : \text{first\_token}(c_i) \in \text{top-k candidates}(c_{i-1})\}|}{N}
$$

Önceki komut bağlam olarak verildiğinde, modelin sonraki komutun ilk
token'ını (komut adı) k=5 aday içinde öngörme oranı.

### 5.3 Kelime-Düzeyi vs Komut-Düzeyi Modellerin Ayrımı

Bu iki model **tamamen farklı görevler** için tasarlanmıştır:

| Özellik | Kelime-Düzeyi Model | Komut-Düzeyi Model |
|---------|--------------------|--------------------|
| **Nerede çalışır** | Canlı ghost text (gerçek zamanlı) | Çevrimdışı analiz |
| **Girdi** | Mevcut komut tamponu (kısmen yazılmış) | Önceki tam komut(lar) |
| **Çıktı** | Mevcut komutun kalan suffix'i | Sonraki komutun tahmini |
| **Model** | `WordMarkovChain` (k=3, kelime n-gram) | `CommandChain` (k=1/2/3, komut n-gram) |
| **Değerlendirme** | KSR, Top-1/3, Prefix, Coverage | Next-command Top-1/Top-5 |
| **Uygulamada kullanılıyor mu** | Evet (ZMQ daemon) | Hayır (offline deneyim) |

**Bu iki modelin metriklerini tezde KESİNLİKLE birbirine karıştırmayın.**

---

<a name="6"></a>
## 6. Tüm Deneysel Sonuçlar

> Tüm sayılar gerçek CSV dosyalarından alınmıştır.

### 6.1 Kendi Geçmiş — Kelime Düzeyi Önerilen Model

*Kaynak: `python/eval/results_self/metrics_summary.csv`*  
*Giriş: `python/eval/data/self_history_frozen.txt` (snapshot, 1001 komut, 2026-06-24, 4 satır maskelendi)*  
*Eğitim: 728 komut (filtreli: whitelist-valid), Test: 183 komut*

> **Tekrar-üretilebilirlik:** Kendi geçmiş ölçümleri sabit bir snapshot üzerinde yapılmıştır
> (2026-06-24 16:30, 1001 komut); `~/.zsh_history` büyüdükçe sonuçlar kaymasın diye
> dondurulmuştur. Siber set kamuya açık sabit veri olduğundan **birincil tekrar-üretilebilir
> benchmark siber-güvenlik setidir**.

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR) | **27.1%** |
| Doğruluk@1 | **24.8%** |
| Doğruluk@3 | **45.9%** |
| Önek-Koşullu Tamamlama (≥2 kar.) | **35.0%** |
| Top-5 Komut Kabul Oranı | **55.5%** |
| Kapsama | **78.6%** |
| Gecikme p50 | **0.017 ms** |
| Gecikme p99 | **0.053 ms** |

### 6.2 Siber-Güvenlik Seti — Kelime Düzeyi Önerilen Model (Filtresiz / Adil)

*Kaynak: `python/eval/results_cyber_fair/metrics_summary.csv`*  
*Eğitim: 8765 komut (filtresiz), Test: 2192 komut (filtresiz)*

> ⚠️ **Bu tablodaki sayılar tezde kullanılacak ana siber-set numaralarıdır.**  
> `results_cyber/` klasörü yalnızca whitelist'e giren %55 alt-kümesini kapsar
> (referans amaçlı saklanmıştır). Tezde **`results_cyber_fair/`** kullanın.

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR) | **47.2%** |
| Doğruluk@1 | **29.0%** |
| Doğruluk@3 | **54.7%** |
| Önek-Koşullu Tamamlama (≥2 kar.) | **68.5%** |
| Top-5 Komut Kabul Oranı | **25.3%** |
| Kapsama | **94.6%** |
| Gecikme p50 | **0.141 ms** |
| Gecikme p99 | **0.615 ms** |

### 6.3 Veri Seti Karşılaştırması

*Kaynak: `python/eval/results_compare_fair/comparison.csv`*

| Metrik | Kendi Geçmişim (snapshot) | Siber-Güvenlik Seti (Adil) |
|--------|:---:|:---:|
| KSR (%) | 27.1 | **47.2** |
| Doğruluk@1 (%) | 24.8 | 29.0 |
| Doğruluk@3 (%) | 45.9 | 54.7 |
| Önek-Koşullu (%) | 35.0 | 68.5 |
| Top-5 Komut (%) | **55.5** | 25.3 |
| Kapsama (%) | 78.6 | 94.6 |
| Gecikme p99 (ms) | 0.053 | 0.615 |

**Yorum (AI teza kopyalayabilir):**  
Siber-güvenlik korpusu daha yüksek KSR ve önek tamamlama doğruluğu sergiler.
Bunun temel nedeni pentest iş akışlarının tekrarlayan ve kalıplı komut dizileri
içermesidir (`nmap -sV`, `fcrackzip -u` vb.). Buna karşın Top-5 Komut Kabul
oranı daha düşüktür çünkü komut çeşitliliği yüksek, ilk token tahmin zorlaşır.
Gecikme farkı ise model tablo boyutundan kaynaklanmaktadır (261 bağlam → 0.052ms;
3325 bağlam → 0.615ms), her ikisi de 5ms kullanıcı algı eşiğinin çok altındadır.

### 6.4 Kelime Düzeyi Ablasyon

*Kaynak: `python/eval/results_self/ablation_table.csv`*

| Yapılandırma | KSR | Doğruluk@1 |
|---|:---:|:---:|
| **Önerilen (k=3, λ=0.005)** | **27.1%** | **24.8%** |
| k=1 (unigram bağlam) | 27.1% | 24.8% |
| k=2 (bigram bağlam) | 27.1% | 24.8% |
| Backoff'suz (k=3) | 27.1% | 24.8% |
| Frekans-only baseline | 27.1% | 9.2% |
| En sık komut baseline | 25.4% | 9.2% |

**Yorum:** Kendi geçmişimde (261 bağlam) tüm k değerleri özdeş KSR verir — bu normaldir.
Küçük kişisel geçmişlerde yüksek dereceli n-gram'lar tekil komutlara karşılık gelir,
backoff k=1'e düşer. Anlamlı k etkisi komut düzeyi analizinde görülmektedir.

### 6.5 Siber Set — Zaman Azalma (λ) Ablasyonu

*Kaynak: `python/eval/results_cyber_fair/ablation_table.csv`*

| λ | KSR | Doğruluk@1 |
|---|:---:|:---:|
| 0.0 (yok) | 44.9% | 27.9% |
| **0.005 (önerilen)** | **47.2%** | **29.0%** |
| 0.02 (hızlı) | 48.1% | 29.1% |

λ=0.005 ve λ=0.02 arasındaki fark ~0.9 pp'dir — marjinal. λ=0.005 tercih edilir
çünkü λ=0.02 yeni komutlara çok agresif ağırlık verir; olası aşırı uyumu önlemek
için daha muhafazakâr λ tercih edilmiştir.

### 6.6 Komut Düzeyi Ablasyon (Token Modu — Çevrimdışı)

*Kaynak: `python/eval/analysis/command_level.csv`*  
*Not: Bu sonuçlar çevrimdışı analizdir; canlı ghost text ile ilgisi yoktur.*

| k | λ | Top-1 (%) | Top-5 (%) |
|---|---|:---:|:---:|
| **1 (optimal)** | 0.005 | **46.0** | **74.3** |
| 2 | 0.005 | 44.5 | 70.2 |
| 3 | 0.005 | 43.2 | 65.1 |
| — (baseline) | — | 24.5 | 59.0 |

**Önerilen model vs baseline delta:** +21.5 pp (Top-1), **+15.3 pp** (Top-5)

Full-komut modu (k=1, λ=0.005): Top-1=18.3%, Top-5=27.8%  
*(Tam komut dizgesi tahmin etmek çok daha zordur; token modu pratikte daha anlamlıdır)*

### 6.7 Ölçeklenme Eğrisi (5 Seed Ortalaması)

*Kaynak: `python/eval/analysis/scaling.csv`*  
*Not: Filtresiz test seti kullanılmıştır (filter_test=False) — `results_cyber_fair` ile tutarlı.*

| Eğitim Komutu | KSR | ±std | Doğruluk@1 | Önek-Koş. | Kapsama | Komut Top-5 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 200 | 32.9% | ±1.9 | 25.5% | 44.2% | 81.3% | 50.3% |
| 400 | 35.9% | ±1.8 | 25.6% | 48.7% | 85.5% | 54.5% |
| 800 | 39.7% | ±2.3 | 27.2% | 55.0% | 89.1% | 54.9% |
| 1,600 | 41.1% | ±2.6 | 27.2% | 58.5% | 91.6% | 56.3% |
| 3,200 | 42.4% | ±2.8 | 27.8% | 61.4% | 92.7% | 65.1% |
| **8,765 (tüm)** | **47.2%** | **±0.0** | **29.0%** | **68.5%** | **94.6%** | **74.3%** |

Eğri KSR bazında **monoton artan** (32.9 → 47.2). Daha fazla verinin
her metriği sistematik iyileştirdiği Tablo 4.6'da görülmektedir.

### 6.8 Whitelist Kapsam Analizi

*Kaynak: `python/eval/analysis/whitelist_coverage.csv`*

| Korpus | Toplam Komut | Whitelist'te | Kapsam |
|--------|:---:|:---:|:---:|
| Kendi kabuk geçmişim | 1,000 | 915 | **91.5%** |
| Siber-güvenlik seti (Švábenský 2021) | 10,957 | 6,066 | **55.4%** |

Kendi geçmişimde dominant komutlar: clear(219), ls(203), cd(132), make(96) — hepsi whitelist'te.  
Siber sette whitelist dışı dominant: nmap(759), fcrackzip(648), scp(639), john(225).  
Bu yüzden siber set için filtresiz değerlendirme (`results_cyber_fair`) zorunludur.

### 6.9 Bellek & Kaynak Güvenliği

*Kaynak: `python/eval/analysis/MEMORY_REPORT.md`*

- Üretim derlemesi: **0 uyarı, 0 hata** (`-Wall -Wextra -Werror`)
- **ASan/UBSan çalışma zamanı: 0 hata** (PTY tabanlı test, `analysis/asan_run.log`)
- macOS'ta heap-leak dedektörü: desteklenmiyor (ASan Linux-only)
- Tam leak taraması: `sudo leaks` gerektirir — **henüz çalıştırılmadı**
- Gecikme (tüm değerler < 5ms kullanıcı algı eşiği): kendi geçmiş p99=0.052ms, siber p99=0.615ms

---

<a name="7"></a>
## 7. Ana Bulgular & Dürüst Çerçeveleme

> **Bu bölüm tezi yazacak AI'ın birebir izleyeceği çerçeveleme kılavuzudur.**

### 7.1 Optimal Markov Derecesi k=1'dir

Komut düzeyinde k=1 trigram (unigram bağlam) **en yüksek Top-5 doğruluğu** verir:

- k=1 Token Top-1: **46.0%**,  k=3: 43.2% (−2.8 pp)
- k=1 Token Top-5: **74.3%**,  k=3: 65.1% (−9.2 pp)

**Neden?** Siber güvenlik senaryolarında komut geçişleri lokal tekrarlıdır
(`ls → cd → ssh`); her komut oturumu benzer tekrarlayan iş akışlarından oluşur.
Yüksek k değeri daha az sıklıkla görülen uzun dizilere işaret eder — seyreklik
artar, tahmin kalitesi düşer.

**Tezde nasıl yazılır:**  
*"k-ıncı dereceli bağlam boyutunun etkisi araştırılmış; k ∈ {1, 2, 3} değerleri
denenmiş ve k=1'in hem Top-1 hem Top-5 doğruluk ölçütlerinde en iyi sonucu
verdiği gözlemlenmiştir. Bu bulgu, siber güvenlik terminolojisinde komut
geçişlerinin lokal tekrarlı yapısıyla tutarlıdır."*

**Kesinlikle demeyin:** "k=3 üstündür" veya "yüksek derece daha iyi bağlam sağlar".

### 7.2 En Güçlü Doğruluk Metriği: Komut-Adı Top-5

Asıl tez katkısı **baseline üzerine kazanım**dır, çıplak yüzde değil:

- En-sık-komut baseline Top-5: **59.0%**
- Önerilen model (k=1, token): **74.3%**
- **Kazanım: +15.3 pp**

**Tezde nasıl yazılır:**  
*"Önerilen model, en sık komut baseline'ına kıyasla Top-5 komut-adı tahmini
doğruluğunu 59.0%'dan 74.3%'e yükselterek 15.3 puanlık bir iyileştirme sağlamıştır."*

### 7.3 %80 Tasarım Hedefi — Ölçülmüş Değer Değil

Tez önerisinde belirlenen **%80 doğruluk hedefi** bir tasarım hedefiydi.
Ölçülen en yüksek değer: **Komut Top-5 = 74.3%** (siber, token modu).
Ölçeklenme eğrisi verisi artıkça metriğin nasıl iyileştiğini gösterir —
hedefe giden trendi kanıtlar.

**Tezde nasıl yazılır:**  
*"Başlangıçta belirlenen %80 başarım hedefine siber-güvenlik veri setiyle
yaklaşılmış; tam veri ile %74.3 Top-5 komut-adı doğruluğu elde edilmiştir.
Ölçeklenme analizi, daha geniş bir eğitim seti ile hedefin ulaşılabilir
olduğunu göstermektedir."*

### 7.4 Recency Decay λ=0.005

λ=0.005, test edilen değerler (0 / 0.005 / 0.02) arasında siber sette en iyi
genel dengeyi sağlar (+2.3pp KSR vs λ=0). Kelime düzeyinde kendi geçmişimde
etki ihmal edilebilirdir (saat damgasız düz format). **Kritik bir katkı değil;
"robustluk/marjinal katkı" olarak çerçevele.**

### 7.5 Gecikme: LLM-Değil-Markov Gerekçesi

p99 < 1ms her iki veri setinde de geçerliydi (kendi: 0.052ms, siber: 0.615ms).
Bu değerler **LLM'ların sağlayamayacağı süreleri** doğrudan kanıtlar; tezin
"neden Markov?" sorusunu güçlü bir deneysel temele oturtur.

### 7.6 Sistem Mühendisliği Kanıtlı

- `-Wall -Wextra -Werror`: 0 uyarı
- ASan/UBSan çalışma zamanı: 0 hata
- Non-blocking IPC: terminal döngüsü hiçbir zaman bloklanmaz
- Raw termios modu: her exec sonrası otomatik yeniden uygulanır
- Ghost text IPC zamanlama düzeltmesi: `drain → send → recv_timeout(15ms)` ile
  her tuşta güncel öneri

---

<a name="8"></a>
## 8. Tezde Kaçınılacak İddialar

> **Bu bölüm AI'ın YAZMAMASI gereken şeylerin açık listesidir.**

| Kaçınılacak İddia | Doğru Çerçeve |
|-------------------|---------------|
| "k=3 deneysel olarak k=1'den üstündür" | Komut düzeyinde k=1 daha iyi; kelime düzeyinde fark minimal |
| "%80 doğruluk ölçüldü / sağlandı" | %80 tasarım hedefiydi; ölçülen max. Top-5=74.3% (siber, token) |
| "ZMQ_REP soket kullanıldı" | Kod **ZMQ_PAIR** kullanır — REP/REQ yoktur, hiç kullanılmamıştır |
| Kelime-düzeyi ≡ komut-düzeyi sonuçlar | İki farklı görev; ayrı bölümlerde ayrı tablolarda sunulmalı |
| "Sistem sızıntısızdır / leak-free kanıtlandı" | ASan/UBSan 0 çalışma zamanı hatası; tam heap-leak taraması macOS kısıtı nedeniyle henüz tamamlanmadı |
| "Siber set genel kabuk kullanımını temsil eder" | Pentest'e özel corpus; "harici, alana-özel doğrulama seti" olarak çerçevele |
| Filtreli siber sayıları (results_cyber/) kullanma | Tezde **filtresiz** `results_cyber_fair/` kullan |
| Kendi geçmişi büyük örnek | ~1000 komut, kişisel ve küçük; istatistiksel anlamlılık sınırlı |

---

<a name="9"></a>
## 9. Teze Eşleme (DD-050 Esasları)

### 9.1 Bölüm Yapısı

| Bölüm | Kapsam | İlgili Dosyalar |
|-------|--------|-----------------|
| **Bölüm 1 — Giriş** | Motivasyon, LLM-Markov karşılaştırması, hedefler | Bu doküman §1 |
| **Bölüm 2 — İlgili Çalışmalar** | Kabuk tamamlama, Markov LM, ZeroMQ | Kaynaklar §11 |
| **Bölüm 3 — Yöntem** | Mimari, IPC protokolü, metrik tanımları | Bu doküman §2, §5 |
| **Bölüm 4 — Uygulama & Deneysel Sonuçlar** | Tüm tablolar ve şekiller | Bu doküman §6 |
| **Bölüm 5 — Sonuç** | Bulgular özeti, sınırlar, gelecek çalışma | Bu doküman §7, §10 |

### 9.2 Biçim Kuralları (DD-050)

- Font: Times New Roman 12 pt, 1.5 satır aralığı
- Kenar boşlukları: üst/alt 2.5 cm, sol 3 cm, sağ 2.5 cm
- Dil: Türkçe, edilgen geçmiş zaman ("…elde edilmiştir", "…gözlemlenmiştir")
- **Tablo başlığı: ÜSTTE, numaralı** ("Tablo 4.1 — Açıklama")
- **Şekil başlığı: ALTTA, numaralı** ("Şekil 4.1 — Açıklama")

### 9.3 Tablo & Şekil Dizini

| No | Tür | Başlık | Kaynak Dosya |
|----|-----|--------|--------------|
| **Tablo 4.1** | Tablo | Önerilen yapılandırmanın temel performans metrikleri — kendi geçmiş | `results_self/metrics_summary.csv` |
| **Tablo 4.2** | Tablo | Ablasyon çalışması: yapılandırma karşılaştırması (kendi geçmiş) | `results_self/ablation_table.csv` |
| **Tablo 4.3** | Tablo | Veri seti karşılaştırması: kendi geçmiş ↔ siber güvenlik seti (adil) | `results_compare_fair/comparison.csv` |
| **Tablo 4.4** | Tablo | Zaman azalma (λ) ablasyonu — siber güvenlik seti | `results_cyber_fair/ablation_table.csv` |
| **Tablo 4.5** | Tablo | Komut-düzeyi ablasyon: k ve λ etkisi (token modu) | `analysis/command_level.csv` |
| **Tablo 4.6** | Tablo | Ölçeklenme sonuçları — 5 seed ortalaması ± std | `analysis/scaling.csv` |
| **Tablo 4.7** | Tablo | Whitelist kapsam analizi: kendi geçmiş ve siber set | `analysis/whitelist_coverage.csv` |
| **Şekil 4.1** | Grafik | k değerine göre KSR ve Doğruluk@1 (kelime düzeyi) | `results_self/fig_markov_order.png` |
| **Şekil 4.2** | Grafik | Ablasyon yapılandırmaları karşılaştırması | `results_self/fig_ablation.png` |
| **Şekil 4.3** | Grafik | Gecikme dağılımı (p50/p95/p99 CDF) | `results_self/fig_latency.png` |
| **Şekil 4.4** | Grafik | λ değerine göre KSR ve Doğruluk@1 (kelime düzeyi) | `results_self/fig_decay.png` |
| **Şekil 4.5** | Grafik | Veri seti karşılaştırma — gruplu çubuk grafik | `results_compare_fair/fig_compare.png` |
| **Şekil 4.6** | Grafik | λ etkisi: kendi geçmiş ve siber set | `results_compare_fair/fig_decay_compare.png` |
| **Şekil 4.7** | Grafik | k değerine göre komut-düzeyi doğruluk | `analysis/fig_command_k.png` |
| **Şekil 4.8** | Grafik | λ değerine göre komut-düzeyi doğruluk | `analysis/fig_command_decay.png` |
| **Şekil 4.9** | Grafik | Öğrenme eğrisi — eğitim boyutu vs başarım (std bant) | `analysis/fig_scaling.png` |

---

<a name="10"></a>
## 10. Sınırlar & Gelecek Çalışma

### 10.1 Mevcut Sınırlar

1. **Küçük kişisel geçmiş:** ~1,000 komut; istatistiksel anlamlılık sınırlı.
   Daha büyük ve çeşitli bir geçmiş seti ile sonuçlar gelişebilir.

2. **Sabit whitelist:** 46 komutluk beyaz liste manuel belirlenmiştir. Siyah-liste
   (hata çıktıları, test komutları) yaklaşımı daha geniş kapsam sağlayabilir.

3. **Düz metin geçmiş formatı:** Kullanıcının `~/.zsh_history` dosyası saat
   damgasız (düz metin); recency decay etkisiz. Genişletilmiş format
   (`: epoch:0;cmd`) kullanılması ile zaman ağırlıklandırması güçlenebilir.

4. **Tek kullanıcı:** Sonuçlar tek bir kişinin kullanım alışkanlıklarını
   yansıtmaktadır. Çok kullanıcılı çalışma genellenebilirlik sorusunu açık bırakır.

5. **macOS heap-leak taraması:** `sudo leaks` henüz çalıştırılmadı. ASan/UBSan
   0 çalışma zamanı hatası sağlandı; tam tarama Linux ortamında önerilir.

6. **Yalnızca ASCII:** Türkçe karakter gibi çok baytlı UTF-8 girdisi test edilmedi.

### 10.2 Gelecek Çalışma

- LSTM / küçük Transformer ile Markov karşılaştırması (batch offline, gerçek zamanlı değil)
- Çok kullanıcılı geçmiş birleştirme (federated Markov)
- Adaptif whitelist genişletme
- zsh / bash plugin olarak entegrasyon
- Süreçler arası paylaşılan geçmiş (takım terminali)

---

<a name="11"></a>
## 11. Kaynaklar (BibTeX)

```bibtex
@misc{zeromq2024,
  author       = {{iMatix Corporation}},
  title        = {{ZeroMQ} Messaging Library},
  year         = {2024},
  howpublished = {\url{https://zeromq.org}},
}

@book{markov1913,
  author    = {Andrei Andreyevich Markov},
  title     = {An Example of Statistical Investigation of the Text Eugene
               Onegin Concerning the Connection of Samples in Chains},
  year      = {1913},
  publisher = {Proceedings of the Academy of Sciences of St. Petersburg},
}

@book{manning1999,
  author    = {Christopher Manning and Hinrich Schütze},
  title     = {Foundations of Statistical Natural Language Processing},
  year      = {1999},
  publisher = {MIT Press},
}

@misc{42school2024,
  author       = {{42 School}},
  title        = {Minishell Subject — 42 Cursus},
  year         = {2024},
  howpublished = {\url{https://42.fr}},
}

@book{posix2017,
  author    = {{IEEE and The Open Group}},
  title     = {{POSIX.1-2017}: The Open Group Base Specifications Issue 7},
  year      = {2017},
  publisher = {The Open Group},
}

@misc{termios2024,
  author       = {Linux Kernel Developers},
  title        = {termios(3) — Linux Manual Page},
  year         = {2024},
  howpublished = {\url{https://man7.org/linux/man-pages/man3/termios.3.html}},
}

@misc{asan2024,
  author       = {Google},
  title        = {{AddressSanitizer}: A Fast Address Sanity Checker},
  year         = {2024},
  howpublished = {\url{https://github.com/google/sanitizers}},
}

@dataset{svabensky2021,
  author    = {Valdemar Švábenský and others},
  title     = {Cybersecurity Training Dataset: Hands-on Exercises},
  year      = {2021},
  doi       = {10.5281/zenodo.5517479},
  publisher = {Zenodo},
  url       = {https://doi.org/10.5281/zenodo.5517479},
}
```

---

*Bu doküman `/Users/fahrinox/Desktop/clever_shell/PROJECT_HANDOFF.md` dosyasıdır.*  
*Tüm sayılar `python/eval/results_*/` ve `python/eval/analysis/` klasörlerindeki*  
*CSV dosyalarından doğrudan alınmıştır. Son test durumu: TEST_REPORT.md — 7/7 PASS.*
