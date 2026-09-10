"""Build deep eleven-market research dossiers from per-market thesis evidence.

Each dossier groups one Trader across the exact QORE eleven-market universe and
retains Story Forensics plus production-default characterization, OOS and stress
evidence under deterministic per-market digests.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import cast

_MARKET_SCHEMA = "qore.trader_lab.first_cohort_market_thesis_evidence.v1"
_SCHEMA = "qore.trader_lab.eleven_market_trader_research_dossier.v1"
_SET_SCHEMA = "qore.trader_lab.eleven_market_trader_research_dossier_set.v1"
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


class ElevenMarketResearchDossierError(ValueError):
    """Raised when deep market evidence cannot form coherent Trader dossiers."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ElevenMarketResearchDossierError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise ElevenMarketResearchDossierError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ElevenMarketResearchDossierError(f"{field_name} must be non-empty text")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise ElevenMarketResearchDossierError(f"{field_name} must be bool")
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
        raise ElevenMarketResearchDossierError(
            "research dossier material must be canonical JSON"
        ) from error


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ElevenMarketResearchDossierError(
            f"cannot read market thesis evidence: {path}"
        ) from error
    return _object(decoded, field_name="market thesis evidence")


def _validate_market_package(
    payload: dict[str, object],
) -> tuple[str, dict[str, dict[str, object]]]:
    if _text(payload.get("schema"), field_name="market schema") != _MARKET_SCHEMA:
        raise ElevenMarketResearchDossierError("unexpected market thesis evidence schema")
    if _text(payload.get("environment"), field_name="environment") != "demo":
        raise ElevenMarketResearchDossierError("market thesis evidence must be DEMO")
    if not _strict_bool(payload.get("research_only"), field_name="research_only"):
        raise ElevenMarketResearchDossierError(
            "market thesis evidence must be research-only"
        )
    if not _strict_bool(payload.get("read_only"), field_name="read_only"):
        raise ElevenMarketResearchDossierError("market thesis evidence must be read-only")
    if _strict_bool(payload.get("execution_authority"), field_name="execution_authority"):
        raise ElevenMarketResearchDossierError(
            "market thesis evidence cannot carry execution authority"
        )
    symbol = _text(payload.get("symbol"), field_name="symbol")
    if symbol not in _MARKETS:
        raise ElevenMarketResearchDossierError(
            "market thesis evidence is outside QORE eleven"
        )
    observed_market_digest = _text(
        payload.get("market_thesis_evidence_fingerprint"),
        field_name="market_thesis_evidence_fingerprint",
    )
    material = deepcopy(payload)
    material.pop("market_thesis_evidence_fingerprint", None)
    if _digest(material) != observed_market_digest:
        raise ElevenMarketResearchDossierError(
            "market thesis evidence fingerprint mismatch"
        )

    rows: dict[str, dict[str, object]] = {}
    for item in _array(payload.get("trader_evidence"), field_name="trader_evidence"):
        row = _object(item, field_name="trader evidence")
        code = _text(row.get("trader_code"), field_name="trader_code")
        if code not in _TRADERS or code in rows:
            raise ElevenMarketResearchDossierError(
                "market thesis evidence Trader set is invalid"
            )
        identity = _object(row.get("identity"), field_name="identity")
        _text(identity.get("config_fingerprint"), field_name="config_fingerprint")
        _text(
            identity.get("methodology_fingerprint"),
            field_name="methodology_fingerprint",
        )
        _text(identity.get("execution_period"), field_name="execution_period")
        _object(row.get("story_forensics"), field_name="story_forensics")
        characterization = _object(
            row.get("characterization"),
            field_name="characterization",
        )
        walk_forward = _object(
            characterization.get("walk_forward_assessment"),
            field_name="walk_forward_assessment",
        )
        _strict_bool(walk_forward.get("oos_pass"), field_name="oos_pass")
        _strict_bool(walk_forward.get("stress_pass"), field_name="stress_pass")
        _object(row.get("provenance"), field_name="provenance")
        observed_row_digest = _text(
            row.get("trader_market_evidence_digest"),
            field_name="trader_market_evidence_digest",
        )
        row_material = deepcopy(row)
        row_material.pop("trader_market_evidence_digest", None)
        if _digest(row_material) != observed_row_digest:
            raise ElevenMarketResearchDossierError(
                f"{code} trader market evidence digest mismatch"
            )
        rows[code] = row
    if set(rows) != set(_TRADERS):
        raise ElevenMarketResearchDossierError(
            "market thesis evidence must cover canonical five Traders"
        )
    return symbol, rows


def build_eleven_market_research_dossiers(
    market_payloads: list[dict[str, object]],
) -> dict[str, object]:
    """Group five Trader identities over the exact eleven deep market packages."""
    if len(market_payloads) != len(_MARKETS):
        raise ElevenMarketResearchDossierError(
            "exactly eleven market thesis evidence packages are required"
        )
    indexed: dict[str, tuple[dict[str, object], dict[str, dict[str, object]]]] = {}
    for payload in market_payloads:
        symbol, rows = _validate_market_package(payload)
        if symbol in indexed:
            raise ElevenMarketResearchDossierError("duplicate market thesis evidence")
        indexed[symbol] = (payload, rows)
    if set(indexed) != set(_MARKETS):
        raise ElevenMarketResearchDossierError(
            "market thesis evidence must cover exact QORE eleven"
        )

    dossiers: list[dict[str, object]] = []
    for code in _TRADERS:
        market_rows: list[dict[str, object]] = []
        identities: set[tuple[str, str, str]] = set()
        for symbol in _MARKETS:
            package, trader_rows = indexed[symbol]
            trader_row = trader_rows[code]
            identity = _object(trader_row.get("identity"), field_name="identity")
            identity_tuple = (
                _text(identity.get("config_fingerprint"), field_name="config_fingerprint"),
                _text(
                    identity.get("methodology_fingerprint"),
                    field_name="methodology_fingerprint",
                ),
                _text(identity.get("execution_period"), field_name="execution_period"),
            )
            identities.add(identity_tuple)
            evidence_digest = _text(
                trader_row.get("trader_market_evidence_digest"),
                field_name="trader_market_evidence_digest",
            )
            market_rows.append(
                {
                    "symbol": symbol,
                    "evidence_ready": True,
                    "evidence_digest": evidence_digest,
                    "summary": {
                        "story_forensics": deepcopy(trader_row.get("story_forensics")),
                        "characterization": deepcopy(trader_row.get("characterization")),
                        "provenance": {
                            **deepcopy(
                                _object(
                                    trader_row.get("provenance"),
                                    field_name="provenance",
                                )
                            ),
                            "software_sha": _text(
                                package.get("software_sha"),
                                field_name="software_sha",
                            ),
                            "account_fingerprint": _text(
                                package.get("account_fingerprint"),
                                field_name="account_fingerprint",
                            ),
                            "market_thesis_evidence_fingerprint": _text(
                                package.get("market_thesis_evidence_fingerprint"),
                                field_name="market_thesis_evidence_fingerprint",
                            ),
                        },
                    },
                }
            )
        if len(identities) != 1:
            raise ElevenMarketResearchDossierError(
                f"{code} changes config, methodology, or timeframe across eleven markets"
            )
        config_fingerprint, methodology_fingerprint, execution_period = next(
            iter(identities)
        )
        dossier: dict[str, object] = {
            "schema": _SCHEMA,
            "research_only": True,
            "execution_authority": False,
            "trader_code": code,
            "identity": {
                "config_fingerprint": config_fingerprint,
                "methodology_fingerprint": methodology_fingerprint,
                "execution_period": execution_period,
            },
            "markets": market_rows,
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


def build_eleven_market_research_dossiers_from_paths(
    paths: list[Path],
) -> dict[str, object]:
    """Read exactly eleven deep market evidence packages and build dossiers."""
    return build_eleven_market_research_dossiers([_read_json(path) for path in paths])


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != len(_MARKETS):
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_eleven_market_research_dossier "
            "EURUSD GBPUSD USDJPY AUDUSD USDCAD XAUUSD NAS100 SP500 "
            "GBPJPY AUDJPY US30",
            file=sys.stderr,
        )
        return 2
    try:
        payload = build_eleven_market_research_dossiers_from_paths(
            [Path(item) for item in arguments]
        )
    except ElevenMarketResearchDossierError as error:
        print(f"eleven-market research dossier build failed: {error}", file=sys.stderr)
        return 1
    print(_canonical(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
