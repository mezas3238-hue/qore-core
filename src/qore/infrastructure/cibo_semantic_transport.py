"""Canonical read-only semantic transport for CIBO native intelligence.

Native engine semantics are preserved in full for downstream CIBO cognition.
The transport is observational only and never manufactures evidence sufficiency
or grants sizing, capital, Risk, execution, broker, LIVE, or production
authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def canonicalize_cibo_semantics(value: Any) -> Any:
    """Convert one native CIBO result into deterministic JSON-safe semantics."""

    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CiboCapitalManagementError(
                "semantic transport datetime must be timezone-aware"
            )
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    logical = getattr(value, "logical_values", None)
    if callable(logical):
        return canonicalize_cibo_semantics(logical())
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: canonicalize_cibo_semantics(
                getattr(value, field.name)
            )
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): canonicalize_cibo_semantics(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [canonicalize_cibo_semantics(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def build_semantic_transport_payload(value: object) -> dict[str, object]:
    """Bind full native semantics to an immutable digest without authority."""

    canonical = canonicalize_cibo_semantics(value)
    raw = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    payload: dict[str, object] = {
        "result_type": type(value).__name__,
        "result_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "semantic_transport": "FULL_CANONICAL_READ_ONLY",
        "advisory_only": True,
        "economic_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
    }
    if isinstance(canonical, (str, int, float, bool)) or canonical is None:
        payload["result_value"] = canonical
    else:
        payload["result_semantics"] = canonical
    return payload
