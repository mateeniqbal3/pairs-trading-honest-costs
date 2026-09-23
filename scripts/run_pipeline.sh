#!/usr/bin/env bash
# Full research pipeline, run in order:
#   data -> cointegration testing across all candidates -> pair selection
#   -> signal construction -> gross backtest (recorded) -> costed backtest
#   -> gross-vs-net comparison output.
set -euo pipefail

cd "$(dirname "$0")/.."

# Phases 1-2: data, cointegration tests on the formation period, pair selection.
python scripts/select_pair.py "$@"

echo "Pipeline incomplete: stopped after pair selection. Phases 3-5 (signal, backtest," \
     "costs) are not implemented yet (see TASKS.md)." >&2
exit 1
