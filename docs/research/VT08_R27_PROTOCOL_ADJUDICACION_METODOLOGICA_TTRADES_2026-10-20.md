# VT08 R27 — Protocolo de adjudicación metodológica TTrades, antes de cognitiva

Fecha: 2026-10-20. Alcance exclusivo: VT08 M30 bullish C2 sweep de C1.low → confirmación M3 → C3.open posicional. Documento metodológico; no certificación ni órdenes. Se apoya en dictamen R17 y handoff maestro A+B, sin modificar sus hechos.

## Orden causal obligatorio

1. **Congelar situación**: mercado, source SHA y bar IDs, C1/C2/C3, relojes de apertura/cierre, y límite `as_of`. El adjudicador no ve PnL, MFE/MAE ni futuro.
2. **Swing relevante**: registrar *todos* los candidatos HTF visibles al momento, distinguir pivote confirmado de ventana fractal de tres velas incluyendo la actual; para cada uno registrar extremos, separación contextual y motivo. La fuente define pivote, pero no una fórmula universal para escoger entre varios. Si el desempate requiere regla inventada, `D/WAIT`.
3. **POI**: inventariar FVG y highs/lows pertinentes *antes* del CISD, con zona, primer contacto, timeframe, ID y `available_at`. Separar `exists`, `reacted` y `selected`. La jerarquía de continuación no se importa automáticamente a reversión C2. Dos POI plausibles sin desempate fundamentado → `D/WAIT`.
4. **Protected Swing**: enlazar POI seleccionado → extremo generado → secuencia exacta de velas opuestas → cierre que supera la apertura/umbral correspondiente, con IDs y disponibilidad. Barrido aislado o wick no certifica PS. Si varias series causales son plausibles, mantener todas y `D/WAIT`.
5. **CISD y reloj**: confirmar cierre, no wick, sobre la serie opuesta causal. Si la barra M3 confirma justo al cierre de C2, está disponible en C3.open, nunca antes. Cualidades V/displacement se anotan descriptivamente; no imponer ATR/pips ficticios.
6. **EQ condicional**: con swing seleccionado y dirección definida, aplicar fórmula específica del artículo EQ; sin selección de swing, solo escenarios condicionales, sin EQ operativo.
7. **Breaker/stop/target**: exigir IDs de secuencia breaker cuando el ejemplo concreto lo requiere; invalidación por PS y restricciones específicas del ejemplo no se mezclan como universal. Target high previo, untouched a C3.open; múltiples targets → `D/WAIT` salvo criterio auténtico.
8. **Decisión**: `SOURCE_COMPLETE` solo cuando cada dependencia obligatoria tenga evidencia primaria, recibo físico y reloj causal. Si falta un selector: `WAIT/ABSTAIN`. Nunca promover geometría R14/R25/R26 a autoridad TTrades.

## Ficha de adjudicación por caso (campos obligatorios)

`case_id_sha256, market, frozen_source_sha256, decision_as_of_utc, c1_bar_id, c2_bar_id, c3_open_utc, reference_swing_candidates[], selected_swing_id|null, swing_selection_source_section|null, poi_candidates[], selected_poi_id|null, poi_selection_source_section|null, opposing_series_bar_ids[], cisd_close_bar_id|null, protected_swing_extreme_bar_id|null, eq_formula_branch|null, breaker_source_ids[], stop_invalidating_structure_ids[], untouched_target_ids[], unresolved_disagreements[], A_reviewer_identity|null, A_signed_evidence|null, B_reviewer_identity|null, B_signed_evidence|null, verdict`.

Cada candidato lleva `source_bar_id, timeframe, available_at_utc, primary_author_url, author_section, reviewer_reason`. Los dos revisores deben ser personas realmente independientes; la ausencia de firmas no se suple con código ni con un agente que se firma a sí mismo.

## Tres expedientes de prioridad, ya identificados en el handoff

- **Múltiples POI**: 17 casos con intersección FVG bullish H1 pre-CISD y NY DTD low barrido. Resolver cuál POI causó la reacción sin elegir por éxito posterior.
- **Contacto intrabar ambiguo**: cuatro casos con primer toque FVG en la M3 confirmadora; orden tick desconocido → no afirmar precedencia sin evidencia.
- **Múltiples objetivos**: 2.437 casos con varios highs H1 candidatos; no elegir el que dio mejor PnL.

La muestra ciega R19 de 107 expedientes se conserva intacta; la revisión es source-only y los desacuerdos se documentan, no se borran. Las 2.657 geometrías son denominador físico, no operaciones.

## Gate metodológico (no económico)

`G_MET_PASS` exige identidad de familia, trazabilidad fuente primaria por cada regla obligatoria, selector contextual adjudicado, secuencia causal comprobada, relojes as-of correctos y revisión A/B auténtica sin disensos P0 abiertos. De otro modo `G_MET_BLOCKED`. `G_COG` solo después, con 27 campos causales de Situation real y decisión explicable. Gates económicos después de ambos, nunca para reescribir metodología.

Fuentes primarias: https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/ ; https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/ ; https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/ ; https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/ ; https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ ; https://ttrades.com/positional-entries-enter-before-the-expansion/ .

**Veredicto a publicación:** `VT08_NOT_CERTIFIED`, `G_MET_BLOCKED`, `G_COG_BLOCKED`; ninguna firma A/B inventada, ningún LIVE/DEMO/VPS, sizing, merge o holdout abierto.
