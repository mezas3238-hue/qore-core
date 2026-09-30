#!/usr/bin/env python3
from __future__ import annotations

import json

from qore.infrastructure.core_stack_v2.shared_integrator_reconciliation import (
    build_integrator_reconciliation,
)


def main() -> None:
    print(json.dumps(build_integrator_reconciliation(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
