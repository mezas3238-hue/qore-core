# VT31 — Preregistro CENSO M1 REAL (TTrades NY AM COG source-only)
Fecha 14-10-2026. Esta preregistración se crea ANTES del script de censo / de abrir datos 3Y para esta ronda.

## Fuente congelada y límites
- Fuente única inmutable: NAS100 CFD 3Y ya usado en estudios anteriores del proyecto, 2023-10-01 a 2026-10-01, exactamente 1,059,784 velas M1; ZIP GitHub Actions artifact **11459859004**. Verificar hash SHA256 del JSON **0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa** antes de cualquier análisis.
- Esta muestra 3Y fue examinada previamente para otros estudios VT31 y NO es OOS / Fresh Holdout. No abrir datos futuros más allá del as_of de cada decisión. No modificar parámetros en respuesta al censo; NO calcular PnL, WR, PF, retornos a futuro, fills, stops, capital ni sizing.
- Base metodológica: propuesta `propose_ttrades_am_cognition` **ya congelada** en PR #933 @ `1556766c1831190b5459bf93404081412200ba7d`, tests CI 154 PASS. El censo no cambia ese código.

## Pregunta y método ex ante
¿Cuántos días NY con M1 completos 09:00–11:00 ofrecen un primer barrido y primer regreso, cuántos tienen MSS QORE en el mismo primer regreso, y cuántos DTO obtienen confirmación de testigos M1 independientes #929 y V2?

1. Leer y validar TODO M1 en orden; agrupar por fecha NY 09h y 10h sin deducir mercado de futuros. Días con horas incompletas => `INCOMPLETE_M1_HOURS`, separados sin interpolar.
2. Para cada día con las 120 M1 completas, avanzar `as_of` CERRADO cronológicamente desde 10:01 a 11:00, llamando al productor `propose_ttrades_am_cognition` con sólo el prefijo conocido (09h completo + 10h hasta ese cierre).
3. Detener adjudicación de la oportunidad al PRIMER retorno direccional posterior al primer sweep, o al primer rechazo/ambigüedad, o al cierre de sesión. Nunca esperar retornos posteriores para rescatar una mala decisión (sin hindsight ni reintentos que aumenten densidad).
4. Emitir conteos por categoría disjunta: `CONTEXT_ATTESTED_NOT_CERTIFIED`, `QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN`, `AWAIT_SWEEP`, `AWAIT_RETURN`, `REJECTED`, `UNKNOWN_*`, `INCOMPLETE_M1_HOURS`. Guardar evidencia agregada, prefijos de muestra y hashes; no PnL ni optimizar.
5. No comparar tasa con inventada rentabilidad de otros traders ni asumir que un día = trade/fill. 0 trader-certificación, 0 LIVE, 0 sizing, 0 MERGE.

## Condiciones de aceptación
- Fuente SHA exacta; M1 total exacto; sin mirar OHLC futuro desde cada `as_of`; 0 leaks; contabilidad consistente: suma de estados = total días con velas en intervalo 10h.
- COG/OPS G3 frozen original hashes, CI Ruff + tests sintéticos e integración + censo factual. Diferenciar `SOURCE_NATIVE_MATCH` de método autoral y edge.
- Si el artifact no está accesible, publicar `BLOCKED_DATA_ARTIFACT` con error real, no inventar tasas ni comprar datos. No reducir reglas para inflar oportunidades.
