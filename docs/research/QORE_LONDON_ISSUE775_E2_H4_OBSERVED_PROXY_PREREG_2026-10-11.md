# E2 Prerregistro — reconstrucción de H4 observada con M1 no contiguas (NO H4 strict)

**Fecha:** 2026-10-11. Este documento se publica antes de consultar resultados de clasificación H4 bajo reglas E2. **E1 permanece inmutable**, [resultado](https://github.com/mezas3238-hue/qore-core/blob/research/london-eur-gbp-divergence-h4-audit-20261011/docs/research/QORE_LONDON_ISSUE775_E1_BOOTSTRAP_H4_EXECUTED_RESULTS_2026-10-11.md): interacción +22,38pp, IC95 [+7,34,+36,91]pp; E1 H4 strict 0/458 por faltar ≥1 M1 en cada ventana de 720 M1. Este E2 es una **sensibilidad diagnosticada DESPUÉS del bloqueo E1**, no test independiente de verdad, ni criterio ajustado por outcome, ni reconstrucción del H4 autoral.

## Fuentes y universo congelados
Los mismos 261 días NY/mercado, los mismos 458 checkpoints, estados y `terminal_60` del replay #38150980682, y los mismos M1 nativos del run #35548099334. **FAIL CLOSED** para sus conteos y rates originales. Ningún dato económico alterado, ningún trade, ninguna selección por resultado.

## Nueva convención H4 observada fija ANTES de medir sus tasas
- Velas nominales H4 UTC 00,04,08,12,16,20; tres intervalos H4 **consecutivos y nominalmente terminados** antes o en `raid_at`. Nunca barra en formación ni apertura temporal posterior.
- Cada intervalo H4 incluye 4 horas, **cada hora contiene >=45 de 60 minutos M1 nativos observados** (umbral operativo de cobertura 75%; no inferencia de que reflejan un H4 de proveedor oficial).
- El CLOSE de cada H4 estimado es el cierre del **último M1 observado** del intervalo, siempre que su `closed_at` esté **como máximo 5 minutos antes** del cierre H4 nominal y nunca después. Si falta, `H4_PROXY_UNKNOWN_CLOSE_STALE`. El cierre no se lleva adelante desde la siguiente barra, no se interpola, no se inventa tick de 00/04/08 UTC. Se registra `last_M1_closed_at` como evidencia para cada H4. Todos los precios elegidos son estrictamente pre-raid.
- Una hora con 44 o menos M1 causa `H4_PROXY_UNKNOWN_LOW_COVERAGE`; otro gap mayor causa UNKNOWN; no reconstruir H4 si no cumple. H4 3-closes dirección: `sign(last_close - oldest_close)`, alineado/opuesto al HIGH/LOW raid como en E1. Si ==0 `H4_FLAT`.
- **No cambiar umbral 45/60 ni frescura 5 minutos** después de ver tasas. Datos faltantes por apertura/rollover/jornadas se reportan; no usar `H4_UNKNOWN` como etiqueta predictiva ni seleccionar solo días de buen resultado.

## Contraste y control de composición
Misma diferencia de diferencias D_EUR-D_GBP que E1; comparar (i) raw full 458, (ii) raw exclusivamente con H4 E2 válido, (iii) estandarizado con pesos comunes entre `H4_ALIGNED_WITH_RAID` y `H4_OPPOSED_TO_RAID`, requiriendo **>=10 casos por cada una de las cuatro celdas** EUR/GBP × RECLAIM/ACCEPTED en cada régimen. Si una categoría no tiene soporte, excluirla y renormalizar los pesos, especificando universo y pérdida de cobertura; si ninguna, H4 E2 `INCONCLUSIVE` sin estimar efecto.
Mismo bootstrap circular 2.000 remuestreos de bloques de cinco jornadas NY COMPARTIDAS entre EURUSD y GBPUSD; seed 77520261012. No inferir que perder significancia equivale a desaparecer efecto. Definir caída material descriptiva como reducción absoluta >=50% entre interacción de **la misma submuestra H4 válida** sin estandarizar y estandarizada. Predecir que H4 es causa sería ilegítimo; se trata de control observacional de confusión, **no prueba causal de H4**.
Reportar N de cada régimen, datos faltantes y motivos, p_reversal, intervalos; suprimir cualquier resultado que no cumpla cobertura.

## Condición STOP
Publicar resultados negativos/inconclusos. No autorizar filtro H4, no rescatar estrategias. La divergencia del histórico y H4 E2 son exploratorias; la hipótesis SMT requiere ensayo separado con definiciones causales y reproductibilidad propia, no combinaciones en esta ronda. No mezclar con TTrades CISD fiel, V49/DCVC, Master Frame, VPS/MT5 live; GitHub/Trader Lab exclusivamente.
