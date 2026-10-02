"""Immutable receipt for the pre-outcome Phase22 provider numeric freeze."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RUN_ID = 36956504705
RUN_HEAD_SHA = "887f062f253631aad24aea1d01412e79ce46569b"
ARTIFACT_ID = 11206475793
ARTIFACT_DIGEST = (
    "sha256:cb32ced57e8e5d077b6dee2bc69f9e2d3df03b806062e3878deab91df2d19b4b"
)
ACCOUNT_LINEAGE_FILE_SHA256 = (
    "sha256:bf559eb7f5a27c908ad11ebd29c88ce8f91c4cd9bb3725fc5d49b0e534676c60"
)
PROVIDER_NUMERIC_FREEZE_FILE_SHA256 = (
    "sha256:e753868fb83a1efdaf1a79a8c8403a58bd5947e2932dcb2638fb477f1a7ce867"
)
ACCOUNT_LINEAGE_RECEIPT_SHA256 = (
    "sha256:fda49a5ee1d5d6397915f022fae2009bcb799c242b6fc346eb2e1e3037cc2619"
)
PROVIDER_TERMS_ARTIFACT_ID = 11139835744
PROVIDER_TERMS_ARTIFACT_SHA256 = (
    "sha256:dc9bb7a969c12fabfca4ce7ea1ca1c015298b8f3817035d39ed24597d993fa02"
)
EMPIRICAL_EXECUTION_ARTIFACT_ID = 11194919112
EMPIRICAL_EXECUTION_ARTIFACT_SHA256 = (
    "sha256:9e20c1d1486391cc1c9e70ab4fa8b9cae7eb36bd23b8774ae70353c93a8852ab"
)
LEGACY_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
PHASE22_ACCOUNT_FINGERPRINT_SHA256 = (
    "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
)
_REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22ProviderNumericExecutionFreezeReceipt:
    run_id: int
    run_head_sha: str
    artifact_id: int
    artifact_digest: str
    account_lineage_file_sha256: str
    provider_numeric_freeze_file_sha256: str
    account_lineage_receipt_sha256: str
    provider_terms_artifact_id: int
    provider_terms_artifact_sha256: str
    empirical_execution_artifact_id: int
    empirical_execution_artifact_sha256: str
    legacy_account_fingerprint_sha256: str
    phase22_account_fingerprint_sha256: str
    required_symbols: tuple[str, ...]
    status: str
    same_account_proven: bool
    holdout_market_data_read: bool
    holdout_outcomes_used: bool
    broker_mutation_performed: bool
    historical_provider_economics_claimed: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        if self.status != "READY" or self.required_symbols != _REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric freeze receipt readiness drift"
            )
        if (
            not isinstance(self.run_id, int)
            or isinstance(self.run_id, bool)
            or self.run_id <= 0
            or not isinstance(self.artifact_id, int)
            or isinstance(self.artifact_id, bool)
            or self.artifact_id <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider numeric freeze run/artifact id invalid"
            )
        if _SHA1_RE.fullmatch(self.run_head_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric freeze HEAD invalid"
            )
        for value in (
            self.artifact_digest,
            self.account_lineage_file_sha256,
            self.provider_numeric_freeze_file_sha256,
            self.account_lineage_receipt_sha256,
            self.provider_terms_artifact_sha256,
            self.empirical_execution_artifact_sha256,
        ):
            if _SHA256_RE.fullmatch(value) is None:
                raise CiboCapitalManagementError(
                    "Phase22 provider numeric freeze digest invalid"
                )
        for value in (
            self.legacy_account_fingerprint_sha256,
            self.phase22_account_fingerprint_sha256,
        ):
            if _RAW_SHA256_RE.fullmatch(value) is None:
                raise CiboCapitalManagementError(
                    "Phase22 provider numeric account fingerprint invalid"
                )
        if not self.same_account_proven:
            raise CiboCapitalManagementError(
                "Phase22 provider numeric account lineage not proven"
            )
        if any(
            (
                self.holdout_market_data_read,
                self.holdout_outcomes_used,
                self.broker_mutation_performed,
                self.historical_provider_economics_claimed,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 provider numeric freeze governance contamination"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT = (
    Phase22ProviderNumericExecutionFreezeReceipt(
        run_id=RUN_ID,
        run_head_sha=RUN_HEAD_SHA,
        artifact_id=ARTIFACT_ID,
        artifact_digest=ARTIFACT_DIGEST,
        account_lineage_file_sha256=ACCOUNT_LINEAGE_FILE_SHA256,
        provider_numeric_freeze_file_sha256=PROVIDER_NUMERIC_FREEZE_FILE_SHA256,
        account_lineage_receipt_sha256=ACCOUNT_LINEAGE_RECEIPT_SHA256,
        provider_terms_artifact_id=PROVIDER_TERMS_ARTIFACT_ID,
        provider_terms_artifact_sha256=PROVIDER_TERMS_ARTIFACT_SHA256,
        empirical_execution_artifact_id=EMPIRICAL_EXECUTION_ARTIFACT_ID,
        empirical_execution_artifact_sha256=EMPIRICAL_EXECUTION_ARTIFACT_SHA256,
        legacy_account_fingerprint_sha256=LEGACY_ACCOUNT_FINGERPRINT_SHA256,
        phase22_account_fingerprint_sha256=PHASE22_ACCOUNT_FINGERPRINT_SHA256,
        required_symbols=_REQUIRED_SYMBOLS,
        status="READY",
        same_account_proven=True,
        holdout_market_data_read=False,
        holdout_outcomes_used=False,
        broker_mutation_performed=False,
        historical_provider_economics_claimed=False,
        productive_authority=False,
    )
)


def phase22_provider_numeric_execution_freeze_receipt_payload() -> dict[str, object]:
    receipt = PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT
    return {
        "schema": "qore.cibo.phase22.provider-numeric-execution-freeze-receipt.v1",
        **asdict(receipt),
        "receipt_sha256": receipt.fingerprint(),
    }
