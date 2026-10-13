# QORE Native H5 — FX carry por diferencial de políticas: TEST ÚNICO REAL, sin soporte SPOT; carry teórico no certificado

**Ejecución real concluida después del preregistro, 12–13 octubre de 2026 UTC.** NO es un análisis pendiente. No introducir optimizaciones retrospectivas de señal, lag, composición ni costes.

## Referencias exactas e inmutabilidad de decisión

- [PR H5 #887](https://github.com/mezas3238-hue/qore-core/pull/887), DRAFT research, sin merge a producción.
- [Preregistro previo a resultados](QORE_NATIVE_H5_POLICY8_RATE_DIFFERENTIAL_FX28_ONE_TEST_PREREG_2026-10-12.md), commit **`4da9ea8ba42ddaef808d14b9097235a7eb45b12d`**, tasa política BIS, FX 28, 6 long/6 short, reequilibrio mensual, coste **2 bp por lado** sobre cambio absoluto del nocional, lookback tasa **m−2**. El prereg se congeló antes de cualquier PnL H5.
- [Enmienda de elegibilidad de FUENTE antes de PnL](QORE_NATIVE_H5_POLICY8_BIS_JPY_SOURCE_ELIGIBILITY_PRE_ECON_AMENDMENT_2026-10-12.md), commit **`43ee7b0cd6875583be7a3cdfe3bad3baa524e6d2`**: la política japonesa mensual BIS inicia 2016-09 (96 observaciones a 2024-08); con m−2 no hay señal completa antes de **noviembre de 2016**, septiembre/octubre 2016 se quedan flat cash y continúan dentro de DEV. Las corridas previas habían FALLADO por cobertura, **antes de leer un PnL**.
- **[GitHub Actions #38324559982](https://github.com/mezas3238-hue/qore-core/actions/runs/38324559982) COMPLETED SUCCESS 2/2**, 10/10 pruebas sintéticas y job 28 FX económicos. **Código exacto evaluado: `a9d7dd50dfa3937c3de824372edef221cf8faf82`** (el documento enmienda commit posterior no modifica el código ejecutado).
- 28/28 fuentes G0 originales DEMO restauradas de artefactos existentes y verificadas con los SHA RAW de 11 particiones anuales; ocho tasas mensuales BIS `WS_CBPOL` AUD/AU, CAD/CA, CHF/CH, EUR/XM, GBP/GB, JPY/JP, NZD/NZ, USD/US, con **104/104 mensual salvo JPY 96/96 desde 2016-09**, mismos 2016–2024 límites. No hay cotización forward1M ni carry broker original acreditado.
- [Artefacto Actions #11780915492](https://github.com/mezas3238-hue/qore-core/actions/runs/38324559982/artifacts/11780915492), SHA256 ZIP **`1392e141dfe091058ad8e643a68f953bbae4a7dafc37091137c688c2d1853183`**, expira **2026-11-11 23:59:53Z**; temporal, no es custodia permanente. JSON con evidencia G0, IDs y hashes BIS y desglose de métricas, no guarda series de tasas RAW ni precios.

## Especificación ejecutada SIN cambio económico

**Universo fijo:** 28 pares FX correspondientes a ocho monedas, seis con mayor tasa BASE menos QUOTE long y seis con menor tasa base menos quote short; peso ±1/12, gross1 y nominal net0, no neutralidad por moneda ni correlación. Primer día válido del mes, fuente `BIS mensual de mes m−2` (dos meses completos atrás), retener notional hasta siguiente decisión; no reoptimizar, no cambiar por carry 3M, ni seleccionar activos por performance.

**Dos curvas económicas obligatoriamente SEPARADAS:**

- **A, spot-only tras 2bp lado:** `Σ_s weight_previous_s × (open_s(t)/open_s(t−1) − 1) − 0.0002 Σ_s|w_new−w_old|`; apertura M5 UTC de primera barra elegible >=00:10, serie 28 completa y calendario basado en completitud de las sesiones, marcado al día común siguiente. Es una señal de **apreciación spot bajo ranking carry** y la puerta de evaluación fijada en prereg, pero no mide excess carry.
- **B, spot + interés de política hipotético:** añade diariamente `Σ_s weight_previous_s × (policy_base−policy_quote)/100 × Δdías_calendario/365`; **este componente es un ingreso teórico**, no tasa de depósitos/borrow overnight negociables, no forward discount 1M, ni swap de IC Markets. El programa permite cuantificar sensibilidad al diferencial, no demostrar renta cobrable. No deducir de B "NET" o "edge real".

Los datos de policy publicados ahora 2026 NO están probados vintage/PIT para toda la historia aunque se aplique lag dos meses; el calendario completo M5 retrospectivo puede conocer a posteriori que un día tiene >=12 barras. No hay prueba de acceso/ejecución causal exacta, BID/ASK, slippage, swaps, comisiones, conversión o margin. Estudios H1/H2/H3 previos comparten ventanas, selección H5 adaptativa. **0/3 traders certificados** cualquiera que sea Sharpe H5.

## Resultado ECONÓMICO confirmado (salida directa del job, sin interpretación selectiva)

| Métrica | DEV 2016-09-17 a 2021-12-31 | DIAG 2022-01-01 a 2024-09-16 |
|---|---:|---:|
| **Sharpe A spot-only** | **−0.2845796431173876** | **−0.1750437437160499** |
| **CAGR A spot-only** | **−0.014877434817355262 (−1.487743%)** | **−0.009363541997615465 (−0.936354%)** |
| MaxDD A spot-only | −0.13702854156346767 (−13.702854%) | −0.08272788038612888 (−8.272788%) |
| Retorno acumulado A spot | −0.07880523178730614 | −0.02601207068264144 |
| **Sharpe B spot + policy carry IDEAL** | **−0.018086357569529463** | **+0.3134929897904274** |
| **CAGR B ideal** | **−0.002052203131126973 (−0.205220%)** | **+0.013833818262704467 (+1.383382%)** |
| MaxDD B ideal | −0.08902123515342564 (−8.902124%) | −0.06852998729395388 (−6.852999%) |
| Retorno acumulado B ideal | −0.01118676023095444 | +0.03924139626946577 |
| Rebalances cartera mensual | 62 | 33 |
| Cambios individuales de símbolo incluyendo liquidación final | 66 | 92 |
| Turnover total de lados de nocional, unidades NAV | 5.5 | 7.666666666666667 |
| Coste 2bp / lado acumulado SIN capitalizar, bp NAV inicial | **11.0 bp** | **15.333333333333337 bp** |
| Mayor exposición neta nominal a una moneda (no hedged) | 0.5833333333333333 | 0.5 |
| Días M5 comunes (28 instrumentos) | 1378 | 706 |
| Días calendarios hábiles usados con cash para ausencia | 1380 | 706 |

Preprueba clasifica **`NO_POSITIVE_SPOT_SUPPORT`** porque Sharpe spot DIAG -0.175 <0. Al mismo tiempo, el rendimiento idealizado B DIAG Sharpe +0.313 **NO cruza** 0.5, ni puede convertirse en atribución de carry económico sin demostrar financiación. **La distinción es sustancial**: H5 no demuestra que *carry FX real* sea inexistente; demuestra que **el componente spot** de esta cesta de diferenciales de política fue negativo con 2bp supuesto, y que una financiación ideal altera el signo en DIAG.

### Lectura metodológica del resultado combinado H1–H5

- H1 TSMOM20 DIAG Sharpe -0.272, sin soporte.
- H2 TSMOM252-vol20 DIAG +0.077, débil.
- H3 XS reversal5D DIAG -0.507, sin soporte.
- H4 forwards 1M carry autentico BLOQUEADO por fuente, nunca probado económicamente.
- **H5 policy proxy real de tasas** DIAG A SPOT -0.175 / B IDEALIZED +0.313, evidencia no promotable.
- Los anteriores no son **cuatro falsaciones independientes** de edges documentados: distintos mecanismos, mismo panel económico ya expuesto, sin PnL net broker ni universo canónico. El panel FX 28/33 correlacionado es limitación importante, pero que sea *causa única* no está identificado.
- Si se investiga siguiente sin infraestructura interminable, **decisión concreta y acotada:** la diferencia económica entre A y B exige **coste efectivo swap long/short histórico** (o genuine FX forward spot-forward) y una prueba independiente; de lo contrario detener la línea sin fingir un cuarto test. No ajustar tasas lag/sort para rescatar Sharpe.

**Holdout económico 2024-09-17+ sellado, no órdenes, ni producción, VPS, MT5, CIBO, Shared, QDLE, LIVE.** Resultados publicados por ambos signos sin tunear.
