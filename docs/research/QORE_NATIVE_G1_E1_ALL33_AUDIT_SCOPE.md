# QORE Native G1 — 33 mercados × 7 métodos: extracción causal E1 y presupuesto de fuente BID/ASK

**Actualizado 2026-10-12. Exclusivamente investigación en GitHub.** La oportunidad E1 es una identidad gross *método × símbolo × tiempo*, NO una orden, ni un fill, ni prueba de edge. La fuente histórica E1 es el código firmado `dfe78f115957a40f4188c30e78bd7f88c2ce6c42`, [GitHub Actions #38257207836](https://github.com/mezas3238-hue/qore-core/actions/runs/38257207836), prereg `67022daf7e2c3335eda991fd217df83fc1a34bc4`, G0 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. Se cotejan 33 SHA originales ZIP e internos, códigos, ventanas originales UTC/DST y embargo 2024-09-17.

**Gates fuente reproducibles, primera ejecución verificada:** [PR #867](https://github.com/mezas3238-hue/qore-core/pull/867), [Actions #38297791677](https://github.com/mezas3238-hue/qore-core/actions/runs/38297791677) SUCCESS, artifact #11768924691, SHA ZIP `8d32e008d0a5cb8ad316ef7246b32401e3640cadb16a1088e1566c6beb1c612d`, vencimiento ~2027-01-10 19:27 UTC. Sus scripts de investigación read-only están en `docs/research/QORE_NATIVE_E1_SOURCE_CLOCK_BUDGET/`, workflow `.github/workflows/qore-native-g1-all33-original-e1-source-budget.yml`. **No se usan credenciales de broker y no se solicitan datos históricos nuevos.**

| Auditoría histórica E1 pre-expuesta | Total |
|---|---:|
| Mercados × modelos originales | 33 ×7 |
| Eventos originales investigación, NO trades | 373.611 |
| Ventanas entrada/cierre teórico M5 sin dedup | 747.222 |
| Fragmentos source <=30min deduplicados | 412.012 |
| Solicitudes mínimas BID y ASK posibles | 824.024 |
| Fechas ya expuestas 2021-03-16 + 2023-03-21 | 368 eventos / 403 fragmentos / mín. 806 solicitudes |
| Phase-0 cuatro clases sin PnL (EURGBP, USDJPY, XAGUSD, SP500→US500) | 45 eventos / 49 fragmentos / mín. 98 solicitudes |

**Los 824.024, 806 y 98 son presupuestos, NO broker requests ejecutadas.** Históricos adicionales podrían requerir más paginación `hasMore`, retries y custodia a largo plazo. De las 12 fuentes originales CIBO no todos los contratos se han cotejado contra IC Markets DEMO. Alias SP500→US500 y NAS100→USTEC no certifican equivalencia contractual. No borrar ni cambiar los dictámenes E2/E3 Holm/FDR 231 gross: **0 edges positivos replicados, 0/3 traders certificados**.

## Instrucción de continuidad

1. Validar el reporte phase0-source-only de `phase0_source_plan.py` contra el source audit, con **49 fragmentos /98 requests hipotéticos/45 eventos** y `broker_api_calls_executed=0`. No convertir el CSV en cola que se active automáticamente.
2. Resolver [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) custodia privada autorizada/licencia/digest y prueba de restore, [Issue #857](https://github.com/mezas3238-hue/qore-core/issues/857) contrato G0/IC Markets y valor punto/moneda/fees, [Issue #856](https://github.com/mezas3238-hue/qore-core/issues/856) spreads cero del proveedor y [Issue #863](https://github.com/mezas3238-hue/qore-core/issues/863) clocks originales E1 y cierres reales.
3. Sólo entonces autorizar manualmente una fase de adquisición limitada con broker read-only; auditar bytes originales ProtoOATickData por SHA, BID y ASK last-known as-of ≤5s, zero/crossed/stale fail-closed. No usar los eventos gross pre-expuestos como un nuevo holdout virgen; hoy el cierre E1 es horizonte teórico M5, no una ejecución.
4. Para NET se necesitan contratos exactos, tick value, comisiones round-trip por lote, spread ejecutable, slippage, swap/funding, horarios y noticias PIT; sin estos Gates: `NET_BLOCKED`, `CERTIFIED_0_OF_3`.

Todas las operaciones aquí permanecen en research DRAFT. **Prohibidos cambios a VPS, MT5, LIVE, CIBO, Shared y QDLE.** Datos brutos broker no pueden subirse al Git público sin revisión legal. Los artifacts Actions vencen; archivo temporal no es vault.
