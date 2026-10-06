"""Immutable auxiliary-artifact manifest for Phase22 Turtle fresh replay.

Fresh 2015-2016 market data is separate from the frozen methodology support
artifacts. Target Destination, cognitive/regime memory, and candidate-freeze
artifacts are all pre-outcome dependencies and are pinned here by run id,
artifact id, exact name, and archive SHA-256.

No Phase18 outcome ledger is part of this manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PHASE22_TURTLE_AUXILIARY_MANIFEST_ID = (
    "CIBO_PHASE22_TURTLE_AUXILIARY_ARTIFACTS_V1"
)
TURTLE_SYMBOLS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD")
AUXILIARY_ROLES = ("TARGET", "COGNITIVE", "FREEZE")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22TurtleAuxiliaryArtifact:
    symbol: str
    role: str
    run_id: int
    artifact_id: int
    artifact_name: str
    artifact_digest: str
    pre_outcome_dependency: bool = True
    phase18_outcome_ledger: bool = False

    def __post_init__(self) -> None:
        if self.symbol not in TURTLE_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 Turtle auxiliary symbol drift"
            )
        if self.role not in AUXILIARY_ROLES:
            raise CiboCapitalManagementError(
                "Phase22 Turtle auxiliary role drift"
            )
        if self.run_id <= 0 or self.artifact_id <= 0 or not self.artifact_name:
            raise CiboCapitalManagementError(
                "Phase22 Turtle auxiliary identity invalid"
            )
        if _SHA256_RE.fullmatch(self.artifact_digest) is None:
            raise CiboCapitalManagementError(
                "Phase22 Turtle auxiliary digest invalid"
            )
        if not self.pre_outcome_dependency or self.phase18_outcome_ledger:
            raise CiboCapitalManagementError(
                "Phase22 Turtle auxiliary governance contamination"
            )


PHASE22_TURTLE_AUXILIARY_ARTIFACTS = (
    Phase22TurtleAuxiliaryArtifact("AUDJPY","TARGET",35204892665,10489761448,"qore-cibo-target-destination-v2-AUDJPY-2f510461b3360e91d5ee70a72716a76cd6561f16","sha256:5cc4d29d94620c572d0ed2944bd7e59d22337c76357cc933ae224d49d59c1f70"),
    Phase22TurtleAuxiliaryArtifact("AUDJPY","COGNITIVE",35383377176,10562458144,"qore-turtle-soup-audjpy-structural-specialist-v2-r27-e0bec233ed40197a1e969786b24a9dc8a1e5869f","sha256:ed5a0928e83be7af171864c37335d8f3edeb9af096f29eb9e0a23078745b255c"),
    Phase22TurtleAuxiliaryArtifact("AUDJPY","FREEZE",35397198837,10568098058,"qore-turtle-soup-audjpy-r39-candidate-freeze-2210ae38b209103c0dfd6c21addb96bd5bc8a3ac","sha256:94b7f28c0bf3ed8793019a1fc27e5db9a52d86194897583376719b040fcc6037"),
    Phase22TurtleAuxiliaryArtifact("EURUSD","TARGET",35204892665,10489596583,"qore-cibo-target-destination-v2-EURUSD-2f510461b3360e91d5ee70a72716a76cd6561f16","sha256:74b7e73f2e38f6be8a02f3eff01b7fdfa0d4cbd5fd464b580380ac951a4c7a85"),
    Phase22TurtleAuxiliaryArtifact("EURUSD","COGNITIVE",35319457546,10536696948,"qore-turtle-soup-eurusd-cognitive-v3-r28-e6879bbdd3844751af075269ddd93db6d3f9b9e1","sha256:1fea5061f631c1a2a006a43937de9183060256189592cf59a5317ccfdae8c5f5"),
    Phase22TurtleAuxiliaryArtifact("EURUSD","FREEZE",35326864091,10539189859,"qore-turtle-soup-eurusd-r36-candidate-freeze-4fef686b9fc669ad64a5a85fb2c899fae9b42a74","sha256:68b007942b1e8583bfaed2568661cbd01142902d169fb5344a423bb960aa2aa8"),
    Phase22TurtleAuxiliaryArtifact("GBPJPY","TARGET",35204892665,10489327009,"qore-cibo-target-destination-v2-GBPJPY-2f510461b3360e91d5ee70a72716a76cd6561f16","sha256:01989d47b98688ad34fb3afadcd5826409a4c955b36fe133669cb288230f238a"),
    Phase22TurtleAuxiliaryArtifact("GBPJPY","COGNITIVE",35349300927,10549575964,"qore-turtle-soup-gbpjpy-structural-specialist-v2-r27-00fb870826e0cbd30179fe44cbdd6707448be0da","sha256:9e9b57f3a108d4f26b3e0b3600705859dc2491dd735972d563f7a350fe0798d2"),
    Phase22TurtleAuxiliaryArtifact("GBPJPY","FREEZE",35371045165,10558097201,"qore-turtle-soup-gbpjpy-r36-candidate-freeze-035b8772a023fc0a57697aecbcb1a302173491cd","sha256:5c3a9d899827773fa84db8166f63ac669284b161c3fd572b953a73d2dfd7f3f4"),
    Phase22TurtleAuxiliaryArtifact("GBPUSD","TARGET",35204892665,10489089220,"qore-cibo-target-destination-v2-GBPUSD-2f510461b3360e91d5ee70a72716a76cd6561f16","sha256:f208010fedc5619599a1828ff1c243d7696ececdc27a0846b672559384bc9fc1"),
    Phase22TurtleAuxiliaryArtifact("GBPUSD","COGNITIVE",35339237432,10544098544,"qore-turtle-soup-gbpusd-structural-specialist-v2-r27-b7005f4dab80376f3bdd5ce199e37f425ab99633","sha256:be89206b847934fd62cb7f63daabb3032cbeec5a1652575b59022353bb9b2978"),
    Phase22TurtleAuxiliaryArtifact("GBPUSD","FREEZE",35352628190,10550491883,"qore-turtle-soup-gbpusd-r38-candidate-freeze-ca8117643986e9c1fbb8e4ee3ddac5d06e3a6ce7","sha256:c86c10d7bdfc6e226c1005791a05d9257472915bbf117a7ee7344572af85614b"),
    Phase22TurtleAuxiliaryArtifact("XAUUSD","TARGET",35204892665,10489343458,"qore-cibo-target-destination-v2-XAUUSD-2f510461b3360e91d5ee70a72716a76cd6561f16","sha256:61f60ee5df2507c3f7eca02fef1bc9252f0eaae0a428b47a6027882a7b74bfff"),
    Phase22TurtleAuxiliaryArtifact("XAUUSD","COGNITIVE",35305338898,10531258915,"qore-turtle-soup-xauusd-cognitive-v3-r28-c35f8414ce59e26a36cdda27c2a964a426c3e5ba","sha256:33d1b590dd8c11c63bc6d9f3164b567a61795abe7b4582800a87aeb43f0a8bed"),
    Phase22TurtleAuxiliaryArtifact("XAUUSD","FREEZE",35308395893,10531679718,"qore-turtle-soup-xauusd-r33-candidate-freeze-112c4f12c53299764d31c38f8e7a129f1e84305e","sha256:1439d47e69c7c23a7354b8c70cc1519807ae711ab9da002d3eb220dbed4279a6"),
)


def phase22_turtle_auxiliary_manifest_payload() -> dict[str, Any]:
    rows = PHASE22_TURTLE_AUXILIARY_ARTIFACTS
    if tuple((item.symbol, item.role) for item in rows) != tuple(
        (symbol, role) for symbol in TURTLE_SYMBOLS for role in AUXILIARY_ROLES
    ):
        raise CiboCapitalManagementError(
            "Phase22 Turtle auxiliary ordered 5x3 surface drift"
        )
    return {
        "manifest_id": PHASE22_TURTLE_AUXILIARY_MANIFEST_ID,
        "artifacts": [asdict(item) for item in rows],
        "artifact_count": len(rows),
        "phase18_outcome_ledgers_included": False,
        "productive_authority": False,
    }


def phase22_turtle_auxiliary_manifest_sha256() -> str:
    raw = json.dumps(
        phase22_turtle_auxiliary_manifest_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
