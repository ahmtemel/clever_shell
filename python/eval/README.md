# clever_shell – Evaluation Harness

Automatic evaluation infrastructure for the `WordMarkovChain` prediction model.
Produces thesis-ready tables (CSV + LaTeX/booktabs) and figures (PNG) with a
single command.

## Quick Start

```bash
# From the project root (clever_shell/)
make eval                                  # auto-detects ~/.zsh_history
python3 -m python.eval.run_eval            # same
python3 -m python.eval.run_eval --history ~/.zsh_history   # explicit path
```

All output lands in `python/eval/results/`.

## Running the unit tests

```bash
pip install pytest numpy matplotlib       # one-time setup
pytest python/eval/ -v                    # run all tests
pytest python/eval/test_metrics.py -v    # metrics tests only
```

## Output files

| File | Description |
|------|-------------|
| `metrics_summary.csv` | All configs × all metrics, machine-readable |
| `metrics_summary.tex` | Booktabs LaTeX table (paste into thesis) |
| `ablation_table.csv`  | Same data, separate file for LaTeX label |
| `ablation_table.tex`  | Booktabs LaTeX ablation table |
| `fig_markov_order.png`| KSR & Top-1 accuracy vs context length k |
| `fig_ablation.png`    | Full config comparison bar chart |
| `fig_latency.png`     | Inference latency CDF per config |
| `fig_decay.png`       | Recency decay λ vs accuracy |
| `REPORT.md`           | Full textual summary (copy to thesis draft) |

## Directory structure

```
python/eval/
├── __init__.py
├── data.py            # history loading + 80/20 chronological split
├── metrics.py         # pure metric functions (KSR, Acc@1/3, prefix, coverage)
├── runner.py          # model factory + latency/memory measurement
├── ablation.py        # 8-config ablation matrix
├── report.py          # CSV, LaTeX, PNG, REPORT.md generation
├── run_eval.py        # entry point (argparse)
├── test_metrics.py    # pytest unit tests (≥10 tests)
├── sample_history.txt # synthetic fixture (always available)
└── results/           # generated output (.gitkeep committed)
```

## Ablation configurations

| Name | k | Backoff | Decay λ | Note |
|------|---|---------|---------|------|
| **proposed (k=3, λ=0.005)** | 3 | ✓ | 0.005 | **Recommended** |
| k=1 (unigram ctx)  | 1 | ✓ | 0.005 | Order ablation |
| k=2 (bigram ctx)   | 2 | ✓ | 0.005 | Order ablation |
| no backoff (k=3)   | 3 | ✗ | 0.005 | Backoff ablation |
| λ=0 (no decay)     | 3 | ✓ | 0.0   | Decay ablation |
| λ=0.02 (fast decay)| 3 | ✓ | 0.02  | Decay ablation |
| freq-only (unigram)| 3 | ✓ | 0.005 | Baseline |
| most-frequent cmd  | – | – | –     | Baseline |

## CLI options

```
usage: python -m python.eval.run_eval [-h] [--history PATH] [--out DIR]
                                       [--train-ratio F] [--latency-samples N]
                                       [--no-filter]

  --history PATH        zsh/bash history file (auto-detected if omitted)
  --out DIR             output directory   [default: python/eval/results]
  --train-ratio F       train fraction     [default: 0.8]
  --latency-samples N   predict_suffix calls for timing [default: 1000]
  --no-filter           skip is_valid_command + freq-floor on train set
```

## Metrics definitions

See `metrics.py` docstring for the mathematical definition of each metric.

- **KSR** – fraction of keystrokes saved with greedy Tab-acceptance.
- **Acc@1 / Acc@3** – top-1 / top-3 next-word accuracy at word boundaries.
- **Prefix accuracy** – exact-match accuracy for mid-word completions.
- **Coverage** – fraction of (command, position) pairs with a non-empty prediction.
- **p50/p95/p99** – inference latency percentiles (µs resolution).
