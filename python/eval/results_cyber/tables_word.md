# Tablo ve Şekil Listesi — clever_shell Değerlendirmesi

> Bu dosya `python -m python.eval.run_eval` tarafından otomatik üretilmiştir.
> Word'e yapıştırmak için tabloyu seçip Yapıştır (Ctrl+V) uygulayın.

---

**Tablo 4.1 — Önerilen Yapılandırmanın Temel Performans Metrikleri**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti (Švábenský 2021)`, 8765 eğitim / 1335 test komutu).*

| Metrik | Değer |
|--------|-------|
| Tuş Tasarrufu Oranı (KSR)                          | **39.3%** |
| Doğruluk@1 (Sonraki Kelime)                        | **42.8%** |
| Doğruluk@3 (Sonraki Kelime)                        | **71.1%** |
| Önek Tamamlama Doğruluğu                           | **71.2%** |
| Önek-Koşullu Tamamlama Doğruluğu (≥2 karakter)    | **69.7%** |
| Top-5 Komut Kabul Oranı                            | **28.5%** |
| Kapsama (sessiz kalmayan oran)                      | **96.0%** |
| Ortalama Gecikme                                    | **0.205 ms** |
| Gecikme p50                                         | **0.229 ms** |
| Gecikme p95                                         | **0.616 ms** |
| Gecikme p99                                         | **0.651 ms** |
| n-gram Bağlam Sayısı                               | **3,325** |
| Tablo Bellek Ayak İzi (yüzeysel)                   | **1308.2 KB** |

---

**Tablo 4.2 — Ablasyon Çalışması: Yapılandırma Karşılaştırması**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti (Švábenský 2021)`, 8765 eğitim / 1335 test komutu). Kalın: önerilen yapılandırma.*

| Yapılandırma | KSR (%) | Doğruluk@1 (%) | Doğruluk@3 (%) | Önek Doğruluğu (%) | Kapsama (%) | Gecikme p50 (ms) | Gecikme p99 (ms) |
|:-------------|--------:|---------------:|---------------:|------------------:|------------:|-----------------:|-----------------:|
| **Önerilen (k=3, λ=0,005)** | 39.3 | 42.8 | 71.1 | 71.2 | 96.0 | 0.229 | 0.651 |
| k=1 (tekli bağlam) | 39.3 | 42.6 | 71.3 | 71.2 | 96.0 | 0.232 | 0.854 |
| k=2 (ikili bağlam) | 39.3 | 42.8 | 71.2 | 71.2 | 96.0 | 0.335 | 2.810 |
| Geri alma yok (k=3) | 39.2 | 42.4 | 71.1 | 71.2 | 95.7 | 0.231 | 0.655 |
| λ=0 (azalma yok) | 39.7 | 42.6 | 71.0 | 72.4 | 96.0 | 0.232 | 0.655 |
| λ=0,02 (hızlı azalma) | 39.2 | 43.0 | 69.9 | 71.6 | 96.0 | 0.231 | 0.657 |
| Yalnızca frekans | 35.8 | 31.1 | 71.1 | 71.2 | 96.0 | 0.233 | 0.647 |
| En sık komut | 38.4 | 31.0 | 31.0 | 48.3 | 86.3 | 0.443 | 1.523 |

---

**Tablo 4.3 — Gecikme Dağılımı Özeti (ms)**

*Kaynak: Kendi kabuk geçmişi (`Siber-güvenlik eğitim seti (Švábenský 2021)`, 8765 eğitim / 1335 test komutu). predict_suffix çağrısı başına süre (1000 ölçüm).*

| Yapılandırma | Ortalama (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
|:-------------|-------------:|---------:|---------:|---------:|
| **Önerilen (k=3, λ=0,005)** | 0.205 | 0.229 | 0.616 | 0.651 |
| k=1 (tekli bağlam) | 0.223 | 0.232 | 0.634 | 0.854 |
| k=2 (ikili bağlam) | 0.467 | 0.335 | 1.407 | 2.810 |
| Geri alma yok (k=3) | 0.209 | 0.231 | 0.622 | 0.655 |
| λ=0 (azalma yok) | 0.207 | 0.232 | 0.620 | 0.655 |
| λ=0,02 (hızlı azalma) | 0.206 | 0.231 | 0.624 | 0.657 |
| Yalnızca frekans | 0.219 | 0.233 | 0.618 | 0.647 |
| En sık komut | 0.515 | 0.443 | 0.848 | 1.523 |

---

## Şekil Başlıkları

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.1 | `fig_markov_order.png` | Markov bağlam uzunluğu k'ya göre KSR ve Doğruluk@1 değişimi. |
| Şekil 4.2 | `fig_ablation.png` | Ablasyon çalışması: tüm yapılandırmaların KSR ve Doğruluk@1 karşılaştırması. |
| Şekil 4.3 | `fig_latency.png` | predict_suffix çağrısı gecikme CDF dağılımı; kırmızı kesik çizgi 5 ms hedefini gösterir. |
| Şekil 4.4 | `fig_decay.png` | Zaman azalma katsayısı λ'ya göre KSR ve Doğruluk@1 değişimi. |
