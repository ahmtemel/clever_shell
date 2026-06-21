#!/usr/bin/env python3
"""
clever_shell – Phase 6: Markov Prediction Daemon
=================================================

Listens on ipc:///tmp/markov_shell.ipc (ZeroMQ PAIR, server/bind side).
Receives the current input buffer from the C shell and replies with the
predicted completion SUFFIX using a k=5 (5-gram) character-level Markov
chain trained on ~/.zsh_history.

Design constraints:
  • NO LLM / Transformer.  O(1) lookup via defaultdict / Counter.
  • CONTEXT_LEN=5 with automatic backoff to 4, 3, 2, 1, then silent.
  • Line-isolated training: no n-gram ever crosses a command boundary,
    so "git status" and "git config" can never be blended together.
  • Prediction hard-stops at the first predicted '\n' or string-end.
  • Preprocessing: strip zsh extended-history timestamps, deduplicate
    runaway repeated commands, collapse extra whitespace, preserve order.
  • CPU-friendly: zmq.Poller with POLL_TIMEOUT instead of busy-loop.
  • Always sends back a string (may be ""), never raises to the C client.

Usage:
    python3 python/markov_daemon.py [history_file]

    If history_file is omitted, defaults to ~/.zsh_history.
    Run this before (or alongside) the minishell binary.
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional

import zmq


# ── Configuration ─────────────────────────────────────────────────────────────

CONTEXT_LEN    = 5     # 5-gram context: wide enough to distinguish "git clone"
                       # from "git config" without blending them
MAX_PRED_LEN   = 50    # max suffix characters generated per request
MAX_CONSEC_DUP = 5     # runaway-repeat cap (e.g. thousands of "ls")
ZMQ_ADDR       = "ipc:///tmp/markov_shell.ipc"
POLL_TIMEOUT   = 100   # ms – zmq.Poller block; keeps CPU idle between keystrokes


# ── Markov model ──────────────────────────────────────────────────────────────

class MarkovChain:
    """
    Character-level k-gram Markov chain with backoff and line isolation.

    Key design choices:
      • table[context_str] = Counter({next_char: frequency})
      • All n-gram lengths 1 ≤ n ≤ k are stored so backoff always works.
      • Training is LINE-ISOLATED: no n-gram ever spans a '\n' boundary.
        This prevents "git status\ngit config" from teaching the model
        that "git status" leads to "git config".
      • Prediction hard-stops at the first '\n' (command boundary).
    """

    def __init__(self, k: int = CONTEXT_LEN) -> None:
        self.k = k
        self.table: Dict[str, Counter] = defaultdict(Counter)

    # ── Training ──────────────────────────────────────────────────────────

    def _train_line(self, line: str) -> None:
        """
        Train on a single command line.
        Records all n-gram prefixes (1 ≤ n ≤ k) ending at each position
        and the character that follows – strictly within this line only.
        """
        length = len(line)
        for i in range(length - 1):
            next_ch = line[i + 1]
            start   = max(0, i - self.k + 1)
            for j in range(start, i + 1):
                ctx = line[j: i + 1]
                self.table[ctx][next_ch] += 1

    def train(self, text: str) -> None:
        """
        Feed the training corpus into the model in LINE-ISOLATED mode.

        The corpus is split on '\n' and each command line is trained
        independently via _train_line().  This guarantees that no n-gram
        crosses a command boundary, eliminating inter-command contamination
        (e.g. "git status" never bleeds into "git config" predictions).
        """
        for line in text.split("\n"):
            line = line.strip()
            if line:
                self._train_line(line)

    # ── Prediction ────────────────────────────────────────────────────────

    def _next_char(self, context: str) -> Optional[str]:
        """
        Predict the single most-likely next character.
        Tries contexts of length k, k-1, …, 1 (backoff).
        Returns None when no data exists at any level → stay silent.
        """
        for n in range(self.k, 0, -1):
            ctx = context[-n:]
            if ctx and ctx in self.table:
                return self.table[ctx].most_common(1)[0][0]
        return None

    def predict_suffix(self, buf: str) -> str:
        """
        Generate the predicted completion SUFFIX for the current buffer.

        Hard stops (in priority order):
          1. '\n' predicted → command boundary reached, stop immediately.
          2. MAX_PRED_LEN characters generated → cap enforced.
          3. Model returns None → backoff exhausted, stay silent.
          4. Same context key seen twice → loop guard, stop.

        Because training is line-isolated, the model never learned to
        predict cross-command transitions, so condition 1 is triggered
        naturally at the end of a command pattern.
        """
        if not buf:
            return ""

        result:  List[str] = []
        current: str       = buf
        seen:    set[str]  = set()

        for _ in range(MAX_PRED_LEN):
            key = current[-(self.k + 1):]
            if key in seen:
                break
            seen.add(key)

            ch = self._next_char(current)
            # Hard boundary: '\n' = end of command → stop, never cross it
            if ch is None or ch == "\n":
                break

            result.append(ch)
            current = current + ch

        return "".join(result)


# ── Preprocessing ─────────────────────────────────────────────────────────────

# Zsh extended_history format: ": <timestamp>:<elapsed>;<command>"
# Example: ": 1700000000:0;git status"
_ZSH_EXT_RE  = re.compile(r"^: \d+:\d+;")

# Bash HISTTIMEFORMAT standalone timestamp lines: "#<unix-epoch>"
_BASH_TS_RE  = re.compile(r"^#\d+$")

# Collapse internal multi-space runs (normalises indented/copy-pasted cmds)
_MULTI_SP    = re.compile(r" {2,}")


def _extract_command(raw_line: str) -> str:
    """
    Extract the bare command from a raw history line, handling both:
      • Zsh extended format : ": 1700000000:0;git status"  → "git status"
      • Bash timestamp line : "#1700000000"               → "" (skipped)
      • Plain line          : "git status"                → "git status"
    """
    line = raw_line.strip()
    if not line:
        return ""
    # Bash standalone timestamp → discard
    if _BASH_TS_RE.match(line):
        return ""
    # Zsh extended history → strip ": ts:elapsed;" prefix
    m = _ZSH_EXT_RE.match(line)
    if m:
        line = line[m.end():].strip()
    # Collapse multiple spaces introduced by indentation or copy-paste
    return _MULTI_SP.sub(" ", line)


def load_history(path: str) -> str:
    """
    Load a zsh (or bash) history file, clean it, and return a training corpus.

    Cleaning steps (in order):
      1. Extract the bare command from each line:
           • Zsh extended: strip ": <ts>:<elapsed>;" prefix.
           • Bash HISTTIMEFORMAT: skip standalone "#<epoch>" lines.
           • Plain: use as-is.
      2. Strip leading/trailing whitespace; skip blank results.
      3. Collapse internal multi-space runs to a single space.
      4. Cap consecutive identical commands at MAX_CONSEC_DUP to
         prevent a "ls × 10 000" from dominating the model.
         Sequential ordering of distinct commands is fully preserved.
      5. Join surviving commands with '\n'; train() will split on '\n'
         and process each command in isolation (no cross-boundary n-grams).
    """
    if not os.path.isfile(path):
        print(f"[markov_daemon] warning: {path} not found – cold start",
              flush=True)
        return ""

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw_lines = fh.readlines()
    except OSError as exc:
        print(f"[markov_daemon] warning: cannot read {path}: {exc}", flush=True)
        return ""

    filtered:   List[str] = []
    prev_line:  str       = ""
    consec_cnt: int       = 0

    for raw in raw_lines:
        line = _extract_command(raw)
        if not line:
            continue

        if line == prev_line:
            consec_cnt += 1
            if consec_cnt >= MAX_CONSEC_DUP:
                continue                 # skip excess duplicates
        else:
            consec_cnt = 0
            prev_line  = line

        filtered.append(line)

    corpus = "\n".join(filtered)
    if corpus:
        corpus += "\n"
    return corpus


# ── ZMQ daemon loop ───────────────────────────────────────────────────────────

def run_daemon(chain: MarkovChain) -> None:
    """
    Bind the ZMQ PAIR socket and serve prediction requests.

    Protocol:
      C → Python : current input buffer (UTF-8 string, may be empty)
      Python → C : predicted suffix    (UTF-8 string, may be empty)

    Uses zmq.Poller with POLL_TIMEOUT ms so the process sleeps between
    keystrokes rather than spinning.  Both send and recv use NOBLOCK so
    the daemon never stalls if the C client is momentarily busy.
    """
    ctx  = zmq.Context()
    sock = ctx.socket(zmq.PAIR)
    sock.setsockopt(zmq.SNDHWM, 1)   # keep only the latest unsent prediction
    sock.setsockopt(zmq.RCVHWM, 1)   # keep only the latest unread request
    sock.bind(ZMQ_ADDR)

    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)

    print(f"[markov_daemon] listening on {ZMQ_ADDR}", flush=True)

    try:
        while True:
            events = dict(poller.poll(POLL_TIMEOUT))
            if sock not in events:
                continue
            try:
                buf = sock.recv_string(zmq.NOBLOCK)
            except zmq.Again:
                continue

            try:
                prediction = chain.predict_suffix(buf)
            except Exception:       # never let a model bug crash the daemon
                prediction = ""

            try:
                sock.send_string(prediction, zmq.NOBLOCK)
            except zmq.Again:
                pass                # C side busy – silently drop

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sock.close()
        ctx.term()
        print("[markov_daemon] stopped", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    history_path = (
        sys.argv[1] if len(sys.argv) > 1
        else os.path.expanduser("~/.zsh_history")
    )

    print(f"[markov_daemon] loading {history_path} …", flush=True)
    corpus     = load_history(history_path)
    line_count = corpus.count("\n") if corpus else 0
    print(f"[markov_daemon] {line_count} commands after preprocessing",
          flush=True)

    chain = MarkovChain(k=CONTEXT_LEN)
    t0    = time.monotonic()
    chain.train(corpus)
    elapsed = time.monotonic() - t0
    print(
        f"[markov_daemon] trained in {elapsed:.3f}s  "
        f"| {len(chain.table):,} unique n-gram contexts",
        flush=True,
    )

    run_daemon(chain)


if __name__ == "__main__":
    main()
