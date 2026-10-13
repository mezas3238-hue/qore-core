# QORE-Alpha 2 — ÚLTIMO TSMOM-RISK252 / VOL20: resultado independiente de ejecución, cierre de familia en este panel

**Fecha de ejecución:** 2026-10-12. **Estado:** `FINAL_TSMOM_FAIL_CLOSE_FAMILY_ON_EXPOSED_DATA`. **Investigación exploratoria:** la fuente 2016–2024 se había consultado en anteriores investigaciones, aunque este protocolo fue preregistrado antes del resultado de este test. Los datos 2024-09-17+ siguen embargados. **NO es NAV/NET ejecutable ni certificado UTC-001.**

## Cadena de evidencia exacta

- **Protocolo registrado antes de outcomes**: `docs/research/QORE_ALPHA2_FINAL_TSMOM_RISKSCALED_AND_XSREV5_FROZEN_PREREG_2026-10-12.md`, ancestro `f9248d42a6cbced3d6e962b24e47c709cb91161c`. Regla irreversible: este es el último TSMOM en los datos consumidos, ninguna variante de lookback/rebalance/vol-score ni selección posthoc de ganador.
- [GitHub Actions **#38318945616**](https://github.com/mezas3238-hue/qore-core/actions/runs/38318945616) **35/35 jobs SUCCESS**: prereg Ruff+fixtures, 12 originales Atlas, 21 nuevos ICMarkets, 1 panel sincronizado. HEAD original e inmutable de estrategia `09db573527b5e9f607edf75949902c6319d6ab21`. Cada worker valida 11-year original market RAW/QUALITY SHA y manifiesto 33 SHA antes de OHLC; no se accedió al embargo.
- Artifact de informe #**11776789637**: `alpha2-TSMOM-FINAL-RISK33-panel-09db573527b5e9f607edf75949902c6319d6ab21`, **ZIP SHA-256 `63b27be5ea371e863f7df4587b2a700140455f13096be6733112a14629132bd7`**. Se descargó el ZIP oficial, se comprobó su SHA-256 y los **dos SHA-256 internos** de `OUTPUT_SHA256SUMS.txt` contra los bytes contenidos, todos coinciden. JSON `alpha2-final-tsmom-risk33-sector-gross-minus-cost.json` SHA-256 `de479f7114a66b59160850dc5359c8c1853e28b47471176fecb059e006c318ae`.
- **Racional de método**: momentum signo de precio 252 sesiones antes, 20 desviaciones log-retornos anteriores, target vol anual 10%, cap 3×, una entrada semanal, salida después de la quinta sesión observable. Coste supuesto **1bp entrada +1bp salida por unidad de notional**, 2×`abs(weight)`bps. 4wk bootstrap sincronizado B2000. Cero optimización de estos parámetros después de mirar PnL.

## Resultado por universo — bps de exposición nominal por semana, menos coste hipotético por lado

| Universo fijo | Mercados | DEV operaciones | DEV semanas activas | DEV media bps/semana | IC95 DEV 4wk | DIAG operaciones | DIAG semanas | DIAG media bps/semana | IC95 DIAG 4wk |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| **Todos** | **33** | **8.605** | **262** | **−0,55044** | **[−6,14630; +5,00548]** | **3.427** | **104** | **−5,29240** | **[−17,02716; +5,69845]** |
| FX cruces | 21 | 5.481 | 261 | −1,31666 | [−7,95948; +5,72782] | 2.184 | 104 | −7,92231 | [−22,10199; +4,59083] |
| FX mayores | 7 | 1.827 | 261 | −1,06283 | [−10,77381; +8,99467] | 728 | 104 | −6,11246 | [−21,28103; +9,58369] |
| **No-FX** (índices+metales) | **5** | **1.297** | **261** | **+3,38504** | **[−7,79979; +15,16782]** | **515** | **103** | **+6,90132** | **[−14,06004; +26,19852]** |

**Exposición completa:** 28 FX = 84,85% del panel, 5 no-FX = 15,15%. Los 21 *cruces FX* son 63,64%; no suman la totalidad de divisas. No existen 11 no-FX. El universo original no incluye bonos ni futuros de energía/agro y los CFDs sin contratos homologados NO son reproducción exacta de Moskowitz–Ooi–Pedersen (2012).

**Bruto antes de coste supuesto**: full33 DEV +1,7126 bps/semana, DIAG −2,6685; no-FX DEV +4,5895, DIAG +8,2575; los costes hipotéticos mueven los estimandos. Los CIs son por semanas con todas las semanas cash=0; el recuento de 12.032 operaciones nominales agregadas (8.605+3.427) **NO es** el número independiente de observaciones; correlación entre símbolos y calendario importa.

**Diagnóstico de saturación del cap de exposición (fijo 3×):** el output original registra solo **106/8.605 (1,23%)** operaciones FULL33 DEV y **57/3.427 (1,66%)** DIAG en el cap. Cruces FX **89/5.481 (1,62%)** DEV y **54/2.184 (2,47%)** DIAG; majors **16/1.827 (0,88%)** DEV y **3/728 (0,41%)** DIAG; no-FX5 **1/1.297 (0,08%)** DEV y **0/515 (0%)** DIAG. Estos son hechos descriptivos del artefacto SHA, NO un argumento para quitar o cambiar el cap; la familia queda cerrada y la exposición está escalada aun cuando no alcance el cap.

### Dictamen científico

1. La **puerta primaria preregistrada FULL33** exige media *cost_proxy* y límite inferior IC95 >0 en **ambos** periodos. **FALLA** en DEV y DIAG, que además presentan medias negativas. `FINAL_TSMOM_FAIL_CLOSE_FAMILY_ON_EXPOSED_DATA`: prohíbe otra variante en este histórico gastado incluso si un futuro investigador detectara un sector promisorio.
2. El sector **no-FX5** tiene media positiva en ambos periodos, pero intervalos amplísimos cruzando cero en ambas eras. `sector_only_exploratory_not_selected=false`. No hay señal sectorial robusta; **NO** seleccionar estos cinco ni certificar un edge.
3. Ningún número es broker NET: 1bp/side es supuesto y no mide spread real, comisiones, swap, conversión cash/point, financiación, borrow, margen, rejections ni disponibilidad temporal de BID/ASK. La estrategia de 10% vol con cap3 es **inspirada en** familia trend-following de MOP, no replica sus 58 futuros, márgenes ni contratos.
4. El anclaje diario UTC 00:00 y primera OPEN M5 puede ser **precio teóricamente inalcanzable por latencia cero** en algunos horarios; el riesgo de lookahead de ejecución no desaparece con vol scaling. Esto no es una decisión real ejecutada; no producir Sharpe, PF, Sortino, DD NET ni UTC-001.
5. Las tres antiguas exploraciones Alpha2 siguen: **W1 PATR y W2 PADE = `INCONCLUSIVE_UNDERPOWERED`**, **W3 CMTRL = `PREDECLARED_GROSS_TEST_FAILED`** para su contraste; el TSMOM-D1 sin scaling anterior también falló, y este último TSMOM escalado completa el único intento adicional autorizado.

## Regla de parada y trabajo paralelo

- **Cerrar TSMOM en este histórico; no nuevos 60/120/180d, rebalances, targets, caps, stops, subset no-FX outcome-selected.** No deducir que toda tendencia de mercado o toda estrategia multi-día sea falsa.
- Segundo y último test independiente previamente preregistrado **XSREV5 cross-sectional 5d**: [workflow en GitHub](https://github.com/mezas3238-hue/qore-core/blob/research/qore-alpha2-original-intermarket-propagation-20261012/.github/workflows/qore-alpha2-xsrev5-one-independent-33.yml), experimentación NO retuning TSMOM.
- Custodia legal/encrypted/restore original33 728MB antes del 16-dic 2026 sigue #837 P0 y **no está hecha**; contrato #868, BIDASK/costes PIT #852 y nuevo OOS auténtico siguen impidiendo toda certificación. PR #840 DRAFT, no main/VPS/MT5/CIBO/Shared/QDLE/PAPER/LIVE, 0 órdenes, 0 traders Alpha2 certificados.
