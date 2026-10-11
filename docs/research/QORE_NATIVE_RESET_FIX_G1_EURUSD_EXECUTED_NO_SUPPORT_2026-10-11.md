# QORE Native RESET G1 — dictamen ejecutado: NO SUPPORT

**2026-10-11. Programa [PR #802](https://github.com/mezas3238-hue/qore-core/pull/802) / issue #793.** Resultado de la configuración única preregistrada: **DEV_GROSS_NO_SUPPORT**. No trader certificado.

## Procedencia reproducible

- Prerregistro PRE-PnL: `2e1742bcfc3186084886b04c63e091aa3256bf12`.
- Addendum de percentil y bootstrap PRE-PnL: `db6017f6046c27e7b1c134a23b4d963e0f5b4634`.
- [CI #38175711378](https://github.com/mezas3238-hue/qore-core/actions/runs/38175711378), commit ejecutado `58fe2c74a3d3002753f8800438faca0c154975b0`: **2/2 PASS**, 9 tests causales PASS. Artefacto resultados **[#11714969393](https://github.com/mezas3238-hue/qore-core/actions/runs/38175711378/artifacts/11714969393)**.
- Fuente CIBO Atlas cTrader DEMO EURUSD M5, run #35166210458, artifact original #10475354631. **745.458 M5 comprobadas**, 11 ledgers anuales con SHA256 verificados y manifest SHA256 `c1826dd450ddeb8a3763ea2ed2bb2cdea7fa01bb56d7f7815b21ac1c460db376`.
- Artefacto investigado descargado desde GitHub, sin captura nueva, cuentas transaccionales, VPS ni modificaciones de CIBO. Fuente previamente utilizada (`research_evidence_consumed=true`), **NO OOS virgen**.

## Modelo congelado

EURUSD, reloj `Europe/London`, 15:30–15:55 presión conocida a 15:55, p75 de magnitud en últimas 120 formaciones válidas estrictamente previas, reversión del `open` M5 16:05 al `open` 16:30 en bps brutos. Placebo 13:30–13:55, reversión 14:05→14:30. Cohorte de fechas común con los dos brazos completos, cuantil lineal, bootstrap 2.000 semanas ISO (seed 941102). Una prueba, sin búsqueda de parámetros.

| Estrato | Días | Reversión media bruta |
|---|---:|---:|
| FIX high | 596 | +0,157998 bps |
| FIX low | 1.854 | +0,343051 bps |
| Placebo high | 625 | +0,561022 bps |
| Placebo low | 1.825 | +0,054165 bps |

**2.450 fechas comunes**. Efecto prereg `D=(FIXhigh-FIXlow)-(PLACEBOhigh-PLACEBOlow)` = **−0,6919104537 bps**. IC95 bootstrap conjunto de 2.000 réplicas válidas: **[−1,935366; +0,547365] bps**. Incluye cero; efecto bruto en dirección opuesta al requisito. Gate de 50/celda y 300 fechas **PASS**; gate científico `DEV_GROSS_POTENTIAL` **FAIL**. Resultado auditado independientemente contra las 2.450 filas individuales y SHA256 del ZIP de resultados.

Controles secundarios, no seleccionables: 1 M5 de retraso, D **−0,461300 bps**; proxy último día laborable del mes, 114 días y D **−3,290436 bps**. Los años individuales no pueden usarse para escoger un ganador. Total 2.608 días laborables nominales: 18 formación incompleta, 120 warmup de historia, 18 presión cero, 2 entrada/salida incompleta y 2.450 utilizables. Cobertura de formación: FIX 2.591, placebo 2.590.

## Límites y decisión

El experimento mide **precio OHLC histórico**, no el benchmark WMR real ni el flujo de órdenes. No hay evidencia de spread, bid/ask, latencia o costes de entrada: **NO se presentan PF/Sharpe/Sortino/PnL, ni rentabilidad neta o drawdown de cuenta**. La prueba no demuestra inexistencia de presiones institucionales; invalida la promoción de **esta identidad operacional específica** en DEV.

**STOP de esta especificación G1:** no ajustar umbral, duración u horas; no usar GBPUSD/USDJPY como rescate post hoc. Cualquier trabajo de una nueva familia RESET exige tesis económica nueva y preregistro propio, idealmente datos directos sobre fixing e OOS realmente independiente. Sin certificación, VPS ni LIVE.
