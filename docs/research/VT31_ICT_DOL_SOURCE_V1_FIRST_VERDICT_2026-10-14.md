# VT31 — ICT_DOL_SOURCE_V1 · Primer dictamen M2 (14-OCT-2026)

## Custodia
- Antecedente código base: PR #929, commit `54ed47d35db25df5c47115cac6888da4c58801d7`.
- Handoff maestro independiente: PR #931, commit `778e419d005951c0efb435256cb0859b4d042946`.
- Preregistro **antes de código**: `e9b80f32864af51c745f754a1f05628831a57dea`.
- Nuevo PR #932 DRAFT: `agent/vt31-ict-dol-source-v1-20261014`.
- **CI VERDE CONFIRMADA**: [run #38613733685](https://github.com/mezas3238-hue/qore-core/actions/runs/38613733685) para commit **`7fbb9919981cde34dfb91f0532703fb215555a91`**: Ruff OK, Python compilación OK, 136/136 pytest PASS, locks de blobs G3 OK, checksums SHA256 internos OK, artifact [11918473488](https://github.com/mezas3238-hue/qore-core/actions/runs/38613733685/artifacts/11918473488), ZIP sha256 `978ec5da480e20cd0ebd0a826b12ab3f98e55a0d184872f8e730ceddf49f2ac4`.
- **Después de esa CI** se ha añadido test de **COG original real sobre M1 sintéticas** en commit `f899113b8dc152f2aa334479cac9196dea4aab94`. **No se atribuyen 136 tests verdes a este SHA posterior**; exige CI independiente final y eventual corrección documentada. Su caso tiene pool NY cash 150 y gap entre cierre cash anterior y 09AM; lo esperable es precio/familia reconstruidos y disponibilidad UNKNOWN, jamás inventar "no consumido" durante horas de mercado no observadas.

## Aporte verificable de la primera cohorte (testigos sintéticos)
1. `PRIOR_NY_CASH_SESSION` 390 M1 NY 09:30–16 día hábil anterior; `ASIA_NY_CLOCK` 180 M1 00–03; `LONDON_NY_CLOCK` 120 M1 03–05. Dos extremos por intervalo, niveles derivados exclusivamente de M1 completos.
2. Para `VT31_LONDON` nunca se usa la fuente Londres 03–05 sin haber cerrado. Para NY AM/PM puede usarse tras las 05:00. DST verano/invierno probado.
3. Level touch ya sucedido ⇒ CONSUMED; hueco entre cierre de fuente y momento de decisión sin touch observado ⇒ UNKNOWN, **no** asumir disponibilidad; cash previo inexistente/feriado/early-close incompleto ⇒ UNKNOWN sin retroceder a viernes u otro día como si fuese el último día de mercado.
4. Compara un `CognitiveDecision` *ya existente* con lado, nombre de pool, nivel exacto, as-of y fuente independiente. No crea una señal COG ni toca el productor. La semántica de fuente es **QORE**, no axioma universal ICT/TTrades.
5. CI adversarial anterior cubre fuentes, lados, sesiones, DST, datos faltantes, precio alterado, timestamps, duplicados, consumo y límites del contrato, regresiones previas #926/#928/#929 + COG/OPS/G3.

## Hallazgo y límites
**TECHNICAL_M2_SOURCE_RECONSTRUCTION_VERIFIED_ON_SYNTHETIC_FIXTURES**, hasta el commit CI verde indicado. No demostrado todavía que la COG genuina de la historia NAS100 3Y resuelva todas las clases de perfiles ni que el rango sea elegible para la fuente ICT autoral. **CUIDADO**: en el esquema actual, inferir que un target previo sigue vivo requiere cobertura M1 completa desde la creación, lo que puede fallar en fines de semana, cortes y huecos nocturnos; la salida prudente es UNKNOWN. Esto es un hecho sobre verificabilidad, no un veto estratégico del trader.

## Bloqueos de certificación no resueltos
- **M2/M3**: el COG real todavía puede escoger high cash 150 donde la variante TTrades AM busca high09 110, tal como PR #927/#928; falta productor nuevo específico del perfil TTrades que integre testigo #929.
- **M3**: displacement autoral no certificado; pivote3+1.25 mediana5 es proxy QORE.
- **M4**: displacement/FVG/OB/Breaker sin cobertura completa source exact; OB/Breaker son QORE_PROXY.
- **M5**: stop swing displacement vs C2 QORE, TP/expiración/intrabar sin certificado.
- **M6**: Issue #897, G3 pendiente doble firma real independiente; no simular identidades.
- **M7**: Issue #900, NAS100 BID/ASK símbolo exacto no acreditado, no fills/costes/OOS real; edge y PF/DD NO demostrados.

## Próxima ronda metodológica
(a) Obtener CI verde del commit que incorpora caso COG real, (b) usar los M1 genuinos ya disponibles en GitHub/QORE Native para medir **acuerdo de fuente**, tasas CONFIRMED/REJECTED/UNKNOWN sin calibrar umbrales ni revisar PnL, (c) COG productor nuevo versionado por perfil para TTrades NY AM vs ICT general, (d) testigos M4/M5, (e) gobernanza M6 y economía M7 por separado.

**FRONTERA**: DRAFT / NO MERGE / NO LIVE / NO VPS / NO OMS / NO sizing propio / NO Fresh Holdout / NO afirmación de rentabilidad.
