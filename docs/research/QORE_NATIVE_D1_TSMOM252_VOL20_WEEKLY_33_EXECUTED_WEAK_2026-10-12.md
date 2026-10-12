# QORE Native — TSMOM252 vol-scaled semanal: RESULTADO DE UNA ÚNICA PRUEBA ECONÓMICA

**12 octubre 2026 · Ejecución real, no promesa de trabajo futuro.**

- [Preregistro ANTERIOR a retorno](QORE_NATIVE_D1_TSMOM252_VOL20_WEEKLY_33_PREREG_2026-10-12.md).
- [PR de investigación #880](https://github.com/mezas3238-hue/qore-core/pull/880). Relacionada con el ensayo negativo TSMOM20 [PR #877](https://github.com/mezas3238-hue/qore-core/pull/877).
- **[GitHub Actions #38318426853](https://github.com/mezas3238-hue/qore-core/actions/runs/38318426853) COMPLETED / SUCCESS, ambos jobs 2/2:** pruebas sintéticas 10/10, 33/33 ZIP originales revalidados con SHA RAW de once particiones y cálculo económico después de pasar tests. **Commit exacto ejecutado**: `eea8c9f02b721bb451695836beb4842ea22ab794`.
- [Artefacto GitHub #11777579571](https://github.com/mezas3238-hue/qore-core/actions/runs/38318426853/artifacts/11777579571), ZIP `sha256:faa601e689881ec1dbbf64346c8de415420880c3a1873342ccbb3daf117494f6`; expira **2026-11-11T22:50:17Z**. Temporal, no vault.

## Especificación congelada sin modificaciones en los outcomes

33 activos originales G0 M5 en FX/índices/metales, sin seleccionar. Son **28 FX, 3 índices, 2 metales**. Señal `sign(C[t-1]/C[t-253]−1)` con 252 sesiones de retorno; exposición `sign × min(3, 0.10/(sqrt(252) × std_20_close_returns))` con 20 retornos diarios completados. Primer día con precio válido de cada semana ISO, mantiene notional hasta próxima semana, sin rebalanceo diario. Ingreso proxy al siguiente M5 abierto >= 00:10 UTC después del cierre previo + 5min. Comisiones supuestas **1 bp por lado de notional** incluso liquidación, exposición fija 1/33 por instrumento; no coste carry, swap, apalancamiento marginal, spreads BID/ASK o slippage real. No utilizar precios ni outcomes desde **2024-09-17**.

## Resultado confirmado por la salida literal del job original

| Medida | DEV 2016-09-17 → 2021-12-31 | DIAG 2022-01-01 → 2024-09-16 |
|---|---:|---:|
| Sharpe diario anualizado, Rf=0 | **-0.05084215024563726** | **+0.0766923203611419** |
| Retorno geométrico anualizado, 252 | **-0.002601044564636279** (−0,2601%) | **+0.0022407295825932483** (+0,2241%) |
| Drawdown máximo (NAV) | **-0.06976509207458148** (−6,9765%) | **-0.05899066259229946** (−5,8991%) |
| Correlación con SP500 CFD (NO SPX cash) | **-0.02596905515755142** | **-0.1343486074523972** |
| Rebalanceos instrumentales | **7.423** | **4.653** |

**Veredicto científico preregistrado: `WEAK_EXPLORATORY_ONLY`** porque `0 < Sharpe_DIAG=0.0767 <= 0.5`. El rendimiento del periodo DEV fue negativo. No afirmar réplica independiente, edge robusto, beneficio NET real ni certificación del trader. No ajustar 252d, 20d, target 10%, leverage cap3 ni costes para superar 0.5. Reportar el fracaso de umbral incluso si el signo DIAG es ligeramente positivo. TSMOM20 DIAG Sharpe −0.272 se conserva; ambos resultados no son muestras económicas independientes, comparten mercado/periodo.

**No se puede atribuir la debilidad solamente al universo FX.** Hipótesis alternativas: exposición 28/33 FX, falta de futuros de deuda y commodities, proxy precio spot/CFD en lugar de retornos excedentes de futuros/forwards con carry y funding, sesgos de sesión UTC, periodo disponible, costes efectivos y selección adaptativa de la segunda hipótesis después de conocer la primera. No adjudicar el causante sin otra identificación científica; tampoco afirmar que la literatura de TSMOM fue refutada.

## Pendientes y decisión operativa

1. Línea TSMOM252 **no promovida** por criterio científico; Sharpe positivo de 0.077 no equivale a certificación. **0/3 traders QORE Native certificados**.
2. El próximo paso no es retunear modelos ya vistos: o ampliar la capacidad de investigar futures/forwards diversificados con identidad y licencia distintas (requiere justificar un nuevo universo sin sesgo retrospectivo), o fijar una hipótesis causal genuinamente distinta con un periodo OOS independiente antes de leer resultados.
3. Mantener custodia #837 (artefactos vencen), homogenización #857, BID/ASK cero #856 y testigos #863 como impedimentos a cualquier calificación NET, sin dedicarse a reconstruir cientos de miles de ejecuciones de un edge ya no soportado.
4. El holdout histórico **2024-09-17 a 2026-09-17 continúa sellado**. Se verificaron SHA de los archivos, pero ningún retorno económico de ese tramo fue leído para este experimento. Toda línea sigue DRAFT y **VPS, MT5, LIVE, CIBO, Shared, QDLE y producción intactos**.

Este hallazgo muestra la distinción entre validar un algoritmo para evaluar hipótesis y demostrar una ventaja económica realizable. Aquí lo primero pasó y lo segundo todavía no.
