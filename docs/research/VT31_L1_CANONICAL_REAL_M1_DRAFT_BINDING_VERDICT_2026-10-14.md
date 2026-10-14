# VT31 — CIERRE TÉCNICO DEL SUBGATE L1 CANONICAL RESEARCH BINDING · 14-OCT-2026

## Dictamen
**`IDENTITY_BOUND_TO_REAL_M1 / TRADER_LAB_DRAFT`**, NO `RESEARCH_READY`, NO `DEMO_ELIGIBLE`, NO trader/cognitiva/metodología certificada, NO LIVE. Tras PR #936 matriz L1–L10 y PR #937 paridad 1×/32× fuente, se ha eliminado un sub-bloqueo de **identidad técnico/reproducible del candidato**, NO se salta la doctrina pendiente ni OOS, Risk, CIBO, validación independiente.

## Evidencia reproducible de GitHub
- **Prereg antes de código** commit `f5db95eac6cd275add0ed8dafc814932f742b4b5`, [`VT31_L1_CANONICAL_RESEARCH_DRAFT_BINDING_PREREG_2026-10-14.md`](./VT31_L1_CANONICAL_RESEARCH_DRAFT_BINDING_PREREG_2026-10-14.md).
- **[PR #939 DRAFT](https://github.com/mezas3238-hue/qore-core/pull/939)** sobre #937, archivos exclusivos aditivos; no modifica G3 original ni Trader Lab nuclear.
- **[CI #38639109403 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38639109403)**, código/test SHA `cf273efaba6fe913e4438416db1267ecb2acda3c`, **247/247 pytest PASS**, Ruff/compile PASS, G3 COG/OPS/acta blobs SHA PASS, datasets M1 originales SHA PASS, todas negativas y candidatas de fixtures rechazadas/aceptadas de forma causal.
- **[Artefacto #11929462904](https://github.com/mezas3238-hue/qore-core/actions/runs/38639109403/artifacts/11929462904)**, ZIP SHA256 `602b0dbcfe392cb76bb37152f3228adcf3638c180eca66251e4fbed78e711131`. Incluye reporte JSON de vinculación auténtica, fixture/test logs, JUnit, hashes y scope.
- **Fuente**: artifact histórico #11459859004, 1.059.784 velas M1 NAS100, raw SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` verificado antes de abrir.
- **Selección preregistered**: primera fecha NY del corpus con 09h + 10h completas, **2023-10-02**, exactamente 120 velas M1 cerradas. Se usó sólo para construir dataset real *research-source*, jamás para alegar rentabilidad o medir un resultado económico.
- **SHA256 canónico de dataset derivado**: `adc6a06e87b75b9966a6ac41f1dc637703429935d4a1ffc9641f091da34e06e1`.
- **SHA256 `TraderLabCandidateBinding.fingerprint`**: `1710e3782c164eb9d648f64d7a301e74aab6220bdb24a451b252b4913309616f` en el SHA de ejecución y configuración indicados. Modificar trader version, code SHA o contenido OHLC invalida fingerprint/re-evaluación: probado con fixtures.
- **API oficial**: `OhlcSnapshot`→`ReplayMarketDataObservation(STRUCTURAL_BOUNDARY)`→`HistoricalOhlcReplayDataset`→`ResearchRunEvidence`→`ResearchStrategyConfigurationManifest`→`ResearchRunStrategyBinding`→`TraderLabCandidateBinding`→`start_trader_lab_lifecycle`→`evaluate_demo_eligibility`. No reemplaza la API de QORE ni usa ledger fingido.
- **Dictamen de `promotion.py` real**: `not_eligible_incomplete`, `lifecycle.state=draft`, `qualifications=()`. `STRUCTURAL_BOUNDARY` es **el cierre estructural del M1, no receipt-time del broker**; se registró así. `execution_model_id=None`, `transaction_cost_model_id=None`; 0 ACK/fills/lotajes/retornos.

## L1 — Lo logrado vs no logrado
### Logrado
1. El Trader Lab reconoce una versión real de investigación de VT31 por UUID, versión y fingerprint exactos, sustentada por los datos originales y el código M2/M3/M4/M5 actual.
2. Los parámetros de configuración incluyen explícitamente perfil TTrades NY AM 2025 **proxy QORE**, fuente original SHA, 10 puntos desde MSS, 9h/10h, C2 wick (referencia), FVG causal; contrato de broker `UNHOMOLOGATED`, método autor `UNVERIFIED`, rango de datos `CONSUMED_3Y_DEVELOPMENT_NO_OOS`.
3. 247 pruebas integran contratos canónicos Trader Lab y M1 VT31, con negativos de fuente mutilada, duplicación, variación de configuración/versión, hora DST y fuente futura.

### No logrado; bloqueo de **Gate L1 oficial**
1. TTrades autoral MSS/FVG/OB/Breaker vs formalizaciones QORE: falta interpretación verificable independiente; no `Methodology Freeze` que asegure fidelidad completa del autor.
2. **ResearchEvaluationFreezeEvidence** no emitida: el original 3Y ya fue examinado y no se falseó que se congelara antes de conocer resultados. Por eso NO se emitió `RESEARCH_READY`.
3. G3 acta/code originales necesitan dos identidades humanas distintas COG/OPS reales, [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897). El Owner puede aprobar revisión, no simular dos GitHub reviewers.
4. El ambiente fuente es NAS100 CFD OHLC, no contrato USTEC ejecutable oficialmente homologado; 30h quote-side USTEC histórico [PR #901](https://github.com/mezas3238-hue/qore-core/pull/901), homologación #857/#900 pendiente. Usar `STRUCTURAL_BOUNDARY` no miente sobre `received_at`.

## A continuación: qué hacer para superar todos los Gates
**L1** fijar metodología completa con prueba de fuentes TTrades/ICT per-profile, registrar estrategia exacta que incluya salida/expiración y verificación de independencia G3; evaluar qué segmentos de datos siguen verdaderamente sin utilizar, preregistrar *futura* evaluación legítima y crear evidencia `ResearchEvaluationFreezeEvidence` sólo cuando sea temporalmente justificable. La investigación ya no debe seleccionar un nuevo parámetro tras observar 128/119 casos.

**L2** replay integral incluyendo quotes exacto símbolo, broker stop/tick, eventos de entrada/ACK/fill, SL/TP/time-exit reales y costes, sin autorizar LIVE ni presuposiciones en los 61 contactos M1.

**L3** usar exactamente la versión y su investigación/playback para el `qualify_trader_lab_fast_forward` oficial. La paridad 92.280 eventos 1×/32× de #937 ya es evidencia auxiliar (NO certificado).

**L4–L7** OOS previamente intocado, stress, Monte Carlo preregistrado, cuantificar PF, Sharpe, Sortino, expectancy, DD con PnL realmente financiable. **Sin sizing propio del Trader**: CIBO/CMA/QDLE tienen autoridad; registrar riesgo en sus dominios gobernados.

**L8–L10** Risk, CIBO y auditor independiente emiten atestaciones externas vinculadas al mismo fingerprint; `DEMO_ELIGIBLE` no implica DEMO CERTIFIED ni LIVE.

## Integridad del resultado
`CI_GREEN=247` prueba implementación de identidad y negativas, **no certificación económica**. ZIP 90d de GitHub Actions requiere preservar continuidad antes de expiración; cualquier merge, LIVE, FundedNext LIVE, VPS, órdenes o nuevas credenciales siguen prohibidos. No reclamar progreso asincrónico; este documento recoge trabajo realmente ejecutado.
