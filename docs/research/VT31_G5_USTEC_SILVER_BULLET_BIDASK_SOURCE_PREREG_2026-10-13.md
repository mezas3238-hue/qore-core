# VT31 G5 — Preregistro de fuente USTEC BID/ASK para horas Silver Bullet (2026-10-13)

**SOLICITUD DEL PROPIETARIO: descargar desde cTrader los BID/ASK históricos faltantes.** Fase inicial: adquirir cobertura REAL en reloj correcto, no probar PnL. Rama de investigación separada, derivada de [QORE Native PR #854](https://github.com/mezas3238-hue/qore-core/pull/854), reutiliza recuperador broker de [PR #853](https://github.com/mezas3238-hue/qore-core/pull/853). No cambiar Acta G3 ni código COG/OPS de [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896), no acceder a Fresh Holdout, no órdenes, no VPS, no LIVE.

## Ventanas fijas ANTES de adquirir precios

Fuente: IC Markets cTrader **DEMO**, proveedor EXACT **USTEC**, symbolId **10014**, BID y ASK oficiales **por separado** (ProtoOAGetTickDataReq); es **CANDIDATO** a NAS100, NO contrato NAS100/NDX100 homologado. Revalidar broker demo, identidad de cuenta efímera, USTEC enabled + ID10014 antes de leer cualquier tick. Debe usarse histórico que ya sea desarrollo **antes del holdout fresco**.

- Día NY **2024-06-12 (EDT, UTC-4)**: London 03–04 = 07:00–08:00Z; NY AM 10–11 = 14:00–15:00Z; NY PM 14–15 = 18:00–19:00Z.
- Día NY **2025-01-15 (EST, UTC-5)**: London 03–04 = 08:00–09:00Z; NY AM 10–11 = 15:00–16:00Z; NY PM 14–15 = 19:00–20:00Z.

**6 horas históricas, 12 side-streams, como lote de capacidad antes de expandir a ~3Y.** Las fechas fueron elegidas por cobertura estacional, no por señales VT31, PnL, intervalos conocidos con fills ni mejores retornos. La selección de dos fechas no implica cobertura de todo VT31 y **no da permiso a seleccionar ganadores**. Sin extrapolar spread/cobertura de estas dos fechas al resto del histórico.

## Controles fuente y límites explícitos

- Zona IANA `America/New_York`; convertir inicio/fin a UTC y comparar offset DST esperado, sin adivinar horarios por screenshot.
- Cada hora como rango [start, end), 1 hora máximo, dos flujos separados BID y ASK; decoder fuente probado cTrader: primer timestamp/price absoluto, subsiguientes signed deltas, paginación `hasMore` o BLOQUEAR. El componente QORE Native `complete_side` limita a **64 queries por lado/hora**.
- Presupuesto adicional total: **300 requests nativos** en todo el lote y timeout CI **35 min**. No emitir ni enviar órdenes, sin refresh OAuth. Ante error: adjuntar manifiesto con causa segura, no rellenar ceros ni interpolar.
- Guardar tick nativo INTEGER y normalización decimal fiel por lado con epoch UTC ms, índice causal de secuencia por timestamp; hash SHA256 por archivo, `SHA256SUMS`, manifest de procedencia, commit, workflow y fuente, cobertura por hora/dos lados. **NUNCA subir precios al Git público**, sólo GitHub Actions artifact con retención limitada a **90 días**, pendiente vault autorizado.
- Una cotización de lado no implica cotización ejecutable del lado opuesto. 0 filas ≠ missing=0 o coste cero; same-ms sin orden causal verificado no inventa prioridad; ASK/BID positivos y staleness se auditarán después.
- **STOP/DOCTRINA:** no lanzar reconstrucción V1, replay, papel económico, holdout ni certificar. Registro de `NATIVE_USTEC_SAMPLE_ONLY_NAS100_UNHOMOLOGATED` hasta homologar contrato y calcular verdaderas coberturas/latencias/costes por entry/exit.

## Escala posterior a la validación

Si y solo si el lote retorna BID+ASK fuente completos con hashes y bajo presupuesto, construir manifiesto de todos los días del desarrollo VT31 por sesión NY; dividir en shards por día/hora con journaling y SHA inmutables, cuotas/rate limits y restauración permanente de vault **antes** de un volcado de millones de ticks. Las velas M1 de VT31 proceden de otro universo/proveedor; la verificación de identidad/equivalencia económica será independiente, nunca sustituida por proximidad de precios.

**Par G3 SIN CAMBIOS:** doc `a446afa17ed6e411b8f0b6fc182b103a78959a97`, código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`; sigue `G3_PENDING_DUAL_SIGNATURE`. El propietario autorizó recuperación SOURCE, no certificación de estrategia.
