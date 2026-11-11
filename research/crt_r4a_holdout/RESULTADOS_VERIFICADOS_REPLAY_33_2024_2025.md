# QORE CRT Trader R4-A — resultados consolidados 2024–2025

**Fecha del corte 2026-11-11 · EXPLORATORIO · NO CERTIFICACIÓN · NO LIVE / NO MERGE / NO VPS**

## Evidencia ejecutada en GitHub

- [Replay original 33/33 SUCCESS — run 43094233453](https://github.com/mezas3238-hue/qore-core/actions/runs/43094233453); código ejecutado SHA `74092c66710449baed2ebcbbee8e7448e5ca54e3`.
- [Consolidación 33/33 SUCCESS — run 43102693708](https://github.com/mezas3238-hue/qore-core/actions/runs/43102693708); artefacto `qore-crt-r4a-2024-2025-real-m5-33-proxy-report` con `summary.md` y `summary.json` (33 filas de mercado; copia original del ZIP no contiene OHLC brutas).
- [PR #1007](https://github.com/mezas3238-hue/qore-core/pull/1007), rama `research/crt-r4a-34-holdout-2y-20261111`.
- Fuente Pine original R4-A pinneada por Git blob `693e3f49719e86e2ea0702f7b355af33bd0c4c7c`.

## Universo y cuentas

| Magnitud | Total |
|---|---:|
| Instrumentos con históricos 2024–2025 originales y SHA verificado | **33 de 34** |
| Atlas DEMO (proveedor exacto IC no homologado) | 12 |
| IC Markets DEMO (origen de catálogo verificado) | 21 |
| BTCUSD con feed IC equivalente | **Sin fuente autorizada** |
| Velas M5 reales totales | **4.890.804** |
| H4 reconstruidas y cerradas | **98.937** |
| Estructuras 2C detectadas por proxy | **14.966** |
| MSS15 de proxy | **10.312** |
| Estructuras TRUE3C por proxy | **1.242** |
| MSS5 de proxy | **457** |

## Resultado de los dos modelos *aproximados*, antes de costos

| Métrica | Modelo A: 2C RETURN + MSS15 (proxy) | Modelo B: TRUE3C + MSS5 (proxy) |
|---|---:|---:|
| Trades cerrados del simulador | **8.237** | **391** |
| Win rate bruto | **53,9274 %** | **54,2199 %** |
| Expectativa R bruta por operación | **−0,021092** | **+0,030721** |
| Suma descriptiva de R sin capital/sizing | **−173,7319 R** | **+12,0118 R** |
| Mercados positivos | 13 | 16 |
| Mercados negativos | 20 | 16 |
| Mercados sin trades | 0 | 1 |

### Falsación de costos, sólo hipótesis de R constante por trade

| Coste supuesto por trade | Expectativa aproximada A | Expectativa aproximada B |
|---:|---:|---:|
| 0,00 R | −0,021092 R | +0,030721 R |
| 0,02 R | −0,041092 R | +0,010721 R |
| 0,05 R | −0,071092 R | **−0,019279 R** |
| 0,10 R | −0,121092 R | −0,069279 R |
| 0,20 R | −0,221092 R | −0,169279 R |

**Esos descuentos NO son comisiones/spreads reales.** El cálculo sólo cuantifica el margen de la señal de investigación. La suma R no equivale a rentabilidad porcentual de una cuenta ni tiene modelada correlación/riesgo simultáneo.

## Hallazgos críticos

1. **Modelo A**: expectativa negativa incluso sin costos; no aprobar.
2. **Modelo B**: muestra una expectativa bruta marginal con muestra más pequeña, que desaparece bajo el escenario hipotético de 0,05R por trade; no aprobar sin costos reales y señal exacta.
3. **Las 7 categorías de R4-A no son 7 estrategias**. Este estudio solo evalúa aproximaciones a A y B.
4. **Paridad no demostrada:** los pivotes Pine `ta.pivothigh/ta.pivotlow` M5 y el sistema M15 confirmado no equivalen a los pivotes proxy de 8/9 M5. Tampoco está validada paridad del origen IC para Atlas.
5. **Período CONSUMIDO/BURNED:** inspeccionamos resultados sobre 2024–2025; ya no puede ofrecerse como holdout virgen del CRT. `data/manifest.json` lo declara y `runner.py` lo bloquea aunque se intente forzar la bandera de atestación.
6. **BTCUSD falta**: 33/34, nunca presumir cobertura 34 completa.

## Próximas puertas técnicas

Portar `f_engine()` con eventos causales originales, producir las dos cintas de auditoría y pasar `parity_gate.py` frente a la misma fuente OHLC. Obtener spreads/comisiones y un feed BTC equivalente, implementar sizing y cartera y establecer **otro período de 24 meses no usado** antes de un holdout formal.

**Decisión actual: QORE CRT Trader sigue en QA; no certificado ni apto para capital real.** No se ha realizado merge ni acciones en VPS.
