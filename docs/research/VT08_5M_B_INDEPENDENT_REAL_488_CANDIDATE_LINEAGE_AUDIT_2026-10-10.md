# VT08 5M — Arquitecto B: auditoría causal independiente de los 488 candidatos reales B01

**Fecha:** 2026-10-10 · [PR cognitiva #764](https://github.com/mezas3238-hue/qore-core/pull/764) · [Issue B #763](https://github.com/mezas3238-hue/qore-core/issues/763) · contraparte metodología [PR A #765](https://github.com/mezas3238-hue/qore-core/pull/765).  
**Estado:** Investigación GitHub. Ningún trade de estos artefactos fue autorizado, ejecutado o gestionado por cognitiva. No se abrió 7Y, no VPS ni LIVE.

## 1. Evidencia independiente, código y verificación

**GitHub Actions B real:** [run 38095654032](https://github.com/mezas3238-hue/qore-core/actions/runs/38095654032), conclusión **SUCCESS**, SHA de código y tests **`5fbb58cba1b039476b416c178b061b3734ff36c7`**. 13 tests PASS, Ruff PASS, Mypy PASS. Script ejecutado `python -m qore.infrastructure.trader_lab.vt08_5m_b_independent_real_lineage_audit_v1` sobre 10 archivos descargados (5 paquetes A + 5 flujos M15 raw originales). Producto propio B, artefacto [#11685473528](https://github.com/mezas3238-hue/qore-core/actions/runs/38095654032/artifacts/11685473528).

**Inputs congelados:**

- **A:** run [38079270152](https://github.com/mezas3238-hue/qore-core/actions/runs/38079270152), 5 paquetes originales de `vt08_5m_a_b_narrow_source_lineage_v1.py`, SHA productor `b4c7b2df356e1df81bfcf66c810ee1cc794d61e4`. No se sustituyó por los datos actuales del branch móvil A.
- **Raw M15 original:** run [35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), software SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`, cinco archivos JSON `market-evidence-1095d.json`. Se requirió igual `account_fingerprint`, market y software SHA por par.
- **B code:** [independent real audit](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/src/qore/infrastructure/trader_lab/vt08_5m_b_independent_real_lineage_audit_v1.py); [adversarial tests](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/tests/infrastructure/trader_lab/test_vt08_5m_b_independent_real_lineage_audit_v1.py); [workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/.github/workflows/vt08-cognitive-5m-real-a-lineage-independent.yml).

B NO reutilizó el resultado textual de A como prueba final: cargó y cotejó los componentes y hashes de los raw M15 originales para cada candidato. La segunda ejecución también recompuso **independientemente la canonicalización y el SHA-256 de `event_fingerprint` y `source_event_id`**. El resultado de la segunda ejecución es el que rige este documento.

## 2. Resultado por mercado

| Mercado | Candidatos B01 con fuente M15 verificada | Días únicos elegibles bajo cap Owner | Candidatos excluidos por ambigüedad de día |
| --- | ---: | ---: | ---: |
| EURJPY | 88 | 82 | 6 |
| USDCHF | 88 | 78 | 10 |
| NZDUSD | 126 | 114 | 12 |
| CADJPY | 88 | 86 | 2 |
| USDCAD | 98 | 98 | 0 |
| **TOTAL** | **488** | **458** | **30** |

**Ledger consolidado B** (resultado real exacto del proceso, no cifra inferida de documentación):

```json
{
  "schema": "qore.vt08.b_independent_a_source_lineage_audit.research.v1",
  "candidate_events": 488,
  "source_lineage_m15_reverified": 488,
  "cognitive_ready": 0,
  "actual_fills": 0,
  "preregistered_economic_metrics_computed": false,
  "research_only": true
}
```

No se contabiliza `458` como fills: son candidatos únicos por día NY antes de la ejecución. No se han reproducido los **457 terminales** de la simulación legacy en este ensayo B (el residual no se maquilló). Tampoco se agregan los 1.514 fills OHLC de la variante intracycle M15 de A, refutada económicamente; esas identidades no son B01 positional.

## 3. Qué verificó B en cada evento individual

1. Lee únicamente los 10 archivos originales de las dos corridas congeladas de GitHub. Valida símbolos, SHA del software de captura y account fingerprint; el raw debe abarcar 730+ días y no traer barras M15 duplicadas o fuera de orden (validaciones del loader existente).
2. Reconstruye exactamente las barras M15 de los dos source-days 17NY→17NY, sin interpolación, y recalcula sus conteos, SHA-256 por barra, OHLC y horarios. El `bias_feature_cutoff` debe coincidir con el cierre source-day que **ya había ocurrido** al decidir.
3. Calcula el lado de bias desde OHLC directamente en código B, sin invocar el `resolve_bias` del productor de A, y compara con el bias-side de la prueba y del CandidateEvent.
4. Reconstruye C1/C2 desde la serie de barras M15 raw y verifica sus dos SHA256; verifica que confirmación CISD/PS pertenece a un cierre M15 físico en C2. C1/C2 y PS no pueden usar velas posteriores al decision_at.
5. Recalcula **desde el payload original** `evidence_sha256`, `source_lineage_sha256`, snapshot `event_fingerprint`, la relación `event_id` y `source_event_id` estable, construido con mercado, método, perfil, lado, escenario, anchor y origen del opposing-series. Ningún hash de A es aceptado solo porque tenga 64 caracteres.
6. Verifica que los 488 IDs de evento fuente son únicos por mercado, que los conflictos de un día NY se excluyen de modo consistente, que A no falsea autorización LIVE, memoria completa, firmas, PnL ni fills.
7. Llama al auditor B `inspect_architect_a_candidate()` con cada **envelope real**. Exige exactamente:
   - `A_B:COGNITIVE_FEATURE_PROVENANCE_INCOMPLETE`
   - `A_B:CONTRACT_NOT_JOINTLY_FROZEN`
   
   No se admite el bloqueo antiguo de bias temporal (este caso B01 A lo resolvió con M15). **Pero no se autoriza ningún EXECUTE ni se construye una `Vt08FiveMarketResearchSituation` con datos inventados.**

## 4. Cómo repercute en el mandato de 100% cognitiva

Se cierra de forma reproducible **la prueba independiente de origen y as-of de los 488 B01** en desarrollo consumido. Ahora sabemos que el bloqueo de bias histórico de este bundle se puede retirar legítimamente **solo para esos eventos**, sin extrapolar a C2 intracycle/C3 ni mercado live. No prueba fidelidad total a autor TTrades, edge económico o cobertura completa cognitiva.

Los bloqueos P0 aún abiertos son concretos:

- **Fuente metodológica del resto de Situation:** A debe emitir valores **y timestamps de su origen** para `bias_state`, `poi_state`, `protected_swing_state`, `cisd_state`, `displacement_state`, `entry_state`, `liquidity_state`, `range_state`, `volatility_state`, `structural_destination_state`, `exhaustion_state`, `risk_geometry_state`, `journey_stage`, contradicciones, supporting_evidence, etc. B no puede fabricar toda la estructura a partir de OHLC/H4+bias sin fuente.
- **A/B freezing:** aún no hay joint manifest firmado de fuente/atributos/temporalidad, por lo que el verificador B continúa devolviendo 0 cognitive-ready por seguridad.
- **Admisión vs fill:** separado por código B anterior (`EXECUTE→record_fill→evaluate_position`). Aquí 0 fills porque este es un censo **de candidato**, no replay económico. Faltan fills reales del simulador de ejecución causal y su reconciliación con DecisionTrace/FillTrace/PositionTrace.
- **Memorias:** perfiles CIBO Market Memory / Trader Experience cinco mercados siguen `UNKNOWN_NOT_BOUND`, sin extrapolar experiencias del runtime existente; no hay permiso para self-training con resultados futuros.
- **Certificación económica:** no PF/DD cognitive-on ni 100% coverage real hasta consumir source candidates con todos los componentes en orden, barras intratrade, stop/TP/Fill, comisiones BID/ASK y coste causal. La variante C2 intracycle 1514 OHLC NO se rescata por replay cognitivo retrospectivo.

## 5. Siguiente contrato operativo A→B

A proporciona un `CognitiveSourceSnapshot` estructural, prueba de as-of para cada atributo, `source_event_id` estable + `event_fingerprint` mutable, y `SourceComplete` por familia; inicialmente solo B01 positional M15 después de aprobar manifest. B valida los atributos **contra sus barras y evidencias**, luego pasa `evaluate_cognitive_hypothesis`, registra solo fills del simulador causal, y evalúa posiciones una vez confirmado `record_fill`. Todos los candidatos, WAIT/ABSTAIN y pérdidas quedan en denominador; prohibido postseleccionar ganadores.

El único resultado medido ahora: **488/488 source-lineage verified, 0 source→cognitive EXECUTE, 0 fills, 0 PnL**. Eso no es una derrota económica ni una señal de que cognitiva esté bloqueando operaciones source válidas: el contrato completo todavía no existe. Mantener research-only/no live y no abrir sealed 7Y.
