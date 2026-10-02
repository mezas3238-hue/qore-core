"""Frozen six-field market-evidence ABI for the Phase22 V5 VT31 lane."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Protocol

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.market_data import OhlcSnapshot

ABI_IDENTITY = (
    "CIBO_PHASE22_V5_VT31_FROZEN_MARKET_EVIDENCE_ABI_V1:"
    "series,account,evidence_fingerprint,checked_at,collector_git_sha,provider_symbol"
)


class Phase22V5Vt31Source(Protocol):
    series: tuple[OhlcSnapshot, ...]
    fingerprint: str
    last_closed_at: datetime
    corpus_git_sha: str
    provider_symbol: str


def v5_vt31_source_abi_sha256() -> str:
    return "sha256:" + hashlib.sha256(ABI_IDENTITY.encode("utf-8")).hexdigest()


def adapt_v5_vt31_market_evidence(
    source: Phase22V5Vt31Source,
) -> tuple[
    tuple[OhlcSnapshot, ...],
    str,
    str,
    datetime,
    str,
    str,
]:
    series = source.series
    evidence_fingerprint = source.fingerprint
    if evidence_fingerprint.startswith("sha256:"):
        evidence_fingerprint = evidence_fingerprint.removeprefix("sha256:")
    checked_at = source.last_closed_at
    collector_git_sha = source.corpus_git_sha
    provider_symbol = source.provider_symbol
    if (
        not isinstance(series, tuple)
        or not series
        or not evidence_fingerprint
        or checked_at.tzinfo is None
        or checked_at.utcoffset() is None
        or len(collector_git_sha) != 40
        or not provider_symbol
    ):
        raise CiboCapitalManagementError(
            "V5 VT31 frozen evidence ABI metadata invalid"
        )
    return (
        series,
        "PHASE22_V5_HISTORICAL_ACCOUNT_NOT_CLAIMED",
        evidence_fingerprint,
        checked_at,
        collector_git_sha,
        provider_symbol,
    )
