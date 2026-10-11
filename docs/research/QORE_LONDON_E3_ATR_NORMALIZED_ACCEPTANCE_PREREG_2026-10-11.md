# QORE Londres E3 — ¿RECLAIM/ACCEPTED depende de la escala de volatilidad?

**Prerregistro publicado ANTES de programar detector, calcular E3 o consultar sus tasas.** 2026-10-11. EURUSD/GBPUSD exclusivamente. GitHub Trader Lab, sin MT5, VPS, V49, DCVC, Master Frame, tick BID/ASK ni trader.

## La interpretación a corregir

No confundir una reducción relativa de la **estimación de interacción** de +22,38 pp a +14,42 pp al cambiar la cohorte con un "36% del efecto concentrado en días rotos". Esa atribución causal no se sigue. La H4 estricta exigía 720/720 M1, y la proxy E2 45/60 min y <=5min de staleness, **H4 desconocida no implica que las 11 velas del raid estén corruptas**. La causa del missingness y su correlación con resultados queda UNRESOLVED. El ajuste H4 en idéntica cohorte cambia +14,42 a +14,33 pp.

Originales congelados: [run #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682) = 522 filas (261 días ×2), 227 EUR + 231 GBP CHECKPOINT_VALID, y resultados +60m idénticos; four-cell ledger [EUR RECLAIM 94/38 reversal; EUR ACCEPTED 115/40; GBP RECLAIM 92/22; GBP ACCEPTED 123/50]. H4 E2 observacional from [run #38152552686](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686) same identities and E2 H4 statuses, no recalcular el pasado. M1 nativo [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), frozen SHA 18c338aedd5013ce65a6cb6408ffbc2e904a6217. Análisis EXPLORATORIO porque mismo período ya visto (no OOS).

## Test 0 — falta de H4 E2 y control de cobertura, sin atribución causal

Recalcular CONTRASTE DESCRIPTIVO por estratos de H4 E2: \`KNOWN\` (aligned/opposed) y \`UNKNOWN\` (cualquier otra). Interacción I = [EUR(PREV|R)-EUR(PREV|A)] - [GBP(PREV|R)-GBP(PREV|A)] para estados originales y en cada estrato. Publicar cuatro celdas, N, IC bootstrap de 2.000 bloques de cinco fechas NY compartidas, y la distribución por hora/día. Si efecto mayor en UNKNOWN, solo se justifica investigar cobertura, NO concluir que H4 no reconstruible causó el efecto. Nunca imputar H4 ni reetiquetar original.

## Test 1 primario — aceptación NORMALIZADA por volatilidad local (independiente de 3 cierres)

Conservar las 458 oportunidades CHECKPOINT_VALID e inmutables outcome \`terminal_60\` = REVERSAL/CONTINUATION/NEUTRAL a umbral original ±0.25 Asia Range desde checkpoint +60m. No recodificar resultados. Reloj America/New_York y Asia 20:00 previo–00:00 día del raid, primero cruza 02:00–05:00 NY; checkpoint close tras **11 M1 exactas** desde primer raid. E3 solo mide magnitud de extensión al checkpoint, nunca retorno futuro.

- \`ATR14_M15_ASIA\`: construir 16 barras M15 no solapadas de Asia de las 240 M1 originales (240/240 para cada caso CHECKPOINT_VALID). Las 15 últimas barras permiten calcular 14 valores TR, cada uno con previous M15 close:
  TR = max(M15_high-M15_low, abs(M15_high-previous_M15_close), abs(M15_low-previous_M15_close)).
  ATR14 = promedio aritmético de los 14 TR de las últimas 14 barras M15 Asia (índices 2..15, 0-based; barra previa índice 1). Nunca M1 posterior a 00:00 NY. Fail closed si 240/240 no disponibles, duplicados, duraciones invalidas, ATR <=0. Esa es volatilidad del mercado previo; NO ATR de serie H4 ni fuente autoral.
- \`normalized_extension_at_checkpoint\` = (checkpoint_close-AsiaHigh)/ATR14 si raid HIGH; (AsiaLow-checkpoint_close)/ATR14 si raid LOW. Positivo = cierre fuera al lado del raid. Si el precio cierra más allá del extremo opuesto, estrato \`OPPOSITE_OUTSIDE\` y excluido del contraste R/A.
- NUEVA clasificación exclusiva al checkpoint: \`RECLAIM_INSIDE\` = cierre dentro del Asia low..high (exactamente mismo criterio espacial original; no exige número de cierres); \`ACCEPTED_ATR_0P5\` = extensión NORMALIZADA >= **0.50 × ATR14 M15** desde el extremo asiático a la hora del checkpoint, con independencia de cuántos cierres consecutivos hubo fuera; \`OUTSIDE_WEAK\` = cierre fuera hacia raid pero distancia < 0.50 ATR14; \`OPPOSITE_OUTSIDE\`. E3 no usa la regla temporal tres cierres para declarar aceptación. No optimizar 0.5 sobre outcomes; un único umbral fijo es diagnóstico, no regla del autor.
- Publicar censo de todas las transiciones originales a estados E3, no solo celdas convenientes: R/A originales pueden caer en OUTSIDE_WEAK y estados originales OUTSIDE_UNCONFIRMED podrían entrar ACCEPTED_ATR. Censura/UNKNOWN con counts; no buscar retrospectivamente mejor umbral.

**Contraste primario:** sobre E3 \`RECLAIM_INSIDE\` y \`ACCEPTED_ATR_0P5\`, I_E3 = [P_REV(EUR,R)-P_REV(EUR,ATR)] - [P_REV(GBP,R)-P_REV(GBP,ATR)]. IC 95% por bootstrap de 2.000 remuestreos circulares de bloques de cinco fechas NY compartidas, seed 77520261013. Dos mercados no constituyen validación OOS, ni independencia. Registrar mínimo N10 por celda descriptiva; si alguna celda <10 => INCONCLUSIVE_NO_SUPPORT. Bootstrap con celdas vacías se cuenta como inválido, no se reemplaza.

**Secundario descriptivo (no otro modelo promocionable):** comparación de las tasas de reversión y continuidad de \`OUTSIDE_WEAK\` y distribución de \`normalized_extension_at_checkpoint\` por ambos símbolos (mediana/IQR), \`asia_range_pips\` y \`ATR14_M15_pips\`, y la matriz \`original_state → E3_state\`, a fin de diagnosticar si las etiquetas de tres cierres agregan grupos de volatilidad distintos. Si E3 interaction se debilita/fortalece, reconocer que universo de contraste cambió y compararlo además en la misma cohorte elegible (no inferir que "volatilidad causó" la divergencia).

## STOP / GO y límites

- El test es sensibilidad post-resultados, **exploratorio**, no validación confirmatoria ni hipótesis TTrades original.
- CI de E3 que incluya cero = no confirmación de divergencia; que lo excluya = investigación/replicación futura; ninguno autoriza filtros, CISD, SMT, trader, stops ni PF.
- No cambiar 60min ni ±0.25×Asia Range outcomes existentes; no ajustar 0.50 ATR14, tres cierres, pares ni periodos.
- **SMT NO forma parte de E3** ni queda falsado si E3 falla; para SMT importa divergencia de confirmación de extremos *sincrónica*, que puede existir independientemente de la etiqueta RECLAIM. Antes de cualquier SMT, calcular base rate dentro de la misma ventana de confirmación para decidir potencia, separado.
- GitHub/Trader Lab exclusivamente, sin producción.
