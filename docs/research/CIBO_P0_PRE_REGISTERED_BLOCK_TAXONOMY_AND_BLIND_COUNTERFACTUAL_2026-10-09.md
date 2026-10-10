# CIBO P0 — Taxonomía vinculante, muestra ciega y contrafactual prerregistrado

> **OVERRIDE CEO P0 (2026-10-09): DOCUMENTO HISTÓRICO DE LA ARQUITECTURA SELECTOR / NO ES DIRECTIVA OPERATIVA.** El flujo válido es *Trader decide → CIBO recibe y administra todas las señales → QDLE determina factibilidad física*. Mantener este estudio para explicar por qué Native MAX bloqueó 3.357 señales; no ejecutar sus recomendaciones de aflojar/optimizar filtros ni usar su cohorte de 200 como programa prioritario. Directiva vigente: [CIBO P0 PARADIGM OVERRIDE](CIBO_P0_PARADIGM_OVERRIDE_2026-10-09_TRADER_EXECUTION_MANAGEMENT_QDLE.md).


**Estado:** investigación de selección, **NINGUNA modificación de umbrales**; no autorización LIVE, no nuevos retornos ATR calculados.  
**Dueño:** arquitecto integrador CIBO + comité económico QDLE.  
**Código:** `scripts/cibo_p0_rejection_taxonomy_audit.py`, tests `test_cibo_p0_rejection_taxonomy_audit.py`; workflow `cibo-p0-block-taxonomy-blind200.yml`.  
**Referencia:** PR #745 y reporte de replay [#37878805062](https://github.com/mezas3238-hue/qore-core/actions/runs/37878805062).  
**Datos inmutables:** 3.368 señales de 2019–2022, manifest GitHub artifact `11451743578` digest `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`, Native MAX `11588089131` digest `eebf6de43da63aadc200a3783109246188d46e0fcdd7da127f07eff815d6cec6`. **Fuente quemada de investigación, NO fresh OOS.**

## Diagnóstico basado en los recibos emitidos, no en nombres genéricos

La categoría `capital_disposition` es el **punto de salida**. La regla principal se asigna al **primer `return` que realmente ocurre** en `src/qore/infrastructure/cibo_sovereign_capital_runtime.py` (líneas 499–646), usando observaciones trazables de `function_sensors` y `cognitive_sensors`. Otros módulos pueden producir advertencias, pero no cuentan como causa primaria de bloqueo si su salida no gobierna ese `return`.

| Categoría primaria vinculante | Conteo | Evidencia | Interpretación falsable |
| --- | ---: | --- | --- |
| `COG_CF07_NONPOSITIVE_CAUSAL_NET_UTILITY` | **1629** | `CALIBRATION.note=nonpositive-causal-expected-net-utility` y `abstention_required=True` | La predicción predecisión, neta y condicionada, no recomienda invertir; verificar costes, madurez, calibración y calidad sin mirar PnL futuro |
| `COG_CF07_PROVISIONAL_FORECAST` | **140** | `CALIBRATION.note=walk-forward-provisional-forecast-history-required` | Estimador predecisión aún provisional; no bajar su madurez de forma oportunista |
| `COG_CF07_COLD_START` | **35** | `CALIBRATION.note=walk-forward-cold-start-history-required` | Sin pronóstico causal maduro; no sustituir hindsight |
| `CAP_REALIZED_PROFIT_INCREMENTAL_COMPOUND_NOT_ADMITTED` | **1549** | `CIBO_COMPOUND.realized_profit_source_requested=True`, `allow_incremental_compound=False`; precede Portfolio | Investigar restricción de fuente/apalancamiento económico vs política de cuenta $60; no tomar el beneficio de Bank o Cushion si no es fungible |
| `CAP_PORTFOLIO_MULTIPLIER_ZERO` | **3** | `COMPOUND_PORTFOLIO.multiplier=0` después de descartar las ramas anteriores | Portafolio no dispone/autoriza multiplicador, no imputar a QDLE |
| `CAP_GENC12_NEW_CAPITAL_PAUSED` | **1** | `CAPITAL_SCIENCE:GEN-C12.consumer_action=PAUSE_NEW_CAPITAL` | Crisis control activo; precede restricción de compounding |
| `RISK_REVIEW_READY` | **11** | `capital_disposition=RISK_REVIEW_READY`, `risk_decision=ALLOW|REDUCE`, volumen positivo | CIBO remitió al control de riesgo (9 reservas financiables en proxy posterior; 2 no financiables por presupuesto individual) |
| **Total** | **3368** | 1 decisión por `signal_fingerprint` | Sin duplicados, sin reasignaciones, sin tasas infladas |

**Otras puertas coexistentes**: `POSITION_COMPETITION`, `GEN-C5`, `GEN-C8`, `CMA_FINAL_PLAN`, `ADAPTIVE_LEVERAGE` y `CF07` pueden registrar `decision_gate_triggered`/avisos en una misma señal. No se suman como causas independientes. En particular `GEN-C8.blocker_codes=GENC5_CANONICAL_INPUT_UNAVAILABLE` se emite también en las **11 autorizaciones**: *no* clasificarlo erróneamente como el motivo de todos los rechazos. El clasificador expone esas razones como **secundarias** y falla si no reconoce la primaria.

**Interpretación de diseño:** las 1.629 denegaciones por expectativa neta pueden representar un filtro legítimo de convicción. Las 1.549 denegaciones por capital compuesto pueden representar protección real, fuente mal asignada o una calibración desalineada. El conteo por sí solo **no discrimina** intención vs desalineación vs bug. Congelar estos números como hipótesis, no como sentencia.

## Muestra ciega: 200 bloqueadas

1. Universos fijos disjuntos: `COGNITIVE_BLOCK=1804` y `CAPITAL_BLOCK=1553`.
2. Selección reproducible de **100 por clase** ordenando `sha256(seed|class|signal_fingerprint)`; semilla `qore-cibo-p0-2026-10-09-taxonomy-blind-v1`. Nunca seleccionar por `gross_structural_outcome_r`, signo de operación, PnL ni futuro.
3. Artefactos: `summary.json`, `decision-block-census-3368.csv`, `blind-sample-200.json` y SHA256 sellado de muestra. Compartir estas identidades antes de extraer PnL.
4. Describir tasa por instrumento, trader, régimen, periodo, clase y subcausa; los 100/100 no reproducen las proporciones del universo: **ponderar por estrato** al estimar resultados globales.
5. Validar indicadores `market_decision_at == Native.decided_at`; materializar mercado con barras cerradas antes de la decisión, spreads, ticks, SL original, fee all-in, temporalidad ATR y modo. Si falta cualquiera para un outcome: `UNIDENTIFIABLE_UNDER_AVAILABLE_EVIDENCE`.

## Contrafactual definido **antes** de ver los resultados

- **A — CIBO Native control:** 11 autorizadas, 9 financiables en sensibilidad QDLE; NAV proxy USD60→USD62.485388..., PF net proxy 1.56384, **DD cerrado 6.09664% (NO MTM)**. Sin MT5 fills.
- **B — 200 bloqueadas shadow, stops originales, CIBO lock:** hipótesis de financiamiento por cada señal bajo estado causal independiente, presupuesto `min(CIBO_candidate_budget, 5% × QORE_NAV)`, broker lots, fees, margin, Bank/Cushion segregadas; gate de riesgo sigue activo. Esta proyección no equivale a ejecutar todas las 200 simultáneamente.
- **C — 200 bloqueadas shadow, ATR14 por modo:** solo con `CausalATR14` real (Wilder, cierre predecisión, bar source/tick/broker), prueba de estructura, modelo de stop/TP y orden intrabar conservador. **No multiplicar simplemente el resultado Trader original por el nuevo SL**.
- **D — Cambio explícito de una regla como *ablation*: `CF07 expectation threshold` o `COMPOUND cash-source`, nunca las dos a la vez. Recomputar CIBO completo, QDLE y saldo secuencial; no añadir aprobación artificial con `ALLOW_ALL`.** El nuevo modelo debe seguir verificando sus propias razones económicas y permisos legítimos.

### «Señal que debería haber pasado» no significa «ganó después»

Elegible contrafactual `SHADOW_ADMISSIBLE` **solo cuando**: (i) datos predecisión auténticos; (ii) misma geometría/estructura causal; (iii) una regla experimental explícita, versionada y aislada cambiaría su voto, con expectativa neta calculable *ex ante*; (iv) no vulnera protección/no leakage ni fuentes Bank/Cushion; (v) QDLE puede proponer lote real dentro del 5% de NAV dinámico incluyendo OPEN+CLOSE, spread, buffers, margen y el mínimo broker. Resultado posterior es **evaluación**, nunca criterio para seleccionarla.

### Diagnóstico de intención, configuración y calibración

| Hipótesis | Prueba específica | Conclusión permitida |
| --- | --- | --- |
| Sniper legítimo | Historial de regla CF07, expectativa negativa real por costes y posterior desempeño OOS bloqueadas inferior | Mantener selectividad aun si frecuencia 0.33% |
| Umbrales desalineados | Simular misma regla con NAV USD60 vs fuente permitida y bróker, manteniendo invariantes; revisar gasto, source y unidades | Aislar problema de capital sin bajar calidad cognitiva |
| Config bug / default faltante | Inspección de parámetros efectivos y evidencias por señal; valores 0, None, missing vs políticas declaradas, y razón primaria real | Corregir únicamente contrato/valor defectuoso y repetir desde fuente |
| Diagnóstico ambiguo | Causal ATR o proveedor ausentes, pocas autorizadas, fuente quemada | `INCONCLUSIVE`, cero cambios a políticas |

## Criterios pre-registrados de avance (no reajustar tras mirar el resultado)

**Integridad obligatoria:** 3368/3368 IDs únicos, subcausa primaria conocida, 200 muestra blind hash, cero futuro al decidir, cero órdenes reales; sin ello `STOP`.

**Factibilidad:** informar fracción de propuestas elegibles a QDLE por símbolo y causa, riesgo máximo por entrada `<= 0.05 × NAV` y precio SL en ticks, sin fallback a 0.01; contar no ejecutables en el denominador. **Una tasa mayor de autorizaciones nunca es éxito por sí sola.**

**Rendimiento:** únicamente si existen caminos causales completos se informa PF *neto de todas las comisiones* y DD **intraoperación**; si falta mercado intrabar son `NOT_MEASURABLE`. Para considerar cambiar un filtro, exigir simultáneamente: i) mejora neta respecto al control **a igual presupuesto y datos**, ii) PF neto del candidato `> PF neto del control` en el periodo OOS, iii) DD MTM `<= 25%` como límite tolerable, objetivo `<=20%`, iv) saldo/riesgo/margen coherentes y ninguna infracción de restricciones duras, v) bootstrap temporal por bloques (p.ej. mes) con 1000 remuestreos y límite inferior unilateral de 95% del **incremento neto de PnL >0**. Sin muestra de al menos 100 liquidaciones shadow verificables **o** con muy pocas operaciones OOS, resultado `INCONCLUSIVE`, aunque mejore la media.

**No confundir evidencia:** la cohorte 2019–2022 ya fue consumida y **no certifica** ventajas OOS; los 11 trade receipts no permiten estimar calidad de selección con confianza. Dejar para una cohorte de evaluación realmente no usada un sello/commit previo de candidatos, límites y tests. Cualquier `ATR` que falta no se inventa ni se extrapola del SL original.

## Secuencia de implementación

1. Reproducir taxonomía y **sellar muestra ciega** en GitHub Actions (artefactos enlazados); reportar root reason por instrumento y módulo.
2. Auditar por qué `CF07` estima expectativa no positiva y por qué `CIBO_COMPOUND` exige beneficio realizado; inspeccionar procedencia de datos, relación con QORE NAV USD60, y distinguir hard gate de mera advertencia.
3. Construir adaptador de barras causal y reconstructor conservador de entrada/stop/TP; **antes no hay PF/DD shadow válidos**.
4. Ejecutar B/C en la muestra, separado de D, documentar razones por señal; **sin cambiar la política CIBO de producción**.
5. Ejecutar final replays con QDLE en el Trader Lab Fast solamente tras cumplir trazabilidad, con holdout OOS nuevo antes de reclamar mejoras certificadas.

**Autorización CEO a replay experimental:** válida para no bloquear experimentos por gates administrativos de certificación; nunca para borrar los límites financieros o llamar «real» a un fill supuesto.
