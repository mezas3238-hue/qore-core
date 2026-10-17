# VT08 B R18 + R19 — Frontera cognitiva real y expedientes físicos para dos revisores independientes

**Corte:** 15-oct-2026. **B:** rama `agent/vt08-5m-cognition-replay-20261010`, PR #764 DRAFT. **A:** PR #765 DRAFT. **Owner:** SOLO VT08 actual metodología TTrades y cognitiva VT08, no QORE-alpha. Holdout 7Y sellado, sin sizing, sin DEMO/LIVE/VPS ni merges.

## R18: problema de integración realmente encontrado y resuelto

**Antes:** el job de B `VT08 Cognitive 5M Research Bridge` seguía importando A CandidateEvent V1 de un commit antiguo `6e537cd8...` que se autodenominaba `SOURCE_COMPLETE_EXECUTABLE` pese a sus cuatro límites sintéticos QORE B01. Mientras tanto, el autor A ya lo había corregido a `SOURCE_INCOMPLETE_QORE_CONTAINMENT`; una suite vieja verde NO demostraba compatibilidad actual.

**Ahora:** se fijó código A **commit `a60fee1b810b45d6067cd867ae557382135c8604`** en CI B, verificado contra módulo A real. Los tests comprobaron que A declara su B01 como source-incomplete, falso `author_fidelity_verified`, falsa `cognitive_source_admission_authorized`, y B lo **RECHAZA EXPLÍCITAMENTE**. Identidad estable de fuente cambia solo cuando cambia el origen y permanece igual entre snapshots del mismo origen. A/B confirma rechazo aun si un remitente cambia manualmente el estado a completo con confirmación temporal futura.

**Defensa Owner verdaderamente integrada a la ruta `inspect_architect_a_candidate`:** ahora rechaza cualquier rastro QORE-alpha/VT08-alpha en campos, valores o estructuras anidadas, además de `fallback_strategy`, `parallel_track`, `external_strategy`, `foreign_signal_origin`, `alpha_features`, etc., aunque estén anidados. Queda cerrado el hueco de R16, que antes era solo un validador externo y no se invocaba en ingreso cognitivo.

**CI [#38820178304](https://github.com/mezas3238-hue/qore-core/actions/runs/38820178304): SUCCESS**. Ruff, Mypy y cuatro secciones pytest: 14 + 13 + 245 + 3 = **275 PASS, 3 SKIP**. Handoffs anteriores del propio código R18 con Ruff rojo (#38819943913/#38819975926) se corrigieron; la integración completa y repin final solo se declara PASS con el run final.

**Archivos R18:**
- `src/qore/infrastructure/trader_lab/vt08_5m_a_to_b_candidate_readiness_v1.py` (veto Owner real)
- `tests/infrastructure/trader_lab/test_vt08_5m_a_to_b_candidate_readiness_v1.py` (11 pruebas negativas nuevas de alpha/estrategias ajenas)
- `tests/infrastructure/trader_lab/test_vt08_5m_a_to_b_live_contract_bridge.py` (frontera efectiva con módulo A source-incomplete)
- `.github/workflows/vt08-cognitive-5m-research-bridge.yml` (pin A posterior real)

**Lo que R18 NO resuelve:** A solo presenta B01 legado y su sobre aún está source-incomplete; tampoco existen CandidateEvent v2 M30/M3 fuente autor completa, situación cognitiva de 27 campos semánticamente verificada, manifiesto A+B firmado ni fills broker. El software puede rechazar mal uso, no crear un setup TTrades a partir de cero.

## R19: censo fuente + expedientes ciegos para resolver ambigüedades reales

**CI final [#38820822586](https://github.com/mezas3238-hue/qore-core/actions/runs/38820822586): SUCCESS 6/6 jobs**, 14 tests sintéticos adversariales + Ruff PASS, y 5 mercados de origen cTrader **A R3** + **A R7** inmovilizados en los artifacts #38715560333/#38765076497.

Por CADA mercado:
1. Verifica R3 `all_unique_proxy_cases_with_raw_receipts` y R7 `all_source_only_cases` sobre **todas** las identidades C2/C3 (ningún candidato desaparece), clase geométrica, bloqueos semánticos, reloj y SHA market por fuente.
2. Verifica recibos observados de 10 M3 de C1, 10 M3 de C2, 2 M15 de C2 y hasta 12 M15 de tres H1 PRE-C2. **Recalcula desde la estructura original cada `source_bar_id` SHA** y detecta barras alteradas.
3. Cruza ID source, estados H1, shas de raw M3/M15, clase física R7, EQ condicional, H1 highs untouched observados (ninguno seleccionado por PnL).
4. Genera UNA cola completa de **2.657 IDs y clases**, y **46 expedientes con barras y candidatos para revisión cualitativa dual** elegidos por primera/mediana/última posición cronológica en **cada categoría física**. No se eligen por retorno o aparente claridad. CADJPY aporta también el único caso H1 ausente.
5. Cada paquete pregunta por swing relevant previo y separación, POI significativo anterior a CISD, opposing series M3/HTF confirmatorio, breaker verdadero, EQ según régimen, SL bajo EQ+breaker y espacio FVG, target HTF untouched/desempate; deja ambos campos `independent_reviewer_a_answers=None` y `independent_reviewer_b_answers=None`, `source_primary_reference_verified=False`, `eligible_for_pnl=False`.

| Mercado | Casos del universo fuente | Expedientes ciegos de revisión | Revisiones duales completadas |
|---|---:|---:|---:|
| EURJPY | 538 | 9 | 0 |
| USDCHF | 518 | 9 | 0 |
| NZDUSD | 550 | 9 | 0 |
| CADJPY | 516 | 10 | 0 |
| USDCAD | 535 | 9 | 0 |
| **TOTAL** | **2.657** | **46** | **0** |

**Hallazgo de compatibilidad real corregido:** el `_bar_receipt()` original de A R3 NO incluye `market` en cada subrecibo; `market` lo lleva la identidad exterior del caso y el raw SHA pinned. El primer CI R19 [#38820628137](https://github.com/mezas3238-hue/qore-core/actions/runs/38820628137) rechazó indebidamente esos casos por exigir `receipt.market`. Corrección: si esa clave existe, debe concordar; si no, comparar market exterior + raw feed SHA y **SHA recomputado del bar body**. No se rebajó la protección de fuente; se reforzó contra OHLC tampering. El CI final pasa 5/5 mercados.

**Expedientes disponibles SIN subir barras licenciadas al repositorio público:** descargar los cinco artifacts de run [#38820822586](https://github.com/mezas3238-hue/qore-core/actions/runs/38820822586), prefijo `vt08-b-r19-blind-ttrades-review-{MARKET}-{COMMIT}`. Caducidad Actions 30 días; custodiar bajo permisos apropiados. El código reproducible, sí, queda en GitHub:
- `src/qore/infrastructure/trader_lab/vt08_b_r19_blind_author_semantics_reviewer_pack_v1.py`
- `tests/infrastructure/trader_lab/test_vt08_b_r19_blind_author_semantics_reviewer_pack_v1.py`
- `.github/workflows/vt08-b-r19-blind-ttrades-semantic-review-packets.yml`

## Ruta crítica concreta tras R19 (sin promesas de certificación falsa)
1. **A #762**: inspeccionar los **46 source packets** en su ceguera pre-outcome, aportar fuente primaria exacta para `relevant_swing`, separación, identidad POI, HTF closure→M3 CISD, serie causal PS, breaker, EQ, stop/target. Respuesta por caso con URL/párrafo, IDs físicos, reloj y A/B/C/D; D no se rellena eligiendo el caso rentable.
2. **B #763**: segunda revisión independiente del mismo material, resolver discordancias antes de PnL; anotar muestra sin extrapolar resultados de 46 a los restantes 2.657 ni a 1.987 mercados/días. No self-sign B con anotar source A.
3. Tras acordar criterio reproducible escrito para 8 ambigüedades (sin inventar regla de autor), aplicar a **censo completo 2.657**, con puentes A/B válidos, situación de **27 valores con SHA/available_at y 2 raters**, WAL/replay cognitivo, BID/ASK ejecución real y por último Gates económicos PF/DD/Sharpe/Sortino/Monte Carlo/OOS/densidad preregistrados.
4. Si fuente primaria no define selector esencial y revisores no acuerdan un criterio fiel/reproducible, marcar `NO_ESPECIFICABLE_D`; no seguir llamando TTrades exacto a una heurística no fundamentada.

## Certificación y prohibiciones
`R18_AB_INGRESS=PASS`, `R19_SOURCE_PACKETS=PASS`, `SOURCE_RULE_TEXT_R17=REVIEWED`; **`AUTHOR_COMPLETE_ENTRIES=0`, `INDEPENDENT_REVIEWS=0`, `REAL_COGNITIVE_ADMISSIONS=0`, `BROKER_FILLS=0`, `PF/DD/SORTINO=NOT_MEASURED`, `VT08_NO_CERTIFICADO`**. PR #764 y #765 DRAFT, **sin QORE-alpha**, sin sizing, 7Y sellado intacto, no operaciones ni merges.
