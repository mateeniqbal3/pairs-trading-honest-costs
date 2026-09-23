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

echo "Pipeline incomplete: stopped after the stability check. Phases 4-5 (backtest," \
     "costs) are not implemented yet (see TASKS.md)." >&2
exit 1
