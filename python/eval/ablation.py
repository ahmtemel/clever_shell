"""
ablation.py – Ablation study configuration matrix.

Defines the full set of configurations to compare in the evaluation.
Each config is a plain dict consumed by ``runner.build_model``.

Study axes
----------
1. Markov order  k ∈ {1, 2, 3}         — context window size
2. Backoff       on / off               — graceful degradation strategy
3. Recency decay λ ∈ {0.0, 0.005, 0.02} — how fast old habits fade
4. Baselines     freq-only, most-freq   — lower bounds to beat

The "proposed" config (marked with proposed=True) corresponds to the
full system as deployed: k=3, backoff=True, λ=0.005.
"""

from __future__ import annotations

from typing import Dict, List, Any


def get_configs() -> List[Dict[str, Any]]:
    """
    Return the ordered list of ablation configurations.

    Each dict has keys:
        name     (str)   – short identifier used in tables and plot labels
        k        (int)   – word n-gram order
        backoff  (bool)  – whether context backoff is enabled
        decay    (float) – recency decay λ (0 = uniform weights)
        model    (str)   – "word" | "freq" | "mfreq"
        proposed (bool)  – True for the recommended system configuration
        group    (str)   – axis label for grouping in plots
    """
    return [
        # ── Proposed system ──────────────────────────────────────────────────
        {
            "name": "proposed (k=3, λ=0.005)",
            "k": 3, "backoff": True, "decay": 0.005,
            "model": "word", "proposed": True, "group": "proposed",
        },

        # ── Markov order ablation ─────────────────────────────────────────────
        {
            "name": "k=1 (unigram ctx)",
            "k": 1, "backoff": True, "decay": 0.005,
            "model": "word", "proposed": False, "group": "markov_order",
        },
        {
            "name": "k=2 (bigram ctx)",
            "k": 2, "backoff": True, "decay": 0.005,
            "model": "word", "proposed": False, "group": "markov_order",
        },

        # ── Backoff ablation ──────────────────────────────────────────────────
        {
            "name": "no backoff (k=3)",
            "k": 3, "backoff": False, "decay": 0.005,
            "model": "word", "proposed": False, "group": "backoff",
        },

        # ── Recency decay ablation ────────────────────────────────────────────
        {
            "name": "λ=0 (no decay)",
            "k": 3, "backoff": True, "decay": 0.0,
            "model": "word", "proposed": False, "group": "decay",
        },
        {
            "name": "λ=0.02 (fast decay)",
            "k": 3, "backoff": True, "decay": 0.02,
            "model": "word", "proposed": False, "group": "decay",
        },

        # ── Baselines ─────────────────────────────────────────────────────────
        {
            "name": "freq-only (unigram)",
            "k": 3, "backoff": True, "decay": 0.005,
            "model": "freq", "proposed": False, "group": "baseline",
        },
        {
            "name": "most-frequent cmd",
            "k": 0, "backoff": False, "decay": 0.0,
            "model": "mfreq", "proposed": False, "group": "baseline",
        },
    ]


# Convenience sets for targeted plot filtering
MARKOV_ORDER_CONFIGS = [c for c in get_configs()
                        if c["group"] in ("markov_order", "proposed")]
DECAY_CONFIGS        = [c for c in get_configs()
                        if c["group"] in ("decay", "proposed")]
BASELINE_CONFIGS     = [c for c in get_configs()
                        if c["group"] in ("baseline", "proposed")]
