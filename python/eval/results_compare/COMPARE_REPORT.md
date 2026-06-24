# clever_shell — Veri Seti Karşılaştırma Raporu

**Veri seti A:** Kendi Geçmişim  
**Veri seti B:** Siber-Güvenlik Seti  

---

## Tablo 4.3 — Veri Seti Karşılaştırması: Önerilen Modelin İki Korpustaki Başarımı

*Önerilen yapılandırma (k=3, λ=0,005, geri-alma etkin). Satırlar: metrikler. Sütunlar: veri seti.*

| Metrik | Kendi Geçmişim | Siber-Güvenlik Seti |
|--------|------:|------:|
| Tuş Tasarrufu Oranı (KSR %) | 34.3 | 39.3 |
| Doğruluk@1 (%) | 25.5 | 42.8 |
| Doğruluk@3 (%) | 46.1 | 71.1 |
| Önek-Koşullu Tamamlama Doğ. (≥2 kar.%) | 46.0 | 69.7 |
| Top-5 Komut Kabul Oranı (%) | 49.2 | 28.5 |
| Kapsama (%) | 79.4 | 96.0 |
| Gecikme p99 (ms) | 0.091 | 0.651 |

---

## Tablo 4.4 — Zaman Azalma (λ) Ablasyonu: İki Veri Setinde Karşılaştırma

*Timestamp var olan siber sette λ artışı ile recency etkisinin gözlemlenmesi.*

| λ | KSR — Kendi Geçmişim (%) | Doğruluk@1 — Kendi Geçmişim (%) | KSR — Siber-Güvenlik Seti (%) | Doğruluk@1 — Siber-Güvenlik Seti (%) |
|--:|--------------------:|---------------------------:|--------------------:|---------------------------:|
| 0.0 | **34.3** | **25.5** | **39.7** | **42.6** |
| 0.005 | **34.3** | **25.5** | **39.3** | **42.8** |
| 0.02 | **34.3** | **25.5** | **39.2** | **43.0** |

---

## Temel Bulgular

### KSR Karşılaştırması
- **Kendi Geçmişim:** KSR = 34.3%, Doğruluk@1 = 25.5%
- **Siber-Güvenlik Seti:** KSR = 39.3%, Doğruluk@1 = 42.8%
- Fark: +5.0% KSR, +17.3% Doğruluk@1

### Önek-Koşullu Tamamlama ve Top-5 Komut
- **Kendi Geçmişim:** Önek-Koşullu = 46.0%, Top-5 Komut = 49.2%
- **Siber-Güvenlik Seti:** Önek-Koşullu = 69.7%, Top-5 Komut = 28.5%

### Zaman Azalma (λ) Etkisi
- **Kendi Geçmişim'nda** λ=0→0.005 KSR değişimi: +0.00% (küçük etki — eski zsh geçmişinde geniş zaman aralığı)
- **Siber-Güvenlik Seti'nde** λ=0→0.005 KSR değişimi: +0.43% (timestamp mevcut — decay gerçek etki gösteriyor)

---

## Şekiller

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.5 | `fig_compare.png` | Önerilen modelin iki veri setindeki performans karşılaştırması (gruplu bar chart). |
| Şekil 4.6 | `fig_decay_compare.png` | Zaman azalma katsayısı λ'nın iki veri setindeki etkisi. |

---

*`python3 python/eval/compare.py` tarafından otomatik üretilmiştir.*
