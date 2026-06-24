"""
metrics.py – Pure metric functions for evaluating WordMarkovChain.

All functions accept a ``predict_fn: Callable[[str], str]`` (the model's
``predict_suffix`` method) and a list of command strings.  They are
intentionally free of model-specific imports so they can be unit-tested
with any mock predictor.

Mathematical definitions
------------------------
Let  L   = length of command string  c
     K   = keystrokes required WITH prediction assistance
     p_i = prediction returned by model when buffer = c[:i]

Keystroke Savings Ratio (KSR)
    KSR(c) = 1 − K / L
    K is computed by a greedy left-to-right simulation:
      • If p_i ≠ "" and c[i:].startswith(p_i): accept with 1 key (Tab),
        advance cursor by len(p_i).
      • Otherwise: type one character, advance by 1.
    System-level KSR = Σ KSR(c_j) · L_j / Σ L_j  (length-weighted mean).

Top-1 Next-Word Accuracy
    At every word boundary w_0 w_1 … w_{i-1} ⎵ (buffer = join of i words
    + trailing space), the model predicts the next token w_i.
    Acc@1 = |{i : predict(buf_i) = w_i}| / total_boundaries.

Top-3 Next-Word Accuracy
    Acc@3 = |{i : w_i ∈ top_k_fn(buf_i, 3)}| / total_boundaries.
    Requires a ``top_k_fn(buf, k) → List[str]`` which the runner builds
    by querying the model's internal Counter table directly.

Prefix-Completion Accuracy
    For each character position j (1 ≤ j < len(w_i)) within word w_i,
    the buffer ends mid-word.  The model predicts the remaining suffix.
    Acc_prefix = |{(i,j) : predict(buf+w_i[:j]) = w_i[j:]}| / total_mid_positions.

Coverage (1 − Silence Rate)
    Fraction of (command, position) pairs for which the model returns a
    non-empty prediction.  Measured at every character position 0..L.
"""

from __future__ import annotations

import shlex
from typing import Callable, Dict, List, Optional


# Type aliases
PredictFn = Callable[[str], str]
TopKFn    = Callable[[str, int], List[str]]


# ── KSR ───────────────────────────────────────────────────────────────────────

def _simulate_ksr(predict_fn: PredictFn, command: str) -> tuple:
    """
    Greedy keystroke-savings simulation for a single command string.

    Returns:
        ksr        – Keystroke Savings Ratio in [0, 1]
        keystrokes – actual number of key presses with assistance
        saved      – number of characters NOT typed due to acceptance
    """
    L = len(command)
    if L == 0:
        return 0.0, 0, 0
    keystrokes = 0
    saved      = 0
    i = 0
    while i < L:
        pred = predict_fn(command[:i])
        remaining = command[i:]
        if pred and remaining.startswith(pred):
            # Accept prediction with 1 keystroke (Tab)
            keystrokes += 1
            saved      += len(pred) - 1  # chars skipped (prediction_len − Tab)
            i          += len(pred)
        else:
            # Type next character
            keystrokes += 1
            i          += 1
    ksr = saved / L  # == 1 − keystrokes/L
    return ksr, keystrokes, saved


def keystroke_savings_ratio(
    predict_fn: PredictFn,
    commands: List[str],
) -> Dict[str, float]:
    """
    Compute length-weighted mean KSR over *commands*.

    Returns a dict with keys: mean_ksr, total_saved, total_chars.
    """
    total_chars = 0
    total_saved = 0
    for cmd in commands:
        if not cmd.strip():
            continue
        _, _, saved = _simulate_ksr(predict_fn, cmd)
        total_chars += len(cmd)
        total_saved += saved
    mean_ksr = total_saved / total_chars if total_chars > 0 else 0.0
    return {
        "mean_ksr":    round(mean_ksr, 4),
        "total_saved": total_saved,
        "total_chars": total_chars,
    }


# ── Next-word accuracy ────────────────────────────────────────────────────────

def _word_boundaries(command: str):
    """
    Yield (buffer, expected_word) for every word boundary in *command*.

    At boundary i (having typed words 0..i-1 plus a trailing space), the
    model is asked to predict words[i].
    """
    try:
        words = shlex.split(command, posix=False)
    except ValueError:
        return
    for i, word in enumerate(words):
        buf = (" ".join(words[:i]) + " ") if i > 0 else ""
        yield buf, word


def next_word_accuracy_top1(
    predict_fn: PredictFn,
    commands: List[str],
) -> float:
    """
    Top-1 next-word accuracy: fraction of word boundaries where
    predict_fn(buf) exactly equals the actual next word token.

    Acc@1 = |{(c,i) : predict(buf_{c,i}) = words_c[i]}| / Σ |words_c|
    """
    correct = total = 0
    for cmd in commands:
        for buf, word in _word_boundaries(cmd):
            pred = predict_fn(buf)
            if pred == word:
                correct += 1
            total += 1
    return correct / total if total > 0 else 0.0


def next_word_accuracy_topk(
    topk_fn: TopKFn,
    commands: List[str],
    k: int = 3,
) -> float:
    """
    Top-k next-word accuracy: fraction of word boundaries where the actual
    next word appears among the k highest-scored candidates.

    Acc@k = |{(c,i) : words_c[i] ∈ top_k(buf_{c,i})}| / Σ |words_c|

    Args:
        topk_fn: callable(buf, k) → list of up to k candidate next-words.
    """
    correct = total = 0
    for cmd in commands:
        for buf, word in _word_boundaries(cmd):
            candidates = topk_fn(buf, k)
            if word in candidates:
                correct += 1
            total += 1
    return correct / total if total > 0 else 0.0


# ── Prefix-completion accuracy ────────────────────────────────────────────────

def prefix_completion_accuracy(
    predict_fn: PredictFn,
    commands: List[str],
) -> float:
    """
    Prefix-completion accuracy: for each mid-word position, check whether
    the model's prediction exactly equals the remaining word suffix.

    Acc_pfx = |{(c,i,j) : predict(buf+w_i[:j]) = w_i[j:]}| / Σ Σ (|w_i|−1)

    Only word positions with at least 2 characters are counted
    (single-character words have no mid-word prefix).
    """
    correct = total = 0
    for cmd in commands:
        try:
            words = shlex.split(cmd, posix=False)
        except ValueError:
            continue
        for i, word in enumerate(words):
            if len(word) < 2:
                continue
            prefix_context = (" ".join(words[:i]) + " ") if i > 0 else ""
            for j in range(1, len(word)):
                buf            = prefix_context + word[:j]
                expected_suffix = word[j:]
                pred           = predict_fn(buf)
                if pred == expected_suffix:
                    correct += 1
                total += 1
    return correct / total if total > 0 else 0.0


# ── Prefix-conditional accuracy (Ghost-text senaryosu) ───────────────────────

def prefix_conditional_accuracy(
    predict_fn: PredictFn,
    commands: List[str],
    min_chars: int = 2,
) -> float:
    """
    Önek-koşullu tamamlama doğruluğu (Ghost-text gerçek kullanım senaryosu).

    Kullanıcının bir token'ın ilk j ≥ min_chars karakterini yazdığı varsayılır;
    bu noktada modelin tam kalan suffix'i tahmin edip etmediği ölçülür.

    Matematiksel tanım:
      T = { (c, i, j) : c ∈ commands, w_i ∈ tokens(c),
                        j ∈ [min_chars, |w_i| − 1] }
      Acc_cond = |{ (c, i, j) ∈ T : predict(buf_{c,i,j}) = w_i[j:] }| / |T|

    Burada buf_{c,i,j} = " ".join(tokens(c)[:i]) + " " + w_i[:j]
    (önceki kelimeler + kısmen yazılmış güncel token).

    Gerçek kullanım senaryosunu yansıtır: Ghost Text sistemi en az min_chars
    karakter yazıldıktan sonra öneri gösterir.

    Args:
        predict_fn: buf (str) → tahmini suffix (str)
        commands:   değerlendirme komutu listesi
        min_chars:  Ghost Text'in devreye girdiği minimum yazılmış karakter sayısı
    """
    correct = total = 0
    for cmd in commands:
        try:
            words = shlex.split(cmd, posix=False)
        except ValueError:
            continue
        for i, word in enumerate(words):
            if len(word) <= min_chars:
                # min_chars sonrası kalan suffix olmak için en az min_chars+1 kar. gerekli
                continue
            prefix_context = (" ".join(words[:i]) + " ") if i > 0 else ""
            for j in range(min_chars, len(word)):
                buf             = prefix_context + word[:j]
                expected_suffix = word[j:]
                pred            = predict_fn(buf)
                if pred == expected_suffix:
                    correct += 1
                total += 1
    return correct / total if total > 0 else 0.0


# ── Top-k komut kabul oranı ────────────────────────────────────────────────────

def topk_command_acceptance(
    topk_fn: TopKFn,
    commands: List[str],
    k: int = 5,
) -> float:
    """
    Top-k komut kabul oranı: önceki komut bağlamında bir sonraki komutun
    ilk token'ının (komut adı) top-k aday listesinde yer alma oranı.

    Her (c_{i-1}, c_i) çifti için (i ≥ 1):
      • buf = c_{i-1} + " "  (önceki komut + boşluk → yeni komut başlangıcı)
      • candidates = topk_fn(buf, k)
      • first_token(c_i) ∈ candidates ise "kabul"

    Matematiksel tanım:
      Acc_{top-k} =
        |{ i ≥ 1 : first_token(c_i) ∈ top_k( c_{i-1} + " ", k ) }|
        / (|commands| − 1)

    Bu metrik, modelin ardışık komut dizilerini ne ölçüde öğrendiğini;
    yani "komut-sonrası bağlam"dan yeni komut adını tahmin gücünü ölçer.

    Args:
        topk_fn:  callable (buf: str, k: int) → List[str]
        commands: kronolojik komut listesi (test seti)
        k:        aday listesi boyutu (varsayılan 5)
    """
    correct = total = 0
    for i in range(1, len(commands)):
        cmd      = commands[i]
        prev_cmd = commands[i - 1]
        try:
            first_token = shlex.split(cmd, posix=False)[0]
        except (ValueError, IndexError):
            continue
        # Önceki komutun son k kelimesini bağlam olarak ver
        buf        = prev_cmd + " "
        candidates = topk_fn(buf, k)
        if first_token in candidates:
            correct += 1
        total += 1
    return correct / total if total > 0 else 0.0


# ── Coverage ──────────────────────────────────────────────────────────────────

def coverage_rate(
    predict_fn: PredictFn,
    commands: List[str],
    max_cmds: int = 300,
) -> float:
    """
    Coverage (1 − Silence Rate): fraction of (command, position) pairs for
    which the model returns a non-empty prediction string.

    Coverage = |{(c,i) : predict(c[:i]) ≠ ""}| / Σ (|c| + 1)

    Coverage is checked at positions 0 through len(c) inclusive (the final
    position corresponds to the complete command, probing for continuation).
    *max_cmds* caps the computation to keep evaluation fast.
    """
    covered = total = 0
    for cmd in commands[:max_cmds]:
        for i in range(len(cmd) + 1):
            pred = predict_fn(cmd[:i])
            total   += 1
            if pred:
                covered += 1
    return covered / total if total > 0 else 0.0


# ── Convenience aggregator ────────────────────────────────────────────────────

def compute_all_metrics(
    predict_fn: PredictFn,
    commands: List[str],
    topk_fn: Optional[TopKFn] = None,
    max_cmds: int = 500,
) -> Dict[str, float]:
    """
    Tüm değerlendirme metriklerini hesapla ve düz bir dict olarak döndür.

    Anahtarlar:
      ksr, top1_acc, prefix_acc, prefix_cond_acc, coverage  — her zaman
      top3_acc, topk_cmd_acc                                 — topk_fn verilince
    """
    cmds = [c for c in commands if c.strip()][:max_cmds]
    ksr_result = keystroke_savings_ratio(predict_fn, cmds)
    out: Dict[str, float] = {
        "ksr":              ksr_result["mean_ksr"],
        "top1_acc":         next_word_accuracy_top1(predict_fn, cmds),
        "prefix_acc":       prefix_completion_accuracy(predict_fn, cmds),
        "prefix_cond_acc":  prefix_conditional_accuracy(predict_fn, cmds, min_chars=2),
        "coverage":         coverage_rate(predict_fn, cmds),
    }
    if topk_fn is not None:
        out["top3_acc"]      = next_word_accuracy_topk(topk_fn, cmds, k=3)
        out["topk_cmd_acc"]  = topk_command_acceptance(topk_fn, cmds, k=5)
    return out
