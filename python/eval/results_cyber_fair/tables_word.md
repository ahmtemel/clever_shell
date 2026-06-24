# Tablo ve Şekil Listesi — clever_shell Değerlendirmesi

> Bu dosya `python -m python.eval.run_eval` tarafından otomatik üretilmiştir.
> Word'e yapıştırmak için tabloyu seçip Yapıştır (Ctrl+V) uygulayın.

---

**Tablo 4.1 — Önerilen Yapılandırmanın Temel Performans Metrikleri**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti — filtresiz (Švábenský 2021)`, 8765 eğitim / 2192 test komutu).*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **47.2%** |
| Doğruluk@1 (Sonraki Kelime)                        | **29.0%** |
| Doğruluk@3 (Sonraki Kelime)                        | **54.7%** |
| Önek Tamamlama Doğruluğu                           | **67.7%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **68.5%** |
| Top-5 Komut Kabul Oranı                            | **25.3%** |
| Kapsama (sessiz kalmayan oran)                      | **94.6%** |
| Ortalama Gecikme                                    | **0.144 ms** |
| Gecikme p50                                         | **0.141 ms** |
| Gecikme p95                                         | **0.384 ms** |
| Gecikme p99                                         | **0.615 ms** |
| n-gram Bağlam Sayısı                               | **3,325** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **1308.2 KB** |

---

**Tablo 4.2 — Ablasyon Çalışması: Yapılandırma Karşılaştırması**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti — filtresiz (Švábenský 2021)`, 8765 eğitim / 2192 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Doğruluk@3 (%) | Önek Doğruluğu (%) | Kapsama (%) | Gecikme p50 (ms) | Gecikme p99 (ms) |
|:-------------|--------:|---------------:|---------------:|------------------:|------------:|-----------------:|-----------------:|
| **Önerilen (k=3, λ=0,005)** | 47.2 | 29.0 | 54.7 | 67.7 | 94.6 | 0.141 | 0.615 |
| k=1 (tekli bağlam) | 47.1 | 28.4 | 55.0 | 67.6 | 94.6 | 0.139 | 0.575 |
| k=2 (ikili bağlam) | 47.2 | 29.0 | 54.6 | 67.7 | 94.6 | 0.139 | 0.599 |
| Geri alma yok (k=3) | 46.9 | 27.6 | 54.7 | 67.7 | 93.1 | 0.139 | 0.580 |
| λ=0 (azalma yok) | 44.9 | 27.9 | 49.7 | 65.2 | 94.6 | 0.141 | 0.621 |
| λ=0,02 (hızlı azalma) | 48.1 | 29.1 | 54.4 | 69.1 | 94.6 | 0.140 | 0.585 |
| Yalnızca frekans | 45.1 | 16.9 | 54.7 | 67.7 | 94.6 | 0.145 | 0.615 |
| En sık komut | 24.5 | 16.8 | 16.8 | 25.7 | 74.5 | 0.228 | 0.358 |

---

**Tablo 4.3 — Gecikme Dağılımı Özeti (ms)**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti — filtresiz (Švábenský 2021)`, 8765 eğitim / 2192 test komutu). predict_suffix çağrısı başına süre (1000 ölçüm).*

| Yapılandırma | Ortalama (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
|:-------------|-------------:|---------:|---------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 0.144 | 0.141 | 0.384 | 0.615 |
| k=1 (tekli bağlam) | 0.141 | 0.139 | 0.376 | 0.575 |
| k=2 (ikili bağlam) | 0.141 | 0.139 | 0.376 | 0.599 |
| Geri alma yok (k=3) | 0.142 | 0.139 | 0.377 | 0.580 |
| λ=0 (azalma yok) | 0.148 | 0.141 | 0.386 | 0.621 |
| λ=0,02 (hızlı azalma) | 0.142 | 0.140 | 0.376 | 0.585 |
| Yalnızca frekans | 0.155 | 0.145 | 0.389 | 0.615 |
| En sık komut | 0.224 | 0.228 | 0.247 | 0.358 |

---

## Şekil Başlıkları

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.1 | `fig_markov_order.png` | Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi. |
| Şekil 4.2 | `fig_ablation.png` | Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması. |
| Şekil 4.3 | `fig_latency.png` | predict_suffix çağrısı gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir. |
| Şekil 4.4 | `fig_decay.png` | Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi. |
