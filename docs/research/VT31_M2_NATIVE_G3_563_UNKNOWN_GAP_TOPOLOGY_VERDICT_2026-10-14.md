# VT31 M2 — Diagnóstico forense de los 563 UNKNOWN en el COG real (PR #944)
**Corte 14-OCT-2026.** **No certificación M2, cognitiva, económica ni Trader Lab.** Este ensayo no modifica la estrategia.

## Prueba original verificable
- **[CI GitHub Actions #38650370270: SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38650370270)**, código `04800576c73cdb7bf97656645a1613053b29eadf`, **111/111 tests PASS**, G3 COG/OPS y documento original con SHA bloqueados. Archivo [#11934272850](https://github.com/mezas3238-hue/qore-core/actions/runs/38650370270/artifacts/11934272850) ZIP SHA256 `3c927366a35a3bf24485e2fc8a0a40e9ceda58ae2321d0537089d67aa91f0f71`.
- Prerregistro previo al código: `5c59705b3c4f00581a65c5245045182a7497672b`. Rama de investigación child PR #942, DRAFT PR #944, no merge a main.
- Fuente NAS100 M1 exacta de GitHub Actions #11459859004, 1.059.784 M1, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Mismas 12 fechas de desarrollo predefinidas del #942, no fresh holdout. COG G3 genuino ejecutado vía rutina original #942, no DTO sintético.

## Resultado central
| Métrica separada | Resultado | Lectura correcta |
| --- | ---: | --- |
| Emisiones auténticas COG | 1.104 | Incluye tesis repetidas a lo largo de prefijos M1 |
| Primeras tesis diferenciadas | 441 | No son trades ni entradas broker |
| Ambas fuentes SUPPORTED | 541 emisiones / **212 primeras tesis** | Sólo linaje de pool QORE corroborado, no doctrina ICT |
| P3 UNKNOWN / V1 UNKNOWN | 485 emisiones / **210 primeras tesis** | Fuente post-confirmación con M1 incompletas |
| P3 UNKNOWN / V1 REJECTED | 78 emisiones / **19 primeras tesis** | Caso correlacionado 16-ENE-2024 |
| **Primeras tesis afectadas por UNKNOWN P3** | **229** | 210 + 19; ningún grupo fue homologado |
| **Intervalos exactos de faltante (deduplicados por start/end)** | **10** | No 563 fallos independientes |
| Intervalos enteramente en un día NY | **9** | Forma del hueco, no causa operativa demostrada |
| Intervalos que abarcan fin de semana NY | **1** | No autoriza presuponer cierre CFD |
| Suma de minutos de los 10 intervalos | **3.727** | Suma de duraciones intervalares; NO volumen de velas imputadas |
| Emisiones con al menos un gap intradía | **563** | Pueden coincidir con el hueco de fin de semana en la misma emisión |
| Emisiones con al menos un gap que cruza weekend | **78** | Esas 78 también contienen hueco intradía |
| Reetiquetados automáticamente como closed/confirmados | **0** | Fail-closed intacto |
| Órdenes/ACK/fills/PF/edge económico | **0/0/0/no calculado** | Sin derecho a operar |

**Los 10 intervalos se cuentan por su inicio/final UTC exacto, no por trades.** Las 563 emisiones con gap pueden compartir el mismo instante sin vela. La cifra 3.727 es la suma de duraciones de los diez intervalos (no una medición de liquidez negociada, no una autorización de imputación). El código registra intervalos y clasificaciones sin niveles de precio.

## Causa de falta de homologación
- El COG original `VT31CleanroomCognition` mantiene una tesis cuando el nivel no fue tocado **en las M1 observadas**. Los testigos externos #930/#932 requieren **continuidad desde el cierre del pool hasta as-of** para concluir `UNCONSUMED`. Ante un hueco, un barrido del DOL que hubiera sucedido en el tramo ausente no puede refutarse.
- Códigos P3 `POST_CONFIRMATION_M1_MONITORING_GAP` corresponden 1:1 a 563 emisiones con al menos un intervalo realmente ausente según la fuente de desarrollo. **No se descubrió un error de paridad interna del conteo**; persiste bloqueo de fuente.
- En 16-ENE-2024 (78 emisiones correlacionadas), V1 agrega el problema de semana anterior/cash 15-ENE-2024, festivo Nasdaq US: [notificación oficial Nasdaq 08-ENE-2024](https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2024-2). Esta noticia cash no certifica sesiones NAS100 CFD/USTEC ni continuidad de cotizaciones.
- Aunque la ausencia coincida con horario de cierre presumible, **no hay calendario PIT y especificación de símbolo broker suficientes** para convertirla en `MARKET_CLOSED_VERIFIED`. Por tanto las 563 permanecen UNKNOWN/no alineadas y M2 no puede ser aprobado.

## Siguientes acciones P0 para arquitecto
1. Tomar los **10 intervalos exactos** del artifact y cotejar sus marcas UTC/NY con historial M1 BID/ASK cTrader broker exacto, `event_time`, `receipt_time`, simbolización NAS100 vs USTEC, sesiones DST y feriados. Exigir contrato de cuenta/horarios/cambios de mercado y hash de fuente; **no** declarar closed con inferencia de fin de semana por sí sola.
2. Si source auténtica confirma `CLOSED`, especificar contrato causal `TRADING_CLOSED_VERIFIED` separado de `M1_MISSING_UNKNOWN`, con calendario PIT versionado y testigos negativos; **nuevo** prerregistro y propuesta versionada, no mutar G3 frozen.
3. En cada intervalo de ausencia sin cierre confirmado, mantener la decisión sin promoción `UNKNOWN`; verificar si existe quote posterior causal y orden de consumos. No adjudicar intrabar/fill por OHLC.
4. Completar la fuente por perfil TTrades AM #933/H1 09 y el original ICT GENERAL sin contaminar perfiles, M4 OB/Breaker/displacement, M5 stops/ACK y M6 doble frontera de aprobación independiente real.
5. Auditar conservación de artifacts GH Actions 90 días según issue #837. Custodia y hashes antes de caducar.
 
## Gobernanza
**NO MERGE, NO LIVE/DEMO/FundedNext/VPS, NO sizing propio VT31 (CIBO CMA tiene autoridad), NO orden al broker, NO certificación ficticia.** La ingeniería causal no implica que el trader sea rentable; Gates M2/M3/M4/M5/M6 y Trader Lab L1–L10 continúan abiertos.
