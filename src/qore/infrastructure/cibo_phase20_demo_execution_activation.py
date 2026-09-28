"""Explicit Owner activation gate for CIBO Phase20D cTrader DEMO execution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SCHEMA = "qore.cibo.phase20d.demo_execution_activation.v1"
_TOKEN = "CIBO_PHASE20D_DEMO_EXECUTION_AUTHORIZED"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Phase20DemoExecutionActivation:
    schema: str
    authorization_token: str
    authorized_by_owner: bool
    environment: str
    collector_git_sha: str
    authorized_at: datetime
    fundednext_allowed: bool
    live_allowed: bool
    real_capital_allowed: bool
    merge_allowed: bool

    def __post_init__(self) -> None:
        if self.schema != _SCHEMA:
            raise CiboCapitalManagementError(
                "Phase20D DEMO activation schema mismatch"
            )
        if self.authorization_token != _TOKEN:
            raise CiboCapitalManagementError(
                "Phase20D DEMO execution Owner token missing"
            )
        if self.authorized_by_owner is not True:
            raise CiboCapitalManagementError(
                "Phase20D DEMO execution requires explicit Owner authorization"
            )
        if self.environment != "demo":
            raise CiboCapitalManagementError(
                "Phase20D execution activation must remain DEMO-only"
            )
        if _SHA1_RE.fullmatch(self.collector_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase20D collector Git SHA must be lowercase 40-hex"
            )
        if (
            self.authorized_at.tzinfo is None
            or self.authorized_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "Phase20D DEMO authorized_at must be timezone-aware"
            )
        if self.authorized_at.astimezone(UTC) > datetime.now(UTC):
            raise CiboCapitalManagementError(
                "Phase20D DEMO authorization cannot be future-dated"
            )
        if (
            self.fundednext_allowed
            or self.live_allowed
            or self.real_capital_allowed
            or self.merge_allowed
        ):
            raise CiboCapitalManagementError(
                "Phase20D DEMO activation cannot grant non-DEMO authority"
            )


def load_phase20_demo_execution_activation(
    path: Path,
    *,
    expected_git_sha: str,
) -> Phase20DemoExecutionActivation:
    if not isinstance(path, Path):
        raise CiboCapitalManagementError(
            "Phase20D DEMO activation path must be Path"
        )
    if _SHA1_RE.fullmatch(expected_git_sha) is None:
        raise CiboCapitalManagementError(
            "Phase20D expected Git SHA must be lowercase 40-hex"
        )
    if not path.is_file():
        raise CiboCapitalManagementError(
            "Phase20D DEMO execution activation file is required"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CiboCapitalManagementError(
            "Phase20D DEMO activation file is invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20D DEMO activation payload must be object"
        )

    required = {
        "schema",
        "authorization_token",
        "authorized_by_owner",
        "environment",
        "collector_git_sha",
        "authorized_at",
        "fundednext_allowed",
        "live_allowed",
        "real_capital_allowed",
        "merge_allowed",
    }
    if set(payload) != required:
        raise CiboCapitalManagementError(
            "Phase20D DEMO activation fields mismatch"
        )
    for name in (
        "authorized_by_owner",
        "fundednext_allowed",
        "live_allowed",
        "real_capital_allowed",
        "merge_allowed",
    ):
        if type(payload[name]) is not bool:
            raise CiboCapitalManagementError(
                f"Phase20D DEMO activation {name} must be bool"
            )
    authorized_at = datetime.fromisoformat(str(payload["authorized_at"]))
    activation = Phase20DemoExecutionActivation(
        schema=str(payload["schema"]),
        authorization_token=str(payload["authorization_token"]),
        authorized_by_owner=bool(payload["authorized_by_owner"]),
        environment=str(payload["environment"]),
        collector_git_sha=str(payload["collector_git_sha"]),
        authorized_at=authorized_at,
        fundednext_allowed=bool(payload["fundednext_allowed"]),
        live_allowed=bool(payload["live_allowed"]),
        real_capital_allowed=bool(payload["real_capital_allowed"]),
        merge_allowed=bool(payload["merge_allowed"]),
    )
    if activation.collector_git_sha != expected_git_sha:
        raise CiboCapitalManagementError(
            "Phase20D DEMO activation Git lineage mismatch"
        )
    return activation
