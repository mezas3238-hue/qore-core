# QORE Native — Contrato de cobertura completa de 33 mercados sin selección por PnL

**Fase:** preparación estructural G0; no significa 33/33 certificado hasta que aparezca el artefacto fuente de los tres últimos. Código `src/qore/infrastructure/trader_lab/qore_native_market33_source_census_v1.py`, tests `tests/infrastructure/trader_lab/test_qore_native_market33_source_census_v1.py`. Esta investigación del censo **no lee valores OHLC ni señales ni retornos** y no pretende suplir las evidencias de BID/ASK históricos.

## Congelación previa: cobertura exhaustiva

| Familia | Símbolos preasignados (sin ranking por rentabilidad) | n |
|---|---|---:|
| Índices | NAS100, SP500, US30 | 3 |
| Metales | XAUUSD, XAGUSD | 2 |
| FX mayores | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY | 7 |
| FX cruces (menores / cross) | AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, NZDCAD, NZDCHF, NZDJPY | 21 |
| **Total** | **33 únicos** | **33** |

La clasificación considera majors como pares contra USD para fines de inventario, no la disponibilidad real de cotización, profundidad o spread; «minores» significa cruces de la lista fijada sin USD. El censo exige la misma cobertura y lista de la rama fuente final 33, no permite agregar o quitar activos para producir métricas favorables.

## Pruebas que bloquearán el certificado de inventario

1. Revisar SHA del JSON fuente 33 en `OUTPUT_SHA256SUMS.txt`, `.sha256` y el código productor exacto, sin aceptar campos mutados o autofirmados.
2. Validar 33 símbolos distintos, familias disjuntas, 12 series originales `EXISTING12_CTRADER_DEMO_ORIGINAL` y 21 series nuevas IC Markets DEMO por identidad de fuente. No fusionar spreads/cuenta de los orígenes.
3. Las 21 fuentes nuevas requieren ledger `raw_sha256_by_year` de exactamente 2016–2026, once SHA originales. Las doce antiguas remiten al G0/G0B inmutable de origen ya verificado con SHA.
4. Sumar barras M5 por activo, familia y procedencia, comprobar original 12 igual a 8.726.985, parent30 igual a 22.141.699 y las tres finales igual a la diferencia del JSON 33 firmado.
5. Emitir exclusivamente un inventario `G0_FULL33_FAMILIES_ALL_COVERED_NO_MARKET_OUTCOMES`. No computa profit factor, Sharpe, sortino, drawdown, wins ni posibles edges, pues los datos no acreditan ejecución.
6. Demostrar fail-closed frente a símbolo faltante, SHA anual faltante, fuente mal etiquetada, falsedad `broker-account-equivalence` y cuenta M5 no conciliada.

## Después de la cobertura 33

La fase de **33 mercados inventariados no equivale a 33 estrategias ni 3 traders certificados**. Los tres primeros mecanismos probados y falsados seguirán como `NO_SUPPORT`: EURUSD persistencia H4 [#822](https://github.com/mezas3238-hue/qore-core/pull/822), XAUUSD reversión H4 [#825](https://github.com/mezas3238-hue/qore-core/pull/825) y NAS100 apertura NY [#827](https://github.com/mezas3238-hue/qore-core/pull/827). No buscar «mejor mercado» ex post.

Para continuar con **investigación causal de los 33**, predefinir una hipótesis de cartera/panel genuinamente diferente, aportes por familia como diagnósticos **sin seleccionar ganadores**, bootstrap calendar-cluster que considere correlación de pares/índices (no tratar 33 retornos del mismo día como independientes), ventana temporal de desarrollo y diagnóstico, y corrección precomprometida por multiplicidad. El horizonte reservado 2024-09-17→2026-09-17 no se abre con una justificación retrospectiva. Las métricas gross y stress RT son siempre hipotéticas; no hay BID/ASK de hace diez años, eventos PIT o cartera LIVE autorizable.

**Seguimiento GitHub:** [PR #829](https://github.com/mezas3238-hue/qore-core/pull/829) con cierre SHA final de los 33. Sin VPS/MT5/CIBO/Shared/QDLE, 0/3 traders Native certificados.
