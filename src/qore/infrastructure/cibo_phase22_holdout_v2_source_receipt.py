"""Immutable source receipt for the active CIBO Phase22 V2 holdout.

V1 remains a separate burned historical receipt. This module binds only
source evidence already collected from cTrader DEMO. It executes no Trader
logic, inspects no outcomes and grants no productive authority.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)

CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"

SOURCE_AVAILABILITY_RUN_ID = 36892565528
SOURCE_AVAILABILITY_RUN_HEAD_SHA = (
    "00358aad1d174a1e97b2850814f26431979798c6"
)
SOURCE_AVAILABILITY_ARTIFACT_ID = 11177925051
SOURCE_AVAILABILITY_ARTIFACT_DIGEST = (
    "sha256:71b5fef8c957161330badfd29b8ca63b4f7bf3b7f063db0aa34534593a312b91"
)
SOURCE_AVAILABILITY_PAYLOAD_SHA256 = (
    "sha256:feae129e79633be94b698bcaddf0b692a17cd1f1508801cbd05070ada9be1e8d"
)
SOURCE_AVAILABILITY_ARTIFACT_GIT_SHA = (
    "c32d0925570267ab915221fa4a65eba5ac83b500"
)

M5_SOURCE_RUN_ID = 36892253124
M5_COLLECTOR_GIT_SHA = "415afb947405d59ffb139b3758eeacf9f9722a7d"
M1_SOURCE_RUN_ID = 36892555597
M1_COLLECTOR_GIT_SHA = "00358aad1d174a1e97b2850814f26431979798c6"

VT08_REQUIRED_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Phase22V2SourceBinding:
    symbol: str
    timeframe: str
    run_id: int
    artifact_id: int
    artifact_digest: str
    collector_git_sha: str
    retained_bars: int
    first_observed_at: str
    last_observed_at: str

    def __post_init__(self) -> None:
        if self.timeframe not in {"M1", "M5"}:
            raise CiboCapitalManagementError("V2 source timeframe drift")
        if self.timeframe == "M1" and self.symbol != "NAS100":
            raise CiboCapitalManagementError("only NAS100 M1 is valid in V2")
        for name in ("run_id", "artifact_id", "retained_bars"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"V2 source {name} must be positive int"
                )
        if _SHA256_RE.fullmatch(self.artifact_digest) is None:
            raise CiboCapitalManagementError("V2 artifact digest invalid")
        if _GIT_SHA_RE.fullmatch(self.collector_git_sha) is None:
            raise CiboCapitalManagementError("V2 collector Git SHA invalid")
        first = datetime.fromisoformat(self.first_observed_at)
        last = datetime.fromisoformat(self.last_observed_at)
        if first.tzinfo is None or first.utcoffset() is None:
            raise CiboCapitalManagementError("V2 first bar must be aware")
        if last.tzinfo is None or last.utcoffset() is None:
            raise CiboCapitalManagementError("V2 last bar must be aware")
        if last < first:
            raise CiboCapitalManagementError("V2 source chronology invalid")


V2_SOURCE_BINDINGS = (
    Phase22V2SourceBinding(
        "AUDJPY",
        "M5",
        M5_SOURCE_RUN_ID,
        11176724468,
        "sha256:683998c43877d9865faecfef22d28c3be2434c3191a581faaf7199c3d2edb4d0",
        M5_COLLECTOR_GIT_SHA,
        37260,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "AUDUSD",
        "M5",
        M5_SOURCE_RUN_ID,
        11177431240,
        "sha256:39ad9378bb928cb194801d66165bbf4ceb29a3b7571a3397a09b182ee03d50eb",
        M5_COLLECTOR_GIT_SHA,
        37259,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "EURUSD",
        "M5",
        M5_SOURCE_RUN_ID,
        11176444505,
        "sha256:e37d906b0854fab21309e23f3e89739dcb9bcc3025c128ce891d28b07756b947",
        M5_COLLECTOR_GIT_SHA,
        37262,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "GBPJPY",
        "M5",
        M5_SOURCE_RUN_ID,
        11176882965,
        "sha256:1641437f7a21fa1c12cde69f3c7b8dcd74c100adacd12852a69f54d2b2562d6a",
        M5_COLLECTOR_GIT_SHA,
        37260,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "GBPUSD",
        "M5",
        M5_SOURCE_RUN_ID,
        11177545943,
        "sha256:f271499133360bc18c20308ec8e6ad878d13364b5da5630f57d7268ecf2c2b7d",
        M5_COLLECTOR_GIT_SHA,
        37260,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "NAS100",
        "M5",
        M5_SOURCE_RUN_ID,
        11176499717,
        "sha256:ab120be9e294a443b9739a23d9263bda2832ab91f788576b382c27712c742904",
        M5_COLLECTOR_GIT_SHA,
        34747,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "USDCAD",
        "M5",
        M5_SOURCE_RUN_ID,
        11178565127,
        "sha256:0b98be568622301b9c63b02cd8c19c1fbad8891195d88f615c6dbef89195b80a",
        M5_COLLECTOR_GIT_SHA,
        37257,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "USDJPY",
        "M5",
        M5_SOURCE_RUN_ID,
        11177791412,
        "sha256:e5f46696137428e03fef5a6aecad704f74ea4cac8b6747649452da001d799a85",
        M5_COLLECTOR_GIT_SHA,
        37261,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "XAUUSD",
        "M5",
        M5_SOURCE_RUN_ID,
        11177635981,
        "sha256:a51bf8c5e4e870b0062602aba0103b422251f9ab19400eced7c71c86a11dbb71",
        M5_COLLECTOR_GIT_SHA,
        35034,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:55:00+00:00",
    ),
    Phase22V2SourceBinding(
        "NAS100",
        "M1",
        M1_SOURCE_RUN_ID,
        11178100020,
        "sha256:b131229dc5c465de0d6bbaef66cda0a2f53182ec0da20a78b794781e2de3a961",
        M1_COLLECTOR_GIT_SHA,
        170396,
        "2015-10-19T00:00:00+00:00",
        "2016-04-18T23:59:00+00:00",
    ),
)


def validate_phase22_v2_source_receipt() -> None:
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE
    if candidate.candidate_id != CANDIDATE_ID:
        raise CiboCapitalManagementError("V2 active candidate identity drift")
    if candidate.status is not CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN:
        raise CiboCapitalManagementError("V2 active candidate not eligible")
    if not candidate.source_validation_complete:
        raise CiboCapitalManagementError("V2 source validation incomplete")
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("V2 candidate overlaps confirmed burn")

    m5 = tuple(item for item in V2_SOURCE_BINDINGS if item.timeframe == "M5")
    m1 = tuple(item for item in V2_SOURCE_BINDINGS if item.timeframe == "M1")
    expected_m5 = (
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "USDCAD",
        "USDJPY",
        "XAUUSD",
    )
    if tuple(item.symbol for item in m5) != expected_m5:
        raise CiboCapitalManagementError("V2 M5 source surface incomplete")
    if tuple(item.symbol for item in m1) != ("NAS100",):
        raise CiboCapitalManagementError("V2 NAS100 M1 source missing")
    if not set(VT08_REQUIRED_MARKETS).issubset({item.symbol for item in m5}):
        raise CiboCapitalManagementError("V2 source misses VT08 authority")

    for item in V2_SOURCE_BINDINGS:
        first = datetime.fromisoformat(item.first_observed_at)
        last = datetime.fromisoformat(item.last_observed_at)
        if first != candidate.start_at:
            raise CiboCapitalManagementError("V2 source starts after candidate")
        if not (candidate.start_at <= last < candidate.end_exclusive_at):
            raise CiboCapitalManagementError("V2 source ends outside candidate")

    for value in (
        SOURCE_AVAILABILITY_ARTIFACT_DIGEST,
        SOURCE_AVAILABILITY_PAYLOAD_SHA256,
    ):
        if _SHA256_RE.fullmatch(value) is None:
            raise CiboCapitalManagementError("V2 availability digest invalid")
    for value in (
        SOURCE_AVAILABILITY_RUN_HEAD_SHA,
        SOURCE_AVAILABILITY_ARTIFACT_GIT_SHA,
    ):
        if _GIT_SHA_RE.fullmatch(value) is None:
            raise CiboCapitalManagementError("V2 availability Git SHA invalid")


validate_phase22_v2_source_receipt()


def phase22_v2_holdout_source_receipt_payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.phase22.holdout-source-receipt.v2",
        "candidate_id": CANDIDATE_ID,
        "source_validation_complete": True,
        "burn_clean": True,
        "scientifically_consumable": True,
        "status": "ELIGIBLE_FROZEN",
        "source_availability": {
            "run_id": SOURCE_AVAILABILITY_RUN_ID,
            "run_head_sha": SOURCE_AVAILABILITY_RUN_HEAD_SHA,
            "artifact_id": SOURCE_AVAILABILITY_ARTIFACT_ID,
            "artifact_digest": SOURCE_AVAILABILITY_ARTIFACT_DIGEST,
            "payload_sha256": SOURCE_AVAILABILITY_PAYLOAD_SHA256,
            "artifact_git_sha": SOURCE_AVAILABILITY_ARTIFACT_GIT_SHA,
        },
        "source_archives": [asdict(item) for item in V2_SOURCE_BINDINGS],
        "vt08_required_markets": list(VT08_REQUIRED_MARKETS),
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }
