"""Pytest bootstrap: shared test helpers live under tests/ and tests/delivery/."""

import sys
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parent
_DELIVERY = _TESTS_ROOT / "delivery"

for _path in (_TESTS_ROOT, _DELIVERY):
    _entry = str(_path)
    if _entry not in sys.path:
        sys.path.insert(0, _entry)