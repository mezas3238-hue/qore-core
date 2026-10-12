# QORE-Alpha 2 — W3 CMTRL 33 mercados FIRST GROSS ejecutado; cierre del presupuesto W1/W2/W3

**2026-10-12. GitHub Actions exact run [#38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503) = SUCCESS, 35/35 jobs** (causal synthetic, 12 originales, 21 nuevos, panel). HEAD `e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c`. Archivo firmado `alpha2-w3-cmtrl-first33-gross-panel-e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c` en mismo run; fuente original 33 G0 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. W3 prereg congelado BEFORE PRICE OUTCOMES `docs/research/QORE_ALPHA2_W3_CMTRL_LAST_EXPLORATORY_PREREG_2026-10-12.md` commit `a18cb43a6fb69eab948d840c6e6101c6a7251906`. CI anterior #38284751415 falló **antes** de observar retornos por Ruff aliases; un cambio posterior de calidad de imports no alteró features/reglas/estadísticas.

## Resultados comprobados y no embellecidos

| ERA | Original señales | Pares evaluables | PADE? NO: CMTRL GROSS medio (bps) | Delta CMTRL - control (bps) | Sample gate |
|---|---:|---:|---:|---:|---|
| DEV [2016-09-17,2022-09-17) | pendiente desglose exacto eventos no pareados del artefacto | **18.266** | **+0,1865975941188018** | **−0,015164536224339087** | **PASS** |
| DIAG [2022-09-17,2024-09-17) | pendiente desglose | **6.133** | **+0,069241820503673** | **+0,5351572763662205** | **PASS** |
| TOTAL | **24.487** | **24.399** | No mezclar eras para certificar | 10.841 eventos de dirección distinta al control | **NO SOPORTE** |

88 eventos brutos no pareados (24.487 − 24.399) por censura; causas y desglose requeridos al auditor fuente original, no rellenar ni excluir ex-post. El número de señales es suficiente, **la evidencia de ventaja NO**. La ventaja relativa es ligeramente negativa en DEV, y positiva pero pequeña en diagnóstico. Los medios gross absolutos (+0,187 y +0,069 bps) son minúsculos, antes de BID/ASK y costes reales. Sin commissions/spread medidos no conocemos net exacto, no afirmar que el efecto sobreviva siquiera a 1 bp. El estatus del código ejecutado es `NO_SUPPORT_PREDECLARED_GROSS`, incluso si el componente de muestra pasa y aunque el comparador no sea tautológico (10.841 direcciones distintas).

**GROSS NO NET:** cTrader native OHLC M5 OPEN no es precio de orden ejecutada. Calendario noticias PIT no filtrado, spread histórico no auditado, slippage/swap/comisión desconocidos. PF/Sharpe/Sortino/DD **NET** no calculados; UTC-001 `BLOCKED`. No capital, no VPS, CIBO, Shared, QDLE, MT5 o paper orders.

## Contraste íntegro del presupuesto de tres hipótesis PRE-GROSS

| Familia | Hipótesis | n pareadas | Desarrollo medio GROSS | Diagnóstico medio GROSS | Ventaja frente a control | Dictamen |
|---|---|---:|---:|---:|---|---|
| W1 PATR | Transmisión intermercado asincrónica | 176 | −0,1674 bps | −3,4237 bps | Comparador casi tautológico | Underpowered, no soporte |
| W2 PADE | Actividad ticks alta con desplazamiento reducido | 265 | −1,7980 bps | +3,3943 bps | Negativa ambas eras | Underpowered, no soporte |
| W3 CMTRL | Transiciones Bayesianas de morfología H1 | 24.399 | +0,1866 bps | +0,0692 bps | Negativa DEV, positiva DIAG | NO_SUPPORT, muestra suficiente |

Al ser un programa secuencial ADAPTATIVO y usando períodos 2016–2024 previamente consumidos, esta tabla es EXPLORATORIA, no evidencia positiva de tres experimentos independientes ni licencia para multiplicidad sin corrección.

## Decisión investigadora firme

1. **Congelar W1/W2/W3. NO tuning post-hoc.** El usuario pidió metodología propia rentable, pero esa rentabilidad **no fue demostrada**. No fabricar PF, Sharpe o certificaciones.
2. **Preservar los 33 originales, ultrafast, fuente SHA y prereg en PR #840**, sin merge main. Identidades completas y resultados en GitHub.
3. **Fase G2 realista, issue #852**: exact BID/ASK por cuenta y hora, comisiones, spreads, swap, contrato CFD, lotaje, data availability, macro release as-of, benchmark de fills contra M5 y certificación por año/fold; investigar coherencia de 12 Atlas + 21 IC Markets. No dar validez NET retroactiva a pérdidas gross.
4. **Nueva información independiente**, prospectiva, congelada por un plan de observación (no confundir `2024+` reservado con virgin sin testigo de nadie haber accedido): una hipótesis W4 requiere fuente/protocolo realmente nuevo y prereg adecuado. No disparar una cuarta estrategia sobre mismo histórico 2016–2024 para escoger ganadora.
5. **Auditar la causa precisa de 88 censuras de W3**, distribución por cuatro familias, años y intervalos 1/2/4 semanas leyendo SÓLO el primer JSON firmado, sin OHLC adicional; registrar en nuevo testigo. Ningún outcome nuevo.
6. Sin precondiciones de calidad del broker, una prueba CMTRL rentable bruta no habría bastado. Todavía 0/3 trader families certified.

**Estado operacional: Research only / 0 orders / producción intacta.**
