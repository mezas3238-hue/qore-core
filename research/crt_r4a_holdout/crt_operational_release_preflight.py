"""Read-only auditable release assessment of CRT Trader R4-A.

Hard NO LIVE, no broker calls and no synthetic profit certification.
Inspect the repository's actual availability of safety/economic evidence.
No switch or self-attested JSON can substitute an external certification.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from research.crt_r4a_holdout.runner import SYMBOLS

SCHEMA = "QORE_CRT_TRADER_R4A_OPERATIONAL_RELEASE_PREFLIGHT_V1"


@dataclass(frozen=True, slots=True)
class ReleaseCheck:
    id: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class ReleaseReport:
    schema: str
    trader: str
    status: str
    release_authorized: bool
    live_execution_allowed: bool
    supported_market_catalog: int
    historical_broker_coverage: int
    historical_economic_trades_certified: int
    checks: tuple[ReleaseCheck, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["checks"] = [asdict(x) for x in self.checks]
        return result


def evaluate(repo_root: Path) -> ReleaseReport:
    """Only software-verifiable positive tests pass; missing truth stays BLOCKED."""
    root = repo_root.resolve()
    data = root / "research/crt_r4a_holdout/data"
    config_path = data / "manifest.json"
    if not config_path.is_file():
        raise FileNotFoundError("canonical CRT R4-A research manifest unavailable")
    manifest = json.loads(config_path.read_text(encoding="utf-8"))
    quotes = manifest.get("quotes")
    if not isinstance(quotes, dict) or set(quotes) != set(SYMBOLS):
        raise ValueError("CRT 34-market manifest inventory does not match canonical symbols")

    active_quote_records = sum(
        isinstance(quotes[symbol], dict) and bool(quotes[symbol].get("sha256"))
        for symbol in SYMBOLS
    )
    # Even a SHA in a manifest is a declaration, not historical bid/ask proof.
    # Stage remains BLOCKED until provider and files are externally audited.
    transport = (
        root / "src/qore/infrastructure/ctrader_open_api_transport.py"
    ).read_text(encoding="utf-8")
    codec = (
        root / "src/qore/infrastructure/ctrader_demo_execution_codec.py"
    ).read_text(encoding="utf-8")
    send_begin = transport.index("    def submit_order(")
    send_end = transport.index("    def cancel_order(", send_begin)
    wire = transport[send_begin:send_end]
    native_sl = 'fields["relativeStopLoss"]' in wire
    native_tp = 'fields["relativeTakeProfit"]' in wire
    encode_begin = codec.index("def build_ctrader_demo_order_create_plan(")
    encode_end = codec.index("@dataclass(", encode_begin)
    encoder = codec[encode_begin:encode_end]
    protected_codec = (
        "relativeStopLoss" in encoder and "relativeTakeProfit" in encoder
    )
    broker_protection = native_sl and native_tp and protected_codec
    burned = bool(manifest.get("window_consumed_for_crt_research"))
    parity = bool(manifest.get("parity_verified"))
    cost = bool(manifest.get("costs_verified"))
    source_verified = bool(manifest.get("provider_data_verified"))
    checks = (
        ReleaseCheck(
            "01_CATALOG_34", "PASS" if len(SYMBOLS) == 34 else "BLOCKED",
            "Exact fixed 34-market identity, not verified trading coverage",
        ),
        ReleaseCheck(
            "02_HISTORIC_BID_ASK_34", "BLOCKED",
            f"Manifest declares {active_quote_records}/34 SHA references; "
            "source-matched authentic bid/ask files still require independent checks",
        ),
        ReleaseCheck(
            "03_PINE_EVENT_PARITY", "BLOCKED",
            "Pine vs cTrader event-by-event equivalence not externally certified"
            + ("; manifest flag alone is insufficient" if parity else ""),
        ),
        ReleaseCheck(
            "04_PROVIDER_IC_MATCH", "BLOCKED",
            "12 Atlas feed mappings are unverified and BTCUSD is missing"
            + ("; manifest flag alone is insufficient" if source_verified else ""),
        ),
        ReleaseCheck(
            "05_NATIVE_SERVER_SLTP_ORDER", "PASS_STATIC_ONLY"
            if broker_protection else "BLOCKED",
            "Codec and transport static presence is not broker confirmation"
            if broker_protection else (
                "Existing canonical gateway sends no native SL/TP in new orders"
            ),
        ),
        ReleaseCheck(
            "06_BROKER_CONTRACT_COSTS", "BLOCKED",
            "Missing independently audited contract tick value, price digits, "
            "size, spread/slippage, commission, swap and FX conversion"
            + ("; manifest flag alone is insufficient" if cost else ""),
        ),
        ReleaseCheck(
            "07_RISK_CIBO_AND_IDEMPOTENCY", "BLOCKED",
            "CRT proposal is explicitly nonexecutable; no approved pretrade intent, "
            "independent risk sizing, duplicate/unknown-outcome lifecycle certified",
        ),
        ReleaseCheck(
            "08_UNSEEN_24M_HOLDOUT", "BLOCKED",
            "2024-2025 BURNED by prior research" if burned
            else "Independent untouched 24 months not independently attested",
        ),
        ReleaseCheck(
            "09_OOS_POSITIVE_EDGE_NET", "BLOCKED",
            "0 broker-reconciled historical trades; no 34-market after-cost "
            "profit factor, expectancy, max drawdown or Monte Carlo evidence",
        ),
        ReleaseCheck(
            "10_DEMO_FORWARD_AND_RECONCILIATION", "BLOCKED",
            "No 34-symbol protection-verified DEMO forward execution/fill "
            "ledger with kill-switch, outage, duplicate and recovery scenarios",
        ),
        ReleaseCheck(
            "11_OWNER_RELEASE_AND_FROZEN_VERSION", "BLOCKED",
            "No independent sign-off or approved frozen candidate; PR remains "
            "research-only, without merge, VPS or LIVE authority",
        ),
    )
    return ReleaseReport(
        schema=SCHEMA,
        trader="QORE_CRT_TRADER_R4A",
        status="BLOCKED_NOT_CERTIFIABLE",
        release_authorized=False,
        live_execution_allowed=False,
        supported_market_catalog=len(SYMBOLS),
        historical_broker_coverage=0,
        historical_economic_trades_certified=0,
        checks=checks,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="QORE CRT DEMO release gate (NO LIVE)")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.repo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report.status,
        "gates": {item.id: item.status for item in report.checks},
        "live_execution_allowed": report.live_execution_allowed,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
