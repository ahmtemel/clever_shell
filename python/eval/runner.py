"""
runner.py – Build one ablation config, evaluate it, and return results.

Provides:
  • Model variants used in ablation (subclasses + baselines).
  • ``build_model(config, train_entries, now)``   – factory.
  • ``top_k_fn_for(chain, k)``                   – exposes top-k from table.
  • ``measure_latency(predict_fn, commands)``     – p50/p95/p99 / mean.
  • ``measure_memory(chain)``                     – context-table footprint.
  • ``evaluate_config(config, train, test_cmds)`` – full single-config eval.
"""

from __future__ import annotations

import heapq
import math
import shlex
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── project imports ───────────────────────────────────────────────────────────
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.markov_daemon import (
    PRED_TOPK,
    WordMarkovChain,
    apply_frequency_floor,
    is_valid_command,
)
from python.eval.metrics import compute_all_metrics

Entry = Tuple[Optional[int], str]


# ── Model variants ────────────────────────────────────────────────────────────

class _NoBackoffWordMarkovChain(WordMarkovChain):
    """
    WordMarkovChain with backoff disabled.

    ``_predict_next`` only queries the exact k-gram context; if absent it
    returns None immediately without falling to shorter contexts.  This
    gives higher precision when context matches but lower coverage overall.
    """
    def _predict_next(self, ctx_tokens: Tuple) -> Optional[str]:
        ctx = tuple(ctx_tokens[-self.k:]) if ctx_tokens else ()
        counter = self.table.get(ctx)
        if counter:
            top = heapq.nlargest(PRED_TOPK, counter.items(),
                                 key=lambda kv: kv[1])
            return top[0][0]
        return None


class _FrequencyOnlyBaseline(WordMarkovChain):
    """
    Frequency-only baseline (no sequential context).

    Always queries the empty-tuple key ``()`` which accumulates the
    unigram word distribution across all training lines.  Equivalent to
    a k=0 Markov model; predict the globally most-frequent next word.
    """
    def _predict_next(self, ctx_tokens: Tuple) -> Optional[str]:
        counter = self.table.get(())
        if counter:
            top = heapq.nlargest(PRED_TOPK, counter.items(),
                                 key=lambda kv: kv[1])
            return top[0][0]
        return None


class _MostFrequentCommandBaseline:
    """
    Simplest possible baseline: always predict the most frequent complete
    command from the training set regardless of current input.

    predict_suffix(buf) returns the suffix of the most frequent command
    that starts with buf.strip(), or the full command if buf is empty.
    """

    def __init__(self) -> None:
        self.cmd_counter: Counter = Counter()
        self.fallback_counter: Counter = Counter()  # alias for compat
        self.table: Dict = {}   # empty; for memory measure compat

    def train_entries(
        self,
        entries: List[Entry],
        now: Optional[float] = None,
    ) -> None:
        self.cmd_counter.clear()
        for _, cmd in entries:
            self.cmd_counter[cmd] += 1
        self.fallback_counter = self.cmd_counter

    def train(self, text: str) -> None:
        self.cmd_counter.clear()
        for line in text.split("\n"):
            line = line.strip()
            if line:
                self.cmd_counter[line] += 1
        self.fallback_counter = self.cmd_counter

    def predict_suffix(self, buf: str) -> str:
        strip = buf.strip()
        best_cmd, best_cnt = "", 0
        for cmd, cnt in self.cmd_counter.items():
            if not strip:
                # Predict the overall most common command
                if cnt > best_cnt:
                    best_cmd, best_cnt = cmd, cnt
            elif cmd.startswith(strip) and cmd != strip and cnt > best_cnt:
                best_cmd, best_cnt = cmd, cnt
        if best_cmd:
            if not strip:
                suffix = best_cmd
            else:
                suffix = best_cmd[len(strip):]
            return suffix[:60] if len(suffix) >= 1 else ""
        return ""


# ── Custom train function (supports arbitrary decay) ─────────────────────────

def _train_chain_with_decay(
    chain: WordMarkovChain,
    entries: List[Entry],
    decay: float,
    now: Optional[float] = None,
) -> None:
    """
    Train *chain* with an explicit *decay* value (ignores module constant).

    Mirrors ``WordMarkovChain.train_entries`` but injects the caller-
    supplied decay so ablation configs with different λ can share the
    same WordMarkovChain class.
    """
    chain.table.clear()
    chain.fallback_counter.clear()
    if now is None:
        now = time.time()
    for ts, cmd in entries:
        try:
            tokens = shlex.split(cmd, posix=False)
        except ValueError:
            continue
        if not tokens:
            continue
        weight = (
            1.0 if ts is None
            else math.exp(-decay * max(0.0, (now - ts) / 86400.0))
        )
        if weight > 0.0:
            chain._learn_line(tokens, weight)
        chain.fallback_counter[cmd] += 1


# ── Top-k helper ──────────────────────────────────────────────────────────────

def top_k_fn_for(chain: Any, k: int = 3):
    """
    Return a callable ``topk_fn(buf, k)`` that queries *chain*'s table
    directly to produce up to k candidate next-word strings.

    Used by ``next_word_accuracy_topk`` in metrics.py.
    """
    def _topk(buf: str, k: int = k) -> List[str]:
        try:
            tokens = shlex.split(buf, posix=False)
        except ValueError:
            return []
        if not buf.strip() or buf.endswith(" "):
            ctx_tokens = tuple(tokens[-min(chain.k, len(tokens)):]) if tokens else ()
        else:
            if not tokens:
                return []
            prefix     = tokens[-1]
            ctx_tokens = tuple(tokens[:-1])
            # Search for prefix-matching candidates via backoff
            start = min(chain.k, len(ctx_tokens))
            for n in range(start, -1, -1):
                ctx = ctx_tokens[-n:] if n > 0 else ()
                counter = chain.table.get(ctx)
                if counter:
                    cands = [(w, c) for w, c in counter.items()
                             if w.startswith(prefix) and w != prefix]
                    if cands:
                        return [w for w, _ in heapq.nlargest(k, cands, key=lambda x: x[1])]
            return []
        # Space-ending: backoff on ctx_tokens
        start = min(chain.k, len(ctx_tokens))
        for n in range(start, -1, -1):
            ctx = ctx_tokens[-n:] if n > 0 else ()
            counter = chain.table.get(ctx)
            if counter:
                return [w for w, _ in heapq.nlargest(k, counter.items(),
                                                      key=lambda x: x[1])]
        return []
    return _topk


# ── Model factory ─────────────────────────────────────────────────────────────

def build_model(
    config: Dict[str, Any],
    train_entries: List[Entry],
    now: Optional[float] = None,
) -> Any:
    """
    Build and train a model object from an ablation *config* dict.

    Config keys:
        name    (str)   – label for reports
        k       (int)   – context length (word n-gram order)
        backoff (bool)  – True = standard backoff, False = exact-context only
        decay   (float) – recency decay λ  (0.0 = uniform, 0.005/0.02 = decayed)
        model   (str)   – "word" | "freq" | "mfreq"
    """
    model_type = config.get("model", "word")
    k          = config.get("k", 3)
    backoff    = config.get("backoff", True)
    decay      = config.get("decay", 0.005)

    if model_type == "mfreq":
        m = _MostFrequentCommandBaseline()
        m.train_entries(train_entries, now=now)
        return m

    if model_type == "freq":
        m = _FrequencyOnlyBaseline(k=k)
    elif not backoff:
        m = _NoBackoffWordMarkovChain(k=k)
    else:
        m = WordMarkovChain(k=k)

    _train_chain_with_decay(m, train_entries, decay=decay, now=now)
    return m


# ── Latency measurement ───────────────────────────────────────────────────────

def measure_latency(
    predict_fn,
    commands: List[str],
    n_samples: int = 1000,
    seed: int = 42,
) -> Dict[str, float]:
    """
    Measure the latency distribution of *predict_fn* over a sample of
    (command, position) pairs drawn from *commands*.

    Args:
        predict_fn: callable str → str
        commands:   pool of commands to sample prefixes from
        n_samples:  total number of predict_fn calls to time
        seed:       RNG seed for reproducibility

    Returns dict with keys: mean_ms, p50_ms, p95_ms, p99_ms, n.
    """
    import random
    rng = random.Random(seed)

    # Build a flat list of buffer prefixes to probe
    prefixes: List[str] = []
    for cmd in commands:
        for i in range(len(cmd) + 1):
            prefixes.append(cmd[:i])

    if not prefixes:
        return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "n": 0}

    # Sample with replacement to reach n_samples
    sample = [rng.choice(prefixes) for _ in range(n_samples)]

    # Warm up (first few calls can be slower due to Python internals)
    for buf in sample[:10]:
        predict_fn(buf)

    # Timed run
    times_ms: List[float] = []
    for buf in sample:
        t0 = time.perf_counter()
        predict_fn(buf)
        times_ms.append((time.perf_counter() - t0) * 1000.0)

    arr = np.array(times_ms)
    return {
        "mean_ms": float(np.mean(arr)),
        "p50_ms":  float(np.percentile(arr, 50)),
        "p95_ms":  float(np.percentile(arr, 95)),
        "p99_ms":  float(np.percentile(arr, 99)),
        "n":       len(arr),
    }


# ── Memory measurement ────────────────────────────────────────────────────────

def measure_memory(model: Any) -> Dict[str, Any]:
    """
    Estimate the memory footprint of the model's transition table.

    Uses sys.getsizeof for shallow sizes; also reports the number of
    unique n-gram contexts and total (context, next_word) pairs.

    Returns dict with keys: n_contexts, n_pairs, table_shallow_kb.
    """
    table = getattr(model, "table", {})
    n_contexts = len(table)
    n_pairs    = sum(len(c) for c in table.values())

    # Shallow size of the outer defaultdict + all keys + all Counter objects
    shallow = sys.getsizeof(table)
    for ctx, counter in table.items():
        shallow += sys.getsizeof(ctx)
        shallow += sys.getsizeof(counter)

    return {
        "n_contexts":      n_contexts,
        "n_pairs":         n_pairs,
        "table_shallow_kb": round(shallow / 1024, 1),
    }


# ── Full single-config evaluation ─────────────────────────────────────────────

def evaluate_config(
    config: Dict[str, Any],
    train_entries: List[Entry],
    test_commands: List[str],
    now: Optional[float] = None,
    n_latency_samples: int = 1000,
) -> Dict[str, Any]:
    """
    Run the complete evaluation pipeline for one ablation config.

    Steps:
      1. Build + train the model.
      2. Compute all accuracy metrics on test_commands.
      3. Measure latency distribution over test_commands.
      4. Measure memory footprint.

    Returns a flat dict suitable for CSV / LaTeX export.
    """
    model = build_model(config, train_entries, now=now)
    predict_fn = model.predict_suffix

    # Build top-k function (only for models that have a .table attribute)
    topk_fn = top_k_fn_for(model) if hasattr(model, "table") and model.table else None

    metrics = compute_all_metrics(predict_fn, test_commands, topk_fn=topk_fn)
    latency = measure_latency(predict_fn, test_commands,
                              n_samples=n_latency_samples)
    memory  = measure_memory(model)

    return {
        "name":       config.get("name", "?"),
        "k":          config.get("k", "-"),
        "backoff":    config.get("backoff", True),
        "decay":      config.get("decay", 0.0),
        "model_type": config.get("model", "word"),
        **{f"metric_{k}": v for k, v in metrics.items()},
        **{f"lat_{k}": v  for k, v in latency.items()},
        **{f"mem_{k}": v  for k, v in memory.items()},
    }
