# QORE Futures A — CFTC seis mercados: fuente auténtica y examen independiente H-COT-1

**Fecha de investigación:** 13-Oct-2026 (Paraguay) / GitHub Actions 14-Oct-2026 UTC.
**Repositorio:** `mezas3238-hue/qore-core` · **PR:** [#920](https://github.com/mezas3238-hue/qore-core/pull/920), OPEN/DRAFT, NO MERGE.
**Presupuesto:** USD0. **NO LIVE**, NO DEMO, NO capital real. **Reserva EIA 2022-01–2024-04 y FX Native 2024-09-17+ no evaluadas.**

## 1. Fuente externa real y no sintética

Se auditó y descargó de archivos **oficiales de la CFTC** `fut_disagg_txt_YEAR.zip` cada año de **2012 a 2021** para seis raíces: **CL 067651, NG 023651, GC 088691, HG 085692, ZC 002602, ZS 005602**. El verificador comprueba nombre de venue, identidad de mercado, schema de posiciones semanales futures-only, open interest, fechas de martes/feriados, integridad y duplicados. Algunos registros muestran fecha de reporte de lunes/miércoles por calendario CFTC, por lo que se corrigió el supuesto de martes obligatorio.

**Total 3.132 registros market-week (522 semanas por raíz)**, no operaciones ni velas D1. Archivos SHA256 de fuente se fijan en la PR; no se redistribuyen valores de posiciones. CFTC publica posiciones semanales agregadas con referencia martes; el histórico comprimido no acredita el instante exacto original de cada publicación.

**Primer examen de fuente:** [Actions #38493219775](https://github.com/mezas3238-hue/qore-core/actions/runs/38493219775), SUCCESS, 8/8 tests; Ruff PASS; Mypy PASS. Fuente completa 2012–2021 validada y sin datos del holdout.

**Resultado source gate:** `PUBLIC_OFFICIAL_POSITION_DATA_AVAILABLE` para los seis instrumentos; **PERO** `CME_NATIVE_6ROOTS_2_EXPIRIES_D1_PRICE_SOURCE = BLOCKED_DATA_OR_LICENSE` sin cambios. CFTC NO tiene contrato por vencimiento, OHLCV, bid/ask ni coste de ejecución.

## 2. Preregistro independiente anterior a resultados

Documento de hipótesis [H-COT-1](https://github.com/mezas3238-hue/qore-core/blob/research/qore-futures-a-cftc-disagg-sixroots-source-20261013/docs/research/QORE_FUTURES_A_CFTC_MANAGED_MONEY_ONE_SHOT_EXPLORATORY_PREREG_2026-10-13.md) fijado en commit `e6821685cbefd775f820865e4d2b0d03ab94dff2` **anterior al runner de resultados**.

Pregunta: ¿aumentos de cuatro semanas en `(MM_long–MM_short)/OI` de CFTC preceden mayor probabilidad de subida del precio **referencial** F1 de WTI y NG? Se toma **un informe por mes**, retraso conservador de **21 días calendario** tras su fecha as-of antes del precio de entrada EIA, respuesta en las siguientes 5 observaciones EIA. Blackouts prospectivos 2013-Sep–Nov y 2018-Dec–2019-Apr. DEV 2012–18, DIAG 2019–21, reserve 2022+ sellada. Dos pruebas Fisher unilaterales, Bonferroni **p ≤ 0.025** por raíz, efecto ≥ +10 pp y mínimo 8 eventos/régimen en ambas ventanas.

**Advertencia:** las ventanas DEV/DIAG EIA ya se usaron para otras hipótesis; este nuevo contraste no constituye un holdout verdaderamente fresco. La demora 21d NO garantiza `first_published_at` causal para todas las fechas; fuente CFTC/EIA vintage revisable. **NO PnL de futuros.**

## 3. Resultados reales H-COT-1 — no soporte en ambos mercados

[Actions #38493719365](https://github.com/mezas3238-hue/qore-core/actions/runs/38493719365) **SUCCESS**, commit ejecutado `1f6fd22621f7f50e236c1b36653e73dfff52c6bc`.
**17/17 tests (8 fuente + 9 screen); Ruff y Mypy PASS** (Mypy cubre fuente, Ruff también screen).
Artefacto de diagnóstico [#11863400910](https://github.com/mezas3238-hue/qore-core/actions/runs/38493719365/artifacts/11863400910), ZIP SHA256 `712afb84bcdf2c53bd50363ae81a5bf546a76a06d674adb52371d2c65073a7c8`.
Recibo científico lógico SHA256 `3f81da4311dd65493f064a77b5df6077ec5ec3703fdb45892bf979e370c02598`.

| Root | Ventana | n eventos mensuales | X positivo | X negativo | Delta prob. subida | Fisher unilateral p | Dictamen |
|---|---|---:|---:|---:|---:|---:|---|
| WTI | DEV 2012–18 | 80 | 42 | 38 | **+10.7769 pp** | **0.22766484** | NO_SUPPORT |
| WTI | DIAG 2019–21 | 31 | 13 | 18 | **+9.4017 pp** | **0.43927357** | NO_SUPPORT |
| NG | DEV 2012–18 | 80 | 42 | 38 | **−17.6692 pp** | **0.96463782** | NO_SUPPORT |
| NG | DIAG 2019–21 | 31 | 15 | 16 | **+16.2500 pp** | **0.29332602** | NO_SUPPORT |

**Dictamen por hipótesis bajo prereg:**
- H-COT-1 / WTI: `NO_SUPPORT_UNDER_PREREG`.
- H-COT-1 / NG: `NO_SUPPORT_UNDER_PREREG`.

No usar +16.25 pp en NG DIAG para fabricar un resultado positivo: no supera el alfa 0.025 y contradice el signo DEV. Los 31 eventos DIAG/root son escasos. Ninguna inversión de señal, ajuste de meses, recorte de muestra, cambio de rezago u orientación después de mirar estos resultados se considerará nueva confirmación. El screen queda **CLOSED** sin abrir holdout.

## 4. Separación ciencia / economía

Estos son **eventos de asociación en precios EIA rank-F1 referenciales**, no 222 trades negociables. F1 cambia identidad con rollover; no hay contrato exacto de ejecución, profundidad, bid/ask, fee, slippage, margen, tamaño del tick o primera publicación auditada del proveedor. No se calculó net PnL, PF, DD, Sharpe ni retornos de un trader. Aunque los p-values hubieran sido favorables, NO sería edge económicamente certificado.

En particular:
- EIA F1/F2 backwardation original H1_WTI/H1_NG sigue cerrado `NO_SUPPORT`.
- NUEVA hipótesis H-COT-1 WTI/NG también `NO_SUPPORT`.
- CFTC posicionamiento seis mercados: datos de investigación semanal completos 2012–2021, fuente no negociable.
- CME 6×2 D1 OHLCV native legal USD0: `BLOCKED_DATA_OR_LICENSE`.
- No promover Trader Lab/CIBO/CF11/Risk; no LIVE ni merge.

## 5. Siguiente investigación de valor (no más tuning a posteriori)

1. Evitar abrir otra hipótesis WTI/NG sobre las mismas DEV/DIAG inmediatamente. Buscar primero nueva **fuente de precios causal y legal de USD0** para los otros cuatro mercados, y **as-of real CFTC**, o universo alternativo con datos de ejecución disponibles.
2. Una hipótesis nueva debe quedar independiente en mecanismo y familia estadística, con commit prereg anterior a outcomes y aprobación científica, bajo presupuesto 0, sin consumir reservas antiguas.
3. Si no aparece dataset de ejecución native CME por vencimiento, no se puede declarar estrategia de futuros rentable; alternativas con datos disponibles requieren replantear misión, no falsificar el contrato 6×2.
4. Conservar SHA de 10 archivos ZIP, actas de CI y decisiones cerradas; resultados de CFTC/EIA no se usan como nuevos permisos de ejecución.

**Documento y PR DRAFT constituyen el handoff de esta fase. NO MERGE.**
