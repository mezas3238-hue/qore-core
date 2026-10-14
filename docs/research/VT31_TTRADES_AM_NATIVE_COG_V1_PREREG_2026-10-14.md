# VT31 TTrades NY AM — preregistro COG emisor nativo v1 · 2026-10-14

**Base inmutable de este experimento:** `e3f65b34599cc868d6cf1867dcc3df480e1e66d4` (#932, atop #929). PR #930 **es otro testigo ICT-general en rama hermana**, no copiar ni sobrescribir. Este preregistro PRECEDE todo código nuevo.

## Hipótesis verificable
El COG genérico G3 observado en PR #927/#928 elige `PRIOR_NY_CASH_SESSION_HIGH=150` donde **TTrades AM** exige DOL al high del H1 09–10 =110 tras sweep del low. Sin cambiar G3, construir **emisor de propuesta RESEARCH ONLY** que derive decisión estrictamente de M1 cerrado, por perfil `TTRADES_NY_AM_2025`, y contrastarla con el testigo independiente H1 #929 y el testigo estructural `COG_EVIDENCE_V2` #928.

## Contrato previo a pruebas
1. Sesión **NY AM 10:00–11:00 ET**, M1 cronológico, `as_of` externo y cierre M1 exacto. H1 09:00–10:00 completo (60 M1). El primer raid de 10:00 manda: high→SHORT hacia low09; low→LONG hacia high09. Double sweep en una M1 implica `UNKNOWN`, no inferencia intrabar. Contrario posterior implica `REJECTED`. El regreso direccional dentro H1 exige M1 CERRADA posterior distinta al raid.
2. Para no inventar señales tardías, sólo proponer en el **primer M1 de regreso** si además coincide un MSS QORE comprobable a esa misma hora. Una vuelta anterior sin MSS no se reutiliza a posteriori; queda `UNKNOWN_MSS` (no se calibra esperando la próxima vela ganadora). El primer regreso es un requisito de implementación QORE conservador, **no afirmación textual sobre la regla exacta del autor**.
3. El MSS se verifica con pivote local 3×M1 estricto, vela derecha confirmada antes del MSS, cruce previous-close→MSS-close, displacement `abs(body) >= 1.25 × median5` usando las 5 velas terminadas antes de MSS (misma proxy QORE G3). Si hay pivotes múltiples válidos elegir **más reciente** (regla QORE congelada). Sin pivote/mediana válida → `UNKNOWN`; no generar DTO.
4. Sólo entonces producir un `CognitiveDecision` **candidato** con side/target H1 opuesto, timestamp del H1 10:00, estructura MSS y `mss_anchor_close`; perfil y version identificados como propuesta QORE inspirada en TTrades, **no autor-certificado**. Sin entrada, CE, stop, broker, PnL, sizing, OMS ni orden.
5. Testigo independiente #929 y V2 deben poder verificar el mismo DTO, sobre los originales M1 y el mismo as-of. Falta de respuesta del attester o contradicción → `REJECTED` o `UNKNOWN`, nunca permiso.
6. Siempre `method_certified=false`, `cognition_certified=false`, `execution_authorized=false`. Los estados positivos significan únicamente `CONTEXT_ATTESTED_NOT_CERTIFIED`.

## Pruebas adversariales prerregistradas
- Ambos sentidos LONG/SHORT, DST verano e invierno, JSON testigos y no alteración del dato original.
- Sweep ausente, ambos lados en misma M1, sweep contrario posterior, retorno en la misma vela, falta de H1, huecos, timestamps futuros, as-of tardío, rango H1 inválido.
- MSS sin pivote, MSS sin cruce, cuerpo subumbral, falsificación del target, mismatch de perfil. Testigos #929/#928 **rechazan** DTO alterado; el COG general viejo mantiene su contraejemplo #927.
- Comparación del COG genuino anterior contra este nuevo método sobre fixtures sintéticos; no borrar evidencia vieja.
- Regresión original M0/M3 + COG/OPS/G3; SHA y CI checksums. **No explorar retornos ni Fresh Holdout.**

## Criterio de éxito técnico
CI verde del SHA exacto, fixtures sintéticos conformes y adversariales, G3 sin tocar, un nuevo emisor bien versionado. **No** declarar certificación autoral ni trader rentable. M4 entradas, M5 stops, M6 dual firma #897 y M7 BID/ASK #900 siguen separados.
