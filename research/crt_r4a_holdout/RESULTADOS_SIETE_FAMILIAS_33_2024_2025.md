# QORE CRT R4-A — siete familias, matriz histórica 33/33

**Fecha de auditoría:** 2026-11-11 (logs GitHub UTC 2026-11-12). **Solo investigación; no trading.**

## Evidencia reproducible

- [Workflow completo SUCCESS #43126979877](https://github.com/mezas3238-hue/qore-core/actions/runs/43126979877), commit detector `aeeabe5f23f9c1a11b24b2db6548963539968e66`.
- Artifact: `qore-crt-r4a-seven-family-33-market-causal-events-no-pnl` (ID `13903243087`), ZIP SHA256 `9b6b139d946d9b20960a718f079f8f957dcfaae16fcfaf59cdc228330724796f`, expira 2026-12-12.
- Código Pine R4-A original inmutable: blob `693e3f49719e86e2ea0702f7b355af33bd0c4c7c`. Aún **no** hay paridad exacta con `f_engine()` ni equivalencia de 12 fuentes Atlas con IC Markets.
- Source original M5: 4.890.804 filas; 33 mercados distintos (21 IC Markets DEMO, 12 Atlas no homologadas). Falta **BTCUSD** para el universo 34/34.
- USDCAD y AUDNZD, fallidos en #43117258279, ahora SUCCESS con ownership geométrico Multi-N alineado al observador, sin eliminar guardas. Se añadieron pruebas de regresión y se reforzó chequeo de dirección.
- **24 meses 2024–2025 CONSUMIDOS** por investigaciones anteriores: no son holdout virgen. Cero órdenes ejecutadas, cero operaciones cerradas, PnL/PF/DD económicos `null`, costos bid/ask no disponibles.

## Resultados de eventos — NO TRADES

| Familia | Eventos |
|---|---:|
| F1 — CRT 2C RETURN MSS15 C2 | 4.266 |
| F2 — CRT 2C RETURN MSS15 C3 | 7.966 |
| F3 — TRUE 3C MSS5 | 1.748 |
| F4 — Inside Return MSS propio | 554 |
| F5 — Multi4 MSS propio | 647 |
| F6 — Multi-N MSS propio | 369 |
| F7 — Retest M15 original CRT | 8.369 |
| **Total de observaciones superpuestas** | **23.919** |

### 33 mercados (recuento por familia F1 → F7)

| Símbolo | Fuente | M5 | F1 | F2 | F3 | F4 | F5 | F6 | F7 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AUDCAD | IC | 149381 | 144 | 279 | 55 | 10 | 24 | 13 | 298 |
| AUDCHF | IC | 149393 | 141 | 263 | 78 | 11 | 21 | 13 | 282 |
| AUDJPY | Atlas | 149394 | 133 | 279 | 49 | 23 | 21 | 7 | 270 |
| AUDNZD | IC | 149374 | 165 | 277 | 62 | 16 | 28 | 18 | 322 |
| AUDUSD | Atlas | 149355 | 174 | 257 | 49 | 15 | 19 | 12 | 285 |
| CADCHF | IC | 149392 | 122 | 274 | 71 | 16 | 15 | 16 | 274 |
| CADJPY | IC | 149386 | 111 | 276 | 34 | 13 | 21 | 10 | 258 |
| CHFJPY | IC | 149370 | 113 | 268 | 66 | 19 | 29 | 12 | 264 |
| EURAUD | IC | 149403 | 169 | 228 | 61 | 22 | 28 | 15 | 270 |
| EURCAD | IC | 149401 | 131 | 239 | 66 | 16 | 19 | 17 | 266 |
| EURCHF | IC | 149387 | 133 | 242 | 98 | 23 | 32 | 16 | 251 |
| EURGBP | IC | 149368 | 130 | 236 | 70 | 34 | 22 | 18 | 244 |
| EURJPY | IC | 149418 | 132 | 233 | 50 | 19 | 26 | 18 | 242 |
| EURNZD | IC | 149387 | 145 | 263 | 76 | 18 | 28 | 17 | 305 |
| EURUSD | Atlas | 149414 | 125 | 275 | 32 | 15 | 12 | 18 | 277 |
| GBPAUD | IC | 149382 | 146 | 248 | 70 | 26 | 29 | 14 | 268 |
| GBPCAD | IC | 149384 | 124 | 239 | 54 | 24 | 16 | 19 | 258 |
| GBPCHF | IC | 149390 | 132 | 260 | 79 | 19 | 17 | 16 | 271 |
| GBPJPY | Atlas | 149392 | 120 | 238 | 42 | 15 | 22 | 9 | 243 |
| GBPNZD | IC | 149369 | 167 | 276 | 60 | 16 | 33 | 11 | 308 |
| GBPUSD | Atlas | 149343 | 151 | 218 | 38 | 20 | 18 | 14 | 241 |
| NZDCAD | IC | 149362 | 153 | 248 | 65 | 24 | 25 | 7 | 269 |
| NZDCHF | IC | 149372 | 134 | 235 | 87 | 20 | 26 | 12 | 256 |
| NZDJPY | IC | 149382 | 154 | 262 | 50 | 21 | 25 | 10 | 286 |
| NZDUSD | IC | 149300 | 141 | 256 | 48 | 16 | 20 | 7 | 272 |
| US30 | Atlas | 141404 | 91 | 176 | 23 | 5 | 1 | 1 | 181 |
| US500 (SP500) | Atlas | 141343 | 64 | 207 | 17 | 5 | 3 | 4 | 171 |
| USDCAD | Atlas | 149309 | 138 | 256 | 42 | 26 | 15 | 9 | 263 |
| USDCHF | IC | 149342 | 114 | 244 | 57 | 13 | 28 | 11 | 264 |
| USDJPY | Atlas | 149377 | 139 | 252 | 55 | 23 | 14 | 1 | 242 |
| USTEC (NAS100) | Atlas | 141425 | 80 | 213 | 18 | 5 | 2 | 2 | 195 |
| XAGUSD | Atlas | 142030 | 64 | 115 | 17 | 3 | 3 | 1 | 132 |
| XAUUSD | Atlas | 142075 | 86 | 134 | 9 | 3 | 5 | 1 | 141 |

`IC` significa IC Markets DEMO histórico identificado; `Atlas` significa proveedor original Atlas de equivalencia IC **no certificada**. La tabla es un censo de observaciones y puede contener superposición causal entre familias.

## Estado y próximas compuertas

1. **PASS experimental:** conciliación de las siete familias en 33 fuentes originales; las dos discordancias anteriores ya no se reproducen en esta matriz.
2. **OPEN:** BTCUSD histórico IC Markets auténtico; homologación 12 Atlas; paridad evento a evento y precios contra Pine R4-A.
3. **OPEN:** cinta de señales individuales con entradas legales y referencia de precios, motor de fills bid/ask, stops/takes intrabar conservadores, costos reales de cada instrumento/cuenta, riesgo de cartera.
4. **OPEN:** congelar código, parámetros y período de **24 meses genuinamente no visto**; no reciclar 2024–2025 como OOS.
5. **NO CERTIFICADO:** ninguna familia ni cartera demuestra aún rentabilidad neta, PF/DD económicos ni elegibilidad DEMO/LIVE.

**Restricciones:** NO LIVE, NO VPS, NO MERGE, no capital real. El indicador original es la definición de patrones, no un backtester de ejecución.
