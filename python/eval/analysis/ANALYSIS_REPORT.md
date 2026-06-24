# Komut Düzeyi Markov Zinciri — Analiz Raporu

**Veri seti:** Siber-güvenlik eğitim seti (Švábenský 2021)  
**Toplam oturum:** 175  
**Eğitim oturumu:** 140 (%80)  
**Test oturumu:** 35 (%20)  

---

## Tablo 4.5 — Komut Düzeyi Ablasyon: k ve λ'ya Göre Doğruluk

*Her satır: mod × k × λ konfigürasyonu. ★ = önerilen yapılandırma.*

| Mod | Yapılandırma | Top-1 (%) | Top-5 (%) | #Test |
|-----|:-------------|----------:|----------:|------:|
| full | k=1, λ=0.0 | 18.7 | 27.3 | 2,819 |
| full | k=1, λ=0.005 | 18.3 | 27.8 | 2,819 |
| full | k=1, λ=0.02 | 17.9 | 27.7 | 2,819 |
| full | k=2, λ=0.0 | 18.6 | 26.5 | 2,819 |
| full | k=2, λ=0.005 | 18.2 | 26.7 | 2,819 |
| full | k=2, λ=0.02 | 18.1 | 26.1 | 2,819 |
| full | k=3, λ=0.0 | 17.7 | 25.2 | 2,819 |
| full | ★ k=3, λ=0.005 | 17.5 | 25.5 | 2,819 |
| full | k=3, λ=0.02 | 17.2 | 24.9 | 2,819 |
| full | baseline, λ=0.0 | 16.8 | 26.1 | 2,819 |
| full | baseline, λ=0.005 | 16.8 | 26.1 | 2,819 |
| full | baseline, λ=0.02 | 16.8 | 26.1 | 2,819 |
| token | k=1, λ=0.0 | 45.9 | 74.3 | 2,819 |
| token | k=1, λ=0.005 | 46.0 | 74.3 | 2,819 |
| token | k=1, λ=0.02 | 45.7 | 72.9 | 2,819 |
| token | k=2, λ=0.0 | 44.1 | 70.2 | 2,819 |
| token | k=2, λ=0.005 | 44.5 | 70.2 | 2,819 |
| token | k=2, λ=0.02 | 43.4 | 69.1 | 2,819 |
| token | k=3, λ=0.0 | 41.7 | 65.0 | 2,819 |
| token | ★ k=3, λ=0.005 | 43.2 | 65.1 | 2,819 |
| token | k=3, λ=0.02 | 42.3 | 64.4 | 2,819 |
| token | baseline, λ=0.0 | 24.5 | 59.0 | 2,819 |
| token | baseline, λ=0.005 | 24.5 | 59.0 | 2,819 |
| token | baseline, λ=0.02 | 24.5 | 59.0 | 2,819 |

---

## Temel Bulgular

### k Etkisi (λ=0.005 sabit)
| Karşılaştırma | Tam Komut Top-1 fark | Tam Komut Top-5 fark | Token Top-1 fark | Token Top-5 fark |
|:------|---:|---:|---:|---:|
| k=1 → k=2 | -0.04 pp | -1.10 pp | -1.45 pp | -4.04 pp |
| k=2 → k=3 | -0.74 pp | -1.21 pp | -1.31 pp | -5.14 pp |
| k=1 → k=3 | -0.78 pp | -2.31 pp | -2.77 pp | -9.19 pp |

### λ Etkisi (k=3 sabit)
| Karşılaştırma | Tam Komut Top-1 fark | Tam Komut Top-5 fark | Token Top-1 fark | Token Top-5 fark |
|:------|---:|---:|---:|---:|
| λ=0 → λ=0.005 | -0.18 pp | +0.35 pp | +1.49 pp | +0.07 pp |
| λ=0.005 → λ=0.02 | -0.25 pp | -0.67 pp | -0.92 pp | -0.67 pp |

---

## Şekiller

| Şekil No | Dosya | Açıklama |
|----------|-------|---------|
| Şekil 4.7 | `fig_command_k.png` | Markov bağlam uzunluğu k'ya göre Top-1 ve Top-5 doğruluğu (λ=0.005). |
| Şekil 4.8 | `fig_command_decay.png` | Zaman azalma katsayısı λ'ya göre Top-1 ve Top-5 doğruluğu (k=3). |

---

*`python3 python/eval/command_chain.py` tarafından otomatik üretilmiştir.*
