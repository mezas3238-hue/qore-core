"""Resident FundedNext VT-08/CIBO/Risk runtime for the existing Windows VPS.

This process is intentionally self-contained on the VPS.  ChatGPT/RDP is not in
the execution loop.  It continuously reconciles account state and provider MLL,
evaluates only fresh VT-08 Forex anchors, gates through CIBO and sovereign Risk,
runs MT5 order_check for every approved plan, and mutates only in LIVE mode when
an exact-SHA local activation record is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    ReservationState,
    RiskDecision,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.fundednext_live_authorization import (
    FundedNextLiveAccountAuthorization,
)
from qore.infrastructure.fundednext_live_mt5 import (
    FundedNextLiveMt5ExecutionGateway,
    MetaTrader5FundedNextLiveTransport,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    FundedNextMt5MutationState,
    JsonFileFundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_operational import build_account_bound_submission
from qore.infrastructure.fundednext_operational_risk_policy import (
    CapitalBudgetDecision,
    evaluate_qore_operational_capital_budget,
)
from qore.infrastructure.fundednext_runtime_pipeline import (
    cibo_setup_from_b01,
    request_cibo_posture,
)
from qore.infrastructure.fundednext_runtime_state import (
    DurableFundedNextRuntimeStateStore,
    FundedNextRuntimeState,
    SingleWriterRuntimeLock,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    PILOT_INITIAL_BALANCE,
    RuleVerificationState,
    StellarInstantAccountSnapshot,
    StellarInstantRuleVerification,
    evaluate_stellar_instant_budget,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    OWNER_FOREX_ENTRY_ANCHORS,
    Vt08B01Bar,
    evaluate_b01_at_entry,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    Vt08ForexCiboDecision,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import (
    build_certified_vt08_forex_cibo_request,
)

_NY = ZoneInfo("America/New_York")
_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY")
_EXPECTED_SERVER = "FundedNext-Server"
_ACCOUNT_REF = "fundednext-stellar-instant-live"
_LOOP_SECONDS = 10
_ANCHOR_GRACE = timedelta(seconds=105)
_HISTORY_DAYS = 14


def _git_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if len(value) != 40:
        raise RuntimeError("runtime-git-sha-invalid")
    return value


def _account_fingerprint(account: object) -> str:
    material = "|".join(
        (
            str(getattr(account, "login")),
            str(getattr(account, "server")),
            str(getattr(account, "company")),
            str(getattr(account, "currency")),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _magic(client_order_id: str) -> int:
    digest = hashlib.sha256(client_order_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name}-must-be-json-object")
    return value


def _live_authorization(
    payload: dict[str, object],
    *,
    account: MarketTestAccountIdentity,
) -> FundedNextLiveAccountAuthorization:
    return FundedNextLiveAccountAuthorization(
        account=account,
        git_sha=str(payload["git_sha"]),
        account_identity_fingerprint=str(payload["account_identity_fingerprint"]),
        expected_server=str(payload["expected_server"]),
        provider_rules_fingerprint=str(payload["provider_rules_fingerprint"]),
        no_send_evidence_sha256=str(payload["no_send_evidence_sha256"]),
        shadow_evidence_sha256=str(payload["shadow_evidence_sha256"]),
        restart_recovery_evidence_sha256=str(
            payload["restart_recovery_evidence_sha256"]
        ),
        ea_entitlement_verified=bool(payload["ea_entitlement_verified"]),
        provider_rules_current=bool(payload["provider_rules_current"]),
        no_send_passed=bool(payload["no_send_passed"]),
        shadow_passed=bool(payload["shadow_passed"]),
        service_24_7_verified=bool(payload["service_24_7_verified"]),
        restart_recovery_passed=bool(payload["restart_recovery_passed"]),
        activation_timestamp=datetime.fromisoformat(str(payload["activation_timestamp"])),
        order_submission_authorized=bool(payload["order_submission_authorized"]),
    )


def _rules(payload: dict[str, object]) -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        rules_verified_at=datetime.fromisoformat(str(payload["rules_verified_at"])),
        rules_valid_until=datetime.fromisoformat(str(payload["rules_valid_until"])),
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=bool(payload["ea_entitlement_verified"]),
        platform_verified=True,
        exact_product_verified=True,
    )


def _m15_bars(symbol: str, decision_at: datetime) -> tuple[Vt08B01Bar, ...]:
    start = decision_at - timedelta(days=_HISTORY_DAYS)
    end = decision_at + timedelta(minutes=1)
    rows = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
    if rows is None or len(rows) == 0:
        raise RuntimeError(f"m15-data-unavailable-{symbol}")
    bars: list[Vt08B01Bar] = []
    for row in rows:
        opened = datetime.fromtimestamp(int(row["time"]), tz=UTC)
        bars.append(
            Vt08B01Bar(
                opened_at=opened,
                closed_at=opened + timedelta(minutes=15),
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
        )
    return tuple(bars)


def _current_anchor(now: datetime) -> datetime | None:
    local = now.astimezone(_NY)
    if local.hour not in OWNER_FOREX_ENTRY_ANCHORS:
        return None
    anchor_local = local.replace(minute=0, second=0, microsecond=0)
    anchor = anchor_local.astimezone(UTC)
    if now.astimezone(UTC) < anchor or now.astimezone(UTC) - anchor > _ANCHOR_GRACE:
        return None
    return anchor


def _broker_risk(transport: MetaTrader5FundedNextLiveTransport) -> tuple[Decimal, Decimal, Decimal]:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise RuntimeError("broker-exposure-snapshot-unavailable")
    open_stop = Decimal(0)
    floating_loss = Decimal(0)
    pending_stop = Decimal(0)
    for position in positions:
        stop = Decimal(str(position.sl))
        if stop <= 0:
            raise RuntimeError("open-position-without-stop-fails-closed")
        spec = transport.symbol_info(str(position.symbol))
        if spec is None:
            raise RuntimeError("open-position-symbol-economics-unavailable")
        entry = Decimal(str(position.price_open))
        volume = Decimal(str(position.volume))
        open_stop += abs(entry - stop) / spec.tick_size * spec.tick_value * volume
        floating_loss += max(Decimal(0), -Decimal(str(position.profit)))
    for order in orders:
        stop = Decimal(str(order.sl))
        if stop <= 0:
            raise RuntimeError("pending-order-without-stop-fails-closed")
        spec = transport.symbol_info(str(order.symbol))
        if spec is None:
            raise RuntimeError("pending-order-symbol-economics-unavailable")
        entry = Decimal(str(order.price_open))
        volume = Decimal(str(order.volume_current))
        pending_stop += abs(entry - stop) / spec.tick_size * spec.tick_value * volume
    return open_stop, floating_loss, pending_stop


def _reconcile_filled_reservations(
    *,
    risk: DurableAccountWideRiskEngine,
    risk_ledger: DurableAccountWideRiskLedger,
    mutation_ledger: JsonFileFundedNextMt5MutationLedger,
) -> None:
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise RuntimeError("fill-reconciliation-broker-state-unavailable")
    current_magics = {int(item.magic) for item in (*positions, *orders)}
    mutations = {
        item.risk_authorization_id: item
        for item in mutation_ledger.records()
        if item.state is FundedNextMt5MutationState.ACCEPTED
    }
    for reservation in risk_ledger.load():
        if reservation.state is not ReservationState.FILLED_UNRECONCILED:
            continue
        mutation = mutations.get(reservation.authorization.authorization_id)
        if mutation is None:
            continue
        if _magic(mutation.client_order_id) in current_magics:
            risk.reconcile_fill(reservation.authorization.authorization_id)


def _log(path: Path, event: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["logged_at"] = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")


def _process_anchor(
    *,
    symbol: str,
    decision_at: datetime,
    now: datetime,
    mode: str,
    gateway: FundedNextLiveMt5ExecutionGateway,
    transport: MetaTrader5FundedNextLiveTransport,
    risk: DurableAccountWideRiskEngine,
    account_binding_id: str,
    provider_budget: object,
    capital_budget: object,
    account_equity: Decimal,
    log_path: Path,
) -> None:
    evaluation = evaluate_b01_at_entry(
        symbol=symbol,
        m15_bars=_m15_bars(symbol, decision_at),
        decision_at=decision_at,
    )
    if not evaluation.is_setup:
        _log(
            log_path,
            {
                "event": "VT08_ABSTAIN",
                "symbol": symbol,
                "decision_at": decision_at.isoformat(),
                "reason": str(evaluation.abstain_reason),
            },
        )
        return
    assert evaluation.candidate is not None
    setup = cibo_setup_from_b01(evaluation.candidate)
    posture = request_cibo_posture(
        initial_balance=PILOT_INITIAL_BALANCE,
        balance=Decimal(str(gateway.read_account(now=now).balance)),
        equity=account_equity,
        current_aggregate_risk=risk.active_reserved_stop_risk(),
    )
    cibo = evaluate_vt08_forex_cibo(
        setup,
        enabled=True,
        certification_current=True,
        now=now,
        requested_posture=posture,
    )
    if cibo.decision is not Vt08ForexCiboDecision.ALLOW:
        _log(log_path, {"event": "CIBO_DENY", "symbol": symbol, "reason": cibo.reason})
        return
    spec = gateway.read_symbol(symbol, now=now)
    request = build_certified_vt08_forex_cibo_request(
        request_id=f"vt08-{setup.signal_fingerprint[:24]}",
        cibo_authorization=cibo,
        provider_spec=spec,
        account_equity=account_equity,
    )
    open_stop, floating_loss, pending_stop = _broker_risk(transport)
    del floating_loss
    snapshot = AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=account_equity,
        margin_used=Decimal(str(gateway.read_account(now=now).margin)),
        free_margin=Decimal(str(gateway.read_account(now=now).free_margin)),
        open_stop_worst_case_loss=open_stop,
        open_floating_loss=Decimal(0),
        pending_broker_worst_case_loss=pending_stop,
        qore_authorizable_headroom=capital_budget.qore_authorizable_headroom,
        provider_budget=provider_budget,
        reconciled_at=now,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=now)
    authorization = risk.authorize(request, snapshot, now=now)
    if authorization.decision is RiskDecision.REJECT:
        _log(
            log_path,
            {"event": "RISK_REJECT", "symbol": symbol, "reason": authorization.reason},
        )
        return
    switch = ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=now,
        reason="qore fundednext runtime preflight gate enabled",
    )
    submission = build_account_bound_submission(
        authorization,
        switch=switch,
        authorized_at=now,
        submitted_at=now,
    )
    shadow = gateway.shadow_check(submission, now=now)
    if not shadow.broker_valid:
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {"event": "SHADOW_REJECT", "symbol": symbol, "reason": shadow.reason},
        )
        return
    if mode == "shadow":
        risk.cancel(authorization.authorization_id)
        _log(
            log_path,
            {
                "event": "SHADOW_PASS",
                "symbol": symbol,
                "signal_fingerprint": setup.signal_fingerprint,
                "risk_decision": authorization.decision.value,
                "risk_usd": str(authorization.monetary_stop_loss),
                "volume": str(authorization.authorized_volume),
                "retcode": shadow.retcode,
            },
        )
        return
    provider_ref = gateway.submit_live(submission, now=now)
    risk.record_full_fill(authorization.authorization_id)
    _log(
        log_path,
        {
            "event": "LIVE_SUBMIT_ACCEPTED",
            "symbol": symbol,
            "signal_fingerprint": setup.signal_fingerprint,
            "risk_authorization": authorization.authorization_id,
            "provider_order_ref": provider_ref,
            "risk_usd": str(authorization.monetary_stop_loss),
            "volume": str(authorization.authorized_volume),
        },
    )


def run(root: Path, *, mode: str, activation_path: Path) -> None:
    sha = _git_sha(root)
    if not mt5.initialize():
        raise RuntimeError(f"mt5-initialize-failed-{mt5.last_error()}")
    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError("mt5-account-info-unavailable")
    if str(account_info.server) != _EXPECTED_SERVER:
        raise RuntimeError("mt5-server-mismatch")
    fingerprint = _account_fingerprint(account_info)
    account = MarketTestAccountIdentity(
        provider_key="fundednext-stellar-instant-mt5",
        account_ref=_ACCOUNT_REF,
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )
    activation_payload = _load_json(activation_path)
    live_auth = _live_authorization(activation_payload, account=account)
    rules = _rules(activation_payload)
    transport = MetaTrader5FundedNextLiveTransport(
        api=mt5,
        qore_account_ref=_ACCOUNT_REF,
        expected_login=int(account_info.login),
        expected_server=_EXPECTED_SERVER,
    )
    state_dir = root / "var" / "fundednext"
    mutation_ledger = JsonFileFundedNextMt5MutationLedger(state_dir / "mt5-mutations.json")
    risk_ledger = DurableAccountWideRiskLedger(state_dir / "risk-reservations.json")
    risk = DurableAccountWideRiskEngine(risk_ledger)
    gateway = FundedNextLiveMt5ExecutionGateway(
        account=account,
        transport=transport,
        mutation_ledger=mutation_ledger,
        rule_verification=rules,
        live_authorization=live_auth,
        runtime_git_sha=sha,
        account_identity_fingerprint=fingerprint,
        expected_server=_EXPECTED_SERVER,
        submission_enabled=mode == "live",
    )
    gateway.reconcile_unknown(now=datetime.now(UTC))
    store = DurableFundedNextRuntimeStateStore(state_dir / "runtime-state.json")
    old = store.load()
    now = datetime.now(UTC)
    if old is not None:
        if old.git_sha != sha or old.account_identity_fingerprint != fingerprint:
            raise RuntimeError("runtime-state-binding-mismatch")
        highest = Decimal(old.highest_closed_balance)
        previous_mll = Decimal(old.active_mll)
        state = old
    else:
        highest = max(PILOT_INITIAL_BALANCE, Decimal(str(account_info.balance)))
        previous_mll = PILOT_INITIAL_BALANCE * Decimal("0.94")
        state = FundedNextRuntimeState(
            git_sha=sha,
            account_identity_fingerprint=fingerprint,
            highest_closed_balance=str(highest),
            active_mll=str(previous_mll),
            processed_anchors=(),
            heartbeat_at=now,
            last_reconciliation_at=now,
            service_started_at=now,
        )
        store.store(state)
    log_path = root / "artifacts" / "fundednext_runtime_events.jsonl"
    while True:
        cycle_at = datetime.now(UTC)
        account_state = gateway.read_account(now=cycle_at)
        gateway.reconcile_unknown(now=cycle_at)
        _reconcile_filled_reservations(
            risk=risk,
            risk_ledger=risk_ledger,
            mutation_ledger=mutation_ledger,
        )
        highest = max(highest, account_state.balance)
        provider = evaluate_stellar_instant_budget(
            StellarInstantAccountSnapshot(
                initial_balance=PILOT_INITIAL_BALANCE,
                balance=account_state.balance,
                equity=account_state.equity,
                highest_closed_balance=highest,
                previous_active_mll=previous_mll,
            )
        )
        previous_mll = provider.active_mll
        open_stop, floating_loss, pending_stop = _broker_risk(transport)
        aggregate = open_stop + pending_stop + risk.active_reserved_stop_risk()
        posture = request_cibo_posture(
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            current_aggregate_risk=aggregate,
        )
        capital = evaluate_qore_operational_capital_budget(
            provider_budget=provider,
            initial_balance=PILOT_INITIAL_BALANCE,
            balance=account_state.balance,
            equity=account_state.equity,
            highest_closed_balance=highest,
            current_aggregate_stop_risk=aggregate,
            requested_posture=posture,
        )
        if capital.decision is CapitalBudgetDecision.REJECT:
            _log(
                log_path,
                {
                    "event": "CAPITAL_BUDGET_REJECT",
                    "reason": capital.reason,
                    "equity": str(account_state.equity),
                    "active_mll": str(provider.active_mll),
                    "floating_loss": str(floating_loss),
                },
            )
        anchor = _current_anchor(cycle_at)
        processed_anchor: str | None = None
        if anchor is not None and capital.decision is not CapitalBudgetDecision.REJECT:
            for symbol in _MARKETS:
                anchor_key = f"{symbol}|{anchor.isoformat()}"
                if anchor_key in state.processed_anchors:
                    continue
                try:
                    _process_anchor(
                        symbol=symbol,
                        decision_at=anchor,
                        now=cycle_at,
                        mode=mode,
                        gateway=gateway,
                        transport=transport,
                        risk=risk,
                        account_binding_id=fingerprint,
                        provider_budget=provider,
                        capital_budget=capital,
                        account_equity=account_state.equity,
                        log_path=log_path,
                    )
                    processed_anchor = anchor_key
                    state = state.with_cycle(
                        highest_closed_balance=str(highest),
                        active_mll=str(previous_mll),
                        processed_anchor=anchor_key,
                        reconciled_at=cycle_at,
                        heartbeat_at=cycle_at,
                    )
                    store.store(state)
                except Exception as error:
                    _log(
                        log_path,
                        {
                            "event": "ANCHOR_FAIL_CLOSED",
                            "symbol": symbol,
                            "reason": type(error).__name__,
                        },
                    )
        if processed_anchor is None:
            state = state.with_cycle(
                highest_closed_balance=str(highest),
                active_mll=str(previous_mll),
                processed_anchor=None,
                reconciled_at=cycle_at,
                heartbeat_at=cycle_at,
            )
            store.store(state)
        time.sleep(_LOOP_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("shadow", "live"), default="shadow")
    parser.add_argument(
        "--activation",
        type=Path,
        default=Path("var/fundednext/live-activation.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lock = SingleWriterRuntimeLock(root / "var" / "fundednext" / "runtime.lock")
    try:
        with lock:
            run(root, mode=args.mode, activation_path=(root / args.activation))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
