# VT08 CRT R7 — preregistro de comparación histórica de cierre FX vs huecos originales M5

**16 OCT 2026. RESEARCH ONLY; no aprobación G-M4, ni sustitución V3/G-M4.** Este documento queda en GitHub ANTES de ejecutar R7 sobre Atlas M5 original ya consumido. 139 V3; R6 confirmó 2 eventos `ALREADY_BEYOND_INVALIDATION` y 3 gaps M5 (2 viernes 21:00Z sin barra siguiente dentro de C3; 1 miércoles 22:30Z con barra 22:35 existente). Censo G7 108 WAIT arrastrado por 5 UNKNOWN originales. Nada de sizing/1R/lotes, capital, PnL o órdenes.

## Hipótesis descriptiva comprobable (no jurídica ni de broker específico)

Convención pública: Forex de domingo 17:00 ET a viernes 17:00 ET (fuente externa [FOREX.com: Market Trading Hours](https://www.forex.com/en-us/help-and-support/market-trading-hours/), convención de OTROS proveedores, no garantía del cTrader Atlas). El IANA America/New_York da viernes 21:00Z cuando NY usa EDT y 22:00Z en EST. R7 debe convertir cada hora con zoneinfo, no aplicar un UTC fijo ni “arreglar” gaps sin fuente.

## Algoritmo congelado antes de ver el resultado

1. Leer solamente `load_atlas_vt08_m5`, que comprueba SHA de proveedor, particiones y cronología; no descargar otro feed, no introducir broker credentials.
2. Por mercado inspeccionar los dos huecos semanales declarados 2025-04-25T21:00Z AUDUSD y 2026-06-19T21:00Z USDJPY, más el hueco interior 2025-02-12T22:30Z USDJPY. Comprobar exactitud de TIMESTAMP UTC, NY local, día de semana, presencia de M5 previa 5 minutos, ausencia del M5 objetivo, presencia de la siguiente 5 minutos y ausencia/presencia de cualquier otra M5 en la misma C3 hasta 00:00Z cuando corresponda. Nunca rellenar ni imputar OHLC.
3. Para CADA viernes con M5 reales en periodo investigado, computar corte convencional `Friday 17:00 America/New_York` para ese viernes convertido a UTC. Muestrear por separado evidencias `last_before_close_5m_present`, `first_after_close_5m_absent`, y `no_post_conventional_close_during_next_60m`; contar comparadores en bloque de ocho semanas antes/después de cada caso, sin excluir las semanas con datos discordantes ni horarios de vacaciones. No “validar el bróker” con convención.
4. Comparar el gap del miércoles dentro de mercado teóricamente abierto: requerir barras M5 a -5 y +5 minutos para reportar `INTERNAL_ONE_BAR_GAP`, no sustituirlas.
5. Producir resumen JSON y `r7-original-m5-gap-evidence.jsonl` que hagan trazable mercado, hora, días, evidencias, estado `CONVENTION_CONSISTENT_PROVIDER_CALENDAR_UNVERIFIED` / `INTERNAL_ONE_BAR_GAP_PROVIDER_SOURCE_REQUIRED` / `NOT_CONSISTENT`, y flags explícitos `G_M4_PASS=false`, `terminal_adjudicated=false`, `no_sizing=true`. Nunca volcar retornos, precio futuro, sizing ni PnL.
6. Tests sintéticos de las tres fechas (verano EDT, invierno EST, miércoles aislado), feed discordante, timestamps erróneos, market isolation. CI Ruff/mypy/pytest y ambos mercados originales; si cualquiera falla, no proclamar éxito.

## Criterios / prohibiciones

- No reetiquetar los 5 G-M4 UNKNOWN: R7 agrega diagnóstico distinto y separado del ledger de decisión. 2 casos "entry beyond invalidation" ya observados en R6 también siguen UNKNOWN.
- Clasificador no concede expiración económica ni fuente CRT y NO elimina el arrastre de 108 WAIT. Resolver la semántica de expiración y el scope de lineage G7 requiere revisión G-M1 independiente con regla congelada ANTES de OOS nuevo. Una vela de miércoles sin testigo del proveedor original debe quedar censurada si no se recupera con provenance.
- Los viernes constituyen *plausibilidad empírica de cierre habitual*, **NO** una constancia del schedule del broker cTrader histórico. En particular los calendarios de símbolos pueden cambiar por cuenta/servidor; exigir calendario autentificado con fecha y símbolos exactos para cierre jurídico de G-M4.
- G-M1..4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED. CIBO/Risk exclusivamente sizing y DD patrimonial; sin live/demo/órdenes/VPS/merge.
