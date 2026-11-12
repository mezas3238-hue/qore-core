# QORE CRT R4-A · Resultado histórico del detector causal integrado (33 mercados)

**Corte: 11 de noviembre de 2026. QA / NO LIVE / NO VPS / NO MERGE.**

## Evidencia de GitHub — resultados ejecutados

- [33 jobs históricos independientes — run #43109506089](https://github.com/mezas3238-hue/qore-core/actions/runs/43109506089): **33/33 jobs de cada mercado SUCCESS** en fuentes originales M5 para 2024–2025, con hash SHA-256 de las dos particiones por fuente. **El job de agregación de esa ejecución falló** por faltar el campo `provider_cohort` en los JSON de mercado, *no* por un fallo de los 33 detectores.
- [Reagregación sin repetir velas — run #43110266221](https://github.com/mezas3238-hue/qore-core/actions/runs/43110266221): **SUCCESS**, con **13/13 pruebas de contrato**, recuperando atribución de proveedor de la matriz de fuentes inmovilizada. Artefacto: `qore-r4a-integrated-33-2024-2025-event-audit-no-pnl`, que contiene `summary.md` y `summary.json` con los **33 instrumentos individuales**.
- [QA general del trader — run #43110275782](https://github.com/mezas3238-hue/qore-core/actions/runs/43110275782): **150/150 PASS**; verifica también la fuente Pine R4-A original Git blob `693e3f49719e86e2ea0702f7b355af33bd0c4c7c`.
- [Piloto causal USDCHF — run #43108824142](https://github.com/mezas3238-hue/qore-core/actions/runs/43108824142): PASS sobre 149.342 M5 originales, 358 eventos modelo A y 57 eventos modelo B.

## Resultados históricos por modelo — EVENTOS, NO OPERACIONES

| Métrica | Total |
|---|---:|
| Datos originales M5 procesados | **4.890.804** |
| Feeds históricos con ambas particiones 2024 y 2025 | **33 de 34** |
| Fuentes IC Markets DEMO confirmadas | **21** |
| Fuentes Atlas DEMO sin homologación TradingView/IC | **12** |
| Señales de investigación **A: CRT 2C RETURN + MSS15 propio** | **12.232** |
| Señales de investigación **B: TRUE 3C + MSS5 propio** | **1.748** |
| Total eventos CRT/MSS registrados | **13.980** |
| Ejecuciones de órdenes | **0** |
| Profit factor, win rate, expectativa neta, drawdown de este detector | **NO CALCULADOS** |

**Reglas incorporadas:** seis ventanas H4 de Nueva York por familia según fuente R4-A, 48 M5 cerradas y continuas por H4 (si el feed permite), C2/C3 estrictas, exclusión de doble barrida, pivote propio congelado antes de sweep, M15 de tres M5 consecutivas, cruces por cierre M5/M15 con tiempo legal y causalidad. Dos modelos independientes. No se utilizan resultados de beneficio para calibrar filtros.

**Las 13.980 observaciones no son comparables directamente con las 8.237 + 391 operaciones cerradas del primer proxy:** aquel detector usaba solo tres ventanas H4 por día, pivotes alternativos y simulaba entradas/salidas; el nuevo mide únicamente eventos, con seis ventanas.

## Fuente y límites innegociables

1. **NO se ha demostrado paridad exacta** contra `f_engine()` de Pine R4-A en TradingView. La réplica reproduce partes del motor, no toda la máquina de estados ni las siete familias; quedan por certificar reglas de empate de pivotes, casos DST, fases de M5 específicas por proveedor, históricos en TradingView y coincidencia exacta de precios/timestamps.
2. **BTCUSD** carece de archivo del feed IC equivalente; **33/34**, no declarar 34 certificados.
3. **12 Atlas** (incluidos alias NAS100→USTEC y SP500→US500) aún no tienen equivalencia con el feed de TradingView demostrada. El resumen deja registrada su procedencia original.
4. **No se ejecutaron trades**, no se incluyen órdenes limit, stop loss, take profit, spread variable, bid/ask, comisiones, swap, slippage, sizing ni correlación. **No atribuirle R, PF, win rate, DD o rentabilidad a los 13.980 eventos.**
5. Los 24 meses **2024–2025 están CONSUMIDOS/BURNED** como investigación retrospectiva CRT. Prohibido usarlos de nuevo como holdout virgen tras observar los resultados.
6. La ejecución original de 33 jobs #43109506089 conserva su error de **agregación** como evidencia; la corrección está probada separadamente en #43110266221. No reetiquetar run fallido como workflow completamente PASS.

## Próximo trabajo con criterio binario

- Construir/exportar un **ledger Pine verdadero**, sin snapshots `barstate.islast` reciclados, para la misma fuente, con `event_id, symbol, model, side, c1_at, sweep_at, ratified_at, mss_at, available_at, c1_high, c1_low, sweep_high, sweep_low, mss_pivot`.
- Contrastar el ledger Pine y el replay real con `parity_gate.py`: **cero eventos faltantes, cero adicionales, cero anticipados y precios coincidentes**. Si el feed es diferente, no adjudicar desacuerdo a la estrategia.
- Recuperar BTC IC, paridad de las 12 fuentes Atlas y costos de cada cuenta/mercado, antes de un **nuevo holdout 24 meses previamente no consumido**.
- Solo después de esas puertas, evaluar un trader económico con riesgo limitado y reportar todas las pérdidas, sin optimización posterior sobre el mismo holdout.

**Veredicto: DETECTOR CRT/MSS INTEGRADO 33/34 EJECUTADO SOBRE HISTÓRICOS REALES EN QA. TRADER Y RENTABILIDAD: AÚN NO CERTIFICADOS.**
