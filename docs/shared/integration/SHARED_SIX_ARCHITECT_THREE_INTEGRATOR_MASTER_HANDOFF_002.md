# QORE CORE — SHARED MASTER HANDOFF 6 ARCHITECTOS + 3 INTEGRADORES · V2

**Owner:** Sergio Meza  
**Fecha:** 2026-10-02  
**Repo:** `mezas3238-hue/qore-core`  
**PR #635:** OPEN / DRAFT / UNMERGED

## Topología final

- Arquitecto 1 — A Cognitive Core — Integrador 1
- Arquitecto 2 — A STI — Integrador 1
- Arquitecto 3 — A Transversal Seam — Integrador 2
- Arquitecto 4 — B World Foundation — Integrador 2
- Arquitecto 5 — B Relational + Asset Worlds — Integrador 3
- Arquitecto 6 — B Active Perception + Provenance/Freeze — Integrador 3

Pairs:
- Integrador 1 = A1 + A2
- Integrador 2 = A3 + A4
- Integrador 3 = A5 + A6

Todos los integradores tienen la misma misión: **INTEGRAR · REPARAR · AVANZAR**.

## Ownership A

A1:
`WP-05..WP-12`
`MC-01 MC-05 MC-08 MC-11 MC-12 MC-13 MC-14 MC-16 MC-17 MC-18 MC-19 MC-23 MC-24 MC-25 MC-26 MC-27`

A2:
`STI-0..STI-12 STI-14 STI-15 STI-16`
(STI-13 ya cerrado)

A3:
`MC-28 X-01 X-02 X-03 X-05 X-06 X-07 X-08 X-09 X-10 X-12 X-14 X-15 X-16`

## Ownership B

A4:
`B-06 B-07 B-08 B-09 B-10`

A5:
`B-11 B-12 B-13 B-14 B-15`

A6:
`B-16 B-21 B-22 B-24`

B terminales, no reabrir:
`B-01 B-02 B-03 B-04 B-05 B-17 B-18 B-19 B-20 B-23`

## Gates no delegables

`X-20 X-21 X-22` pertenecen al Consejo de Integradores 1+2+3 + Owner.

B-22/B-24 pertenecen operacionalmente a A6, pero no pueden cerrarse hasta que B4/B5/B6 estén terminales y provenance/zero-open lo prueben.

## Leyes

GitHub source of truth. No merge sin Owner. No LIVE/VPS/producción/capital real. No sizing/Risk/CIBO/Execution authority. No final holdout. No outcome-aware tuning. CI GREEN != scientific closure.

## Handoffs canónicos

A:
- `SHARED_ARCHITECT_1_COGNITIVE_CORE_HANDOFF_001.md`
- `SHARED_ARCHITECT_2_STI_HANDOFF_001.md`
- `SHARED_ARCHITECT_3_TRANSVERSAL_SEAM_HANDOFF_001.md`
- `SHARED_INTEGRATOR_1_A1_A2_HANDOFF_001.md`

B:
- `SHARED_B_456_MASTER_HANDOFF_001.md`
- `SHARED_ARCHITECT_4_WORLD_FOUNDATION_HANDOFF_001.md`
- `SHARED_ARCHITECT_5_RELATIONAL_ASSET_WORLD_HANDOFF_001.md`
- `SHARED_ARCHITECT_6_PROVENANCE_FREEZE_HANDOFF_001.md`
- `SHARED_INTEGRATOR_3_B5_B6_HANDOFF_001.md`

Cross-seam:
- `SHARED_INTEGRATOR_2_A3_B4_FINAL_HANDOFF_001.md`

Matrix:
- `SHARED_6X3_OWNERSHIP_MATRIX_002.json`

Cada actor revalida HEAD y ledger antes de modificar código.
