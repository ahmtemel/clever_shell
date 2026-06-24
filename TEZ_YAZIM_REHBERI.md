# TEZ YAZIM REHBERİ
## clever_shell — Yapay Zeka Destekli Akıllı Terminal Tasarımı

> **Bu doküman kime yönelik?**  
> Word'de Claude ile tez yazacak öğrenciye ve yardım eden AI'a.
> Her bölüm için (a) ne yazılacağı, (b) hangi dosyadan besleneceği,
> (c) kim yazacağı `[AI YAZAR]` / `[ÖĞRENCİ YAZAR]` etiketi ile belirtilmiştir.
> Tüm sayılar gerçek CSV dosyalarından alınmıştır.
>
> **Referans doküman:** `PROJECT_HANDOFF.md` (ayrıntılı sayılar ve mimari)  
> **Test durumu:** `TEST_REPORT.md` — 7/7 PASS

---

## BÖLÜM BAŞLIKLARI (Hızlı Referans)

1. Giriş
2. Teorik Altyapı ve Yöntemler
3. Sistem Tasarımı ve Gerçekleştirme
4. Deneysel Sonuçlar
5. Sonuçlar ve Öneriler

---

## 1. KAPAK & KÜNYE BİLGİLERİ

### 1.1 Hazır Kapak Metni

```
YILDIz TEKNİK ÜNİVERSİTESİ
KİMYA-METALÜRJÜ FAKÜLTESİ
MATEMATİK MÜHENDİSLİĞİ BÖLÜMÜ

ÇOK DİSİPLİNLİ TASARIM PROJESİ (BİTİRME)

BAŞLIK (birini seçin veya danışmanla tartışın):

Seçenek A (önerilen):
"Yapay Zeka Destekli Akıllı Terminal Tasarımı"

Seçenek B (teknik odaklı):
"Markov Zinciri Tabanlı Komut Tahmini ile Düşük Gecikmeli
 Akıllı Terminal Tasarımı"

Seçenek C (daha kısa, dengeli):
"Ghost Text Otomatik Tamamlama ile POSIX Uyumlu Akıllı Kabuk Tasarımı"

Danışman: Doç. Dr. Mert Bal
Öğrenci  : 20052076 Ahmet Salih Temel

İstanbul, 2026
```

### 1.2 Telif Hakkı Sayfası (DD-050 Md. 2.2)

```
© Ahmet Salih Temel, 2026

Bu çalışmanın tüm hakları saklıdır. Eserin tamamı ya da bir bölümü,
kaynak gösterilmek koşuluyla alıntılanabilir; ancak yazarın yazılı
izni olmaksızın çoğaltılamaz ve yayımlanamaz.
```

---

## 2. ÖN SAYFALAR REHBERİ

### 2.1 Sıra ve Üretim Yöntemi

| Ön Sayfa | Yazar | Üretim |
|----------|-------|--------|
| Kapak | Öğrenci | Word şablonu |
| İç kapak | Öğrenci | Kapakla aynı |
| Onay / imza sayfası | Öğrenci + Danışman | Bölüm şablonu |
| Telif hakkı | Öğrenci | Yukarıdaki metin |
| **Önsöz** | **[ÖĞRENCİ YAZAR]** | Kişisel deneyim, teşekkür |
| **Özet** | **[AI TASLAK + öğrenci onayı]** | Bkz. §2.2 |
| **Abstract** | **[AI TASLAK + öğrenci onayı]** | Özet çevirisi |
| İçindekiler | Otomatik | Word alan kodu |
| Şekil Listesi | Otomatik | Word alan kodu |
| Tablo Listesi | Otomatik | Word alan kodu |
| Kısaltma Listesi | Öğrenci | Bkz. §2.3 |

### 2.2 Özet Taslağı — [AI TASLAK]

> AI bu taslağı üretir; öğrenci içeriği onaylar, üslubu kişiselleştirir.

---

**ÖZET**

Bu çalışmada, kullanıcı komut geçmişinden öğrenen ve her tuş vuruşunda
otomatik tamamlama önerisi sunan yapay zeka destekli bir terminal kabuğu
(clever_shell) tasarlanmış ve gerçekleştirilmiştir. Sistem, iki bağımsız
süreçten oluşmaktadır: POSIX uyumlu C çekirdeği (minishell) ve kelime
düzeyi Markov zinciri tabanlı Python tahmın servisi. Bileşenler arasındaki
iletişim, engelleyici olmayan (non-blocking) ZeroMQ PAIR soketleri
aracılığıyla sağlanmakta; tahmin edilen tamamlama, kullanıcı arayüzünde
gri renkte "hayalet metin" (ghost text) olarak anlık sunulmaktadır.

Büyük dil modellerinin (LLM) terminal otomatik tamamlama için sunduğu
yüzlerce milisaniyelik gecikmenin aksine, önerilen Markov tabanlı yaklaşım
p99 gecikmeyi kendi geçmiş veri setinde 0,053 ms, 10.957 komutluk kamuya
açık siber güvenlik veri setinde ise 0,615 ms düzeyinde tutmaktadır; her
iki değer de 5 ms insan algı eşiğinin çok altındadır. Kelime düzeyi
değerlendirmede önerilen model, kendi geçmiş snapshot'ında Tuş Tasarrufu
Oranı (KSR) %27,1; siber güvenlik setinde (filtresiz) %47,2 olarak
ölçülmüştür. Komut düzeyi Markov zinciri analizinde, k=1 bağlam
derinliğinin en iyi sonucu verdiği gözlemlenmiş (komut adı Top-5 doğruluğu
%74,3); bu değer en sık komut baseline'ını %59,0'dan %74,3'e (+15,3 puan)
iyileştirmektedir. Ölçeklenme analizi, eğitim verisi arttıkça modelin
monotonik biçimde iyileştiğini göstermektedir. Sistem, AddressSanitizer ve
UndefinedBehaviorSanitizer ile doğrulanmış; sıfır çalışma zamanı hatası
elde edilmiştir.

**Anahtar Kelimeler:** Akıllı terminal, Markov zinciri, ghost text, POSIX
kabuk, ZeroMQ, otomatik tamamlama, tuş tasarrufu oranı, gecikme optimizasyonu

---

**ABSTRACT** (yukarıdakinin çevirisi — AI üretir, öğrenci onaylar)

In this study, an AI-assisted intelligent terminal shell (clever_shell) that
learns from the user's command history and provides autocomplete suggestions
on every keystroke has been designed and implemented. The system consists of
two independent processes: a POSIX-compliant C core (minishell) and a
word-level Markov chain-based Python prediction service. Communication between
components is achieved through non-blocking ZeroMQ PAIR sockets; the predicted
completion is displayed in real time as grey-colored "ghost text" in the user
interface.

Unlike the hundreds of milliseconds of latency offered by Large Language Models
(LLMs) for terminal autocomplete, the proposed Markov-based approach keeps p99
latency at 0.053 ms on the personal history dataset and 0.615 ms on a public
10,957-command cybersecurity dataset — both well below the 5 ms human perception
threshold. In word-level evaluation, the proposed model achieved a Keystroke
Savings Ratio (KSR) of 27.1% on the personal history snapshot and 47.2% on the
cybersecurity dataset (unfiltered). In command-level analysis, k=1 context depth
yielded the best performance (command-name Top-5 accuracy: 74.3%), improving
over the most-frequent-command baseline by +15.3 percentage points. Scaling
analysis shows monotonically improving metrics as training data increases. The
system was validated with AddressSanitizer and UndefinedBehaviorSanitizer,
achieving zero runtime errors.

**Keywords:** Intelligent terminal, Markov chain, ghost text, POSIX shell,
ZeroMQ, autocomplete, keystroke savings ratio, latency optimization

### 2.3 Kısaltma Listesi (Öneri)

| Kısaltma | Açılım |
|----------|--------|
| AI | Artificial Intelligence / Yapay Zeka |
| ANSI | American National Standards Institute |
| ASan | AddressSanitizer |
| IPC | Inter-Process Communication |
| KSR | Keystroke Savings Ratio / Tuş Tasarrufu Oranı |
| LLM | Large Language Model / Büyük Dil Modeli |
| NLP | Natural Language Processing |
| POSIX | Portable Operating System Interface |
| PTY | Pseudo Terminal |
| UBSan | UndefinedBehaviorSanitizer |
| ZMQ | ZeroMQ |

---

## 3. TAM BÖLÜM İSKELETİ

---

### BÖLÜM 1 — GİRİŞ

**Yazar:** `[AI YAZAR]` — öğrenci gözden geçirir ve onaylar  
**Uzunluk hedefi:** 4–6 sayfa  
**Tablo/Şekil:** Yok (Giriş bölümünde veri tablosu konulmaz)

#### 1.1 Problem Tanımı ve Motivasyon

**Ne anlatılacak:**
- Terminal (komut satırı arayüzü) hâlâ yazılım geliştiriciler, sistem
  yöneticileri ve siber güvenlik uzmanlarının birincil aracı olduğunu yaz.
- Kullanıcıların uzun ve karmaşık komutları elle yazmak zorunda kaldığını;
  bunun zaman kaybı ve yazım hatalarına yol açtığını belirt.
- Mevcut kabukların (bash, zsh) `history` ve `tab completion` özelliklerinin
  sınırlı kaldığını; komut tamamlama için sözlük/statik kural tabanlı çalıştığını açıkla.
- "Her tuş vuruşunda bağlam-duyarlı, kişiselleştirilmiş öneri" ihtiyacını ortaya koy.

**Handoff kaynağı:** `PROJECT_HANDOFF.md` §1

#### 1.2 Büyük Dil Modeli Neden Değil?

**Ne anlatılacak:**
- LLM tabanlı tamamlama (GitHub Copilot, ChatGPT API) 100–500 ms gecikme yaratır.
- Terminal arayüzünde 40 ms üzeri gecikme kullanıcı tarafından hissedilir
  (Shneiderman'ın altın kuralları, Miller 1968).
- Kaynak tüketimi: LLM'ler onlarca GB RAM gerektirir; yerel çalışma pratik değildir.
- Önerilen Markov modeli: p99 < 1 ms (ölçülen), < 2 MB bellek.
- **Tezde şunu yaz:** "Markov zinciri tercihinin temel gerekçesi gecikme kısıtıdır;
  LLM'lerin sunduğu daha zengin bağlamsal anlama kapasitesi bu çalışmanın kapsam
  dışında bırakılmıştır."

**Handoff kaynağı:** §1.2, §7.5

#### 1.3 İlgili Çalışmalar

**Ne anlatılacak (AI, her maddeyi 2–3 cümleyle genişletir):**

1. **CLAI (IBM, 2020)** — AI destekli terminal asistan; NLP tabanlı komut önerir;
   bulut bağımlılığı nedeniyle yüksek gecikme sorunu var.
2. **NL2Bash (Lin vd., 2018)** — Doğal dil → bash komutu çevirisi; kullanıcı
   geçmişini öğrenmez, komut sentezi amacıyla farklı problem.
3. **N-gram Dil Modelleri (Manning & Schütze, 1999)** — Klasik istatistiksel
   yaklaşım; hesaplama verimliliği kanıtlanmış; bu çalışmanın teorik temeli.
4. **42-okul minishell projesi** — POSIX uyumlu kabuk gerçekleştirme standardı;
   bu çalışmanın C çekirdeği bu standarda uyar.
5. **Švábenský vd. (2021) siber güvenlik veri seti** — 175 siber güvenlik
   eğitim oturumundan 10.957 bash komutu; dış doğrulama benchmark'ı olarak kullanıldı.

**Kaynaklar:** [1][2][3][4][5] (§7 referans listesinden sırayla)

#### 1.4 Çalışmanın Amacı ve Katkıları

**Ne anlatılacak:**
- **Birincil amaç:** Kişisel komut geçmişinden öğrenen, ≤ 5 ms gecikmeyle
  her tuş vuruşunda öneri sunan terminal kabuğu geliştirmek.
- **Katkı 1:** Kelime düzeyi Markov zincirinin canlı ghost text tamamlama için
  uygulanması ve değerlendirilmesi.
- **Katkı 2:** C (termios/ZMQ) + Python (Markov daemon) çift-süreç mimarisi;
  non-blocking IPC protokolü tasarımı.
- **Katkı 3:** 7 metrik, 2 veri seti, ablasyon + ölçeklenme içeren kapsamlı
  değerlendirme altyapısı.
- Tasarım hedefi: %80 Top-5 komut adı doğruluğu (bağlam: §4.1'de ölçülen değerler verilecek).

#### 1.5 Tez Planı

**Ne anlatılacak:** Bölüm 1–5'i bir paragrafta özetle.

---

### BÖLÜM 2 — TEORİK ALTYAPI VE YÖNTEMLER

**Yazar:** `[AI YAZAR]` — matematiksel bölümler AI üretir, öğrenci formülleri kontrol eder  
**Uzunluk hedefi:** 8–12 sayfa  
**Tablo/Şekil:** Gerekirse formül numaralandırması (Word'de denklem editörü)

#### 2.1 k-ıncı Dereceden Markov Zinciri

**Ne anlatılacak:**

Markov zincirinin matematiksel tanımı (AI formülleri Word denklem editörüyle üretir):

*Geçiş olasılığı (k-ıncı derece):*

> P(w_t | w_{t-1}, w_{t-2}, ..., w_{t-k}) = count(w_{t-k},...,w_{t-1},w_t) / count(w_{t-k},...,w_{t-1})

*Kelime düzeyi model (bu çalışmada k=3):*
- Durum uzayı: son k kelime
- Gözlem: sonraki kelime
- Tablo yapısı: `Dict[Tuple[str,...], Counter[str]]`

*Backoff mekanizması:*
- k bağlamında tahmin yoksa k−1'e düş
- 0'a kadar backoff; 0 = yalnızca prefix eşleşmesi
- Sessizlik (boş string) sonunda mümkün — fallback counter devreye girer

*Recency weighting (zaman ağırlıklandırma):*

> w_i = exp(−λ · Δt_i)

Δt_i = eğitim anı ile ilgili komutun zaman damgası arasındaki gün farkı;
λ = 0,005 (yarılanma ömrü ≈ 139 gün).

*Frekans tabanı:* MIN_FREQ = 1 (tek gözlemlenen komutlar tutulur).

**Kaynaklar:** [3] Manning & Schütze; [6] Wikipedia / Markov (1913)

#### 2.2 POSIX Kabuk Kavramları

**Ne anlatılacak:**

| Kavram | Açıklama |
|--------|----------|
| Lexer | Ham satırı token'lara ayırır (WORD, PIPE, REDIRECT) |
| Parser | Token listesini AST'ye dönüştürür; pipe kök düğüm |
| Executor | AST üzerinde `fork/execve/pipe/dup2/waitpid` çalıştırır |
| fd hijyeni | Her fork'ta kullanılmayan fd'ler kapatılır — "too many open files" önlenir |

`fork() + execve()` modelini açıkla: çocuk süreç ikiliyi kendi adres alanına yükler;
ebeveyn `waitpid()` ile bekler.

**Kaynaklar:** [5] POSIX.1-2017

#### 2.3 termios Raw Mod

**Ne anlatılacak:**
- Canonical (satır) mod vs raw (karakter) mod arasındaki fark.
- `tcgetattr` ile yedekleme; `tcsetattr` ile aktivasyon.
- `c_lflag &= ~(ECHO | ICANON)` — yankı ve tampon kapatma.
- `VMIN=1, VTIME=0` — tek karakter bekle, hemen dön.
- Backspace (0x7f): programın tamponu güncellemesi + `write(1, "\b \b", 3)`.
- Escape sequence ayrıştırma: `\x1b[A/B/C/D` yön tuşları için state machine.

**Kaynaklar:** [7] termios(3) man page

#### 2.4 ZeroMQ Non-Blocking IPC

**Ne anlatılacak:**
- ZMQ PAIR deseni: iki uçlu, broker'siz iletişim.
- `DONTWAIT` bayrağı ve EAGAIN hatası — terminal döngüsü bloke edilmez.
- `zmq_poll(timeout_ms)` ile sınırlı bekleme.
- Bu çalışmadaki son IPC düzeltmesi (§3.5'te detaylandırılır):
  `drain → send → recv_timeout(15 ms)`.

**Kaynaklar:** [1] ZeroMQ

#### 2.5 Ghost Text ve ANSI Kaçış Dizileri

**Ne anlatılacak:**
- ANSI renk kodları: `\x1b[90m` (koyu gri) … `\x1b[0m` (sıfırla).
- İmleç geri alma: `\x1b[ND` (N birim sol).
- `\x1b[0K` ile satır sonu temizleme.
- Ghost text kabul (Tab) akışı.

---

### BÖLÜM 3 — SİSTEM TASARIMI VE GERÇEKLEŞTİRME

**Yazar:** `[AI YAZAR]` — öğrenci kod bölümlerini açıklayan cümleleri onaylar  
**Uzunluk hedefi:** 10–14 sayfa  
**Tablo/Şekil:** Şekil 3.1 mimari diyagramı, Şekil 3.2 ghost text ekran görüntüsü
(ikisi de `[ÖĞRENCİ OLUŞTURMALI]`)

#### 3.1 Genel Mimari

**Ne anlatılacak:**
- İki süreç yapısını açıkla (C kabuğu + Python daemon).
- Aralarındaki ZMQ PAIR bağlantısını tanımla.
- Neden iki ayrı süreç: güvenilirlik (daemon çöküşü kabuğu etkilemez),
  bağımsız dil seçimi, test edilebilirlik.

**Şekil 3.1 — Sistem mimarisi ve veri akışı diyagramı**  
`[ÖĞRENCİ OLUŞTURMALI]` — Word'de SmartArt veya draw.io kullanılabilir.  
İçermesi gerekenler: Klavye → C buffer → ZMQ → Python → ZMQ → ghost render.

#### 3.2 C Çekirdeği Modülleri

**Ne anlatılacak:**
- Her `src/*.c` dosyasını 2–3 cümleyle açıkla (bkz. `PROJECT_HANDOFF.md §3.1`).
- Özellikle vurgula: `executor.c`'de `_exit()` kullanımı (çocuk süreçte
  `exit()` çağrısı raw modu bozardı), `waitpid()` senkronizasyonu.
- `t_lbuf` struct'ını açıkla: `data`, `prediction`, `last_sent` alanları.

#### 3.3 Python Markov Daemon

**Ne anlatılacak:**
- `WordMarkovChain` eğitim pipeline'ı: parse → whitelist → frequency floor → train.
- `predict_suffix(buf)` mantığı: boşlukla bitiyor mu? (next-word modu) / bitmiyor mu? (prefix modu).
- Whitelist: 46 komut — neden sınırlı? (gürültü filtresi, geçmişte typo'lar, özel komut girdileri).
- Fallback: MatrisS sessizse `buf` ile başlayan en sık komutun suffix'i döndürülür.
- `build_chain` + `run_daemon` imzaları değişmeden korunmuştur (aşamalı geliştirme boyunca).

**Beyaz liste (Whitelist) tasarım kararı:**  
*"46 komutluk beyaz liste, kullanıcı geçmişindeki gürültüyü (tek seferlik
typo'lar, otomatik sistem çıktıları) filtrelemek amacıyla seçilmiştir.
Kendi geçmişimde komutların %91,5'i, siber güvenlik setinde ise %55,4'ü
bu listeye girmektedir."*

#### 3.4 Değerlendirme Altyapısı

**Ne anlatılacak:**
- `python/eval/` klasörünün amacı: yeniden üretilebilir, otomatik değerlendirme.
- Veri bölme stratejisi: kronolojik %80/20 (bkz. §4.1).
- `run_eval.py` — `--fair` bayrağının ne işe yaradığını açıkla.

#### 3.5 IPC Zamanlama Düzeltmesi (Ghost Text Fix)

**Ne anlatılacak — önemli bir mühendislik kararı olarak vurgula:**
- **Sorun (önce):** `recv(DONTWAIT) → EAGAIN → send` sırası. Daemon cevabı
  sonraki tuşta gelir; ghost text her zaman bir adım geride kalır.
- **Teşhis:** `python/eval/diagnose.py` ile doğrulandı; Python modeli doğru
  çalışıyor (`predict_suffix('git s') = 'tatus'`), sorun C IPC zamanlamasında.
- **Çözüm (sonra):** `zmq_ipc_drain() → zmq_ipc_send(buf) → zmq_ipc_recv_timeout(15ms)`.
  Her tuş vuruşunda güncel buffer'ın kendi cevabı alınır.
- **Güvence:** `zmq_poll` 15 ms ile sınırlı — terminal hiçbir zaman süresiz bloklanmaz.

#### 3.6 Bellek ve Süreç Güvenliği

**Ne anlatılacak:**
- `-Wall -Wextra -Werror` ile sıfır uyarı garantisi.
- ASan/UBSan: 0 çalışma zamanı hatası (TEST_REPORT.md §4).
- fd hijyeni: her fork sonrası kullanılmayan uçlar kapatılır.
- Sinyal yönetimi: SIGINT (Ctrl+C) kabuğu kapatmaz; yalnızca aktif çocuk süreci sonlandırır.

**Şekil 3.2 — Ghost Text Ekran Görüntüsü**  
`[ÖĞRENCİ OLUŞTURMALI]` — Terminali açıp "git s" yazarken ekran alıntısı al.  
Alt yazı: *"Şekil 3.2 — 'git s' girildiğinde 'tatus' ghost text önerisi"*

---

### BÖLÜM 4 — DENEYSEL SONUÇLAR

**Yazar:** `[AI YAZAR]` — tablolar ve şekil açıklamaları AI üretir  
**Uzunluk hedefi:** 14–18 sayfa  
**Bu bölüm tüm tablo ve şekillerin büyük bölümünü barındırır (bkz. §4 aşağıda)**

#### 4.1 Değerlendirme Metodolojisi

**Ne anlatılacak:**

**Veri setleri:**

| Veri Seti | Kaynak | Komut Sayısı | Eğitim | Test |
|-----------|--------|:---:|:---:|:---:|
| Kendi geçmişim (snapshot) | `self_history_frozen.txt` | 1001 | 728 | 183 |
| Siber güvenlik seti | Švábenský 2021 [8] | 10.957 | 8765 | 2192 |

*Siber güvenlik seti, 175 pentest eğitim oturumunu (7 farklı senaryo) kapsar;
kişisel geçmiş ile örtüşmez — "harici, alana-özel doğrulama seti" olarak çerçevelenir.*

**Bölme stratejisi:** Kronolojik %80/20 — geleceği geçmişe sızdırmama (no data leakage).

**7 Metrik — kısa açıklamalar (tam matematiksel tanım Bölüm 2.6'da verilmişti):**

1. **KSR** — Kullanıcının kaç karakter yazmadan tamamlayabildiği oran
2. **Doğruluk@1** — Modelin en yüksek olasılıklı tahminin doğru olma oranı
3. **Doğruluk@3** — İlk 3 adayda doğru token'ın bulunma oranı
4. **Önek-Koşullu Tamamlama** — ≥2 karakter yazıldıktan sonra tam suffix tahmini
5. **Kapsama** — Modelin boş öneri vermeden cevap ürettiği test komut oranı
6. **Top-5 Komut Kabul** — Önceki komut bağlamında sonraki komut adı Top-5'te mi?
7. **Gecikme p99** — %99'luk gecikme yüzdecisi (ms cinsinden)

**Kelime düzeyi vs komut düzeyi ayrımı** — ÇOK ÖNEMLİ, tezde net belirtilmeli:

> *"Kelime düzeyi model, terminalin canlı ghost text özelliğini besler; her
> tuşta mevcut komutun tamamlanmasını tahmin eder. Komut düzeyi model ise
> tamamıyla çevrimdışı analiz amacıyla kurulmuş olup komut dizilerini (bir
> komuttan sonra hangi komut gelir?) tahmin eder. İki modelin metrikleri
> birbirinin yerine kullanılamaz."*

#### 4.2 Kelime Düzeyi Temel Sonuçlar

**Tablo 4.1 — Önerilen modelin temel performans metrikleri**  
*(Kaynak: `results_self/metrics_summary.csv`, `results_cyber_fair/metrics_summary.csv`)*

| Metrik | Kendi Geçmişim (snapshot) | Siber-Güvenlik Seti (filtresiz) |
|--------|:---:|:---:|
| KSR (%) | 27,1 | **47,2** |
| Doğruluk@1 (%) | 24,8 | 29,0 |
| Doğruluk@3 (%) | 45,9 | 54,7 |
| Önek-Koşullu Tamamlama (≥2 kar., %) | 35,0 | 68,5 |
| Top-5 Komut Kabul Oranı (%) | **55,5** | 25,3 |
| Kapsama (%) | 78,6 | 94,6 |
| Gecikme p50 (ms) | 0,017 | 0,141 |
| Gecikme p99 (ms) | 0,053 | 0,615 |

*Tablo başlığı ÜSTE; kendi veri setimiz.*

**Açıklama paragrafı (AI yazar):**  
*"Siber güvenlik seti üzerinde elde edilen yüksek KSR (%47,2) ve kapsama
değeri (%94,6), tekrarlı pentest iş akışlarının (ör. nmap taramaları, fcrackzip
saldırıları) yüksek derecede tahmin edilebilir diziler oluşturmasından kaynaklanmaktadır.
Buna karşın Top-5 Komut Kabul Oranı'nın daha düşük olması (%25,3 vs %55,5),
söz konusu korpustaki komut çeşitliliğinin kişisel kullanım geçmişine kıyasla
çok daha yüksek olduğuna işaret etmektedir. p99 gecikme değerleri her iki veri
setinde de 1 ms altında kalmış; böylece gerçek zamanlı terminal tamamlama için
belirlenen 5 ms eşiğinin çok ötesinde bir performans sağlanmıştır."*

#### 4.3 Kelime Düzeyi Ablasyon

**Tablo 4.2 — Ablasyon çalışması: k ve λ konfigürasyonu karşılaştırması**  
*(Kaynak: `results_self/ablation_table.csv`)*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) |
|---|:---:|:---:|
| **Önerilen (k=3, λ=0,005)** | **27,1** | **24,8** |
| k=1 (unigram bağlam) | 27,1 | 24,8 |
| k=2 (bigram bağlam) | 27,1 | 24,8 |
| Backoff'suz (k=3) | 27,1 | 24,8 |
| Frekans-only baseline | 27,1 | 9,2 |
| En sık komut baseline | 25,4 | 9,2 |

**Tablo 4.3 — Zaman azalma (λ) ablasyonu — siber güvenlik seti**  
*(Kaynak: `results_cyber_fair/ablation_table.csv`)*

| λ | KSR (%) | Doğruluk@1 (%) |
|---|:---:|:---:|
| 0,0 (yok) | 44,9 | 27,9 |
| **0,005 (önerilen)** | **47,2** | **29,0** |
| 0,02 (hızlı) | 48,1 | 29,1 |

**Açıklama paragrafı (AI yazar):**  
*"Kendi geçmiş veri setinde tüm Markov konfigürasyonları özdeş KSR üretmektedir.
Bu bulgu, az sayıda (728) eğitim komutu içeren küçük kişisel geçmişlerde yüksek
dereceli n-gram'ların tek örneklere karşılık geldiğini ve backoff mekanizmasının
otomatik olarak k=1'e düştüğünü göstermektedir. λ ablasyonu, siber güvenlik
setinde — timestamp içerdiği için — recency decay'in marjinal ama tutarlı bir
etki (+2,3 pp KSR) gösterdiğini ortaya koymaktadır."*

#### 4.4 Komut Düzeyi Analiz (Çevrimdışı)

> **Not:** Bu bölüm tamamen çevrimdışı analizdir; canlı ghost text ile ilgisi yoktur.

**Tablo 4.4 — Komut düzeyi ablasyon: k ve λ etkisi (token modu)**  
*(Kaynak: `python/eval/analysis/command_level.csv`)*

| k | λ | Top-1 (%) | Top-5 (%) |
|---|---|:---:|:---:|
| **1 (en iyi)** | 0,005 | **46,0** | **74,3** |
| 2 | 0,005 | 44,5 | 70,2 |
| 3 | 0,005 | 43,2 | 65,1 |
| — (baseline) | — | 24,5 | 59,0 |

**Önerilen model vs baseline:** Top-5 kazanımı = **+15,3 puan**

**Tablo 4.5 — Tam komut dizgesi tahmini (karşılaştırma)**  
*(Kaynak: `analysis/command_level.csv`, full-cmd mod)*

| Mod | k=1 Top-1 (%) | k=1 Top-5 (%) |
|-----|:---:|:---:|
| Token (komut adı) | 46,0 | 74,3 |
| Tam komut dizgesi | 18,3 | 27,8 |

**Açıklama paragrafı (AI yazar):**  
*"Komut düzeyinde k=1 bağlam derinliği tüm k değerleri arasında en iyi sonucu
vermiştir. Bu, siber güvenlik senaryolarındaki komut geçişlerinin lokal tekrarlı
yapısıyla — yani her komutun büyük olasılıkla önceki tek komuta bağlı olduğuyla
— tutarlıdır. k değeri yükseldikçe bağlam uzunluğu artar, n-gram tablosu
seyrekleşir ve tahmin kalitesi düşer. Bu nedenle tezde 'k=3 her zaman üstündür'
iddiasında bulunulmamalı; bunun yerine 'k=1 bu veri seti için optimal bulunmuştur'
ifadesi kullanılmalıdır."*

#### 4.5 Ölçeklenme Analizi

**Tablo 4.6 — Ölçeklenme sonuçları (5 seed rastgele örnekleme, ortalama ± std)**  
*(Kaynak: `python/eval/analysis/scaling.csv`; filtresiz test seti)*

| Eğitim Komutu | KSR (%) | ±std | Doğ.@1 (%) | Önek-Koş. (%) | Kapsama (%) | Komut Top-5 (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 200 | 32,9 | ±1,9 | 25,5 | 44,2 | 81,3 | 50,3 |
| 400 | 35,9 | ±1,8 | 25,6 | 48,7 | 85,5 | 54,5 |
| 800 | 39,7 | ±2,3 | 27,2 | 55,0 | 89,1 | 54,9 |
| 1.600 | 41,1 | ±2,6 | 27,2 | 58,5 | 91,6 | 56,3 |
| 3.200 | 42,4 | ±2,8 | 27,8 | 61,4 | 92,7 | 65,1 |
| **8.765 (tüm)** | **47,2** | **±0,0** | **29,0** | **68,5** | **94,6** | **74,3** |

**Şekil 4.1 — Öğrenme eğrisi (x=eğitim komutu sayısı log ölçek, std bant)**  
Kaynak: `python/eval/analysis/fig_scaling.png`  `[VAR]`  
Alt yazı: *"Şekil 4.1 — Eğitim seti büyüklüğüne göre model başarımı (5 tohum ortalaması ± std)"*

**Açıklama paragrafı (AI yazar):**  
*"KSR eğrisi tüm boyutlarda monotonik artan bir seyir izlemektedir (%32,9 → %47,2).
Bu bulgu, daha fazla eğitim verisinin modeli düzenli biçimde iyileştirdiğini
doğrulamakta; tasarım aşamasında belirlenen %80 hedefine giden örüntüyü ortaya
koymaktadır. Rastgele örneklemeli 5 tohumlu deney, sonuçların belirli bir veri
düzenlemesine bağlı olmadığını da göstermektedir."*

#### 4.6 Whitelist Kapsam Analizi

**Tablo 4.7 — Whitelist kapsam analizi**  
*(Kaynak: `python/eval/analysis/whitelist_coverage.csv`)*

| Korpus | Toplam Komut | Whitelist'te | Kapsam (%) |
|--------|:---:|:---:|:---:|
| Kendi kabuk geçmişim | 1.000 | 915 | 91,5 |
| Siber-güvenlik seti | 10.957 | 6.066 | 55,4 |

*Siber sette whitelist dışı dominant komutlar: nmap (759), fcrackzip (648),
scp (639), john (225). Bu nedenle siber set için filtresiz değerlendirme zorunludur.*

#### 4.7 Gecikme Analizi

**Şekil 4.2 — Gecikme dağılımı (p50/p95/p99)**  
Kaynak: `results_self/fig_latency.png`  `[VAR]`  
Alt yazı: *"Şekil 4.2 — predict_suffix çağrısı gecikme dağılımı (1000 ölçüm)"*

**Açıklama:** p99 kendi geçmiş: 0,053 ms; siber: 0,615 ms.
Her ikisi de 5 ms kullanıcı algı eşiğinin çok altında. LLM alternatifleriyle
karşılaştırmalı yoruma Bölüm 1.2'ye atıf yap.

---

### BÖLÜM 5 — SONUÇLAR VE ÖNERİLER

**Yazar:** `[AI YAZAR]` — öğrenci kişisel yorumlarını ekler  
**Uzunluk hedefi:** 4–6 sayfa  
**Tablo/Şekil:** Yok

#### 5.1 Elde Edilen Bulgular

**Ne anlatılacak (her maddeyi 2–3 cümleyle genişlet):**

1. **Sistem çalışıyor:** Ghost text her tuşta doğru çalışmaktadır; PTY testi
   "git st" → "atus" öneriyi doğrulamıştır.
2. **Gecikme hedefi karşılandı:** p99 < 1 ms; 5 ms eşiğinin çok altında.
3. **Komut düzeyi k=1 optimaldır:** Siber sette %74,3 Top-5 (baseline üzerine +15,3 pp).
4. **Kelime düzeyi k etkisi küçük geçmişte yok:** Ablasyon tüm k için özdeş sonuç → backoff dominant.
5. **Recency decay marjinal katkı sağlar:** λ=0,005 siber sette +2,3 pp KSR.
6. **Ölçeklenme olumlu:** Daha fazla veri sistematik iyileştirme sağlar (monotonik eğri).
7. **Sistem güvenlidir:** ASan/UBSan 0 hata; strict flag uyarısız derleme.

#### 5.2 %80 Hedefine Ulaşma Değerlendirmesi

**Ne anlatılacak — DÜRÜST ÇERÇEVELEMEYİ KORU:**

*"Tez önerisinde belirlenen %80 başarım hedefi bir tasarım hedefiydi; ölçülen
en yüksek değer komut adı Top-5 doğruluğunda %74,3 olarak gerçekleşmiştir
(siber güvenlik seti, token modu, k=1). Ölçeklenme analizi, daha büyük ve
çeşitli bir eğitim veri seti ile bu hedefe yaklaşılabileceğini göstermektedir.
Kelime düzeyi değerlendirmede ise KSR %27,1–47,2 aralığında ölçülmüştür."*

#### 5.3 Sınırlamalar

Bkz. `PROJECT_HANDOFF.md §10.1` — 6 madde:
- Küçük kişisel geçmiş (~1.000 komut)
- Sabit beyaz liste
- Düz metin geçmiş (zaman damgasız recency decay etkisiz)
- Tek kullanıcı
- macOS heap-leak taraması tamamlanmadı
- ASCII dışı karakter testi yapılmadı

#### 5.4 Gelecek Çalışma

Bkz. `PROJECT_HANDOFF.md §10.2` — 5 öneri genişletilmiş olarak yaz.

---

## 4. ŞEKİL & TABLO YERLEŞİM HARİTASI

> **Kural hatırlatma:**  
> • Tablo başlığı → ÜSTTE, ortalı, koyu: **Tablo 4.1 — Açıklama**  
> • Şekil başlığı → ALTTA, ortalı, koyu: **Şekil 4.1 — Açıklama**  
> • Numaralama: Bölüm.sıra (3. bölümdeki 1. şekil = Şekil 3.1)

### 4.1 Tablolar

| No | Başlık (Türkçe) | Kaynak Dosya | Durum |
|----|-----------------|--------------|-------|
| **Tablo 4.1** | Önerilen yapılandırmanın temel performans metrikleri | `results_self/metrics_summary.csv` + `results_cyber_fair/metrics_summary.csv` | ✅ VAR |
| **Tablo 4.2** | Ablasyon çalışması: k ve λ konfigürasyonu karşılaştırması | `results_self/ablation_table.csv` | ✅ VAR |
| **Tablo 4.3** | Zaman azalma (λ) ablasyonu — siber güvenlik seti | `results_cyber_fair/ablation_table.csv` | ✅ VAR |
| **Tablo 4.4** | Komut düzeyi ablasyon: k ve λ etkisi (token modu) | `analysis/command_level.csv` | ✅ VAR |
| **Tablo 4.5** | Token modu vs tam komut dizgesi tahmini | `analysis/command_level.csv` | ✅ VAR |
| **Tablo 4.6** | Ölçeklenme sonuçları (5 seed, ort. ± std) | `analysis/scaling.csv` | ✅ VAR |
| **Tablo 4.7** | Whitelist kapsam analizi: kendi geçmiş ve siber set | `analysis/whitelist_coverage.csv` | ✅ VAR |

### 4.2 Şekiller

| No | Başlık (Türkçe) | Kaynak Dosya | Durum |
|----|-----------------|--------------|-------|
| **Şekil 3.1** | Sistem mimarisi ve veri akışı diyagramı | — | ⚠️ ÖĞRENCİ OLUŞTURMALI |
| **Şekil 3.2** | Ghost text ekran görüntüsü ("git s" → "tatus") | — (ekran alıntısı) | ⚠️ ÖĞRENCİ OLUŞTURMALI |
| **Şekil 4.1** | Öğrenme eğrisi (log x, std bant, 5 seed) | `analysis/fig_scaling.png` | ✅ VAR |
| **Şekil 4.2** | Gecikme dağılımı CDF (p50/p95/p99) | `results_self/fig_latency.png` | ✅ VAR |
| **Şekil 4.3** | k değerine göre KSR ve Doğruluk@1 | `results_self/fig_markov_order.png` | ✅ VAR |
| **Şekil 4.4** | Ablasyon yapılandırmaları karşılaştırması | `results_self/fig_ablation.png` | ✅ VAR |
| **Şekil 4.5** | Veri seti karşılaştırması (gruplu çubuk grafik) | `results_compare_fair/fig_compare.png` | ✅ VAR |
| **Şekil 4.6** | λ etkisi: kendi geçmiş ve siber set | `results_compare_fair/fig_decay_compare.png` | ✅ VAR |
| **Şekil 4.7** | k değerine göre komut düzeyi doğruluk | `analysis/fig_command_k.png` | ✅ VAR |
| **Şekil 4.8** | λ değerine göre komut düzeyi doğruluk | `analysis/fig_command_decay.png` | ✅ VAR |

### 4.3 Öğrenci Oluşturması Gereken Görseller

**Şekil 3.1 — Mimari Diyagram:**
- Araç: Word SmartArt, draw.io, veya Mermaid → PNG
- İçerik: `[Klavye] → [C: input.c] → [ZMQ PAIR] → [Python: markov_daemon.py] → [ZMQ] → [Ghost Text]`
- Ayrıca: Executor alt akışı (fork/execve/pipe/waitpid)

**Şekil 3.2 — Ghost Text Ekran Görüntüsü:**
- Terminal aç, `python3 -m python.markov_daemon` başlat
- `./minishell` çalıştır
- "git s" yaz → "tatus" gri göründüğünde ekran görüntüsü al
- Terminal emülatörü tercihen tmux ile bölünmüş iki panel göstersin

---

## 5. DÜRÜST ÇERÇEVELEMEVE KAÇINILACAK İDDİALAR

> **Bu bölüm `PROJECT_HANDOFF.md §8`'in özetidir. AI tez yazarken bu listeye karşı
> kendi çıktısını her bölüm sonunda kontrol etmelidir.**

### 5.1 Kaçınılacak İddialar (Açık Liste)

| ❌ Yazmayın | ✅ Bunun yerine yazın |
|------------|----------------------|
| "k=3 deneysel olarak üstündür" | "k-ıncı derece incelenmiş; bu veri setinde k=1 optimal bulunmuştur" |
| "%80 doğruluk elde edilmiştir" | "%80 tasarım hedefiydi; ölçülen: Top-5 komut adı %74,3 (siber, token modu)" |
| "ZMQ_REP soket kullanılmıştır" | "ZMQ_PAIR soket kullanılmıştır (REP/REQ kullanılmamıştır)" |
| Kelime düzeyi = komut düzeyi | Ayrı bölümlerde, ayrı tablolarda belirtilmeli |
| "Sistem sızıntısızdır / leak-free" | "ASan/UBSan 0 çalışma zamanı hatası; tam heap-leak taraması macOS kısıtı nedeniyle tamamlanmadı" |
| "Siber set genel kullanımı temsil eder" | "Harici, alana-özel (pentest) doğrulama seti olarak kullanılmıştır" |
| `results_cyber/` sayılarını kullan | `results_cyber_fair/` (filtresiz) kullan — Top1=29,0% Kapsama=94,6% |
| Kişisel geçmiş büyük örnek | "~1.000 komut, kişisel ve sınırlı; istatistiksel anlamlılık kısıtlı" |
| "Decay kritik katkı sağladı" | "Recency decay marjinal ama tutarlı bir iyileştirme (+2,3 pp KSR) göstermiştir" |

### 5.2 Siber Set ile İlgili Açıklama Zorunluluğu

Her siber set sonucunun yanında şu notu ekleyin:

> *"Siber güvenlik seti 10.957 komut ve 175 oturumdan oluşmakla birlikte
> pentest senaryolarına özgü bir dağılım sergilemektedir. Bu nedenle sonuçlar
> genel terminali kullanım alışkanlıklarına genellenmemelidir."*

### 5.3 Kendi Geçmişi İle İlgili Not

> *"Kendi geçmiş ölçümleri, 2026-06-24 tarihinde alınan sabit bir snapshot
> üzerinde gerçekleştirilmiştir (1.001 komut; 4 hassas satır maskelenmiştir).
> Siber güvenlik seti kamuya açık ve değişmez olduğundan birincil tekrar-üretilebilir
> karşılaştırma benchmarkıdır."*

---

## 6. BİÇİM KURALLARI (DD-050)

### 6.1 Yazı ve Sayfa Düzeni

| Özellik | Kural |
|---------|-------|
| Yazı tipi | Times New Roman |
| Metin boyutu | 12 pt |
| Başlık boyutu | 14 pt (bölüm), 12 pt (alt bölüm), hepsi **koyu** |
| Sol kenar boşluğu | **3,5 cm** (cilt payı) |
| Sağ kenar boşluğu | 2,5 cm |
| Üst kenar boşluğu | 3 cm |
| Alt kenar boşluğu | 3 cm |
| Satır aralığı | **1 satır** (tek) |
| Paragraf arası boşluk | 6–12 pt (Word: Aralık Sonra) |
| Sayfa numarası | Altta ortalı; ön sayfalar Roma rakamı (i, ii…), metin Arap rakamı (1, 2…) |

### 6.2 Başlık Numaralandırma

```
1. GİRİŞ             (Bölüm 1 — büyük harf)
   1.1 Problem       (Alt bölüm)
      1.1.1 Detay    (Alt-alt bölüm — gerekirse)
```

- Ana bölümler yeni sayfadan başlar.
- 4. seviye başlık (1.1.1.1) kullanmamaya çalışın.

### 6.3 Dil ve Üslup

- Türkçe, akademik, **edilgen geçmiş zaman**: "…yapılmıştır", "…elde edilmiştir",
  "…gözlemlenmiştir"
- Birinci tekil şahıs (`ben, benim`) **kullanılmaz**; birinci çoğul (`biz, bizim`)
  da kaçınılır → edilgen yapı tercih edilir.
- Kısaltmalar ilk kullanımda açılır: "Tuş Tasarrufu Oranı (KSR)".

### 6.4 Kaynak Atıf Biçimi (DD-050 Nümerik)

Metin içinde köşeli parantez: `[1]`, `[2]`, `[3,4]`  
Kaynakça listesinde ilk atıf sırasına göre numaralandırma.

### 6.5 Tablo ve Şekil Kuralları

```
Tablo 4.1 — Önerilen modelin temel başarım metrikleri
[tablo içeriği]
```

```
[şekil içeriği]
Şekil 4.1 — Eğitim seti büyüklüğüne göre model başarımı
```

- Tablolarda `%` yerine `(%)` sütun başlığında belirtilir; hücrede sade sayı.
- Ondalık ayraç: **virgül** (Türkçe standardı).
- Tüm tablo/şekillere metin içinde atıf yapılmalı ("Tablo 4.1'de görüldüğü üzere…").

---

## 7. KAYNAKLAR (DD-050 Nümerik Liste)

Kaynak listesi ilk atıf sırasına göre numaralandırılır.
Word'de `References` bölümü oluşturun ve aşağıdaki kaynakları girin.

```
[1] iMatix Corporation. ZeroMQ Messaging Library. 2024. [Çevrimiçi].
    Erişim: https://zeromq.org

[2] C. Manning ve H. Schütze, Foundations of Statistical Natural Language
    Processing. MIT Press, 1999.

[3] A. A. Markov, "An Example of Statistical Investigation of the Text Eugene
    Onegin Concerning the Connection of Samples in Chains," Proceedings of the
    Academy of Sciences of St. Petersburg, 1913.

[4] 42 School. "Minishell Subject — 42 Cursus," 2024. [Çevrimiçi].
    Erişim: https://42.fr

[5] IEEE ve The Open Group, POSIX.1-2017: The Open Group Base Specifications
    Issue 7. The Open Group, 2017.

[6] Linux Kernel Developers. "termios(3) — Linux Manual Page," 2024. [Çevrimiçi].
    Erişim: https://man7.org/linux/man-pages/man3/termios.3.html

[7] Google. AddressSanitizer: A Fast Address Sanity Checker. 2024. [Çevrimiçi].
    Erişim: https://github.com/google/sanitizers

[8] V. Švábenský ve diğerleri, "Cybersecurity Training Dataset: Hands-on
    Exercises," Zenodo, 2021. doi: 10.5281/zenodo.5517479.
```

---

## EK — AI KULLANIM KILAVUZU (Claude için)

> Bu bölüm Word'de tez yazacak Claude'a yöneliktir.

### Adım Adım Tez Yazım Süreci

1. **Her bölüm başlamadan önce** bu rehberin ilgili bölüm maddesini oku.
2. **`[AI YAZAR]`** etiketli bölümleri doğrudan yaz. `[ÖĞRENCİ YAZAR]` bölümlerini taslak olarak sun.
3. **Sayıları** doğrudan bu rehberdeki tablolardan al; değiştirme.
4. **Her bölüm sonunda** §5'teki "Kaçınılacak İddialar" tablosunu kontrol et.
5. **Şekil/tablo referansı** → metnin içinde mutlaka atıf yap ("Şekil 4.1'de…").
6. **Kelime düzeyi / komut düzeyi** ayrımını her bahsedildiğinde netleştir.
7. **Gecikme tartışmasında** LLM karşılaştırması paragrafını mutlaka ekle (Bölüm 1.2 → Bölüm 5).
8. **Siber set yorumunda** alana-özel sınırlamayı belirt.

### Tutarlılık Kontrol Listesi (Her Oturumda)

- [ ] Self KSR = 27,1%; Siber KSR = 47,2%
- [ ] Komut Top-5 k=1: 74,3%; Baseline: 59,0%; Delta: +15,3 pp
- [ ] p99 gecikme < 1 ms (kendi: 0,053 ms; siber: 0,615 ms)
- [ ] Whitelist: self %91,5; siber %55,4
- [ ] ZMQ_PAIR (REP/REQ değil)
- [ ] Kapsama %94,6 → siber filtresiz (`results_cyber_fair`)
- [ ] Ölçeklenme: 32,9% → 47,2% monotonik
- [ ] ASan/UBSan 0 hata (leak-free DEMEYİN)

---

*Bu rehber `/Users/fahrinox/Desktop/clever_shell/TEZ_YAZIM_REHBERI.md` dosyasıdır.*  
*Gerçek sayıların kaynakları: `python/eval/results_*/` ve `python/eval/analysis/`.*  
*Mimari ve dosya açıklamaları: `PROJECT_HANDOFF.md`.*
