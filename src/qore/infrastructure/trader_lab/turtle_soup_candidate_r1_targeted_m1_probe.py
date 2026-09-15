"""Read-only targeted M1 evidence for Turtle Soup R1 M15 ambiguities.

The target sessions are frozen from source-detector `INTRABAR_PATH_AMBIGUOUS`
outcomes only.  No P&L, winner/loser state, policy ranking, or fresh-OOS data
participates in target selection.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _collect_period_window,
    _connect_and_resolve_symbol,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.targeted_m1_evidence.v1"
_MANIFEST_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.targeted_m1_manifest.v1"
_EMBARGO = datetime(2026, 3, 1, tzinfo=UTC)
_SESSION_SPAN = timedelta(days=1)
_NATIVE_M1_PERIOD = 1
_M1_SECONDS = 60
_EXPECTED_MARKETS = frozenset(
    {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "GBPJPY", "AUDJPY"}
)
_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA64 = re.compile(r"[0-9a-f]{64}")


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise CTraderDemoLabProbeError("target session timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CTraderDemoLabProbeError("target session timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CTraderDemoLabProbeError("target session timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _canonical_manifest_digest(payload: Mapping[str, object]) -> str:
    material = dict(payload)
    material.pop("manifest_digest_sha256", None)
    encoded = json.dumps(
        material,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def load_target_sessions(path: Path, *, symbol: str) -> tuple[datetime, ...]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise CTraderDemoLabProbeError("targeted M1 manifest must be a JSON object")
    if loaded.get("schema") != _MANIFEST_SCHEMA:
        raise CTraderDemoLabProbeError("unexpected targeted M1 manifest schema")
    expected_digest = loaded.get("manifest_digest_sha256")
    if not isinstance(expected_digest, str) or _SHA64.fullmatch(expected_digest) is None:
        raise CTraderDemoLabProbeError("targeted M1 manifest digest is invalid")
    if _canonical_manifest_digest(loaded) != expected_digest:
        raise CTraderDemoLabProbeError("targeted M1 manifest digest mismatch")
    if loaded.get("research_identity") != "turtle-soup-candidate-r1":
        raise CTraderDemoLabProbeError("targeted M1 manifest research identity mismatch")
    if loaded.get("fresh_oos_embargo_start") != _EMBARGO.isoformat():
        raise CTraderDemoLabProbeError("targeted M1 manifest embargo mismatch")
    if symbol not in _EXPECTED_MARKETS:
        raise CTraderDemoLabProbeError("symbol is outside the frozen R1 universe")
    sessions = loaded.get("sessions")
    if not isinstance(sessions, dict) or set(sessions) != _EXPECTED_MARKETS:
        raise CTraderDemoLabProbeError("targeted M1 manifest market universe changed")
    selected = sessions.get(symbol)
    if not isinstance(selected, dict):
        raise CTraderDemoLabProbeError("targeted M1 manifest symbol entry is invalid")
    classic = selected.get("classic")
    plus_one = selected.get("plus-one")
    if not isinstance(classic, list) or not isinstance(plus_one, list):
        raise CTraderDemoLabProbeError("targeted M1 variant session lists are invalid")
    parsed = tuple(sorted({_parse_time(item) for item in (*classic, *plus_one)}))
    if not parsed:
        raise CTraderDemoLabProbeError("targeted M1 symbol has no frozen sessions")
    if any(item >= _EMBARGO or item + _SESSION_SPAN > _EMBARGO for item in parsed):
        raise CTraderDemoLabProbeError("targeted M1 manifest crosses fresh-OOS embargo")
    return parsed


def collect_targeted_m1(
    *,
    manifest_path: Path,
    symbol_name: str,
    software_sha: str,
) -> dict[str, object]:
    if _SHA40.fullmatch(software_sha) is None:
        raise CTraderDemoLabProbeError("software_sha must be exact Git SHA")
    sessions = load_target_sessions(manifest_path, symbol=symbol_name)
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
            client,
            symbol_name=symbol_name,
            timeout_seconds=15.0,
        )
        session_payloads: list[dict[str, object]] = []
        for index, opened_at in enumerate(sessions):
            checked_at = opened_at + _SESSION_SPAN
            bars = _collect_period_window(
                client,
                account_id=account_id,
                symbol=symbol,
                period_name="M1",
                native_period=_NATIVE_M1_PERIOD,
                seconds=_M1_SECONDS,
                opened_at=opened_at,
                checked_at=checked_at,
                window_index=index,
                timeout_seconds=15.0,
            )
            if any(item.opened_at < opened_at or item.closed_at > checked_at for item in bars):
                raise CTraderDemoLabProbeError("targeted M1 collector escaped frozen session")
            session_payloads.append(
                {
                    "opened_at": opened_at.isoformat(timespec="microseconds"),
                    "nominal_closed_at": checked_at.isoformat(timespec="microseconds"),
                    "bar_count": len(bars),
                    "bars": [item.payload() for item in bars],
                }
            )
        digest_material = json.dumps(
            session_payloads,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return {
            "schema": _SCHEMA,
            "environment": "development-market-data",
            "read_only": True,
            "research_only": True,
            "fresh_oos_consumed": False,
            "research_identity": "turtle-soup-candidate-r1",
            "selection_reason": "resolve-only-INTRABAR_PATH_AMBIGUOUS",
            "target_manifest_digest_sha256": json.loads(
                manifest_path.read_text(encoding="utf-8")
            )["manifest_digest_sha256"],
            "symbol": symbol.symbol_name,
            "symbol_digits": symbol.digits,
            "account_fingerprint": account_fingerprint,
            "period": "M1",
            "native_period_value": _NATIVE_M1_PERIOD,
            "session_count": len(session_payloads),
            "software_sha": software_sha,
            "evidence_digest_sha256": sha256(digest_material).hexdigest(),
            "sessions": session_payloads,
        }
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = collect_targeted_m1(
        manifest_path=args.manifest,
        symbol_name=args.symbol,
        software_sha=args.software_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
