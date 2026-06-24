# Tablo ve Şekil Listesi — clever_shell Değerlendirmesi

> Bu dosya `python -m python.eval.run_eval` tarafından otomatik üretilmiştir.
> Word'e yapıştırmak için tabloyu seçip Yapıştır (Ctrl+V) uygulayın.

---

**Tablo 4.1 — Önerilen Yapılandırmanın Temel Performans Metrikleri**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim`, 730 eğitim / 182 test komutu).*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **34.3%** |
| Doğruluk@1 (Sonraki Kelime)                        | **25.5%** |
| Doğruluk@3 (Sonraki Kelime)                        | **46.1%** |
| Önek Tamamlama Doğruluğu                           | **47.6%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **46.0%** |
| Top-5 Komut Kabul Oranı                            | **49.2%** |
| Kapsama (sessiz kalmayan oran)                      | **79.4%** |
| Ortalama Gecikme                                    | **0.036 ms** |
| Gecikme p50                                         | **0.032 ms** |
| Gecikme p95                                         | **0.071 ms** |
| Gecikme p99                                         | **0.091 ms** |
| n-gram Bağlam Sayısı                               | **229** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **88.4 KB** |

---

**Tablo 4.2 — Ablasyon Çalışması: Yapılandırma Karşılaştırması**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim`, 730 eğitim / 182 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Doğruluk@3 (%) | Önek Doğruluğu (%) | Kapsama (%) | Gecikme p50 (ms) | Gecikme p99 (ms) |
|:-------------|--------:|---------------:|---------------:|------------------:|------------:|-----------------:|-----------------:|
| **Önerilen (k=3, λ=0,005)** | 34.3 | 25.5 | 46.1 | 47.6 | 79.4 | 0.032 | 0.091 |
| k=1 (tekli bağlam) | 34.3 | 25.5 | 46.1 | 47.6 | 79.4 | 0.033 | 0.097 |
| k=2 (ikili bağlam) | 34.3 | 25.5 | 46.1 | 47.6 | 79.4 | 0.033 | 0.093 |
| Geri alma yok (k=3) | 34.3 | 25.5 | 46.1 | 47.6 | 77.6 | 0.033 | 0.110 |
| λ=0 (azalma yok) | 34.3 | 25.5 | 46.1 | 47.6 | 79.4 | 0.033 | 0.099 |
| λ=0,02 (hızlı azalma) | 34.3 | 25.5 | 46.1 | 47.6 | 79.4 | 0.033 | 0.096 |
| Yalnızca frekans | 34.2 | 9.8 | 46.1 | 47.6 | 79.4 | 0.033 | 0.093 |
| En sık komut | 32.5 | 9.8 | 9.8 | 36.1 | 72.2 | 0.017 | 0.024 |

---

**Tablo 4.3 — Gecikme Dağılımı Özeti (ms)**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim`, 730 eğitim / 182 test komutu). predict_suffix çağrısı başına süre (1000 ölçüm).*

| Yapılandırma | Ortalama (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
|:-------------|-------------:|---------:|---------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 0.036 | 0.032 | 0.071 | 0.091 |
| k=1 (tekli bağlam) | 0.036 | 0.033 | 0.070 | 0.097 |
| k=2 (ikili bağlam) | 0.036 | 0.033 | 0.071 | 0.093 |
| Geri alma yok (k=3) | 0.039 | 0.033 | 0.079 | 0.110 |
| λ=0 (azalma yok) | 0.037 | 0.033 | 0.071 | 0.099 |
| λ=0,02 (hızlı azalma) | 0.036 | 0.033 | 0.071 | 0.096 |
| Yalnızca frekans | 0.037 | 0.033 | 0.071 | 0.093 |
| En sık komut | 0.016 | 0.017 | 0.019 | 0.024 |

---

## Şekil Başlıkları

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.1 | `fig_markov_order.png` | Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi. |
| Şekil 4.2 | `fig_ablation.png` | Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması. |
| Şekil 4.3 | `fig_latency.png` | predict_suffix çağrısı gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir. |
| Şekil 4.4 | `fig_decay.png` | Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi. |
