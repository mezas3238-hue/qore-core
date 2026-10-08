#!/usr/bin/env python3
"""Research-only causal cross-ledger Sovereign restoration experiment.

NEVER activated by default QORE; monkeypatch lives in isolated batch wrapper.
Portfolio transfers are limited to unreserved realized cushion and debit the
ATTACK credit simultaneously. All operations are post-settlement, causal,
capital conserving and identity-free. Not approved for live use.
"""
from __future__ import annotations

import json
from decimal import Decimal
from qore.infrastructure.trader_lab import cibo_three_mode_capital_lab as lab
import cibo_trader_lab_batch_runner as batch

_original_mark = lab._State.mark
_original_child = batch._child
_current_policy = "baseline"
_mark_index = 0
_rebalance_count = 0
_rebalanced_total = Decimal(0)
_unfunded_total = Decimal(0)
_first_rebalance = None


def reconcile_available_cushion(state, target: Decimal) -> Decimal:
    """Transfer only unreserved Portfolio assets. Preserve total capital."""
    gap = max(Decimal(0), target - state.sovereign_bank_usd)
    available = max(Decimal(0), state.portfolio_cushion_usd - state.cushion_reserved_usd)
    transfer = min(gap, available)
    if transfer == 0:
        return transfer
    before = state.total_capital_usd
    credit_before = state.portfolio_attack_credit_usd
    state.portfolio_cushion_usd -= transfer
    state.sovereign_bank_usd += transfer
    state.portfolio_attack_credit_usd = max(
        Decimal(0), min(credit_before - transfer, state.cushion_available_usd)
    )
    if state.total_capital_usd != before:
        raise AssertionError("cross-ledger transfer silently created capital")
    if state.portfolio_cushion_usd < state.cushion_reserved_usd:
        raise AssertionError("cross-ledger transfer spent reserved cushion")
    if state.portfolio_attack_credit_usd > state.cushion_available_usd:
        raise AssertionError("cross-ledger transfer double-pledged ATTACK credit")
    return transfer


def _mark(state):
    global _mark_index, _rebalance_count, _rebalanced_total, _unfunded_total
    global _first_rebalance
    _mark_index += 1
    if _current_policy != "baseline":
        target = (
            state.sovereign_protection_floor_usd
            if _current_policy == "restore-floor"
            else Decimal(0)
        )
        deficit = max(Decimal(0), target - state.sovereign_bank_usd)
        if deficit:
            available_before = max(
                Decimal(0), state.portfolio_cushion_usd - state.cushion_reserved_usd
            )
            transferred = reconcile_available_cushion(state, target)
            _unfunded_total += deficit - transferred
            if transferred:
                _rebalance_count += 1
                _rebalanced_total += transferred
                if _first_rebalance is None:
                    _first_rebalance = {
                        "mark_index": _mark_index,
                        "policy": _current_policy,
                        "deficit": str(deficit),
                        "transferred": str(transferred),
                        "available_before": str(available_before),
                        "sovereign_after": str(state.sovereign_bank_usd),
                        "cushion_after": str(state.portfolio_cushion_usd),
                        "credit_after": str(state.portfolio_attack_credit_usd),
                        "capital_after": str(state.total_capital_usd),
                    }
                    print("CIBO_REBALANCE_FIRST_EVENT=" +
                          json.dumps(_first_rebalance,sort_keys=True),flush=True)
    _original_mark(state)


def _child(name, args, result_dir=None, identity=None):
    global _current_policy, _mark_index, _rebalance_count, _rebalanced_total
    global _unfunded_total, _first_rebalance
    _current_policy = (
        "restore-floor" if name.startswith("transfer-floor")
        else "restore-zero" if name.startswith("transfer-zero")
        else "baseline"
    )
    _mark_index=0
    _rebalance_count=0
    _rebalanced_total=Decimal(0)
    _unfunded_total=Decimal(0)
    _first_rebalance=None
    _original_child(name,args,result_dir,identity)
    print("CIBO_REBALANCE_SUMMARY=" + json.dumps({
        "case":name,"policy":_current_policy,
        "mark_count":_mark_index,
        "transfer_count":_rebalance_count,
        "transferred_total_usd":str(_rebalanced_total),
        "unfunded_deficit_cumulative_usd":str(_unfunded_total),
        "first_rebalance":_first_rebalance,
    },sort_keys=True),flush=True)


lab._State.mark = _mark
batch._child = _child

if __name__ == "__main__":
    raise SystemExit(batch.main())
