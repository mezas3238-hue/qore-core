# VT31 NAS100 · P0 resolución urgente STOP / GO tras screening CE

**Fecha: 13 octubre 2026 · Dictamen: `NO_GO_FURTHER_V1_INVESTMENT_NOW`.**

**No equivale a demostrar que toda implementación futura V1 carece de edge.** Es una **decisión racional de cartera de investigación**: no destinar nuevos recursos de integración G6, compra de BID/ASK ni operación LIVE al V1 actual sin evidencia adicional externa; conservar el estado V1 `EDGE_NOT_DEMONSTRATED`. No retocar filtros para rescatar muestra.

## Trabajo ejecutado realmente

- **[GitHub Actions #38378129887 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38378129887)**, código y pruebas commit `61566b5302f0d8810dc013d791f15faba366c27b`, artifact `11802550181`, **6/6** pruebas adversariales, Ruff y py_compile PASS, manifest SHA256 PASS.
- Universo original exacto: **2.140** FVG candidatos de la metodología antigua (NO V1 G3): ledger histórico artifact `11657461650`, 0 broker fills; M1 source artifact `11459859004`, **1.059.784** velas de desarrollo, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` comprobado antes de análisis. Fresh holdout no consultado.
- Reproducción exacta del screening original preregistrado de horizonte **15m desde la apertura de la siguiente M1 después del cierre C3/FVG**, no desde CE: bruto −1,919664 puntos de índice. Se mide `side * (open[formed+15m] - open[formed])`, sólo si hay 16 M1 consecutivas. Los 2140 tienen cobertura.
- **301 de 2140** (~14,07%) presentan primera intersección **OHLC M1** con precio CE mientras el candidato estaba en estado admisible, según sello conservador del ledger. **No son 301 ejecuciones limit**. **1.839** candidatos no presentan ese testigo de toque CE admisible. Los solapamientos en la misma M1 que la revocación/las cancelaciones ambiguas no se suman a los 301 como operaciones; permanecen UNKNOWN.
- Análisis de 301 realizado con **dos relojes claramente distintos**: retorno 15m original desde apertura siguiente a C3 condicionado a que luego toque CE; y retorno 15m **después del cierre M1 que contuvo la primera intersección OHLC CE**, con precio de inicio = apertura de la siguiente M1, **NO precio de ejecución CE**. El segundo no es PnL de entrada ni puede interpretarse como target vs stop.
- Remuestreo de **bloques de semana ISO**, 2.000 réplicas, semillas determinadas; IC 95% **exploratorios**, sin p confirmatorio ni corrección por selección ex post. Tres años ya consumidos para investigación antes de este corte; jamás OOS independiente.

## Resultado bruto observado (sin spread/comisiones/slippage)

| Subconjunto y referencia | N | Media bruta pts | IC bootstrap semanal 95% | Comentario |
|---|---:|---:|---:|---|
| Todo universo, desde primera M1 tras FVG, +15m | 2.140 | **−1,919664** | [−3,549534; −0,402129] | Réplica del resultado preregistrado; nuevo bootstrap descriptivo |
| **Los que llegarían después a CE, desde el mismo inicio original, +15m** | **301** | **−4,594419** | **[−7,836663; −1,201525]** | Subgrupo definido por futuro, sesgado, NO filtro implementable |
| Los otros 1.839 sin testigo CE admisible a futuro, mismo reloj | 1.839 | **aprox. −1,481871** | Ver JSON del artefacto | Diferencia descriptiva, no prueba independiente |
| **301 con contacto CE; desde M1 posterior al contacto, +15m** | **301** | **−2,365615** | **[−6,088034; +1,324325]** | NO es CE→DOL, no es fill y su IC incluye cero |

Proporción de desplazamientos positivos **no equivale a win rate** de trades: conjunto total 47,06%; grupo CE-touch desde señal 45,85%; grupo postcontacto 46,84%. No hay prueba de expectancy neta positiva, PF/Sharpe/Sortino/DD ni de fills.

## Qué descarta y qué NO

1. **Refuta como evidencia económica positiva** que la dirección cruda de la metodología antigua tenga ventaja media en la ventana predefinida; la muestra que posteriormente alcanza CE **no revela una señal direccional positiva** en este screening.
2. **NO falsifica matemáticamente** el protocolo integral **G3 V1** CE LIMIT+C2 mecha completa+buffer tick oficial+2 ticks de riesgo+TP DOL+cancelaciones+liquidación 15:55, porque esa población **debe reconstruirse desde M1** con MSS anchor corregido y datos BID/ASK + OMS/ACK; no se ha hecho, G3 sigue sin dos firmas.
3. Exigir el subgrupo `CE seguido de DOL antes del stop C2` y después medir sólo esos retornos sería **selección retrospectiva de ganadores / tautología**: no seleccionable en tiempo real. Además la vela M1 OHLC **no resuelve la precedencia** entre CE, stop, DOL y revocación same-minute. Sin tick grid broker mismo símbolo, tampoco se puede adjudicar exactamente stop C2. No transformar esa celda en tercer test confirmatorio ni en operaciones.
4. La media **−2,365615 pts después de M1 de toque CE** no coincide con el precio CE: puede subestimar/sobrestimar el valor de una compra LIMIT, pero **tampoco ofrece evidencia positiva** para priorizar V1 frente a investigación nativa alternativa.
5. El umbral de negocio no es sólo `media > 0` sino edge **neto, robusto e independientemente repetible** con costes y Core gates. La actual V1 ni siquiera tiene los instrumentos de adjudicación para ello.

## Decisión P0 para el propietario

**`STOP / NO_GO`: congelar gastos y desarrollo de VT31 V1 por ahora.** Conservar GitHub ramas/hallazgos, 3Y de desarrollo, sus hashes y el acta unsigned, pero no comenzar integración G6/reescritura de filtros, replay económico, búsqueda de ganadores ni compra de USD125 de datos basándose en este proyecto. No habilitar PAPER operativo ni LIVE/VPS. No asumir que 51 B o 619 UNKNOWN cambian.

**Sólo reabrir con evidencia nueva no seleccionada retrospectivamente**: G3 firma dual válida, base de ticks históricos real del **mismo símbolo/bróker** y contrato/costes certificables (ideal fuente gratuita), motor V1 íntegro bajo nueva revisión propia y evaluación independiente preregistrada con holdout sellado. Si estos insumos no existen, clasificar `VT31_CE_EDGE_NOT_IDENTIFIED`, **NO** `ECONOMICALLY_FALSIFIED`.

### Estado de gates intacto

- G3 acta SHA `a446afa17ed6e411b8f0b6fc182b103a78959a97` + código SHA `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` **sin firmas**. Este trabajo no edita estos artefactos, ni exige reinicio de firmas.
- G5 BID/ASK cTrader: piloto #898 no encontró NAS100 habilitado en cuenta DEMO conectada; bloqueo de esa cuenta, no prueba de inexistencia global.
- G6 modelo V1 STOP+LIMIT+ACK: no integrado. G7 economía neta: no identificado. Holdout sellado, producción inalterada.

**Resultado operacional definitivo de esta decisión:** no invertir más recursos en VT31 V1 bajo la evidencia actual; el edge económico sigue desconocido, con señales exploratorias desfavorables y ninguna evidencia favorable nueva derivada de CE-touch.
