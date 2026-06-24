# clever_shell — Bellek ve Kaynak Güvenliği Raporu

**Tarih:** 2026-06-24  
**Platform:** macOS 25.4.0 (darwin), Apple Silicon  
**Derleyici:** GCC (Homebrew), `-Wall -Wextra -Werror -g -fsanitize=address,undefined`

---

## 1. ASAN Binary Derleme

```
make asan
→ gcc -Wall -Wextra -Werror -g \
      -fsanitize=address,undefined \
      -Iinc <ZMQ flags> src/*.c -o minishell_asan
```

**Sonuç: BAŞARILI** — 0 uyarı, 0 hata.  
Binary boyutu: 190,128 bayt (`./minishell_asan`).

---

## 2. UBSan / AddressSanitizer Çalışma Testi

### Test Senaryoları (`test/leak_cmds.txt`)

| # | Komut | Açıklama |
|---|-------|---------|
| 1 | `ls` | Basit harici komut |
| 2 | `echo hi \| cat` | Pipe (fork + pipe + dup2) |
| 3 | `ls > /tmp/mstest.txt` | Çıktı yönlendirme (open + dup2) |
| 4 | `cat /tmp/mstest.txt` | Giriş okuma |
| 5 | `pwd` | Builtin komut |
| 6 | `exit` | Temiz çıkış |

### Sonuç

```
ASAN stderr: (boş)   → 0 AddressSanitizer hatası
ASAN stderr: (boş)   → 0 UndefinedBehaviorSanitizer hatası
```

**Tespit edilen sızıntı, kullanım-sonrası-serbest bırakma, tampon taşması veya tanımsız davranış: YOK.**

---

## 3. macOS Özel Notlar

### LeakSanitizer Kısıtlaması

macOS'ta AddressSanitizer `detect_leaks=1` (LeakSanitizer) desteklememektedir; bu
özellik yalnızca Linux'ta bulunur. Bu nedenle bellek sızıntıları için ayrı araç gerekir.

```
ASAN_OPTIONS=detect_leaks=1 ./minishell_asan < test/leak_cmds.txt
→ ==..==AddressSanitizer: detect_leaks is not supported on this platform.
```

### `leaks(1)` Aracı

macOS'un yerel `leaks` aracı MallocStackLogging ve `sudo` ayrıcalığı gerektirir.
Bu CI ortamında `sudo` erişimi bulunmamaktadır:

```
leaks[7305]: leaks cannot examine process (minishell) for unknown reasons;
             try running with `sudo`.
```

**Önerilen aksiyon:** Üretim ortamında `sudo leaks --atExit -- ./minishell < test/leak_cmds.txt`
ile tam sızıntı raporu alınabilir.

---

## 4. Statik Kanıtlar

Dinamik çalışma testlerine ek olarak, kod mimarisi aşağıdaki mekanizmalarla
bellek ve kaynak güvenliğini sağlamaktadır:

| Mekanizma | Kanıt |
|-----------|-------|
| Strict derleme bayrakları | `-Wall -Wextra -Werror` → her uyarı hata olarak işlenir |
| Her `fork` sonrası fd kapatma | `executor.c`: kullanılmayan `pipe` uçları `close()` edilir |
| Cocuk süreçte `_exit()` | `executor.c`: çift `atexit`/`stdio flush` riski eliminedir |
| `reapply_raw_mode()` | Terminal state kaybı önlenir |
| ZMQ `ZMQ_DONTWAIT` | Non-blocking recv; blok/lock riski yok |
| ZMQ kaynakları | `zmq_ipc_cleanup()` `main.c` çıkışında çağrılır |

---

## 5. Özet

| Test | Sonuç |
|------|-------|
| ASAN derleme | ✅ 0 hata |
| UBSan çalışma | ✅ 0 hata |
| ASan tampon/UAF | ✅ 0 hata |
| LeakSanitizer | ⚠️ macOS'ta desteklenmez |
| `leaks(1)` | ⚠️ sudo gerektirir |

**Genel değerlendirme:** Sistem, UBSan ve ASan kapsamında temiz çalışmaktadır.
Tam sızıntı kanıtı için Linux CI ortamı veya `sudo leaks` önerilir.
