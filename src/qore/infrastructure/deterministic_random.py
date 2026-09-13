"""Explicit deterministic pseudo-randomness for reproducible research workloads."""

from __future__ import annotations

import random


class DeterministicRandom:
    """Seeded MT19937 adapter with the narrow interface required by QORE research."""

    def __init__(self, seed: int) -> None:
        self._generator = random.Random(seed)

    def randint(self, start: int, end: int) -> int:
        """Return a deterministic integer in the inclusive interval [start, end]."""
        return self._generator.randint(start, end)
