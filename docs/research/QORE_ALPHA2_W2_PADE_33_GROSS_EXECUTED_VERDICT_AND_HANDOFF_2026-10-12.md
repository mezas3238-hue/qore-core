# QORE-Alpha 2 — W2 PADE v0.1, primer ensayo gross ejecutado — DICTAMEN / HANDOFF

**2026-10-12.** Runner GitHub [#38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547) = **SUCCESS**, exactamente **35/35 jobs** (preflight, 12 Atlas, 21 IC Markets, agregado). Exact code head `3f81e41ba6af5c226402f68621db7f78980231fe`. Artefacto `alpha2-w2-pade-first33-gross-panel-3f81e41ba6af5c226402f68621db7f78980231fe` en esa ejecución. El preregistro económico precede a todos los outcomes: `docs/research/QORE_ALPHA2_W2_PADE_FIRST_ECONOMIC_PREREG_2026-10-12.md` HEAD `43688569fa8d9c5ba93a127ff6ae66f9091aeede`. Los fallos CI previos se limitaron a Ruff en preflight **antes** de leer retornos; condiciones y fórmulas no se retocaron.

## G0 de fuente y semántica

- 33/33 fuentes SHA originales 11-year RAW+QUALITY de G0 frozen 33 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`, dos cohortes sin equivalencia cuenta acreditada. Investigación de volumen W2 anterior al PnL: run #38273144621, **19.496.136/19.496.136** M5 en período investigado con `volume` positivo entero, 33/33.
- Documentación oficial cTrader *ProtoOATrendbar* `volume`: **bar volume in ticks**. URL exacta https://help.ctrader.com/open-api/model-messages/#protooatrendbar ; hilo staff cTrader https://community.ctrader.com/forum/connect-api-support/36774/ confirma que volumen ticks NO equivale a volumen real comprador/vendedor negociado. Queda pendiente un test de genealogía `ProtoOATrendbar.volume -> archived RAW_M5_LEDGER.volume` por productor original, no sólo nombre de campo.
- Variables de PADE `Σ tick_count * sign(body_M5)` son **proxy de actividad de cotización según dirección de barra**, no flujo de órdenes agresoras ni volumen comprado/vendido; prohibido confundir.

## RESULTADO BRUTO PADE (extraído del log de agregación)

| Período | Pareadas nativas originales | GROSS promedio PADE (bps) | Delta PADE-control (bps) | Mínimos congelados | Gate |
|---|---:|---:|---:|---|---|
| Desarrollo 2016-09-17→2022-09-17 | **220** | **−1,798045555926468** | **−4,558631253760526** | 150, 52 semanas, ≥20 por cohorte | `sample_gate: true` |
| Diagnóstico 2022-09-17→2024-09-17 | **45** | **+3,3942737980940363** | **−1,972772091247587** | 50, 26 semanas, ≥20 por cohorte | `sample_gate: false` |
| Total | **265/265 señales pareadas** | **NO promediar para Gates** | **Negativa en ambos** | Year/fold por separado | **NO SOPORTE** |

El comparador direccional PRE-evento produjo **134 casos con dirección opuesta** entre los 265 eventos pareados; a diferencia de W1, NO es algebraicamente idéntico. El desempeño bruto positivo en diagnóstico no rescata el delta **negativo** frente al control ni la falta de potencia.

**Estado auditable** `UNDERPOWERED / NEGATIVE_RELATIVE_EDGE / COSTS_PIT_UNVERIFIED / 0 TRADERS CERTIFIED`. La calidad de código y la ejecución de los 33 jobs son éxito de ingeniería, no éxito de estrategia. Nunca convertir resultado GROSS OHLC de cTrader en PF/Sharpe/Sortino/DD NET ni PAPER/LIVE. No publicar supuestas ganancias. No tocar VPS, MT5, QDLE, Shared, CIBO ni main.

## Gates fallidos y acciones inmediatas

1. Cerrar PADE v0.1 y W1 PATR como **dos hipótesis expuestas**, sin retunar umbrales 1,65x, 0,20, 0,30, 20h, stop 1x, target2R, 4h, ni escoger mercados rentable posthoc.
2. Auditoría G2 SOURCE-ONLY de resultado W2: importar el JSON original firmando SHA, auditar 33 filas, 4 familias, año×cohorte, número de mercados sin señales, exclusiones de reglas, IC95 bootstrap 1/2/4 semanas, distribuciones y diversidad del comparador; sólo descriptiva y sin precios nuevos. Aislar la causa de escasez preestablecida sin usarla para reoptimizar W2.
3. Registrar una **tercera y última familia exploratoria W3** con mecanismo causal distinto y presupuesto experimental PREdeclarándolo antes de analizar outcomes nuevos. Limitar variantes y hacer evaluación sobre todo el universo; después exigir nuevos datos independientes OOS. Ya son dos modelos inspeccionados con el mismo período, imposible llamar al próximo un OOS virgen.
4. Certificación UTC-001 sólo con source/provenance, BUY/SELL BID/ASK as-of, coste por operación, comisiones, swaps, sesiones y noticias PIT reales, paper independiente y cumplimiento por año/fold del PF/E/Sharpe/Sortino/DD/MC/winner-preservation; sin eso `BLOCKED`.

**No fusionar PR #840 a main / 0 PAPER o LIVE autorizado**.
