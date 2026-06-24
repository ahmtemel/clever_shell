#!/usr/bin/env python3
"""
clever_shell – Phase 6: Markov Prediction Daemon
=================================================

Listens on ipc:///tmp/markov_shell.ipc (ZeroMQ PAIR, server/bind side).
Receives the current input buffer from the C shell and replies with the
predicted completion SUFFIX using a word-level k=3 (trigram) Markov chain
trained on ~/.zsh_history.

Filtering Pipeline (ALL at TRAINING-TIME – inference stays < 5 ms)
-------------------------------------------------------------------
  Layer 1 · Syntactic whitelist + validation  (is_valid_command)
            - shlex.split must succeed (balanced quotes),
            - line must not match the noise regex (URL, exit:?, ANSI, '$'),
            - first token must be in WHITELIST.
  Layer 2 · Recency weighting                 (WordMarkovChain.train_entries)
            - weight = exp(-RECENCY_DECAY · Δdays) ≈ 1.0 for new commands,
              fading for old ones.  Half-life ≈ 139 days (λ=0.005).
  Layer 3 · Min-count frequency floor         (apply_frequency_floor)
            - command lines appearing fewer than MIN_CMD_FREQ times are dropped.

Model design:
  • Word-level trigram (k=3 tokens); table key = Tuple[str,...].
  • All context lengths 0 ≤ n ≤ k stored → backoff always finds a level.
  • LINE-ISOLATED training: no n-gram ever crosses a command boundary.
  • predict_suffix() handles two modes:
      space-or-empty  → predict the next full word,
      mid-word        → complete the current partial token (prefix mode).
  • Fallback: prefix-match against trained command strings by frequency.
  • ZeroMQ PAIR socket protocol is unchanged (C client untouched).

Usage:
    python3 python/markov_daemon.py [history_file]

    If history_file is omitted, defaults to ~/.zsh_history.
    Run this before (or alongside) the minishell binary.
"""

from __future__ import annotations

import heapq
import math
import os
import re
import shlex
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

import zmq


# ── Configuration ─────────────────────────────────────────────────────────────

CONTEXT_LEN   = 3      # word-level trigram (k=3 tokens)
MAX_PRED_LEN  = 60     # hard cap on returned suffix characters
PRED_TOPK     = 5      # heapq.nlargest candidates pulled per lookup
RECENCY_DECAY = 0.005  # λ in w=exp(-λ·Δdays); half-life ≈ 139 days
MIN_CMD_FREQ  = 1      # Layer-3 floor: single-occurrence commands are kept
ZMQ_ADDR      = "ipc:///tmp/markov_shell.ipc"
POLL_TIMEOUT  = 100    # ms – zmq.Poller block; keeps CPU idle between keystrokes


# ── Layer 1: syntactic whitelist ───────────────────────────────────────────────
# Only lines whose first token is one of these are trained.
# "./" marks local-script invocations (checked separately via startswith).
WHITELIST: frozenset[str] = frozenset({
    "git", "ls", "cd", "python", "python3", "make", "gcc",
    "cat", "ssh", "brew", "touch", "clear",
    "vim", "nvim", "nano",
    "grep", "find", "sed", "awk",
    "curl", "wget",
    "tar", "zip", "unzip",
    "docker", "npm", "node",
    "cargo", "rustc", "go", "ruby",
    "pip", "pip3",
    "chmod", "chown",
    "mv", "cp", "rm", "mkdir", "rmdir",
    "echo", "printf", "source", "export", "alias",
    "./",
})


# ── ZSH history parsing ────────────────────────────────────────────────────────

# Zsh extended_history: ": <epoch>:<elapsed>;<command>"
_ZSH_LINE_RE = re.compile(r"^: (\d+):\d+;(.+)$")
_MULTI_SP    = re.compile(r" {2,}")


def parse_zsh_history(path: str) -> List[Tuple[Optional[int], str]]:
    """
    Parse a zsh history file into [(timestamp, command), ...].

    • Extended-history lines yield an int timestamp and the bare command.
    • Plain lines (no timestamp) yield None and the line as-is.
    • Standalone "#<epoch>" and blank lines are skipped.

    Timestamps are preserved so Layer-2 recency weighting can use them.
    """
    entries: List[Tuple[Optional[int], str]] = []
    if not os.path.isfile(path):
        print(f"[markov_daemon] warning: {path} not found – cold start",
              flush=True)
        return entries

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw_lines = fh.readlines()
    except OSError as exc:
        print(f"[markov_daemon] warning: cannot read {path}: {exc}", flush=True)
        return entries

    for raw in raw_lines:
        raw = raw.rstrip("\n")
        m = _ZSH_LINE_RE.match(raw)
        if m:
            ts:  Optional[int] = int(m.group(1))
            cmd: str           = m.group(2).strip()
        else:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ts, cmd = None, line

        cmd = _MULTI_SP.sub(" ", cmd)
        if cmd:
            entries.append((ts, cmd))

    return entries


# ── Layer 1: command validation ────────────────────────────────────────────────

_NOISE_RE = re.compile(
    r"""(
        https?://              |   # http / https URLs
        ftp://                 |   # ftp URLs
        www\.                  |   # bare www. hosts
        \x1b\[[0-9;]*[A-Za-z]  |   # ANSI escape sequences
        \bexit\b:?             |   # exit  /  exit:
        \$                         # variable interpolation / subshell
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def is_valid_command(cmd: str) -> bool:
    """
    Layer-1 gate. Return True only if cmd is a clean, learnable command.

    Rejection criteria (training-time only; inference never calls this):
      1. Matches the noise regex (URL, exit/exit:, ANSI codes, '$').
      2. shlex cannot tokenise it (unbalanced quotes → broken paste).
      3. First token is not in WHITELIST (unknown binary / env-var assignment).
         Exception: tokens starting with "./" are always allowed.
    """
    if not cmd:
        return False

    if _NOISE_RE.search(cmd):
        return False

    try:
        tokens = shlex.split(cmd, posix=False)
    except ValueError:
        return False
    if not tokens:
        return False

    first = tokens[0]
    if first.startswith("./"):
        return True
    return os.path.basename(first) in WHITELIST


# ── Layer 3: min-count frequency floor ────────────────────────────────────────

def apply_frequency_floor(
    entries: List[Tuple[Optional[int], str]],
    min_freq: int = MIN_CMD_FREQ,
) -> List[Tuple[Optional[int], str]]:
    """
    Drop command lines whose total occurrence count is below min_freq.

    A Counter over full command strings gives O(1) lookups.  With
    MIN_CMD_FREQ=1 all entries pass; raising it filters one-off outliers.
    """
    counts = Counter(cmd for _, cmd in entries)
    return [(ts, cmd) for ts, cmd in entries if counts[cmd] >= min_freq]


# ── Word-level Markov model ────────────────────────────────────────────────────

class WordMarkovChain:
    """
    Word-level k-gram Markov chain with backoff, line isolation, and fallback.

    Design:
      • table[Tuple[str,...]] = Counter({next_word: weight})
        Key = last k word tokens as a tuple; value = weighted next-word counts.
      • All context lengths 0 ≤ n ≤ k are stored so backoff always works.
        The empty-tuple key () accumulates all words (universal fallback level).
      • Training is LINE-ISOLATED: no n-gram ever spans a command boundary.
      • Recency weighting: weight = exp(-RECENCY_DECAY * delta_days).
      • Fallback: prefix-match against trained command strings by raw frequency.
      • Inference: dict lookup + heapq.nlargest → well under 1 ms per call.
    """

    def __init__(self, k: int = CONTEXT_LEN) -> None:
        self.k = k
        self.table: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)
        # Stores raw occurrence counts of each full command string for fallback.
        self.fallback_counter: Counter = Counter()

    # ── Training ──────────────────────────────────────────────────────────

    def _learn_line(self, tokens: List[str], weight: float = 1.0) -> None:
        """
        Record all word n-gram transitions within a single tokenized line.

        For word at index i, records every context of length 0..min(k,i)
        immediately preceding it, adding weight to each counter entry.
        The empty-tuple context () captures the universal distribution.
        Strictly line-isolated: no context ever crosses a command boundary.
        """
        for i, next_word in enumerate(tokens):
            max_ctx = min(self.k, i)
            for ctx_len in range(max_ctx + 1):
                ctx = tuple(tokens[i - ctx_len: i]) if ctx_len > 0 else ()
                self.table[ctx][next_word] += weight

    def train_entries(
        self,
        entries: List[Tuple[Optional[int], str]],
        now: Optional[float] = None,
    ) -> None:
        """
        Layer-2 recency-weighted training (resets the matrix first).

        Each entry's weight = exp(-RECENCY_DECAY * Δdays) where
        Δdays = max(0, (now - timestamp) / 86400).  Entries without a
        timestamp default to weight 1.0.  The fallback_counter is
        populated with raw integer counts (unweighted) for prefix matching.
        """
        self.table.clear()
        self.fallback_counter.clear()
        if now is None:
            now = time.time()

        for ts, cmd in entries:
            try:
                tokens = shlex.split(cmd, posix=False)
            except ValueError:
                continue
            if not tokens:
                continue

            if ts is None:
                weight = 1.0
            else:
                delta_days = max(0.0, (now - ts) / 86400.0)
                weight = math.exp(-RECENCY_DECAY * delta_days)

            if weight > 0.0:
                self._learn_line(tokens, weight)
            self.fallback_counter[cmd] += 1

    def train(self, text: str) -> None:
        """
        Uniform-weight training from a '\n'-joined corpus string.
        Used for tests and cold corpora that carry no timestamps.
        Resets the matrix before training.
        """
        self.table.clear()
        self.fallback_counter.clear()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                tokens = shlex.split(line, posix=False)
            except ValueError:
                continue
            if tokens:
                self._learn_line(tokens, 1.0)
                self.fallback_counter[line] += 1

    # ── Prediction (hot path – keep it cheap) ─────────────────────────────

    def _predict_next(self, ctx_tokens: Tuple[str, ...]) -> Optional[str]:
        """
        Return the highest-weight next word for the given context.
        Backs off from len(ctx_tokens) down to 0 (empty = universal dist.).
        O(PRED_TOPK) via heapq.nlargest on a small Counter.
        """
        start = min(self.k, len(ctx_tokens))
        for n in range(start, -1, -1):
            ctx     = ctx_tokens[-n:] if n > 0 else ()
            counter = self.table.get(ctx)
            if counter:
                top = heapq.nlargest(PRED_TOPK, counter.items(),
                                     key=lambda kv: kv[1])
                return top[0][0]
        return None

    def _fallback(self, buf: str) -> str:
        """
        Prefix-match buf.strip() against all trained commands by frequency.
        Returns the remaining suffix of the best matching command, or "".
        """
        strip = buf.strip()
        if not strip:
            return ""
        best_cmd: Optional[str] = None
        best_cnt: int           = 0
        for cmd, cnt in self.fallback_counter.items():
            if cmd.startswith(strip) and cmd != strip and cnt > best_cnt:
                best_cmd = cmd
                best_cnt = cnt
        if best_cmd:
            suffix = best_cmd[len(strip):]
            if len(suffix) >= 1:
                return suffix[:MAX_PRED_LEN]
        return ""

    def predict_suffix(self, buf: str) -> str:
        """
        Generate the predicted completion SUFFIX for the current buffer.

        a. Tokenize buf with shlex.split(posix=False); return "" on ValueError.

        b. buf ends with a space OR is blank (new-word boundary):
             Context = last min(k, len(tokens)) tokens as a tuple.
             Call _predict_next() with backoff; return the predicted word.

        c. buf does NOT end with a space (mid-word):
             prefix     = tokens[-1]  (the partial word being typed)
             ctx_tokens = tokens[:-1]
             Back off from min(k, len(ctx)) down to 0, filtering candidates
             with candidate.startswith(prefix).  Return candidate[len(prefix):]
             (only the missing suffix, not the part already typed).

        d. Hard cap: returned string is at most MAX_PRED_LEN characters.
        e. Never returns a string shorter than 1 character (returns "" instead).

        Falls back to _fallback() when the model is silent at every level.
        """
        MIN_LEN = 1

        # a. Tokenize
        try:
            tokens: List[str] = shlex.split(buf, posix=False)
        except ValueError:
            return ""

        # b. New-word boundary (buf empty or ends with space)
        if not buf.strip() or buf.endswith(" "):
            ctx  = tuple(tokens[-min(self.k, len(tokens)):]) if tokens else ()
            word = self._predict_next(ctx)
            if word and len(word) >= MIN_LEN:
                return word[:MAX_PRED_LEN]
            return self._fallback(buf)

        # c. Mid-word: complete the partial token
        if not tokens:
            return self._fallback(buf)

        prefix     = tokens[-1]
        ctx_tokens = tuple(tokens[:-1])
        start      = min(self.k, len(ctx_tokens))

        for n in range(start, -1, -1):
            ctx     = ctx_tokens[-n:] if n > 0 else ()
            counter = self.table.get(ctx)
            if not counter:
                continue
            candidates = [
                (w, c) for w, c in counter.items()
                if w.startswith(prefix) and w != prefix
            ]
            if candidates:
                best_word = max(candidates, key=lambda x: x[1])[0]
                suffix    = best_word[len(prefix):]
                if len(suffix) >= MIN_LEN:
                    return suffix[:MAX_PRED_LEN]

        return self._fallback(buf)


# ── Training pipeline orchestrator ────────────────────────────────────────────

def build_chain(
    path: str,
    k: int = CONTEXT_LEN,
    now: Optional[float] = None,
) -> Tuple[WordMarkovChain, Dict[str, int]]:
    """
    Run the full 3-layer training pipeline and return (chain, stats).

    Pipeline:
        parse_zsh_history  →  is_valid_command (Layer 1)
                           →  apply_frequency_floor (Layer 3)
                           →  WordMarkovChain.train_entries (Layer 2 weighting)

    stats keys: parsed, validated, floored, contexts.
    """
    entries = parse_zsh_history(path)
    valid   = [(ts, cmd) for ts, cmd in entries if is_valid_command(cmd)]
    floored = apply_frequency_floor(valid)

    chain = WordMarkovChain(k=k)
    chain.train_entries(floored, now=now)

    stats = {
        "parsed":    len(entries),
        "validated": len(valid),
        "floored":   len(floored),
        "contexts":  len(chain.table),
    }
    return chain, stats


# ── ZMQ daemon loop ───────────────────────────────────────────────────────────

def run_daemon(chain: WordMarkovChain) -> None:
    """
    Bind the ZMQ PAIR socket and serve prediction requests.

    Protocol (unchanged – C client untouched):
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
    t0 = time.monotonic()
    chain, stats = build_chain(history_path, k=CONTEXT_LEN)
    elapsed = time.monotonic() - t0

    print(
        f"[markov_daemon] pipeline: parsed={stats['parsed']} "
        f"→ valid={stats['validated']} → floored={stats['floored']}",
        flush=True,
    )
    print(
        f"[markov_daemon] trained in {elapsed:.3f}s "
        f"| {stats['contexts']:,} unique n-gram contexts",
        flush=True,
    )

    run_daemon(chain)


if __name__ == "__main__":
    main()
