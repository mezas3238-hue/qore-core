"""CLI for the irreversible Phase22 V4 execution closure."""

from __future__ import annotations

import argparse
import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_consumption_ledger import (
    load_phase22_execution_consumption_receipt,
    persist_phase22_consumed_receipt,
)
from qore.infrastructure.cibo_phase22_v4_execution_closure import (
    PHASE22_SOVEREIGN_BRANCH,
    close_phase22_v4_one_shot_execution,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
)
from qore.infrastructure.cibo_phase22_v4_git_durable_claim import (
    CONSUMPTION_RECEIPT_RELATIVE_PATH,
    ONE_SHOT_CLAIM_RELATIVE_PATH,
    Phase22V4GitDurableClaimEvidence,
    load_phase22_v4_one_shot_claim,
    verify_phase22_v4_git_durable_claim,
)
from qore.infrastructure.cibo_phase22_v4_historical_regime import (
    PHASE22_REGIME_SYMBOLS,
    load_phase22_historical_regime_corpora,
)


def _json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw

def _preserved_durable_claim_evidence(
    path: Path,
) -> Phase22V4GitDurableClaimEvidence:
    raw = _json_object(path)
    expected = str(raw.pop("evidence_sha256", ""))
    raw["changed_paths"] = tuple(str(x) for x in raw["changed_paths"])
    evidence = Phase22V4GitDurableClaimEvidence(**raw)
    if evidence.fingerprint() != expected:
        raise ValueError("preserved durable claim evidence digest mismatch")
    return evidence


def _source_roots(values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw_path = value.partition("=")
        if not sep or not symbol or not raw_path:
            raise ValueError("source root must be SYMBOL=PATH")
        if symbol in parsed:
            raise ValueError(f"duplicate source root: {symbol}")
        parsed[symbol] = Path(raw_path)
    if set(parsed) != set(PHASE22_REGIME_SYMBOLS):
        raise ValueError("exact Phase22 five-market regime source roots required")
    return parsed


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--branch-name",
        default=PHASE22_SOVEREIGN_BRANCH,
    )
    parser.add_argument("--remote-name", default="origin")
    parser.add_argument("--fresh-batch", type=Path, required=True)
    parser.add_argument("--provider-numeric", type=Path, required=True)
    parser.add_argument("--provider-numeric-freeze-sha256", required=True)
    parser.add_argument("--source-root", action="append", required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--claim", type=Path, required=True)
    parser.add_argument("--consumption", type=Path, required=True)
    parser.add_argument("--replay-started-at", required=True)
    parser.add_argument("--completed-at")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--durable-claim-evidence", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    expected_claim = (repo_root / ONE_SHOT_CLAIM_RELATIVE_PATH).resolve()
    expected_consumption = (
        repo_root / CONSUMPTION_RECEIPT_RELATIVE_PATH
    ).resolve()
    if args.claim.resolve() != expected_claim:
        raise ValueError("Phase22 closure claim path is not canonical")
    if args.consumption.resolve() != expected_consumption:
        raise ValueError("Phase22 closure consumption path is not canonical")

    durable_claim_evidence = (
        _preserved_durable_claim_evidence(args.durable_claim_evidence)
        if args.durable_claim_evidence is not None
        else verify_phase22_v4_git_durable_claim(
            repo_root=repo_root,
            branch_name=args.branch_name,
            remote_name=args.remote_name,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
        )
    )

    # Fresh evidence access is deliberately below the remote-durable barrier.
    fresh = load_phase22_sealed_fresh_batch(_json_object(args.fresh_batch))
    provider = load_phase22_sealed_provider_numeric(
        _json_object(args.provider_numeric)
    )
    corpora = load_phase22_historical_regime_corpora(
        _source_roots(args.source_root)
    )
    claim = load_phase22_v4_one_shot_claim(args.claim)
    consumption = load_phase22_execution_consumption_receipt(args.consumption)
    if consumption is None:
        raise ValueError("Phase22 durable consumption claim missing")

    closure = close_phase22_v4_one_shot_execution(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=(
            args.provider_numeric_freeze_sha256
        ),
        corpora=corpora,
        store_root=args.store_root,
        replay_started_at=datetime.fromisoformat(args.replay_started_at),
        completed_at=(
            None
            if args.completed_at is None
            else datetime.fromisoformat(args.completed_at)
        ),
        claim=claim,
        consumption_claim=consumption,
        durable_claim_evidence=durable_claim_evidence,
        execution_run_id=args.run_id,
        execution_run_attempt=args.run_attempt,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "durable-claim-evidence.json": closure.durable_claim_evidence,
        "execution-report.json": closure.execution,
        "qualification-report.json": closure.qualification,
        "completion-receipt.json": closure.completion,
        "store-sha256s.json": {
            "store_sha256s": closure.store_sha256s,
        },
        "consumed-receipt.json": closure.consumed.payload(),
    }
    for name, value in outputs.items():
        (args.output_dir / name).write_text(
            json.dumps(_canonical(value), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    persist_phase22_consumed_receipt(
        consumed=closure.consumed,
        path=args.consumption,
    )
    print(
        json.dumps(
            {
                "qualification_status": closure.qualification.status.value,
                "completion_sha256": closure.completion.fingerprint(),
                "outcomes_emitted": closure.consumed.outcomes_emitted,
                "second_fresh_execution_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
