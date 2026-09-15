"""Compose authenticated cTrader DEMO Lab evidence into executable inputs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabMarketEvidence,
    CTraderDemoLabProbeError,
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.transport import ExternalTransportTimeout

_NATIVE_VOLUME_UNIT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CTraderDemoLabComposition:
    configuration: CTraderDemoRuntimeConfiguration
    snapshots: tuple[OhlcSnapshot, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, CTraderDemoRuntimeConfiguration):
            raise CTraderDemoLabProbeError("Lab composition requires runtime configuration")
        if self.configuration.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoLabProbeError("Lab composition must remain DEMO-only")
        if not self.snapshots or any(type(item) is not OhlcSnapshot for item in self.snapshots):
            raise CTraderDemoLabProbeError("Lab composition requires exact OHLC snapshots")
        if {item.timeframe.seconds for item in self.snapshots} != {60, 300, 900, 14_400}:
            raise CTraderDemoLabProbeError("Lab composition requires M1, M5, M15 and H4")


def compose_ctrader_demo_lab_inputs(
    evidence: CTraderDemoLabMarketEvidence,
    *,
    account_ref: str,
    source: ExternalSourceDescriptor,
    timeout_milliseconds: int = 3000,
) -> CTraderDemoLabComposition:
    """Derive exact symbol/volume configuration and closed bars from one probe."""
    if not isinstance(evidence, CTraderDemoLabMarketEvidence):
        raise CTraderDemoLabProbeError("Lab composition requires authenticated evidence")
    evidence.__post_init__()
    if not isinstance(account_ref, str) or not account_ref.isdecimal() or int(account_ref) <= 0:
        raise CTraderDemoLabProbeError("cTrader DEMO account_ref must be positive numeric")
    account_id = int(account_ref)
    if compute_ctrader_demo_lab_account_fingerprint(account_id) != evidence.account_fingerprint:
        raise CTraderDemoLabProbeError("account_ref does not match authenticated Lab evidence")
    if not isinstance(source, ExternalSourceDescriptor):
        raise CTraderDemoLabProbeError("Lab composition source must be canonical")
    symbol = evidence.symbol
    account = MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )
    configuration = CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=account,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument(symbol.symbol_name),
                symbol_id=symbol.symbol_id,
                symbol_name=symbol.symbol_name,
                digits=symbol.digits,
                volume_step=_NATIVE_VOLUME_UNIT,
                min_volume_units=symbol.min_volume_units,
                max_volume_units=symbol.max_volume_units,
                step_volume_units=symbol.step_volume_units,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.CANDLES,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=timeout_milliseconds),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )
    instrument = Instrument(symbol.symbol_name)
    snapshots = tuple(
        OhlcSnapshot(
            snapshot_id=MarketDataSnapshotId(
                uuid5(
                    NAMESPACE_URL,
                    "qore:ctrader-demo:lab-bar:"
                    f"{evidence.account_fingerprint}:{symbol.symbol_id}:"
                    f"{bar.period}:{bar.opened_at.isoformat()}",
                )
            ),
            instrument=instrument,
            source=source,
            timeframe=Timeframe(int((bar.closed_at - bar.opened_at).total_seconds())),
            opened_at=bar.opened_at,
            closed_at=bar.closed_at,
            open=float(Decimal(bar.open)),
            high=float(Decimal(bar.high)),
            low=float(Decimal(bar.low)),
            close=float(Decimal(bar.close)),
        )
        for bar in evidence.bars
    )
    return CTraderDemoLabComposition(configuration=configuration, snapshots=snapshots)
