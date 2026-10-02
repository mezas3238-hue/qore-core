from __future__ import annotations

import json

from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_next_exam_governance import (
    NEXT_CANDIDATE_ID,
)


def payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.next-policy.fingerprints.v1",
        "candidate_id": NEXT_CANDIDATE_ID,
        "policy_bundle_sha256": NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint(),
        "advanced_scientific_eligibility_sha256": (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ),
        "outcomes_inspected": False,
        "productive_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(payload(), sort_keys=True))
