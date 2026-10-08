#!/usr/bin/env python3
"""Forensic-only Sovereign earliest breach probe; no policy changes.

Linux-fork wrapper around the *existing* exact Trader Lab batch runner.
The _State.mark event is merely observed, never altered.
"""
from __future__ import annotations

import json
from decimal import Decimal
from qore.infrastructure.trader_lab import cibo_three_mode_capital_lab as lab
import cibo_trader_lab_batch_runner as batch

_original_mark = lab._State.mark
_mark_counter = 0
_found = set()


def _snapshot(state, event):
    cushion_available = max(
        Decimal(0), state.portfolio_cushion_usd - state.cushion_reserved_usd
    )
    sovereign_floor = state.sovereign_protection_floor_usd
    return {
        "event": event,
        "mark_index": _mark_counter,
        "capital": str(state.total_capital_usd),
        "peak_capital": str(state.peak_total_capital_usd),
        "sovereign_bank": str(state.sovereign_bank_usd),
        "sovereign_floor": str(sovereign_floor),
        "required_to_restore_floor": str(max(Decimal(0), sovereign_floor - state.sovereign_bank_usd)),
        "portfolio_cushion": str(state.portfolio_cushion_usd),
        "cushion_reserved": str(state.cushion_reserved_usd),
        "cushion_available": str(cushion_available),
        "portfolio_attack_credit": str(state.portfolio_attack_credit_usd),
        "sovereign_reserved": str(state.sovereign_reserved_usd),
        "bank_seed_reserved": str(state.bank_seed_reserved_usd),
        "open_stop_risk": str(state.open_stop_risk_usd),
        "open_margin": str(state.open_margin_usd),
    }


def _mark_with_probe(state):
    global _mark_counter
    _mark_counter += 1
    floor = state.sovereign_protection_floor_usd
    is_floor_breach = state.sovereign_bank_usd < floor
    is_bank_negative = state.sovereign_bank_usd < 0
    if is_floor_breach and "first_floor_breach" not in _found:
        _found.add("first_floor_breach")
        print("CIBO_FIRST_SOVEREIGN_FLOOR_BREACH_STATE="+json.dumps(
            _snapshot(state,"first_floor_breach"),sort_keys=True),flush=True)
    if is_bank_negative and "first_negative_sovereign_bank" not in _found:
        _found.add("first_negative_sovereign_bank")
        print("CIBO_FIRST_NEGATIVE_SOVEREIGN_STATE="+json.dumps(
            _snapshot(state,"first_negative_sovereign_bank"),sort_keys=True),flush=True)
    _original_mark(state)


lab._State.mark = _mark_with_probe

if __name__ == "__main__":
    raise SystemExit(batch.main())
