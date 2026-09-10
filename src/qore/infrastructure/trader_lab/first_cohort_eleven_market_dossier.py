"""Build five frozen Trader dossiers across the exact QORE eleven-market universe.

This layer groups one Trader across all eleven retained market Story Forensics
packages before independent thesis review. It refuses to combine different
configurations or methodologies under one Trader identity.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import cast

_MARKET_SCHEMA = "qore.trader_lab.first_cohort_market_story_forensics.v1"
_DOSSIER_SCHEMA = "qore.trader_lab.eleven_market_trader_dossier.v1"
_SET_SCHEMA = "qore.trader_lab.eleven_market_dossier_set.v1"
_MARKETS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "XAUUSD",
    "NAS100",
    "SP500",
    "GBPJPY",
    "AUDJPY",
    "US30",
)
_TRADERS = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


class ElevenMarketDossierError(ValueError):
    """Raised when eleven-market evidence cannot form one coherent Trader dossier."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ElevenMarketDossierError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise ElevenMarketDossierError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ElevenMarketDossierError(f"{field_name} must be non-empty text")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise ElevenMarketDossierError(f"{field_name} must be bool")
    return value


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ElevenMarketDossierError("dossier material must be canonical JSON") from error


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ElevenMarketDossierError(f"cannot read market package: {path}") from error
    return _object(decoded, field_name="market package")


def _index_by_trader(
    rows: object,
    *,
    field_name: str,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in _array(rows, field_name=field_name):
        row = _object(item, field_name=field_name)
        trader_code = _text(row.get("trader_code"), field_name=f"{field_name} trader_code")
        if trader_code not in _TRADERS:
            raise ElevenMarketDossierError(f"{field_name} contains unknown Trader")
        if trader_code in result:
            raise ElevenMarketDossierError(f"{field_name} contains duplicate Trader")
        result[trader_code] = row
    if set(result) != set(_TRADERS):
        raise ElevenMarketDossierError(f"{field_name} must contain all five Traders")
    return result


def _pack_trader_code(pack: dict[str, object]) -> str:
    binding = _object(pack.get("source_binding"), field_name="source_binding")
    return _text(binding.get("trader_code"), field_name="source_binding trader_code")


def _index_story_packs(rows: object) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in _array(rows, field_name="trader_story_packs"):
        pack = _object(item, field_name="trader story pack")
        trader_code = _pack_trader_code(pack)
        if trader_code not in _TRADERS:
            raise ElevenMarketDossierError("story pack contains unknown Trader")
        if trader_code in result:
            raise ElevenMarketDossierError("story packs contain duplicate Trader")
        result[trader_code] = pack
    if set(result) != set(_TRADERS):
        raise ElevenMarketDossierError("story packs must contain all five Traders")
    return result


def _validate_market_package(
    payload: dict[str, object],
) -> tuple[str, dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    if _text(payload.get("schema"), field_name="market schema") != _MARKET_SCHEMA:
        raise ElevenMarketDossierError("unexpected market Story Forensics schema")
    if not _strict_bool(payload.get("research_only"), field_name="research_only"):
        raise ElevenMarketDossierError("market package must be research-only")
    if _strict_bool(payload.get("execution_authority"), field_name="execution_authority"):
        raise ElevenMarketDossierError("market package cannot have execution authority")
    symbol = _text(payload.get("symbol"), field_name="symbol")
    if symbol not in _MARKETS:
        raise ElevenMarketDossierError("market package is outside QORE eleven-market universe")
    summaries = _index_by_trader(
        payload.get("trader_summaries"),
        field_name="trader_summaries",
    )
    packs = _index_story_packs(payload.get("trader_story_packs"))
    for trader_code in _TRADERS:
        if summaries[trader_code].get("trader_code") != trader_code:
            raise ElevenMarketDossierError("summary Trader identity mismatch")
        binding = _object(packs[trader_code].get("source_binding"), field_name="source_binding")
        if _text(binding.get("symbol"), field_name="source_binding symbol") != symbol:
            raise ElevenMarketDossierError("story pack symbol mismatch")
        if (
            _text(binding.get("trader_code"), field_name="source_binding trader_code")
            != trader_code
        ):
            raise ElevenMarketDossierError("story pack Trader identity mismatch")
    _text(payload.get("market_forensics_fingerprint"), field_name="market fingerprint")
    return symbol, summaries, packs


def _market_row(
    *,
    market_payload: dict[str, object],
    symbol: str,
    summary: dict[str, object],
    pack: dict[str, object],
) -> dict[str, object]:
    binding = _object(pack.get("source_binding"), field_name="source_binding")
    forensics_fingerprint = _text(
        pack.get("forensics_fingerprint"),
        field_name="forensics_fingerprint",
    )
    session_fingerprint = _text(
        summary.get("session_intelligence_fingerprint"),
        field_name="session_intelligence_fingerprint",
    )
    evidence_material = {
        "symbol": symbol,
        "market_forensics_fingerprint": _text(
            market_payload.get("market_forensics_fingerprint"),
            field_name="market fingerprint",
        ),
        "forensics_fingerprint": forensics_fingerprint,
        "session_intelligence_fingerprint": session_fingerprint,
        "source_binding": binding,
    }
    return {
        "symbol": symbol,
        "evidence_ready": True,
        "evidence_digest": _digest(evidence_material),
        "summary": {
            "episode_count": summary.get("episode_count"),
            "family_status": deepcopy(summary.get("family_status")),
            "session_breakdown": deepcopy(summary.get("session_breakdown")),
            "outside_primary_session_entry_count": summary.get(
                "outside_primary_session_entry_count"
            ),
            "forensics_fingerprint": forensics_fingerprint,
            "session_intelligence_fingerprint": session_fingerprint,
            "software_sha": _text(binding.get("software_sha"), field_name="software_sha"),
            "account_fingerprint": _text(
                binding.get("account_fingerprint"),
                field_name="account_fingerprint",
            ),
        },
    }


def build_eleven_market_dossiers(
    market_payloads: list[dict[str, object]],
) -> dict[str, object]:
    """Group the same five Trader identities across all eleven frozen markets."""
    if len(market_payloads) != len(_MARKETS):
        raise ElevenMarketDossierError("exactly eleven market packages are required")

    indexed: dict[
        str,
        tuple[dict[str, object], dict[str, dict[str, object]], dict[str, dict[str, object]]],
    ] = {}
    for payload in market_payloads:
        symbol, summaries, packs = _validate_market_package(payload)
        if symbol in indexed:
            raise ElevenMarketDossierError("duplicate market package")
        indexed[symbol] = (payload, summaries, packs)
    if set(indexed) != set(_MARKETS):
        raise ElevenMarketDossierError("market packages must cover the exact QORE eleven")

    dossiers: list[dict[str, object]] = []
    for trader_code in _TRADERS:
        rows: list[dict[str, object]] = []
        identities: set[tuple[str, str, str]] = set()
        for symbol in _MARKETS:
            payload, summaries, packs = indexed[symbol]
            pack = packs[trader_code]
            binding = _object(pack.get("source_binding"), field_name="source_binding")
            identities.add(
                (
                    _text(binding.get("config_fingerprint"), field_name="config_fingerprint"),
                    _text(
                        binding.get("methodology_fingerprint"),
                        field_name="methodology_fingerprint",
                    ),
                    _text(binding.get("execution_period"), field_name="execution_period"),
                )
            )
            rows.append(
                _market_row(
                    market_payload=payload,
                    symbol=symbol,
                    summary=summaries[trader_code],
                    pack=pack,
                )
            )
        if len(identities) != 1:
            raise ElevenMarketDossierError(
                f"{trader_code} changes config, methodology, or timeframe across markets"
            )
        config_fingerprint, methodology_fingerprint, execution_period = next(iter(identities))
        dossier: dict[str, object] = {
            "schema": _DOSSIER_SCHEMA,
            "research_only": True,
            "execution_authority": False,
            "trader_code": trader_code,
            "identity": {
                "config_fingerprint": config_fingerprint,
                "methodology_fingerprint": methodology_fingerprint,
                "execution_period": execution_period,
            },
            "markets": rows,
        }
        dossier["dossier_fingerprint"] = _digest(dossier)
        dossiers.append(dossier)

    result: dict[str, object] = {
        "schema": _SET_SCHEMA,
        "research_only": True,
        "execution_authority": False,
        "market_count": len(_MARKETS),
        "trader_count": len(_TRADERS),
        "markets": list(_MARKETS),
        "traders": list(_TRADERS),
        "dossiers": dossiers,
    }
    result["dossier_set_fingerprint"] = _digest(result)
    return result


def build_eleven_market_dossiers_from_paths(paths: list[Path]) -> dict[str, object]:
    """Read exactly eleven market packages and build the five Trader dossiers."""
    return build_eleven_market_dossiers([_read_json(path) for path in paths])


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != len(_MARKETS):
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_eleven_market_dossier "
            "EURUSD GBPUSD USDJPY AUDUSD USDCAD XAUUSD NAS100 SP500 GBPJPY AUDJPY US30",
            file=sys.stderr,
        )
        return 2
    try:
        payload = build_eleven_market_dossiers_from_paths([Path(item) for item in arguments])
    except ElevenMarketDossierError as error:
        print(f"eleven-market dossier build failed: {error}", file=sys.stderr)
        return 1
    print(_canonical(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
