# VT08 R38 — Gate causal ejecutable, sin autorización de trades

Fecha 2026-10-22. Código implementado en `scripts/research/vt08_r38_causal_admission_gate.py` (rama B DRAFT). Auditoría local ejecutada sobre 5 ZIP originales R25, 2657 case IDs únicos.

**Pruebas:** 8/8 PASS: igualdad C3, primera confirmación en igualdad, estrictamente anterior, futuro, zona horaria inválida, campo ausente, duplicado, regresión 2657 oficiales. En todos los casos `trade_authorized=false` y `status=WAIT` porque este módulo comprueba **solo causalidad**, no fuente TTrades.

| Resultado | Casos |
|---|---:|
| Primer CISD proxy antes C3 | 2504 |
| Primer CISD proxy exactamente C3 | 153 |
| Reclaim viejo nivel antes C3 (subgrupo 316) | 221 |
| Reclaim viejo nivel exactamente C3 | 80 |
| Sin reclaim (subgrupo 316) | 15 |
| Admisiones cognitivas reales | 0 |

El gate rechaza timestamps sin UTC, no inventa orden intrabar ni fills, y falla ante IDs duplicados. **No confundir** 2504 temporales con señales metodológicas válidas. `C3.open` requiere prueba de orden feed/latencia si `available_at==C3.open`.

**Reproducción:** archivo de pruebas de sesión `test_vt08_r38_causal_admission_gate.py`, `python test_vt08_r38_causal_admission_gate.py` con ZIP R25 bajo `/mnt/data`. Código de producción no modificado; falta integrar gate en `CandidateEvent V2` y `evaluate_provenanced` con CI, y adjudicar fuente TTrades Protected Swing/POI/CISD. No merge, LIVE, sizing, holdout 7Y, QORE-alpha. **VT08_NOT_CERTIFIED**.