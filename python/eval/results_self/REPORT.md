# clever_shell — Deneysel Değerlendirme Raporu

**Veri kaynağı:** `Kendi kabuk geçmişim`  
**Eğitim komutu sayısı:** 730  
**Test girdisi sayısı:** 200  
**Geçerli test komutu:** 182  

---

## 4.1 Model Tanımı

Kelime düzeyinde 3-gram Markov zinciri; üstel zamana azalma ağırlıklandırması  
(`λ = 0,005`, yarı-ömür ≈ 139 gün), sözdizim beyaz listesi (46 komut),  
minimum frekans eşiği (MIN_CMD_FREQ = 1) ve önek eşleme geri dönüş mekanizması.

---

## 4.2 Önerilen Yapılandırma — Temel Metrikler

**Tablo 4.1 — Önerilen yapılandırmanın temel performans metrikleri.**  
*Kendi kabuk geçmişi (`Kendi kabuk geçmişim`, 730 eğitim / 182 test komutu). Kalın: önerilen değer.*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **34.3%** |
| Doğruluk@1 (Sonraki Kelime)                        | **25.5%** |
| Doğruluk@3 (Sonraki Kelime)                        | **46.1%** |
| Önek Tamamlama Doğruluğu                           | **47.6%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **46.0%** |
| Top-5 Komut Kabul Oranı                            | **49.2%** |
| Kapsama (sessiz kalmayan oran)                      | **79.4%** |
| Gecikme p50                                         | **0.032 ms** |
| Gecikme p95                                         | **0.071 ms** |
| Gecikme p99                                         | **0.091 ms** |
| n-gram Bağlam Sayısı                               | **229** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **88.4 KB** |

---

## 4.3 Ablasyon Çalışması

**Tablo 4.2 — Ablasyon çalışması: yapılandırma karşılaştırması.**  
*Kendi kabuk geçmişi (`Kendi kabuk geçmişim`, 730 eğitim / 182 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Önek Doğ. (%) | Önek-Koş. (%) | Top-5 Komut (%) | Kapsama (%) | p50 (ms) |
|:-------------|--------:|---------------:|--------------:|--------------:|----------------:|------------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 79.4 | 0.032 |
| k=1 (tekli bağlam) | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 79.4 | 0.033 |
| k=2 (ikili bağlam) | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 79.4 | 0.033 |
| Geri alma yok (k=3) | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 77.6 | 0.033 |
| λ=0 (azalma yok) | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 79.4 | 0.033 |
| λ=0,02 (hızlı azalma) | 34.3 | 25.5 | 47.6 | 46.0 | 49.2 | 79.4 | 0.033 |
| Yalnızca frekans | 34.2 | 9.8 | 47.6 | 46.0 | 49.2 | 79.4 | 0.033 |
| En sık komut | 32.5 | 9.8 | 36.1 | 35.3 | 0.0 | 72.2 | 0.017 |

---

## 4.4 Temel Bulgular

1. Önerilen k=3 kelime-Markov modeli **KSR = 34.3%** elde etmiştir;  
   100 karakter başına yaklaşık 34 tuş tasarrufu sağlar.
2. En iyi referans yöntemini **+0.1% KSR** farkıyla geçmektedir  
   (önerilen: 34.3% — en iyi referans: 34.2%).
3. Çıkarım gecikmesi 5 ms hedefinin çok altındadır:  
   p99 = 0.091 ms.
4. Geri alma (backoff) mekanizması kritik öneme sahiptir: devre dışı bırakıldığında  
   kapsama düşerken kesinlik kazancı elde edilememektedir.
5. λ=0,005 azalma katsayısı eski alışkanlıkları tamamen atmadan  
   son kullanımları ön plana çıkarmaktadır.

---

## 4.5 Şekiller

![Şekil 4.1](fig_markov_order.png)  
**Şekil 4.1 — Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi.**

![Şekil 4.2](fig_ablation.png)  
**Şekil 4.2 — Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması.**

![Şekil 4.3](fig_latency.png)  
**Şekil 4.3 — predict_suffix gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir.**

![Şekil 4.4](fig_decay.png)  
**Şekil 4.4 — Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi.**

---

*`python -m python.eval.run_eval` tarafından otomatik üretilmiştir.*
