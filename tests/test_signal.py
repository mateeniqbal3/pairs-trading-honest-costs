"""Tests for src/signal.py.

Must include a look-ahead test (PROJECT.md section 7): compute the z-score
series twice, once unmodified and once with a single future price changed
to an extreme value, and assert that every z-score at or before the
modified timestamp is identical between the two runs.
"""

import pytest


@pytest.mark.skip(reason="src/signal.py not implemented yet")
def test_no_lookahead_in_zscore():
    raise NotImplementedError
