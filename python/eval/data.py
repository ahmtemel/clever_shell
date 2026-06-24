"""
data.py – History loading and chronological train/test split.

Wraps parse_zsh_history from markov_daemon and adds:
  • Automatic history-file discovery  (zsh → bash → synthetic fixture)
  • Chronological 80/20 split so evaluation reflects "predict the future
    from the past" – no data leakage from future into the training window.
  • Optional is_valid_command + apply_frequency_floor filtering on the
    TRAIN set only (test set stays unfiltered for realistic coverage stats).
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

# ── ensure project root is importable ─────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from python.markov_daemon import (
    apply_frequency_floor,
    is_valid_command,
    parse_zsh_history,
)

# Synthetic fixture bundled with the repository so evaluation always runs.
SAMPLE_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "sample_history.txt")

Entry = Tuple[Optional[int], str]


# ── public API ─────────────────────────────────────────────────────────────────

def load_entries(path: Optional[str] = None) -> List[Entry]:
    """
    Load raw history entries from *path*.

    Discovery order when *path* is None:
      1. ~/.zsh_history
      2. ~/.bash_history
      3. python/eval/sample_history.txt  (bundled synthetic fixture)

    Returns a list of (timestamp_or_None, command_string) tuples in
    chronological order (as stored in the file, oldest first).
    """
    if path is None:
        for candidate in (
            os.path.expanduser("~/.zsh_history"),
            os.path.expanduser("~/.bash_history"),
        ):
            if os.path.isfile(candidate):
                path = candidate
                break
        else:
            path = SAMPLE_HISTORY_PATH
            print(f"[data] no history file found – using fixture: {path}", flush=True)

    return parse_zsh_history(path)


def chronological_split(
    entries: List[Entry],
    train_ratio: float = 0.8,
) -> Tuple[List[Entry], List[Entry]]:
    """
    Split *entries* chronologically into (train, test).

    The first ``train_ratio`` fraction forms the training window; the
    remaining entries form the test window.  Because history files are
    stored oldest-first, this guarantees no future leakage into training.

    Args:
        entries:     List of (timestamp, command) tuples.
        train_ratio: Fraction of entries to use for training (0 < r < 1).

    Returns:
        (train_entries, test_entries)
    """
    if not 0 < train_ratio < 1:
        raise ValueError(f"train_ratio must be in (0, 1), got {train_ratio}")
    split = max(1, int(len(entries) * train_ratio))
    return entries[:split], entries[split:]


def load_split(
    path: Optional[str] = None,
    train_ratio: float = 0.8,
    filter_train: bool = True,
    min_cmd_freq: int = 1,
) -> Tuple[List[Entry], List[Entry], List[str]]:
    """
    Convenience wrapper: load → split → optionally filter train set.

    Returns:
        train_entries  – filtered entries for model training
        test_entries   – unfiltered entries (for realistic eval)
        test_commands  – bare command strings extracted from test_entries
    """
    all_entries = load_entries(path)
    train_raw, test_entries = chronological_split(all_entries, train_ratio)

    if filter_train:
        train_valid  = [(ts, cmd) for ts, cmd in train_raw if is_valid_command(cmd)]
        train_entries = apply_frequency_floor(train_valid, min_freq=min_cmd_freq)
    else:
        train_entries = train_raw

    # Extract bare command strings from the test set (valid commands only)
    test_commands = [
        cmd for _, cmd in test_entries
        if cmd.strip() and is_valid_command(cmd)
    ]

    return train_entries, test_entries, test_commands
