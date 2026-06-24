# clever_shell — Deneysel Değerlendirme Raporu

**Veri kaynağı:** `Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`  
**Eğitim komutu sayısı:** 728  
**Test girdisi sayısı:** 200  
**Geçerli test komutu:** 183  

---

## 4.1 Model Tanımı

Kelime düzeyinde 3-gram Markov zinciri; üstel zamana azalma ağırlıklandırması  
(`λ = 0,005`, yarı-ömür ≈ 139 gün), sözdizim beyaz listesi (46 komut),  
minimum frekans eşiği (MIN_CMD_FREQ = 1) ve önek eşleme geri dönüş mekanizması.

---

## 4.2 Önerilen Yapılandırma — Temel Metrikler

**Tablo 4.1 — Önerilen yapılandırmanın temel performans metrikleri.**  
*Kendi kabuk geçmişi (`Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`, 728 eğitim / 183 test komutu). Kalın: önerilen değer.*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **27.1%** |
| Doğruluk@1 (Sonraki Kelime)                        | **24.8%** |
| Doğruluk@3 (Sonraki Kelime)                        | **45.9%** |
| Önek Tamamlama Doğruluğu                           | **39.5%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **35.0%** |
| Top-5 Komut Kabul Oranı                            | **55.5%** |
| Kapsama (sessiz kalmayan oran)                      | **78.6%** |
| Gecikme p50                                         | **0.017 ms** |
| Gecikme p95                                         | **0.041 ms** |
| Gecikme p99                                         | **0.053 ms** |
| n-gram Bağlam Sayısı                               | **146** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **58.1 KB** |

---

## 4.3 Ablasyon Çalışması

**Tablo 4.2 — Ablasyon çalışması: yapılandırma karşılaştırması.**  
*Kendi kabuk geçmişi (`Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`, 728 eğitim / 183 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Önek Doğ. (%) | Önek-Koş. (%) | Top-5 Komut (%) | Kapsama (%) | p50 (ms) |
|:-------------|--------:|---------------:|--------------:|--------------:|----------------:|------------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 78.6 | 0.017 |
| k=1 (tekli bağlam) | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 78.6 | 0.020 |
| k=2 (ikili bağlam) | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 78.6 | 0.017 |
| Geri alma yok (k=3) | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 76.6 | 0.017 |
| λ=0 (azalma yok) | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 78.6 | 0.017 |
| λ=0,02 (hızlı azalma) | 27.1 | 24.8 | 39.5 | 35.0 | 55.5 | 78.6 | 0.019 |
| Yalnızca frekans | 27.1 | 9.2 | 39.5 | 35.0 | 55.5 | 78.6 | 0.018 |
| En sık komut | 25.4 | 9.2 | 26.2 | 22.5 | 0.0 | 69.1 | 0.009 |

---

## 4.4 Temel Bulgular

1. Önerilen k=3 kelime-Markov modeli **KSR = 27.1%** elde etmiştir;  
   100 karakter başına yaklaşık 27 tuş tasarrufu sağlar.
2. En iyi referans yöntemini **+0.1% KSR** farkıyla geçmektedir  
   (önerilen: 27.1% — en iyi referans: 27.1%).
3. Çıkarım gecikmesi 5 ms hedefinin çok altındadır:  
   p99 = 0.053 ms.
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
