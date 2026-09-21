"""Explicitly seeded deterministic sampling outside strategy-owned modules."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

_T = TypeVar("_T")


class DeterministicChooser:
    """Preserve Python's seeded sampling sequence behind an explicit boundary."""

    def __init__(self, seed: int) -> None:
        self._generator = random.Random(seed)

    def choice(self, values: Sequence[_T]) -> _T:
        return self._generator.choice(values)
