# Tablo ve Şekil Listesi — clever_shell Değerlendirmesi

> Bu dosya `python -m python.eval.run_eval` tarafından otomatik üretilmiştir.
> Word'e yapıştırmak için tabloyu seçip Yapıştır (Ctrl+V) uygulayın.

---

**Tablo 4.1 — Önerilen Yapılandırmanın Temel Performans Metrikleri**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`, 728 eğitim / 183 test komutu).*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **27.1%** |
| Doğruluk@1 (Sonraki Kelime)                        | **24.8%** |
| Doğruluk@3 (Sonraki Kelime)                        | **45.9%** |
| Önek Tamamlama Doğruluğu                           | **39.5%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **35.0%** |
| Top-5 Komut Kabul Oranı                            | **55.5%** |
| Kapsama (sessiz kalmayan oran)                      | **78.6%** |
| Ortalama Gecikme                                    | **0.020 ms** |
| Gecikme p50                                         | **0.017 ms** |
| Gecikme p95                                         | **0.041 ms** |
| Gecikme p99                                         | **0.053 ms** |
| n-gram Bağlam Sayısı                               | **146** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **58.1 KB** |

---

**Tablo 4.2 — Ablasyon Çalışması: Yapılandırma Karşılaştırması**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`, 728 eğitim / 183 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Doğruluk@3 (%) | Önek Doğruluğu (%) | Kapsama (%) | Gecikme p50 (ms) | Gecikme p99 (ms) |
|:-------------|--------:|---------------:|---------------:|------------------:|------------:|-----------------:|-----------------:|
| **Önerilen (k=3, λ=0,005)** | 27.1 | 24.8 | 45.9 | 39.5 | 78.6 | 0.017 | 0.053 |
| k=1 (tekli bağlam) | 27.1 | 24.8 | 45.9 | 39.5 | 78.6 | 0.020 | 0.120 |
| k=2 (ikili bağlam) | 27.1 | 24.8 | 45.9 | 39.5 | 78.6 | 0.017 | 0.048 |
| Geri alma yok (k=3) | 27.1 | 24.8 | 45.9 | 39.5 | 76.6 | 0.017 | 0.050 |
| λ=0 (azalma yok) | 27.1 | 24.8 | 45.9 | 39.5 | 78.6 | 0.017 | 0.052 |
| λ=0,02 (hızlı azalma) | 27.1 | 24.8 | 45.9 | 39.5 | 78.6 | 0.019 | 0.078 |
| Yalnızca frekans | 27.1 | 9.2 | 45.9 | 39.5 | 78.6 | 0.018 | 0.053 |
| En sık komut | 25.4 | 9.2 | 9.2 | 26.2 | 69.1 | 0.009 | 0.011 |

---

**Tablo 4.3 — Gecikme Dağılımı Özeti (ms)**

*Kaynak: Kendi kabuk geçmişi (`Kendi kabuk geçmişim (snapshot, 1001 komut, 2026-06-24)`, 728 eğitim / 183 test komutu). predict_suffix çağrısı başına süre (1000 ölçüm).*

| Yapılandırma | Ortalama (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
|:-------------|-------------:|---------:|---------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 0.020 | 0.017 | 0.041 | 0.053 |
| k=1 (tekli bağlam) | 0.027 | 0.020 | 0.060 | 0.120 |
| k=2 (ikili bağlam) | 0.020 | 0.017 | 0.040 | 0.048 |
| Geri alma yok (k=3) | 0.020 | 0.017 | 0.040 | 0.050 |
| λ=0 (azalma yok) | 0.020 | 0.017 | 0.040 | 0.052 |
| λ=0,02 (hızlı azalma) | 0.023 | 0.019 | 0.045 | 0.078 |
| Yalnızca frekans | 0.021 | 0.018 | 0.042 | 0.053 |
| En sık komut | 0.009 | 0.009 | 0.010 | 0.011 |

---

## Şekil Başlıkları

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.1 | `fig_markov_order.png` | Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi. |
| Şekil 4.2 | `fig_ablation.png` | Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması. |
| Şekil 4.3 | `fig_latency.png` | predict_suffix çağrısı gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir. |
| Şekil 4.4 | `fig_decay.png` | Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi. |
