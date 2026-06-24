# clever_shell — Veri Seti Karşılaştırma Raporu

**Veri seti A:** Kendi Geçmişim (snapshot, frozen)  
**Veri seti B:** Siber-Güvenlik Seti (filtresiz — adil)  

---

## Tablo 4.3 — Veri Seti Karşılaştırması: Önerilen Modelin İki Korpustaki Başarımı

*Önerilen yapılandırma (k=3, λ=0,005, geri-alma etkin). Satırlar: metrikler. Sütunlar: veri seti.*

| Metrik | Kendi Geçmişim (snapshot, frozen) | Siber-Güvenlik Seti (filtresiz — adil) |
|--------|------:|------:|
| Tuş Tasarrufu Oranı (KSR %) | 27.1 | 47.2 |
| Doğruluk@1 (%) | 24.8 | 29.0 |
| Doğruluk@3 (%) | 45.9 | 54.7 |
| Önek-Koşullu Tamamlama Doğ. (≥2 kar.%) | 35.0 | 68.5 |
| Top-5 Komut Kabul Oranı (%) | 55.5 | 25.3 |
| Kapsama (%) | 78.6 | 94.6 |
| Gecikme p99 (ms) | 0.053 | 0.615 |

---

## Tablo 4.4 — Zaman Azalma (λ) Ablasyonu: İki Veri Setinde Karşılaştırma

*Timestamp var olan siber sette λ artışı ile recency etkisinin gözlemlenmesi.*

| λ | KSR — Kendi Geçmişim (snapshot, frozen) (%) | Doğruluk@1 — Kendi Geçmişim (snapshot, frozen) (%) | KSR — Siber-Güvenlik Seti (filtresiz — adil) (%) | Doğruluk@1 — Siber-Güvenlik Seti (filtresiz — adil) (%) |
|--:|--------------------:|---------------------------:|--------------------:|---------------------------:|
| 0.0 | **27.1** | **24.8** | **44.9** | **27.9** |
| 0.005 | **27.1** | **24.8** | **47.2** | **29.0** |
| 0.02 | **27.1** | **24.8** | **48.1** | **29.1** |

---

## Temel Bulgular

### KSR Karşılaştırması
- **Kendi Geçmişim (snapshot, frozen):** KSR = 27.1%, Doğruluk@1 = 24.8%
- **Siber-Güvenlik Seti (filtresiz — adil):** KSR = 47.2%, Doğruluk@1 = 29.0%
- Fark: +20.0% KSR, +4.1% Doğruluk@1

### Önek-Koşullu Tamamlama ve Top-5 Komut
- **Kendi Geçmişim (snapshot, frozen):** Önek-Koşullu = 35.0%, Top-5 Komut = 55.5%
- **Siber-Güvenlik Seti (filtresiz — adil):** Önek-Koşullu = 68.5%, Top-5 Komut = 25.3%

### Zaman Azalma (λ) Etkisi
- **Kendi Geçmişim (snapshot, frozen)'nda** λ=0→0.005 KSR değişimi: +0.00% (küçük etki — eski zsh geçmişinde geniş zaman aralığı)
- **Siber-Güvenlik Seti (filtresiz — adil)'nde** λ=0→0.005 KSR değişimi: -2.24% (timestamp mevcut — decay gerçek etki gösteriyor)

---

## Şekiller

| Şekil No | Dosya | Açıklama (başlık ALTTA) |
|----------|-------|-------------------------|
| Şekil 4.5 | `fig_compare.png` | Önerilen modelin iki veri setindeki performans karşılaştırması (gruplu bar chart). |
| Şekil 4.6 | `fig_decay_compare.png` | Zaman azalma katsayısı λ'nın iki veri setindeki etkisi. |

---

*`python3 python/eval/compare.py` tarafından otomatik üretilmiştir.*
