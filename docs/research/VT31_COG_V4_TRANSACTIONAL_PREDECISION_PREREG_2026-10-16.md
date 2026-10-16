# VT31 — COG V4 / two-phase commit transaccional (PRE-REGISTRADO ANTES DEL CÓDIGO)

Fecha: **2026-10-16**. Base PR #986, commit `584085da5e90e26dd756e10b144a693884acf64f`; fuente V3: `scripts/vt31_m0m4_continuous_tape_seal_cog_v3_20261015.py`, CI #38820088606 203 PASS. Scope exclusivo: cognitiva research M0→M4, un VT31. Ni G3 original ni el código OPS serán alterados.

## Bloqueo B26 observado
V3 accede a `V2._last_assessed` para hacer rollback cuando la validación M4 retorna REJECT o falla. Este acoplamiento al estado privado del evaluador V2 es frágil: futuros cambios internos pueden modificar otra variable o volver incompleto el rollback. El requisito del COG exige que un REJECT sea **atómico**, sin modificar el estado cognitivo autorizado, y permita reenviar el mismo minuto corregido.

## Solución propuesta antes de escribir código
- **V4 aditivo con PREPARE / COMMIT**: el candidato mantiene una referencia al V2 `VT31M0M4CognitiveCandidate` comprometido. Cada intento duplica mediante `copy.deepcopy` ese objeto antes de evaluar. Sólo un veredicto `WAIT` de la copia y evidencia fuente completa autoriza la sustitución atómica del objeto comprometido junto a un sello `ObservedTapeSeal(last_as_of,count,sha256_total)`. `REJECT`, excepción o input malformado: descartar copia y conservar **misma identidad del objeto comprometido**, sello, SHA, tiempo y contexto previos. Nunca leer ni escribir `_last_assessed`, `_source` u otro atributo interno de V2 desde V4.
- En M0 la evaluación se hace igualmente sobre copia PREPARE; only WAIT con `context is not None` crea seal; MIN10 WAIT, ICT London y NYPM UNKNOWN no crean seal. REJECT no muta candidato.
- Antes de PREPARE M4: contexto NYAM comprobado, `as_of` aware estrictamente superior, tupla tipada M1, longitud mayor, SHA256 del **prefijo total comprometido** idéntico, datos family explícitos y listas no aceptadas (usar tuplas). V2 continúa probando continuidad temporal de 10h, H1 09, barrido, mismas OHLC originales y swing.
- `WAIT` sigue siendo investigación, no promoción M3/M4/M5. Ni el tipo V4 ni outputs admiten `ORDER`, `PASS`, `BUY/SELL`, sizing o órdenes; se exige `action ∈ {WAIT, REJECT}`. Fallo interno en duplicación, serialización o validación implica REJECT con razón tipada.
- El sello V4 se calcula antes del COMMIT; si falla SHA, no hay COMMIT parcial. Tests monkeypatch de `V2.assess_later_retest` inyectarán REJECT tras mutación interna, excepción tras mutación, y WAIT sin fuente causal, para comprobar que el objeto original comprometido es inmutable en todos esos casos.
- Regresiones: positivo M0→M4 LONG/SHORT enero EST/julio EDT, 4 contextos compatibles/4 MIN10, London/NYPM UNKNOWN, REJECT forjado y reintento mismo `as_of`, fork M1 tras WAIT, gap, sesión incorrecta, replay, excepción V2, fuente de familia malformada, SHA completo M1 y dos evaluaciones sucesivas.
- CI GitHub Actions Python 3.12, Ruff, pytest-xdist `-n 4`, prueba integrada V2/V3/M0/M4, hashes congelados de G3 COG `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2`, acta `e99c70b4e018d626fb620d9a21b9314a51abc36d`. JSON, SHA256SUMS, artifact, y verificar commit PRE-REG como antecesor del código.

## Falsación y límites
Un test falla si el objeto de V2 comprometido cambia de identidad o contenido tras REJECT, si un minuto inválido no puede repetirse tras corrección, si el sello avanza por rechazo, o si se genera alguna autorización operativa. Esta V4 todavía es **`scripts/` de investigación**, no COG nativo aprobado ni firma humana. Pendientes: M0 policy Owner, doctrina autoral M3 MSS, cuatro entradas M4, stop swing M5, revisión humana COG/OPS Issue #897, caso ICT London y NYPM. No PnL, lot sizing, órdenes, OMS, VPS, LIVE, merge a main.

**Estado invariable:** METODOLOGÍA=PENDIENTE, COGNITIVA=PENDIENTE. Pruebas sintéticas no homologan doctrina ni datos reales.
