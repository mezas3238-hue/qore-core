"""Causal ablation controls for CIBO sovereign ceiling discovery.

Each ablation neutralizes one productive decision function while keeping the
same account, opportunity population, chronology, provider assumptions, frozen
outcomes and downstream QORE Risk. FULL is the ordinary sovereign runtime.

These switches are research-only. They do not grant execution, LIVE,
production, broker or real-capital authority.
"""

from __future__ import annotations

from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboCeilingAblationMode(StrEnum):
    FULL = "full"
    SIZING = "sizing"
    ADAPTIVE_LEVERAGE = "adaptive_leverage"
    CIBO_COMPOUND = "cibo_compound"
    COMPOUND_PORTFOLIO = "compound_portfolio"
    COGNITION = "cognition"


def validate_ceiling_ablation_mode(
    mode: CiboCeilingAblationMode,
) -> CiboCeilingAblationMode:
    if type(mode) is not CiboCeilingAblationMode:
        raise CiboCapitalManagementError(
            "ceiling ablation mode must be canonical"
        )
    return mode
