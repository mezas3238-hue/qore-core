"""Deterministic engineering Golden Traces for QORE Shared Lab data reality."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldenTrace:
    trace_id: str
    version: str
    origin: str
    source_type: str
    instrument: str
    canonical_identity: str
    asset_class: str
    provider: str
    timeframe_or_tick_mode: str
    observed_at: str
    available_at: str
    market_session_context: str
    raw_input_fingerprint: str
    expected_invariants: tuple[str, ...]
    perturbations_allowed: tuple[str, ...]
    provenance: tuple[tuple[str, str], ...]
    expected_failure_classifications: tuple[str, ...]
    deterministic_replay_identity: str

    def __post_init__(self) -> None:
        required = (
            self.trace_id, self.version, self.origin, self.source_type, self.instrument,
            self.canonical_identity, self.asset_class, self.provider, self.timeframe_or_tick_mode,
            self.observed_at, self.available_at, self.raw_input_fingerprint,
            self.deterministic_replay_identity,
        )
        if any(not item.strip() for item in required):
            raise ValueError("golden trace identity fields cannot be empty")
        if not self.expected_invariants:
            raise ValueError("golden trace must declare expected invariants")
        if len(self.raw_input_fingerprint) != 64:
            raise ValueError("raw_input_fingerprint must be sha256 hex")

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class GoldenTraceLibrary:
    def __init__(self) -> None:
        self._traces: dict[str, GoldenTrace] = {}

    def register(self, trace: GoldenTrace) -> None:
        if trace.trace_id in self._traces:
            raise ValueError(f"duplicate golden trace: {trace.trace_id}")
        self._traces[trace.trace_id] = trace

    def get(self, trace_id: str) -> GoldenTrace:
        return self._traces[trace_id]

    def replay_identity(self, trace_id: str) -> str:
        return self.get(trace_id).deterministic_replay_identity

    def list(self) -> tuple[GoldenTrace, ...]:
        return tuple(self._traces[key] for key in sorted(self._traces))


def fingerprint_raw_input(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def deterministic_replay_identity(parts: dict[str, Any]) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()
