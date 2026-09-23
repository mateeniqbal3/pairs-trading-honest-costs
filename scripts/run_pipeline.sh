#!/usr/bin/env bash
# Full research pipeline, run in order:
#   data -> cointegration testing across all candidates -> pair selection
#   -> signal construction -> gross backtest (recorded) -> costed backtest
#   -> gross-vs-net comparison output.
set -euo pipefail

cd "$(dirname "$0")/.."

# Phases 1-2: data, cointegration tests on the formation period, pair selection.
python scripts/select_pair.py "$@"

# Out-of-sample stability diagnostic for the selected pair (no trading).
python scripts/stability_check.py

# Phase 4: gross-of-costs backtest (frozen before costs, ADR-010).
python scripts/run_backtest_gross.py

# Phase 5: net of costs, charged on the frozen gross trade log (ADR-011).
python scripts/run_backtest_net.py
