# QORE — Londres: qué hace el precio DESPUÉS de barrer Asia (EURUSD/GBPUSD)
## Replay source-only ejecutado; la continuación no domina, y la confirmación no transfiere entre pares

**Fecha:** 2026-10-11 · **Estado:** `SOURCE_ONLY_REPLAY_EXECUTED / EXPLORATORY / NO_TRADER`
**Ejecución [GitHub Actions #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682) = 4/4 SUCCESS** (contrato causal + EURUSD + GBPUSD + consolidación). Source SHA exacto: `125bc37709f36ccf9295f6dbd6cc390b44b266c8`. [Aggregate #11705888567](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682/artifacts/11705888567); [EURUSD ledger #11706409700](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682/artifacts/11706409700); [GBPUSD ledger #11705588964](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682/artifacts/11705588964).
**Prerregistro previo a resultados:** commit `ac867df8cab663af9671574f31cd7b08d9bac581`, [reglas](https://github.com/mezas3238-hue/qore-core/blob/research/london-after-asia-sweep-path-20261011/docs/research/QORE_LONDON_AFTER_ASIA_SWEEP_TTRADES_SOURCE_ALIGNED_REPLAY_PREREG_2026-10-11.md). [Revisión de YouTube/TTrades](https://github.com/mezas3238-hue/qore-core/blob/research/london-after-asia-sweep-path-20261011/docs/research/QORE_LONDON_YOUTUBE_METHODS_SOURCE_REVIEW_2026-10-11.md). [PR #779](https://github.com/mezas3238-hue/qore-core/pull/779).

### A. Qué metodología se probó, y qué NO
Perfil primario del autor: https://ttrades.com/london-reversal-and-new-york-continuation-daily-profile/ ; vídeo https://www.youtube.com/watch?v=y6SnEdASVLY . H1 horario Asia **20:00–00:00 EST**, London **02:00–05:00 EST**. Se implementó *America/New_York* con DST como **interpretación QORE**, no prueba de que EST fijo/EDT sea lo que quiso el autor.
Definición mecánica: M1 provider-native #35548099334, 2025-09-17 a 2026-09-17, sin interpolación; 240/240 minutos previos NY 20:00–00:00; primera vela de London 02:00–05:00 que supera high o low asiático, excluyendo ambigüedad high+low simultáneos y gaps. Un checkpoint al cierre de las primeras **11 M1 incluyendo primera ruptura**, sin mirar outcomes. A ese instante clasificamos cierre: `RECLAIM_INSIDE`, `ACCEPTED_OUTSIDE` (3 cierres fuera consecutivos), `OUTSIDE_UNCONFIRMED` u `OPPOSITE_OUTSIDE`. Proxies CISD (cierre más allá del open de secuencia anterior de velas de mismo signo) y ruptura swing M1 (pivot 3 velas confirmado por derecha) as-of; ambos **NO son equivalencia certificada a CISD/MSS del autor**: falta displacement y adjudicación de swing.
Outcomes, no señales: desde cierre del checkpoint, +30/60/120m de cierres M1 y cambio firmado desde checkpoint en unidades `AsiaRange`. A +60m `REVERSAL` si <=−0,25 rango asiático, `CONTINUATION` si >=+0,25, `NEUTRAL` entre ambos. También primer toque ±0,25 rango a 60m sin adjudicación arbitraria si ambos en misma M1. **Cero órdenes/SL/TP/PF/WR/broker.** M1 sirve para rutas/timing, no fill de stop estrecho. Se respeta histórica ya inspeccionada (no OOS).

### B. Cobertura y tasa de primer contacto al cambiar el rango autor-inspirado

| Control (una jornada por par) | EURUSD | GBPUSD |
|---|---:|---:|
| NY jornadas laborables con M1 | 261 | 261 |
| Asia 240/240 completa | 237 | 241 |
| Primero toca high o low Asia durante London | **229 / 237 (96,62%)** | **233 / 241 (96,68%)** |
| Sin raid | 8 | 8 |
| Raid demasiado tarde para checkpoint | 2 | 2 |
| Checkpoints válidos y outcomes 60m conocidos | **227** | **231** |
| Raid inicial 02:00–02:59 NY entre checkpoints | 186 | 197 |

**IMPORTANTE:** los 96,6% no son comparables directamente con 82–89% anterior: cambiamos explícitamente de Asia 00–08 UK a Asia 20–00 NY, y de London 08–11 UK a 02–05 NY. El primer cruce del high/low de un rango más estrecho es casi universal en estos datos; **no indica por sí mismo reversión ni continuación rentable**.

### C. Evolución del precio +60 minutos DESPUÉS de checkpoint

| Outcome terminal ≥0,25 Asia Range | EURUSD n=227 | GBPUSD n=231 |
|---|---:|---:|
| `REVERSAL` | **81 (35,68%)** | **80 (34,63%)** |
| `CONTINUATION` | 61 (26,87%) | 69 (29,87%) |
| `NEUTRAL` | 85 (37,44%) | 82 (35,50%) |
| Censuras de 60m | **0** | **0** |
| Primer toque barrera de reversión −0,25 rango en 60m | **126** | **115** |
| Primer toque barrera de continuación +0,25 rango en 60m | 97 | 111 |
| Ninguna barrera tocada en 60m | 4 | 5 |

**Son DOS preguntas diferentes**: close al minuto 60 versus orden del primer toque de barreras a lo largo de la hora. No afirmar `126 trades ganadores`: no existen órdenes y precio de entrada operativo. La ganancia/pérdida no forma parte del ensayo.

Variación promedio del precio en dirección de la ruptura en unidades del rango Asia: EURUSD +30m **+0,00165**, +60m **−0,04432**, +120m **−0,05481**; GBPUSD +30m **−0,01011**, +60m **−0,04691**, +120m **−0,02722** (GBP 120m cubre 230/231). Las medias, por sí solas, no establecen ventaja de reversión.

### D. El hallazgo CONDICIONAL más importante: el estado RECLAIM no funciona igual en ambos pares

**Todos los siguientes estados están fijados usando solo once M1 hasta checkpoint, SIN mirar +60m:**

| Par / estado al checkpoint | N | Reversión +60m | Continuación +60m | Neutral |
|---|---:|---:|---:|---:|
| EURUSD **RECLAIM_INSIDE** | 94 | 38 (40,43%) | 23 (24,47%) | 33 |
| EURUSD **ACCEPTED_OUTSIDE** | 115 | 40 (34,78%) | 31 (26,96%) | 44 |
| EURUSD OUTSIDE_UNCONFIRMED | 18 | 3 (16,67%) | 7 (38,89%) | 8 |
| GBPUSD **RECLAIM_INSIDE** | 92 | 22 (23,91%) | 26 (28,26%) | 44 |
| GBPUSD **ACCEPTED_OUTSIDE** | 123 | 50 (40,65%) | 39 (31,71%) | 34 |
| GBPUSD OUTSIDE_UNCONFIRMED | 15 | 7 (46,67%) | 4 (26,67%) | 4 |
| GBPUSD OPPOSITE_OUTSIDE | 1 | 1 | 0 | 0 |

**Contraste DESCRIPTIVO preregistrado** P(reversión | reclaim) - P(reversión | 3 cierres fuera):
- **EURUSD: +5,64 puntos porcentuales**, bootstrap jornadas 95% **−8,01 a +18,90 pp**: indistinguible de 0 para este contraste descriptivo.
- **GBPUSD: −16,74 puntos porcentuales**, bootstrap jornadas 95% **−28,92 a −4,39 pp**: diferencia histórica negativa, **en la dirección contraria a la expectativa simple** de que reclaim necesariamente antecede a reversión.
- ***No es efecto causal ni validación OOS.*** Los pares comparten sesiones y factores USD. Umbrales/horarios son QORE preregistrados, no entrada exacta TTrades. No se permiten ajustes ad hoc por payoff. Los 2.000 remuestreos son por observaciones de jornada; como hay un primer raid máximo por par/día, no hay trade duplicado intradía.

### E. Proxies tipo CISD y estructura: evidencia preliminar, NO regla autoral adjudicada

| Confirmación as-of ≤checkpoint | EURUSD casos | EURUSD reversión | GBPUSD casos | GBPUSD reversión |
|---|---:|---:|---:|---:|
| CISD_PROXY presente | 118 | 42 (35,6%) | 115 | 44 (38,3%) |
| CISD_PROXY ausente | 109 | 39 (35,8%) | 116 | 36 (31,0%) |
| STRUCTURE_CLOSE_PROXY presente | 71 | 31 (43,7%) | 75 | 27 (36,0%) |
| STRUCTURE_CLOSE_PROXY ausente | 156 | 50 (32,1%) | 156 | 53 (34,0%) |

El CISD proxy **no separa** el resultado EURUSD, y parece moderadamente distinto en GBPUSD sin garantía estadística ni fuente exacta. Ruptura de swing proxy difiere descriptivamente en EURUSD, débilmente en GBPUSD. Como los dos proxies **son interpretaciones**, estos contrastes NO demuestran que `el CISD TTrades funciona/falla`. MSS autoral requiere displacement y swing correcto, hoy no probados.

### F. Dictamen y siguiente decisión

**HECHO:** under source-aligned NY session Asia high/low, primer raid en 96,6% de jornadas elegibles; más casos terminan revertidos que continuados al umbral 0,25 rango al cierre a +60m; **RECLAIM no discrimina de forma estable entre EURUSD y GBPUSD**. El "aceptado fuera" tampoco garantiza continuación. No hay ventaja económica probada.
**GATE C de fidelidad aún abierto:** adjudicar exactamente el `CISD` del vídeo/autora, displacement/MSS y `draw on liquidity` (sesgo HTF) antes de operar. Los **CISD_PROXY / STRUCTURE_CLOSE_PROXY** se mantendrán explícitamente QORE, no features certificados.
**El protocolo científico permanece:** ni stops de 1 pip ni BID/ASK para este censo de rutas; tampoco rescatar resultados mediante thresholds post hoc. Un nuevo modelo económico necesitaría prerregistro, OOS real, ejecución y riesgos separados.
**Sin modificación** de V49, DCVC, Master Frame, VPS, MT5, trader productivo; **Scalper y Londres NO CERTIFICADOS**.
