# QORE-alpha v1 — Auditoría P0 de congelación y BLOQUEOS REALES a walk-forward 96×3

**2026-10-11.** Issue decisorio #798, PR research draft #797, rama `research/qore-alpha-96-frozen-20261011`. QORE-alpha es sistema QORE original **inspirado** en M30 sweeps / M3 CISD+PS, NO simulación fiel del autor TTrades; la misión fuente-autenticación VT08 #787 queda SUPERSEDED para nuevas pruebas. NO VPS, no LIVE y 7Y holdout sellado.

## 1. Manifiesto 96 — CONGELADO ANTES DE nuevo PnL

[PRERREGISTRO](QORE_ALPHA_V1_96_FEATURE_SPACE_AND_STOP_RULE_PREREG_2026-10-11.md) commit **`ff1ede625180d3c1a06fc36d5964762df42b36bc`** (antes de generar manifest / leer fuentes). Código puro `src/qore/infrastructure/trader_lab/qore_alpha_v1_frozen_96_decision_contract.py`, tests `tests/infrastructure/trader_lab/test_qore_alpha_v1_frozen_96_decision_contract.py`.

**96 EXACTAS** = positional C3 / limit CISD (2) × Asia/London/NY (3) × PS/EQ_M30/BREAKER/ATR_X1 (4) × 1R/2R/3R/external (4). IDs `QALPHA-V001`.. `QALPHA-V096`, sin 97ª; semántica sesión y stop descrita en prereg, UTC→NY DST, una madre por mercado/día por variante, wick+dual no introducir, RR/POI no seleccionar posthoc.

**Fuente reproducible:** [GitHub Actions #38170504936](https://github.com/mezas3238-hue/qore-core/actions/runs/38170504936) **SUCCESS 6/6** (1 manifest+unit tests, 5 mercados datos M3/M15), exact HEAD tested `27ba4bab25ee7fec457c103482b4627100be3be0`. Ruff verde, **14 tests adversariales PASS** sobre conteo 96, leak de segmento, threshold estrictos, 3+ candidatos review, 1 solo winner, ausencia datos/cost bloqueo.
- **SHA256 del contenido del manifiesto (hash stable calculado por código)**: `4332e07f4a8fbdf1125ecd004a70c4216b8ea1a60e954847eedfe3b362184891`.
- Artifact manifest id `11713633331`, zip SHA256 `b80da0eb268a16e57dff4667b8a76d2a455c127ca61102f18e1adc778cb194c2`, 90d.
- Scripts CI de source no consultaron PnL ni Ejecutaron 96 backtests.

## 2. FALLO material dataset — train 2022 AUSENTE en TODOS los cinco pares

El dataset original M3 cTrader DEMO y fuente de cruces M15 (Actions 2026-Sep #35941643396 y #35934924907) fue verificado en los cinco mercados. **M3 inicial NY: 2023-09-24T19:45:00-04:00, final NY: 2026-09-23T19:42:00-04:00, idéntico para 5 pares; M15 comienza 2023-09-24T23:45:00Z.** No existe en los archivos fuente consumidos nada anterior a esa fecha.

| Mercado | Primer M3 NY | Último M3 NY | Meses sin M3 en periodo 2022-01→2026-06 | Bloqueo |
|---|---|---|---:|---|
| EURJPY | 2023-09-24 19:45 EDT | 2026-09-23 19:42 EDT | 20 | DATA_COVERAGE |
| USDCHF | igual | igual | 20 | DATA_COVERAGE |
| NZDUSD | igual | igual | 20 | DATA_COVERAGE |
| CADJPY | igual | igual | 20 | DATA_COVERAGE |
| USDCAD | igual | igual | 20 | DATA_COVERAGE |

Los meses sin M3 incluyen **2022-01..2023-08** (20 completos) y tramo parcial septiembre 2023; el TRAIN solicitado `2022-01-01<=date<2024-07-01` no se puede reconstruir desde source 1095d. Validate `2024-07-01…2025-06-30` y Test `2025-07-01…2026-06-30` están cubiertos **en fechas solamente**; no se ha certificado integridad tick/spread/fee ni ausencia de huecos intra-session en esos segmentos. Se prohíbe mover el split hacia 2023 o reducir muestra para producir PF.

**Artifacts M3/M15 de cobertura GH run #38170504936**:
- EURJPY `11714206859` digest sha256 `24c6e756b2494926927eb6ed83835349dfba1c1658cef17ae27c587362f052b2`
- USDCHF `11713712161` sha256 `c628d86ec18eda71639d5c80415b3ee0b6a3de3a50eecba2f4896d8b6686e038`
- NZDUSD `11713308655` sha256 `9e613d0334b76822a056015d00a9d6b03bd3441984fff13f809d7cae386ca178`
- CADJPY `11713587157` sha256 `80effe29f490829be0bc48352b89115ff86ac62838b67dae40e2191d2ab591c0`
- USDCAD `11713237648` sha256 `aa95b0773fee28d01553c235e0f35a403b8c101de537172618e925659fa527a8`

## 3. Intento real de 2022 histórico cTrader vía GitHub (DEMO read-only) — NO PUDO AUTENTICAR

Para no especular si el broker conserva enero 2022, se implementó `.github/workflows/qore-alpha-2022-demo-m3-feasibility-probe-v1.yml`: consulta exacta 2022-01-03..10 por par, solamente DEMO, mismo adaptador cTrader OpenAPI, sin operaciones ni PnL.

**[GitHub Actions #38170626976](https://github.com/mezas3238-hue/qore-core/actions/runs/38170626976)**: FALLÓ por autorización externa:
- Varios mercados: `CTraderDemoAccountDiscoveryError: cTrader access token invalid and refresh failed`.
- NZDUSD consiguió resolver paso discovery pero `CTraderDemoLabProbeError: cTrader DEMO authentication failed: CTraderOpenApiProtocolError`.
- **IMPORTANTE:** esto NO demuestra que cTrader NO tenga datos 2022. **Ni un dato 2022 fue validado**. Se requiere rotación/reautorización legítima de credenciales DEMO GH secretos QORE_CTRADER_* por Owner, o proveedor alternativo con M3 y M15 íntegros desde 2022 y gastos de ejecución BID/ASK. No introducir credenciales en Markdown/PR/logs ni intentar modo LIVE.

## 4. Criterios de decisión — NO CAMBIADOS tras ver hueco de datos

- Train 2022-01..2024-06: PF bruto >1,40, min50 fills.
- Validate 2024-07..2025-06: PF bruto >1,30, min25 fills.
- Ambos: DD equity <20% asumiendo riesgo 0,1% y win rate train/validate diferencia ≤0,15 absoluto.
- Si 0 variantes pasan ⇒ parar este feature set; si 3+ ⇒ revisar split/overlap antes del test. Elegir exactamente una por VALIDATE PF máximo (desempate ID), solo esa al interno 2025-07..2026-06; PF bruto <1,20 ⇒ reject.
- Supera test ⇒ 3 meses paper prospectivo, PF net>1,20; luego autorización LIVE separada inicial 0,1%. Nada de VPS al detectar meros prototipos.
- `PF train >1.40` **no constituye per se Bonferroni**, alfa FWER 0.05 /96=0.0005208333 por contraste. Mantener threshold PF del Owner pero no afirmar significancia múltiple sin p-values.
- **NO stage metrics calculadas** por este nuevo QORE-alpha manifiesto; NO-GO prototipo viejo VT08 no se atribuye a las 96.

## 5. Estado y desbloqueo mínimo

**Estado real: `BLOCKED_DATA_COVERAGE_AND_BROKER_AUTH`**. No ha ocurrido el walk-forward 96×3; no se puede asegurar respuesta positiva/negativa ni un calendario de 2 semanas sin recuperar credenciales/datos y fees. No se puede decidir GO/NO-GO porque no hay estudio nuevo válido; tampoco es evidencia de que el feature set sea perdedor.

**Desbloqueos:** (1) restaurar acceso a fuente DEMO o fuentes alternativas autorizadas; (2) reconstruir y atestar M3/M15 desde inicios enero 2022 para los 5 pares, sin interpolación de velas; (3) obtener tick BID/ASK, spread, comisión, slippage prescritos para regla realista; (4) implementar/ejecutar 96 variantes exactamente según manifiesto, train+validate primero, elegir una, luego **un test interno**, sin tocar 7Y holdout. No añadir ni modificar opción/filtro después de mirar resultados.
