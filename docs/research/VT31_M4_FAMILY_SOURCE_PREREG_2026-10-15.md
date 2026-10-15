# VT31 M4 + M5 — PRERREGISTRO TESTIGO SEMÁNTICO DE FAMILIAS / INVALIDEZ CAUSAL
**15-OCT-2026 antes de código.** Directiva Owner: CERTIFICACIÓN METODOLÓGICA + COGNITIVA (no profit factor/DD/Sortino/Sharpe, no sizing).

## Fuentes primarias y jerarquía de afirmación
- [TTrades — AM Silver Bullet Strategy on NQ, 19-JUN-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) y [PDF fuente de 6 páginas](https://ttrades.com/wp-content/uploads/2026/01/Silver_Bullet_AM_Session_TTrades_PDF.pdf), figuras de hora/framework p3–5. El artículo exige **sweep H1 09 NY**, desplazamiento/confirmación posterior, admite cuatro modelos `DISPLACEMENT_RETURN / FVG / ORDER_BLOCK / BREAKER_BLOCK`, objetivo H1 09 opuesto, stop más allá del swing causante del desplazamiento; **no da reglas numéricas M1 únicas, prioridad entre familias, límite de latencia desplazamiento→FVG, parámetros OB/Breaker ni el swing por algoritmo**. PDF figuras de barrido/sesgo no añaden esos parámetros.
- P0 clasificación estricta de proveniencia: `AUTHOR_EXPLICIT_CONTEXT`, `QORE_GEOMETRY_ONLY`, `AUTHOR_RULE_UNDERDETERMINED`, `SOURCE_UNKNOWN`, `NOT_IMPLEMENTED`; ninguna observación geométrica QORE puede subir a `AUTHOR_CERTIFIED` sin regla fuente y testigo independiente.
- Emisor cognitivo original #933, V2 WAIT propuesta [PR #954] sólo informe de estados; fuente #929 pinned. G3 OPS/COG original congelado. Testigo de FVG `confirmed_m1_fvg` QORE 3 velas M1 (src m1_execution.py), blob anclado a branch origen; no presenta formación FVG como fill.
- Corpus real 1.059.784 M1 desarrollo SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, 775 días y `FIRST_RETURN_NO_QORE_MSS=483` congelados #934. No selección posterior de precio/PnL.
 
## Hipótesis y decisión
¿Puede un testigo independiente describir la **presencia contextual geométrica** de la familia FVG M1 en cada caso de retorno y de las otras tres familias **SIN inventar fidelidad autoral ni señales/órdenes**? ¿Sabe reconocer invalidación posterior de fuente, ambigüedad, y stop de swing aún no identificado?

**Protocolo:**
1. Para cada día de los mismos 483, observar M1 09h+10h cerradas en stream V2 y tres M1 consecutivas de ventana 10 NY, solo tercera confirmada as-of, posterior al primer regreso confirmado.
2. Solo registrar `QORE_3_M1_FVG_GEOMETRY_OBSERVED` cuando sesgo FVG = primer raid invertido y V2 snapshot aún `WAIT_FOR_CONFIRMATION` o `QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED`; conservar instante y nombre fuente del verificador. Nunca construir `CognitiveDecision`, no enviar a OPS para ejecución, no adjudicar entrada/CE/fill ni presumir toque BID/ASK.
3. Si solo FVG geométrica pero displacement/MSS autoral incompleto: `M4_NOT_CERTIFIED_AUTHOR_RULE_UNDERDETERMINED`, no `READY`. OB/Breaker sólo `NOT_IMPLEMENTED_AUTHOR_GEOMETRY_NOT_SPECIFIED`, no inventar pivote+retest ni priorización. Modelo `DISPLACEMENT_RETURN` sin definición autoral codificable ⇒ `AUTHOR_CONTEXT_PRESENT_UNATTESTED_TRIGGER`.
4. V2 continúa observando toda ventana; registrar si el contexto queda invalidado/desconocido después de primer FVG. Guardar instante y estado final. Un FVG geométrico antes de la invalidez no revive el contexto, ni aumenta certificación.
5. M5: exigir testigo independiente que identifique **swing causante** con tiempo de confirmación y relación causal al displacement; no usar automáticamente extreme del sweep o stop C2 wick+tick de QORE. Hasta prueba: `M5_SWING_SOURCE_UNVERIFIED`, sin stop numérico/sizing.
6. Pruebas adversariales de geometría FVG bullish/bearish/contigüidad/fuera de sesión; sin barrido, sin regreso, M1 faltante, doble barrido misma M1, retorno al límite 11, fuente invalidada, falta de swing; no contar como fallo negativo un `WAIT` correcto.
7. Informe cualitativo de primer día lexicográfico de `QORE FVG observado`, `sin FVG`, `posteriormente invalidado`, si existen. Cantidades para coberturas y trazabilidad, NO scores ni certificar.
8. CI en GitHub: hashes originales y datos, Ruff/pytest, artifacts 90d, veredicto posterior a ejecución.

**Certificación no automática.** M0–M3 por fuente/perfil continúa parcial; M4 solo puede ser aprobado cuando se resuelvan fidelidad autoral de cada familia y política de prioridad, M5 swing causal, M6 firma real; Trader Lab separado, sin MERGE/LIVE/DEMO/VPS/FundedNext ni sizing propio VT31.
