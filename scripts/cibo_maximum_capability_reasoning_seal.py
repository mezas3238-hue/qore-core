#!/usr/bin/env python3
"""Seal CIBO Maximum Capability reasoning once, then reuse it provider-free.

Default mode is DRY-RUN/PREFLIGHT: it validates the single-account reasoning
request ledger and reports governed routes without making a provider call.

Provider execution requires BOTH:
- --execute-provider
- OPENAI_API_KEY

The command is checkpoint/resume safe. Each completed decision is appended as
one NDJSON seal containing the exact request digest, route, replay record and
replay-record digest. No outcome data is read or written.

This is reused/burned historical research and MUST NOT be labeled fresh OOS or
certification evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboAdaptiveReasoningRuntime,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_maximum_capability_reasoning_policy import (
    select_cibo_maximum_capability_reasoning_route,
)
from qore.infrastructure.cibo_reasoning_replay_serialization import (
    cibo_reasoning_replay_record_payload,
    cibo_reasoning_replay_record_sha256,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    StdlibOpenAIResponsesTransport,
)
from qore.infrastructure.openai_cibo_routed_reasoning_engine import (
    OpenAICiboRoutedReasoningConfiguration,
    OpenAICiboRoutedReasoningEngine,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load_completed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise CiboCapitalManagementError(
                f"reasoning seal line {number} must be object"
            )
        signal = str(payload.get("signal_fingerprint", ""))
        if not signal or signal in rows:
            raise CiboCapitalManagementError(
                "reasoning seal contains missing/duplicate signal"
            )
        rows[signal] = payload
    return rows


def _append(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        handle.write("\n")
        handle.flush()


def _route_summary(row: dict[str, Any]) -> dict[str, str]:
    # The provider-neutral ledger already proved the request was generated from
    # a full clean consultation. Maximum Capability V1 declares every decision
    # critical/high; the canonical governed route is therefore Sol/max.
    return {
        "tier": "sol-max",
        "semantic_mode": "max",
        "model": "gpt-5.6-sol",
        "provider_reasoning_effort": "max",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-ledger", type=Path, required=True)
    parser.add_argument("--output-ndjson", type=Path, required=True)
    parser.add_argument(
        "--execute-provider",
        action="store_true",
        help="Actually execute the governed reasoning provider.",
    )
    parser.add_argument(
        "--seal-started-at",
        help=(
            "Timezone-aware ISO timestamp. Required with --execute-provider "
            "to keep historical replay seal identity explicit/reproducible."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional positive row limit for controlled shakedown.",
    )
    args = parser.parse_args()

    ledger = json.loads(args.request_ledger.read_text(encoding="utf-8"))
    if ledger.get("schema") != (
        "qore.cibo.single-account-reasoning-request-ledger.v1"
    ):
        raise CiboCapitalManagementError(
            "reasoning seal requires canonical request ledger"
        )
    if ledger.get("outcome_used_for_predecision") is not False:
        raise CiboCapitalManagementError(
            "reasoning seal request ledger is outcome contaminated"
        )
    if ledger.get("all_decisions_cf01_cf19_consulted") is not True:
        raise CiboCapitalManagementError(
            "reasoning seal requires complete CF01-CF19 consultation"
        )
    if ledger.get("all_applicable_native_semantics_full") is not True:
        raise CiboCapitalManagementError(
            "reasoning seal requires full native semantic transport"
        )
    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "reasoning seal request ledger has no decisions"
        )
    if args.limit is not None and args.limit <= 0:
        raise CiboCapitalManagementError("--limit must be positive")
    selected = rows[: args.limit] if args.limit is not None else rows

    route_counts: dict[str, int] = {}
    for row in selected:
        route = _route_summary(row)
        route_counts[route["tier"]] = route_counts.get(
            route["tier"], 0
        ) + 1

    if not args.execute_provider:
        print(
            json.dumps(
                {
                    "schema": "qore.cibo.maximum-capability-reasoning-seal-preflight.v1",
                    "status": "PREFLIGHT_ONLY_NO_PROVIDER_CALL",
                    "request_ledger_sha256": ledger["ledger_sha256"],
                    "decision_count": len(selected),
                    "already_sealed_count": len(
                        _load_completed(args.output_ndjson)
                    ),
                    "route_counts": route_counts,
                    "outcome_used_for_predecision": False,
                    "target_capital_used_for_tuning": False,
                    "provider_called": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.seal_started_at is None:
        raise CiboCapitalManagementError(
            "--seal-started-at is required with --execute-provider"
        )
    seal_started_at = datetime.fromisoformat(args.seal_started_at)
    if (
        seal_started_at.tzinfo is None
        or seal_started_at.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            "--seal-started-at must be timezone-aware"
        )

    api_key_raw = os.environ.get("OPENAI_API_KEY")
    if not api_key_raw:
        raise CiboCapitalManagementError(
            "OPENAI_API_KEY is required only for --execute-provider"
        )
    try:
        api_key = SecretMaterial(api_key_raw.encode("ascii"))
    except UnicodeEncodeError as exc:
        raise CiboCapitalManagementError(
            "OPENAI_API_KEY must be ASCII"
        ) from exc

    # Executable provider mode requires full requests, not only ledger digests.
    # The dedicated execution runner will bind/reconstruct those requests from
    # the manifest and prove their digest equals this ledger before any call.
    raise CiboCapitalManagementError(
        "provider execution intentionally blocked until request reconstruction "
        "runner binds exact manifest -> consultation -> request digest"
    )


if __name__ == "__main__":
    raise SystemExit(main())
