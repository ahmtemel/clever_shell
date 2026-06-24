"""
test_metrics.py – Unit tests for the pure metric functions in metrics.py.

Run with:
    pytest python/eval/test_metrics.py -v

All tests use deterministic mock predictors so no real model is needed.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest

from python.eval.metrics import (
    _simulate_ksr,
    _word_boundaries,
    coverage_rate,
    keystroke_savings_ratio,
    next_word_accuracy_top1,
    next_word_accuracy_topk,
    prefix_completion_accuracy,
    compute_all_metrics,
)


# ── Mock predictors ───────────────────────────────────────────────────────────

def _perfect_predictor(buf: str) -> str:
    """
    Oracle: knows the exact remaining suffix of these fixed commands.

    At position 0 (empty buf) the oracle returns the full first command
    "git status"; at word-boundaries it returns the next word; at mid-word
    positions it returns the remaining part of the current word.

    KSR behaviour:
      • "git status" (L=10): accepts "git status" at i=0 → 1 keystroke,
        KSR = 9/10 = 0.90
      • "ls -la" (L=6):  accepts " -la" at "ls" → KSR = 3/6 = 0.50
      • "make re" (L=7): accepts " re" at "make" → KSR = 2/7 ≈ 0.286
      • aggregate KSR ≈ 0.608 (length-weighted)
    Top-1 word boundary accuracy = 0.5 (3/6): oracle returns "status",
      "-la", "re" correctly at boundaries "git ","ls ","make "; but at ""
      it returns "git status" (≠ "git"), so the three "" boundaries fail.
    Prefix accuracy = 0.7 (7/10): "git" mid-word positions fail
      because "g"→"it status" ≠ "it"; "status" / "-la" positions pass.
    """
    corpus = {
        "":               "git status",
        "g":              "it status",
        "gi":             "t status",
        "git":            " status",
        "git ":           "status",
        "git s":          "tatus",
        "git st":         "atus",
        "git sta":        "tus",
        "git stat":       "us",
        "git statu":      "s",
        "git status":     "",
        "ls":             " -la",
        "ls ":            "-la",
        "ls -":           "la",
        "ls -l":          "a",
        "ls -la":         "",
        "make":           " re",
        "make ":          "re",
        "make r":         "e",
        "make re":        "",
    }
    return corpus.get(buf, "")


def _word_oracle(buf: str) -> str:
    """
    Word-boundary oracle: returns exactly the next WORD (not full suffix).
    Used for top-1 accuracy tests where prediction must equal the next token.
    """
    word_corpus = {
        "":       "git",
        "git ":   "status",
        "ls ":    "-la",
        "make ":  "re",
        # mid-word completions (same as _perfect_predictor)
        "g":      "it",
        "gi":     "t",
        "l":      "s",
        "git s":  "tatus",
        "git st": "atus",
        "git sta":"tus",
        "git stat":"us",
        "git statu":"s",
        "ls -":   "la",
        "ls -l":  "a",
        "make r": "e",
    }
    return word_corpus.get(buf, "")


def _silent_predictor(buf: str) -> str:
    """Always returns empty (worst-case model – no predictions)."""
    return ""


def _wrong_predictor(buf: str) -> str:
    """Always predicts the wrong thing."""
    return "XXXXX"


# ── Test 1: _simulate_ksr – perfect oracle ────────────────────────────────────

def test_simulate_ksr_perfect_oracle():
    """
    KSR for "git status" (L=10) with the full-suffix oracle.

    At i=0: predict("") = "git status", remaining = "git status" → accept
    immediately with 1 Tab keystroke.
    KSR = saved/L = 9/10 = 0.9.
    """
    ksr, keystrokes, saved = _simulate_ksr(_perfect_predictor, "git status")
    assert ksr == pytest.approx(0.9, abs=1e-6), \
        f"Expected KSR≈0.9 for perfect oracle, got {ksr}"
    assert keystrokes == 1, f"Full-suffix oracle accepts at i=0 with 1 Tab, got {keystrokes}"
    assert saved == 9,      f"Expected 9 saved chars, got {saved}"


def test_simulate_ksr_silent_model():
    """A silent model never helps: KSR must be exactly 0.0."""
    ksr, keystrokes, _ = _simulate_ksr(_silent_predictor, "git status")
    assert ksr == 0.0, f"Silent model KSR should be 0.0, got {ksr}"
    assert keystrokes == 10, f"Should type all 10 chars, got {keystrokes}"


def test_simulate_ksr_empty_command():
    """Empty command edge-case: KSR is 0.0, no keystrokes."""
    ksr, keystrokes, saved = _simulate_ksr(_perfect_predictor, "")
    assert ksr == 0.0
    assert keystrokes == 0
    assert saved == 0


# ── Test 2: keystroke_savings_ratio – aggregation ─────────────────────────────

def test_ksr_aggregate_perfect():
    """
    Length-weighted aggregate KSR for three commands.
    "git status"→KSR=0.9, "ls -la"→KSR=0.5, "make re"→KSR≈0.286
    Weighted mean ≈ 0.608 (14 saved / 23 total chars).
    """
    cmds = ["git status", "ls -la", "make re"]
    result = keystroke_savings_ratio(_perfect_predictor, cmds)
    assert result["mean_ksr"] > 0.5, \
        f"Aggregate KSR should be >0.5 (got {result['mean_ksr']:.4f})"
    assert result["total_chars"] == sum(len(c) for c in cmds)
    assert result["total_saved"] >= 0


def test_ksr_aggregate_silent():
    """Silent model → mean_ksr = 0.0."""
    result = keystroke_savings_ratio(_silent_predictor, ["git status", "make re"])
    assert result["mean_ksr"] == 0.0
    assert result["total_saved"] == 0


# ── Test 3: _word_boundaries ──────────────────────────────────────────────────

def test_word_boundaries_single():
    """Single-word command has exactly one boundary (empty buf → word)."""
    bds = list(_word_boundaries("git"))
    assert len(bds) == 1
    buf, word = bds[0]
    assert buf == "" and word == "git"


def test_word_boundaries_multi():
    """'git status' has 2 boundaries: '' → 'git' and 'git ' → 'status'."""
    bds = list(_word_boundaries("git status"))
    assert len(bds) == 2
    assert bds[0] == ("", "git")
    assert bds[1] == ("git ", "status")


def test_word_boundaries_invalid_shlex():
    """Unbalanced quotes should produce zero boundaries (no crash)."""
    bds = list(_word_boundaries("echo 'unbalanced"))
    assert bds == [], "Unbalanced quote command should yield no boundaries"


# ── Test 4: next_word_accuracy_top1 ──────────────────────────────────────────

def test_top1_accuracy_perfect():
    """
    Top-1 accuracy with the word-boundary oracle (returns exact next token).

    A stateless predictor can be "perfect" only when evaluated on a single
    fixed command (otherwise the empty-buffer boundary has a different
    correct first word per command).

    For "git status" (2 boundaries):
      ("", "git")    → _word_oracle("") = "git"    ✓
      ("git ","status") → _word_oracle("git ") = "status" ✓
    → acc = 2/2 = 1.0.
    """
    acc = next_word_accuracy_top1(_word_oracle, ["git status"])
    assert acc == pytest.approx(1.0), \
        f"Word oracle top-1 acc on single command should be 1.0, got {acc}"


def test_top1_accuracy_silent():
    """Silent model → top-1 accuracy == 0.0."""
    acc = next_word_accuracy_top1(_silent_predictor, ["git status", "make re"])
    assert acc == 0.0, f"Silent model top-1 acc should be 0.0, got {acc}"


def test_top1_accuracy_wrong():
    """Always-wrong predictor → top-1 accuracy == 0.0."""
    acc = next_word_accuracy_top1(_wrong_predictor, ["git status"])
    assert acc == 0.0


# ── Test 5: next_word_accuracy_topk ──────────────────────────────────────────

def test_topk_accuracy():
    """
    A top-k function that returns the correct word in position 3
    should give acc@3 = 1.0 and acc@1 = 0.0 (if position 1 is wrong).
    """
    def _topk_oracle(buf: str, k: int):
        # Return wrong words first, correct word last
        bds = list(_word_boundaries("git status"))
        for bd_buf, word in bds:
            if buf == bd_buf:
                return ["WRONG1", "WRONG2", word][:k]
        return []

    acc3 = next_word_accuracy_topk(_topk_oracle, ["git status"], k=3)
    assert acc3 == pytest.approx(1.0), \
        f"Top-3 oracle should give 1.0, got {acc3}"


# ── Test 6: prefix_completion_accuracy ────────────────────────────────────────

def test_prefix_completion_perfect():
    """
    Prefix-completion accuracy with the word oracle.

    Mid-word positions tested (word with ≥2 chars):
      "git": g→"it" ✓, gi→"t" ✓
      "status": s→"tatus" ✓, st→"atus" ✓, sta→"tus" ✓, stat→"us" ✓, statu→"s" ✓
      "-la": -→"la" ✓, -l→"a" ✓

    All mid-word positions return the exact remaining suffix → acc = 1.0.
    """
    cmds = ["git status", "ls -la"]
    acc = prefix_completion_accuracy(_word_oracle, cmds)
    assert acc == pytest.approx(1.0, abs=1e-6), \
        f"Word oracle prefix acc should be 1.0, got {acc}"


def test_prefix_completion_silent():
    """Silent model → prefix-completion accuracy = 0.0."""
    acc = prefix_completion_accuracy(_silent_predictor, ["git status"])
    assert acc == 0.0


def test_prefix_completion_single_char_words():
    """Single-character words have no mid-word prefix; should not crash."""
    acc = prefix_completion_accuracy(_perfect_predictor, ["a b c"])
    # All words are single chars; no mid-word positions → returns 0.0
    assert acc == 0.0


# ── Test 7: coverage_rate ────────────────────────────────────────────────────

def test_coverage_perfect():
    """Perfect oracle covers every position → coverage close to 1.0.
    (It returns "" for the last position of each command, so < 1.0.)
    """
    cov = coverage_rate(_perfect_predictor, ["git status"])
    assert cov > 0.8, f"Perfect oracle coverage should be >0.8, got {cov}"


def test_coverage_silent():
    """Silent model → coverage = 0.0."""
    cov = coverage_rate(_silent_predictor, ["git status", "ls -la"])
    assert cov == 0.0


# ── Test 8: compute_all_metrics – integration ────────────────────────────────

def test_compute_all_metrics_keys():
    """compute_all_metrics returns at least ksr, top1_acc, prefix_acc, coverage."""
    metrics = compute_all_metrics(_perfect_predictor, ["git status", "ls -la"])
    for key in ("ksr", "top1_acc", "prefix_acc", "coverage"):
        assert key in metrics, f"Missing key '{key}' in metrics dict"


def test_compute_all_metrics_with_topk():
    """When topk_fn is provided, top3_acc key is also returned."""
    def _topk(buf, k):
        return [_perfect_predictor(buf)] * k
    metrics = compute_all_metrics(
        _perfect_predictor, ["git status"], topk_fn=_topk
    )
    assert "top3_acc" in metrics, "top3_acc should be present when topk_fn given"


def test_compute_all_metrics_empty_commands():
    """Empty command list → all metrics = 0.0, no crash."""
    metrics = compute_all_metrics(_perfect_predictor, [])
    assert metrics["ksr"] == 0.0
    assert metrics["top1_acc"] == 0.0


# ── Test 9: data split ────────────────────────────────────────────────────────

def test_chronological_split_ratio():
    """80/20 split preserves order and correct sizes."""
    from python.eval.data import chronological_split
    entries = [(i, f"cmd{i}") for i in range(100)]
    train, test = chronological_split(entries, train_ratio=0.8)
    assert len(train) == 80
    assert len(test)  == 20
    # Order preserved
    assert train[-1][0] < test[0][0]


def test_chronological_split_fixture():
    """load_split on the bundled fixture completes without errors."""
    from python.eval.data import load_split, SAMPLE_HISTORY_PATH
    train, test, cmds = load_split(path=SAMPLE_HISTORY_PATH)
    assert len(train) > 0, "Train set should be non-empty"
    assert len(test)  > 0, "Test set should be non-empty"
    # Chronological: first train timestamp ≤ last train timestamp ≤ first test
    train_ts = [ts for ts, _ in train if ts is not None]
    test_ts  = [ts for ts, _ in test  if ts is not None]
    if train_ts and test_ts:
        assert max(train_ts) <= min(test_ts), "Train must precede test chronologically"


# ── Test 10: runner – model build smoke test ──────────────────────────────────

def test_runner_build_proposed():
    """build_model for the 'proposed' config produces a working predict_suffix."""
    from python.eval.ablation import get_configs
    from python.eval.runner   import build_model
    from python.eval.data     import load_split, SAMPLE_HISTORY_PATH

    cfg = next(c for c in get_configs() if c.get("proposed"))
    train_entries, _, test_commands = load_split(SAMPLE_HISTORY_PATH)
    model = build_model(cfg, train_entries)

    result = model.predict_suffix("git ")
    assert isinstance(result, str), "predict_suffix must return a string"
    # No newline should leak into prediction
    assert "\n" not in result, "Prediction must not contain newline"


def test_runner_build_mfreq_baseline():
    """Most-frequent command baseline builds and predicts without error."""
    from python.eval.runner import build_model
    from python.eval.data   import load_split, SAMPLE_HISTORY_PATH

    cfg = {"name": "mfreq", "k": 0, "backoff": False,
           "decay": 0.0, "model": "mfreq"}
    train_entries, _, _ = load_split(SAMPLE_HISTORY_PATH)
    model = build_model(cfg, train_entries)
    pred = model.predict_suffix("")
    assert isinstance(pred, str)
