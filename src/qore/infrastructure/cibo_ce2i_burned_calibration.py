"""Frozen causal calibration extracted only from burned Phase19 training evidence.

No provider USD economics, 2017H1 data, validation outcomes, or economic target
are used here.  T04 is calibrated only in structural-R space and T10 only in
normalized capital-time space.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage

SOURCE_PHASE19_ARTIFACT_ID = 10972948493
SOURCE_PHASE19_ARTIFACT_SHA256 = (
    "e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)
SOURCE_PRIOR_SHA256 = (
    "15b059ea1e303fee7a9ed0894480ee1da6091647482a0811f1090335925b6caa"
)
TRAINING_START = "2021-09-23T05:00:00+00:00"
TRAINING_END = "2022-03-09T17:00:00+00:00"


@dataclass(frozen=True, slots=True)
class CiboBurnedLineageCalibration:
    lineage: TraderLineage
    expected_structural_r: Decimal
    expected_capital_minutes: Decimal
    train_rows: int

    @property
    def normalized_r_per_capital_minute(self) -> Decimal:
        return self.expected_structural_r / self.expected_capital_minutes


CIBO_BURNED_T04_T10_CALIBRATION: tuple[CiboBurnedLineageCalibration, ...] = (
    CiboBurnedLineageCalibration(TraderLineage.R34_XAUUSD, Decimal("0.01123928933790496197574842467647058823529"), Decimal("30.0"), 85),
    CiboBurnedLineageCalibration(TraderLineage.R38_EURUSD, Decimal("-0.07406596871747924540112516922"), Decimal("40.0"), 75),
    CiboBurnedLineageCalibration(TraderLineage.R38_GBPJPY, Decimal("0.2772449399623627771422912858"), Decimal("55.0"), 97),
    CiboBurnedLineageCalibration(TraderLineage.R42_AUDJPY, Decimal("0.15558135309771811105602414900375"), Decimal("80.0"), 81),
    CiboBurnedLineageCalibration(TraderLineage.R43_GBPUSD, Decimal("0.04540176351632619076884529877058823529412"), Decimal("45.0"), 84),
    CiboBurnedLineageCalibration(TraderLineage.VT08_FOREX, Decimal("-0.09821428571428571428571428572"), Decimal("105.0"), 24),
    CiboBurnedLineageCalibration(TraderLineage.VT31_NAS100, Decimal("0.2981877694835413223925389858666666666667"), Decimal("6.0"), 77),
)


def burned_t04_t10_calibration_payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.ce2i.burned_t04_t10_calibration.v1",
        "source": {
            "phase19_artifact_id": SOURCE_PHASE19_ARTIFACT_ID,
            "phase19_artifact_sha256": SOURCE_PHASE19_ARTIFACT_SHA256,
            "prior_sha256": SOURCE_PRIOR_SHA256,
            "training_start": TRAINING_START,
            "training_end": TRAINING_END,
            "evidence_status": "BURNED_DEVELOPMENT",
        },
        "t04": {
            "calibration_space": "STRUCTURAL_R_PER_TRUE_STRUCTURAL_STOP_RISK_UNIT",
            "usd_economic_calibration": False,
        },
        "t10": {
            "calibration_space": "NORMALIZED_R_PER_CAPITAL_MINUTE",
            "usd_output_per_capital_hour": False,
        },
        "rows": [
            {
                "lineage": row.lineage.value,
                "expected_structural_r": str(row.expected_structural_r),
                "expected_capital_minutes": str(row.expected_capital_minutes),
                "normalized_r_per_capital_minute": str(
                    row.normalized_r_per_capital_minute
                ),
                "train_rows": row.train_rows,
            }
            for row in CIBO_BURNED_T04_T10_CALIBRATION
        ],
        "governance": {
            "holdout_2017h1_used": False,
            "phase19j_validation_used_for_fit": False,
            "provider_usd_economics_claimed": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_t04_t10_calibration_sha256() -> str:
    encoded = json.dumps(
        burned_t04_t10_calibration_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
