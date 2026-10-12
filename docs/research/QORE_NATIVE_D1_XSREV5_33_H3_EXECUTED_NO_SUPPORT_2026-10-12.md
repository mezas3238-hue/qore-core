# QORE Native — H3 CROSS-SECTIONAL REVERSAL 5D ×33: EJECUCIÓN REAL Y VEREDICTO NEGATIVO

**12 octubre 2026 — resultado efectivamente ejecutado DESPUÉS de congelar el preregistro.**

## Evidencias inmutables

- [Preregistro previo a resultados](QORE_NATIVE_D1_XSREV5_33_SINGLE_H3_PREREG_2026-10-12.md), commit `27918037de29d62f75044b337bc2488079c0a639`.
- [PR H3 #882](https://github.com/mezas3238-hue/qore-core/pull/882) DRAFT investigación, rama `research/qore-native-d1-xsrev5-33-one-test-20261012`.
- [GitHub Actions run #38320043103](https://github.com/mezas3238-hue/qore-core/actions/runs/38320043103) **COMPLETED SUCCESS 2/2**; job `synthetic_causal_regression` **12/12 tests PASS** y `one_signed_economic_panel` SUCCESS. HEAD económico ejecutado **`860256ed2ec1c0d5ca2e7a52521b5b242b117aa0`**; NO confundir con commits documentales posteriores.
- **33/33 instrumentos** restaurados desde runs originales Atlas DEMO doce #35166210458 e IC Markets DEMO nuevos veintiuno #38193802541. Verificado manifiesto y RAW SHA256 de 11 particiones fuente por símbolo. Cero nuevos datos broker.
- [Artefacto Actions #11778212572](https://github.com/mezas3238-hue/qore-core/actions/runs/38320043103/artifacts/11778212572) incluye reporte JSON por símbolo, manifiesto de SHA y commit exacto, sin datos crudos M5 ni precios. SHA256 ZIP artifact **`f543e1e5838f785ce7d3dc9c16bff64e4ca6b073482e337089205a2cea593b5f`**, expira el **2026-11-11T23:07:14Z**; NO confundir con vault permanente.

## Hipótesis H3 congelada (NO versión ajustada al PnL)

Investigación inspirada en **Lehmann (1990), Fads, Martingales and Market Efficiency**, referencia académica a reversión semanal de **acciones**, NO documento que demuestre que funciona con FX/CFDs. Reuso único del lector de precios G0 SHA original, no de resultados H1/H2. Por cada fecha común de 33 símbolos, ranking por retorno últimos cinco cierres completos `close[j−1]/close[j−6]−1`; **LONG seis perdedores, SHORT seis ganadores**, pesos `+1/12` y `−1/12`; 21 activos sin posición, gross1 net0. Mantenimiento exactamente cinco fechas comunes, cambio de cartera cada quinto día elegible. Proxy de apertura M5 diaria >=00:10 UTC posterior al último cierre previo + margen; coste **1 bp por lado de peso nocional transado** incluyendo liquidación al cierre de cada tramo. Nada de volatilidad scaling, seleccionar mercados, tuning del hold o menor coste.

**Universo = 28 FX, 3 índices, 2 metales**, no 33 acciones como Lehmann. **Fechas comunes simultáneas M5** `2068` del 2016-09-19 al 2024-09-16; unión de fechas 2084; excluidas por ausencia de cobertura en al menos un activo `16`. No imputación. Sello económico HOLDOUT **2024-09-17+ intacto**.

## Resultado económico realmente observado

| Métrica | DEV 2016-2021 | DIAG 2022-2024-09-16 |
|---|---:|---:|
| Sharpe anualizado diario (Rf0, 252) | **+0.24788008718946142** | **−0.5070560377370273** |
| Retorno geométrico anualizado (252) | **+0.013747611223048128** (+1,3748%) | **−0.03466550165922622** (−3,4666%) |
| Drawdown máximo | **−0.08669519470747278** (−8,6695%) | **−0.11913451374722484** (−11,9135%) |
| Rebalanceos de cartera 6L+6S | **272** | **141** |
| Coste total supuesto, bp de NAV inicial SIN capitalizar | **434.0000000000002 bp** | **219.83333333333348 bp** |
| Correlación diaria con SP500 CFD (NO SPX) | **+0.04676374409476837** | **+0.2105020232554599** |

**Resultado bajo criterio H3 preregistrado:** `NO_POSITIVE_SUPPORT` porque Sharpe DIAG **−0.507 < 0**. El resultado DEV positivo no replica en DIAG y no alcanza ni el umbral 0.5 por sí mismo. **No promover H3**, no abrir holdout 2024–2026, ni corregir el signo, elegir mercados, cambiar ventana 3/10d, volatilidad, quintiles o costes para forzar Sharpe positivo. Ninguna lectura de PnL bruto del tramo embargado.

### Control contra extrapolaciones indebidas

- El resultado **NO refuta** reversión semanal de acciones de Lehmann; esta muestra no contiene 33 acciones ni 58 futuros multiasset del paper MOP. Los 28 FX en 33 activos son dependientes y retornos de cruces también tienen convenciones de base/quote; efecto de factor dólar/moneda común no corregido.
- Este es **H3** después de observar H1 TSMOM20 DIAG Sharpe −0.272 y H2 TSMOM252 DIAG +0.077; DIAG 2022–2024 ya utilizado por investigación anterior, **no holdout independiente**. Ningún Sharpe positivo de DEV/DIAG cuenta como certificación.
- Coste de 1bp/side es hipotético/favorable; financiación/carry FX, swaps, comisiones y slippage no están incluidos; `OPEN` histórico M5 no es ejecución atestada BID/ASK. Omitir costos de financiación podría empeorar resultados.
- **Limitación causal explícita:** el calendario de fechas admisibles se obtiene ex post desde jornadas completas con umbral de >=12 barras M5 en el lector G0 previo. Disponibilidad al abrir ese día no totalmente acreditada; un selector de sesión así podría conocer al final del día qué días sobreviven. Por tanto, aun con Sharpe favorable exigiría reconstrucción decisional causal antes de certificar. **No se realizó segunda ejecución para corregir/selectivamente mejorar resultado tras ver PnL**.
- La correlación con SP500 CFD no reemplaza SPX cash; exposición gross neutral no garantiza neutralidad factor o costes de borrow. El reporte deja net broker=False, traders certificados=0, LIVE=False.

## Decisión de investigación y continuidad

1. **TSMOM20 H1:** DIAG Sharpe −0.272; `NO_POSITIVE_SUPPORT`.
2. **TSMOM252 VOL20 H2:** DIAG +0.077; `WEAK_EXPLORATORY_ONLY`, no certificado.
3. **Cross-sectional reversal 5D H3:** DIAG Sharpe −0.507; `NO_POSITIVE_SUPPORT`.

Tres pruebas económicas concretas, ninguna robusta ni certificada. No hacer cuarta variante extra por optimización post-hoc. El objetivo general **3 traders originales QORE** permanece, pero actualmente **0/3**, broker NET no medido. Línea M5 de reconstruir 373.611 operaciones E1 no priorizada para mejorar scores negativos. **P0 #837** custodia de artefactos sigue urgente y debe abordarse independientemente del resultado económico (fuentes originales vencen en dic/ene). No alterar producción, MT5, VPS, CIBO, Shared, QDLE, LIVE ni E1.

**Síntesis ejecutiva:** Se investigó exactamente la alternativa propuesta y no se sostuvo en el diagnóstico, bajo el modelo de costos acordado; trabajo probado, fuente verificable, holdout protegido y decisión sin reoptimización.
