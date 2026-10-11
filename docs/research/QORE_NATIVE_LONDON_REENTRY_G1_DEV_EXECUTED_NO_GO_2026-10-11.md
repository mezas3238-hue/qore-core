# QORE Native London Reentry G1 DEV — informe final ejecutado: **NO-GO**

**Fecha:** 2026-10-11. **Identity:** `QORE_NATIVE_LONDON_REENTRY_G1_FIXED_DEV_V1`. **Estado:** `DEV_NO_SUPPORT / NO_GO_FOR_FROZEN_IDENTITY`. Sin trading, sin certificación, sin holdout nuevo. **NO habilitar traders ni retocar reglas por este PnL**.

## Rastro de hipótesis y datos ANTES de leer resultados

- Prerregistro original inmutable: [QORE_NATIVE_LONDON_REENTRY_G1_FROZEN_DEV_PREREG_2026-10-11.md](QORE_NATIVE_LONDON_REENTRY_G1_FROZEN_DEV_PREREG_2026-10-11.md), commit **`dfe4af6918e172843ad71c1f5a9d4d86481520be`**, escrito ANTES de la primera ejecución económica y antes de calcular R de las fuentes.
- [GitHub Actions G1 #38174719898](https://github.com/mezas3238-hue/qore-core/actions/runs/38174719898): código ensayado **`5b3d39a31d22194ce2e0fe8c3b603d3a5a8fc455`**, **2/2 jobs SUCCESS** (`causal_quality` y `historical_dev`), **Ruff PASS, pytest 10/10 PASS**, y reportes/operaciones persistidos.
- Artefacto de resultados [#11715172711](https://github.com/mezas3238-hue/qore-core/actions/runs/38174719898/artifacts/11715172711): `results/g1-london-reentry-report.json`, `g1-london-reentry-trades.jsonl`, hashes SHA256 y commits. **599/599** operaciones hipotéticas conciliadas entre JSONL y resumen en auditoría de hashes independiente, sin selección de trades perdedores.
- Fuentes cTrader DEMO históricas **EXISTENTES** en [run #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), EURJPY artifact #10840979795, USDCHF #10840849959, mismos hashes sellados del G0C. **No se usó cTrader OAuth ni se emitió request de captura**. M5 nativo EURJPY 297.766 barras DEV y M15 99.233; USDCHF M5 297.352 y M15 99.208.
- Operaciones con fechas locales London **2020-09-24 a 2023-09-22**, exclusivamente. Lectura M5/M15 detenida antes de **2023-09-24 23:45:00 UTC**, cutoff reservado a VT08. No lectura de M1, M3, H4 u OHLC posterior al cutoff. **DEV ya consumido**; no OOS limpio para QORE Native.

## Modelo único ensayado (NO reinterpretar)

Referencia 00:00–08:00 local, excursión >0.1 ATR M15 de uno solo de los extremos durante 08:00–09:00 con cierre 08:55 adentro, entrada contraria proxy a open 09:00, stop distancia **1.5 ATR14 M15**, target **1R**, liquidación temporal open 11:00 si no se toca SL/TP. Stop-first para doble toque en M5. Placebo idéntico desplazado 2 horas, rango 22:00 anterior–06:00 actual, exploración 06:00–07:00, entrada 07:00, fin 09:00. DST London verdadero. Sin sweep `NO_TRADE`, no inferir stops reales ni orden institucional.

## Resultado económico bruto, sin spreads, sin comisión

| Símbolo | Brazo | Trades | Mean R bruto | Profit Factor bruto | DD R secuencial hipotético |
|---|---|---:|---:|---:|---:|
| EURJPY | Londres | **187** | **-0.060403** | **0.880099** | 22.22R |
| EURJPY | Placebo | 92 | -0.217391 | 0.642857 | 22.00R |
| USDCHF | Londres | **216** | **+0.052864** | **1.111948** | 11.00R |
| USDCHF | Placebo | 104 | -0.096154 | 0.824561 | 13.00R |

- Muestra total: **599** proxies de operación: **403** Londres y **196** placebo. Resultado de las 403: 194 stop-first, 194 target, 15 salida por hora. Placebo: 113 stop-first y 83 target.
- Mean Londres EQUIPONDERADO por activo = **-0.00376936R/trade**. Mean placebo = **-0.15677258R/trade**. Diferencia primaria predefinida `D = London - placebo` = **+0.15300321R**.
- Bootstrap **2000** réplicas de bloques semanales ISO, seed **941102**, 157 semanas, 2000 réplicas válidas: **IC95 D = [-0.00681395R, +0.30681633R]**. **Incluye cero**. **IC95 media Londres = [-0.10095677R, +0.09002623R]**, también incluye cero. No hay soporte de superioridad ni media positiva verificable.
- Gates de densidad predefinidos **50/mercado/brazo**: sí (mínimo 92); `UNDERPOWERED` no aplica por umbral operativo, pero intervalos siguen anchos y la inferencia queda limitada por sesgos de investigación previa.
- Costes de operación **solo supuestos ilustrativos**: con 0.10R por operación, EURJPY Londres **-0.160403R, PF proxy 0.71236**, USDCHF Londres **-0.047136R, PF proxy 0.90926**; media equiponderada Londres **-0.103769R**. USDCHF PF bruto >1 **NO** justifica seleccionar ese mercado a posteriori, ni prueba coste real. No se usó BID/ASK/latencia/commissions del broker, stop idealizado puede ser optimista.

## Auditoría de completitud y problemas que limitan interpretación

Se evaluaron **782 días locales laborables** por mercado y brazo. Registros de decisiones `TRADE / NO_UNIQUE_REENTRY / MISSING_REFERENCE / MISSING_EVENT`:

| Mercado | Brazo | TRADE | NO_UNIQUE_REENTRY | MISSING_REFERENCE | MISSING_EVENT |
|---|---|---:|---:|---:|---:|
| EURJPY | Londres | 187 | 496 | 98 | 1 |
| EURJPY | Placebo | 92 | 525 | 165 | 0 |
| USDCHF | Londres | 216 | 464 | 101 | 1 |
| USDCHF | Placebo | 104 | 400 | **278** | 0 |

Los **278 días USDCHF placebo sin referencia completa (35.5% de 782)** frente a 101 en Londres (12.9%) significan poblaciones con disponibilidad desigual; el placebo no constituye un contrafactual pareado limpio. Se reporta explícitamente, sin intentar corregir usando datos posteriores a ver outcomes. En el escenario más favorable Londres tiene meanR cercano a cero bruto, por lo que esa ambigüedad **NO cambia el dictamen económico**. Las faltas pueden corresponder a horarios, festivos, cortes de fuente o cobertura: **no adjudicar sin registro oficial de mercado IC Markets cTrader**.

El experimento tampoco sabe qué sucede dentro de una vela M5: STOP_FIRST es resolución conservadora de orden de niveles, no ejecución real; fills y costes reales pueden ser peores. Las medidas de DD son trayectorias hipotéticas por señal, no drawdown de cuenta/porfolio Core.

## Dictamen vinculante y continuidad

1. `QORE_NATIVE_LONDON_REENTRY_V1`: **NO-GO en la definición congelada**; no crear Trader certificado, no volver a correr con parámetros cambiados y venderlo como confirmación; no optimizar sobre estos mismos R.
2. **USDCHF aislado no promocionable**: PF 1.112 bruto y 216 señales tienen media y PF negativos bajo coste ilustrativo 0.1R; además la condición confirmatoria predefinida exigía evidencia estadística conjunta y ambos mercados.
3. Esto **no demuestra que no exista ninguna ventaja** de reversión londinense, ni invalida la tesis amplia de demandas recurrentes, ni refuta RESET fixing 16:00 Londres (es otro modelo). Solo falsifica la primera **implementación única** según gates preregistrados.
4. Para QORE Native los futuros ensayos deben derivarse de un mecanismo distinto y preregistrar una hipótesis nueva antes de nueva inspección de retornos, con separación documental y corrección por multiplicidad. La línea RESET fixing EURUSD del otro equipo se mantiene autónoma.
5. Conservar artefacto, informe y log para el arquitecto siguiente. No tocar el OOS reservado VT08, no usar VPS, no operar DEMO transaccional ni LIVE, no cambiar CIBO/Shared/otros Traders, no requerir OAuth para estos datos ya archivados.

### Registro mínimo de fallos de CI

La primera build CI **#38174663748** falló **solamente Ruff** por nombres ambiguos `l` y estilo identidad; **sin ejecutar** motor histórico. Se corrigieron las ambigüedades y la build final **#38174719898** pasó tests y backtest integral. No se modificaron hipótesis, SL, TP, reloj, placebo o umbral después de revelar R: **sin iteración económica**.
