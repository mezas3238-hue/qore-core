# VT31 — M7-A prereg before code (15 October 2026)

Base: PR #982 commit cfab08786ecc09ed0b3b0a930d46d74345235fff. Objective: one VT31 trader, three Silver Bullet sessions, G3 producer and G3 OPS consistent. This is research only, no orders, no sizing, no trading authorization, no certificates.

Problem: native VT31Trader currently instantiates LEGACY OPS even when original COG uses G3. On first G3 decision, OPS rejects the mismatch. Issue #984.

Precommitted changes:
1. Change ONLY the VT31Trader coordinator, not original G3 cognition, original OPS, DTO, or G3 decision act. Add optional explicit framework_policy parameter. Legacy default unchanged, G3 opt-in explicit. Constructor rejects policy mismatch BEFORE any market observation. Every per-session OPS receives identical policy. Reject policy switches before mutating cognition.
2. Use original source M1 with 1,059,784 bars sha256 0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa, NY timezone DST and 775 days times three windows. NY AM only: H1 09 requires 60 completed M1 before COG; London and NY PM no 09H requirement.
3. Compare full original online G3 2325-case casebook hash cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1 from PR #982 against the native G3 coordinator on the same M1 source, with all WAIT cases and as-of timestamps unchanged. Source coverage independent hash 7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d, post-hoc only. Never alter expected counts to fit results.
4. Tests: G3 explicit constructor, legacy default, mismatch rejected without memory mutation, unsupported framework, all three sessions EST/EDT, midwindow gaps, source 09h veto, no orders, no sizing.
5. GitHub CI verifies G3 COG blob d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9 and OPS blob 0ce9707314aecb71155de8b57044b6ec028847b2 untouched, runs full M1 and publishes hashes and artifact.

Passing engineering M7-A is NOT a full methodology/cognition certificate. M0 owner policy approval, M2 source doctrine London/NY PM, M3 author displacement, M4 four entries, M5 caused swing, M6 two independent human signatures issue #897, and M7 full three-session integration remain blocking. No LIVE, DEMO, VPS, fills, sizing, PnL, or merge to main.
