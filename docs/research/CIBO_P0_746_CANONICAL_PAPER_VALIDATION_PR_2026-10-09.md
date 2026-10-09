# PR #746 — independent CI of migrated canonical PAPER authority

This branch points to code that migrates PR #746's singleton Trader Lab research
journal to the **same** `PaperQDLE` selected in integrator PR #745. Previous
`QDLE(research_paper_mode=True)`, `paper_transition`, `paper_events` and
`PAPER_OPEN/PAPER_ABORTED` states must not be merged as competing authorities.

Pending verified CI:
- `test_qdle_paper_account_lifecycle.py`: canonical PaperQDLE, 5% all-held
  NAV accounting, fee-at-open reserve, idempotent lifecycle, source isolation.
- `test_cibo_trader_lab_single_qdle_account.py`: bridge from alternate
  #746 simulator to PaperQDLE, deterministic chronological PAPER fills,
  no broker settle, shared 5% risk.
- `test_qore_dynamic_lot_engine.py`: broker-side QDLE regression.
- `test_cibo_p0_universal_3368_evidence_gate.py`: inspect evidence without
  changing unrelated Core or claiming profitability.

The PR is a **validation-only child of #746**, not a second live runtime or
alternative reservation policy. After the gate passes, #746's integration
conflicts against #745 still require explicit reconciliation and review.
No VPS, LIVE orders, MT5 deals, or historically verified broker PnL.
