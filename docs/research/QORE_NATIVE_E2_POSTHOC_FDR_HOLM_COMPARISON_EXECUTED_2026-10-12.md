# QORE Native — Auditoría de sensibilidad de Holm frente a FDR-BH (POST HOC, sin precios nuevos)

**2026-10-12 — EJECUTADO en GitHub, 5/5 tests PASS.** Owner cuestionó la selectividad de Holm FWER 231 al 5%. Se probó exactamente la alternativa solicitada: Benjamini–Hochberg (BH), FDR del 5% y 10%, sobre **los mismos 231 p-valores** de **cada** período, **sin optimizar señales, no descargar OHLC, no nuevo backtest, no abrir 2024+**.

- Fuente económica original [Actions E2 #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836), [artifact original #11749739981](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836/artifacts/11749739981), `qore-native-e2-33x7-full-gross-results.json` **SHA256** `5161dbdf157805af3e37957ec25acad3657962a50c99d214883005cb03945f80`; código exacto `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`.
- Nueva auditoría [Actions #38260058465](https://github.com/mezas3238-hue/qore-core/actions/runs/38260058465) **SUCCESS**, 5/5 pytest y Ruff PASS, [artefacto de sensibilidad #11751248539](https://github.com/mezas3238-hue/qore-core/actions/runs/38260058465/artifacts/11751248539); revalida SHA original, identidad de 231 celdas, n, estado NO-NET e incluso que Holm se reproduce antes de ejecutar BH.
- Script: `src/qore/infrastructure/trader_lab/qore_native_e2_posthoc_bh_sensitivity_v1.py`, tests correspondientes. Estado `POSTHOC_EXPLORATORY_SENSITIVITY_NOT_PREREG_CONFIRMED`; esto es un **análisis de sensibilidad después de ver el test antiguo**, no una confirmación prospectiva.

## Resultados observados — MISMAS 231 hipótesis, no filtrar pérdidas

| Métrica sobre deltas pareadas brutas vs control | Desarrollo (2016–2022) | Diagnóstico temporal (2022–2024) |
|---|---:|---:|
| Universo exacto | 231/231 | 231/231 |
| P nominal bilateral <=0.05, **cualquier signo** | 8 | 8 |
| P nominal bilateral <=0.05, **ventaja Y retorno brutos positivos** | **5** | **2** |
| Holm FWER <=0.05, cualquier signo | **1** (negativo) | **0** |
| BH FDR <=0.05, cualquier signo | **1** (negativo) | **0** |
| BH FDR <=0.10, cualquier signo | **1** (negativo) | **0** |
| BH FDR <=0.10, delta positiva/gross positiva | **0** | **0** |
| **Misma celda** con delta/gross positivas y P nominal <=0.05 en AMBOS | **0 combinaciones** | **0 combinaciones** |
| **Misma celda** con delta/gross positivas y BH FDR <=0.10 en AMBOS | **0 combinaciones** | **0 combinaciones** |

**Un hallazgo corregido de signo NEGATIVO en development**: `OPEN_INITIAL_REACTION__XAUUSD`, delta bruta contra control **−1.708110 bps**, P bilateral original **0.00014999**, q BH **0.034648** y p Holm **0.034648**; diagnóstico delta **−0.314426 bps** p **0.63117**, no replicación. Ni siquiera es positivo.

**Nominal positivo si se relaja SIN AJUSTE a P <=0.10 en ambos períodos:** `TREND_MULTI_DAY__GBPCHF`, delta +1.462970 bps dev (p=0.04280) y +1.644665 bps diagnóstico (p=0.08245). Retorno bruto absoluto **+1.255268 bps dev y +0.090071 bps diagnóstico**, y no pasa BH global; con un supuesto coste roundtrip de 1bp el retorno bruto diagnóstico sería **−0.909929 bps**. Esta es una observación **posthoc no confirmada**, no una estrategia ni un trader.

## Conclusión estadística

1. **Holm es más severo que BH en general** porque controla FWER (evitar al menos un falso positivo), mientras BH controla la proporción esperada de descubrimientos falsos entre los hallazgos bajo condiciones apropiadas. Para búsqueda inicial QORE es correcto usar BH al 5% o 10%, **como exploración**, no como criterio único de certificación.
2. **Aquí los datos no sostienen que Holm haya eliminado los supuestos ganadores**: cambiar realmente a BH de 5% o 10% sobre los mismos resultados no produce NI UNA combinación positiva corregida en desarrollo o diagnóstico. Más aún, positivos nominalmente significativos sin corrección NO se replican 1:1 entre ambos períodos al umbral 5%.
3. **Dependencia:** BH no garantiza control nominal bajo TODA dependencia arbitraria. La matriz contiene cruces correlacionados y reglas incluso simétricas de signo, aunque los p primarios provienen de 20.000 bootstrap semanales sincronizados. Holm es válido bajo dependencia arbitraria si los **p marginales** están correctamente calibrados; la serialidad de múltiples semanas y los costes siguen sin resolver. Este análisis BH no «prueba» independencia.
4. **Cartera/descubrimiento futuro:** para otra investigación, predefinir *antes* de mirar retornos un **modelo jerárquico** o inferencia global a nivel siete mecanismos primero y luego activos, con pooling/shrinkage sobre clústeres temporales, y una **muestra realmente nueva**; no bajar más alfa después del resultado. Esto no da permiso para retocar 231 horarios de la muestra actual ni para elegir el mejor instrumento ex post.
5. **Ejecución bloqueada:** 24.377.420 M5 originales G0 33/33, pero NO bid/ask histórico, comisiones, slippage/latencia, calendario de noticias PIT, stops ni fills. 0/3 traders Native certificados, NO CIBO/Shared/QDLE/MT5/VPS/LIVE, no otra corrida económica con estos mismos datos bajo pretexto FDR.

**Veredicto:** `HOLM_CONSERVATISM_NOT_PRIMARY_OBSTACLE_IN_OBSERVED_231_TESTS`; resultados positivos robustos `0`; conservar exploración con estructura estadística futura, no fabricar una certificación retrospectiva.
