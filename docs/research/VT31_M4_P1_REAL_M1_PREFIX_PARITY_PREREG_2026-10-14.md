# VT31 M4-P1 — Prerregistro falsificación prefix-M1 sobre 128 contextos reales

14-Oct-2026. Owner ordena continuar certificación metodología/cognitiva. PR #934 censó 1.059.784 M1 con 128 primeros regresos M2/M3. PR #935 reportó 119 first-FVG, 8 no FVG, 1 tardío al cierre 11:00; M5 61 touch, 31 ambiguos, 27 expirados. Se verifica una propiedad no establecida: ¿el FVG y su C2 son iguales cuando el software sólo recibe un prefijo y cuando lee toda la sesión? Documento anterior a software y nueva prueba; no utilizar retornos, PnL ni holdout para calibrar.

## Pregunta causal

Para los 128 contextos históricos de PR #934, ejecutar first_fvg_and_source_path a CADA M1 cerrada desde MSS hasta 11:00 NY, con la decisión COG congelada en MSS. Comparar primer FVG C3.timestamp, side, lower/upper, CE, C2 full wick, DOL, MSS close, potencial puntos. Una vez formado debe ser inmutable en prefijos posteriores. Si hay un primer FVG en sesión completa que no haya existido justo en su C3.closed_at, FAIL. La primera etiqueta terminal M5 de touch/ambiguous/invalidated tampoco puede cambiar con velas futuras. Un M1 touch nunca se convierte en broker fill.

## Entrada source fija

Artefacto 3Y NAS100 M1 #11459859004, miembro NAS100/market-evidence.json, SHA256 0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa, 1.059.784 barras de desarrollo ya visto. Usar SOLO primer retorno M2/M3 de adjudicate_day del PR #934 y propuesta COG con ese prefijo, no buscar segundo retorno ni alterar umbrales, no mirar mercado futuro para seleccionar candidato.

## Gate de aceptación y falla

Esperados: 775 días, 128 contextos; M4 119 formas, 8 none, 1 late; M5 61 TOUCH_NOT_FILL / 31 AMBIGUOUS_M1_SEQUENCE_NO_FILL / 27 EXPIRED_NO_ORDER_OR_ACK, exactamente como #935. Si los conteos cambian, FAIL. Paridad FVG y primer estado M5 terminal perfecta para todos los prefijos. Guardar evidencia por día con resultados de prefijos, marcas C3, conteos, SHA256, sin raw market en git.

CI con prereg ancestor, G3 COG/OPS/doc blob lock, Ruff, pytest regresiones y origen SHA M1, artifact privado temporal. Éxito máximo M4_FIRST_FVG_CAUSAL_PREFIX_PARITY_PASS de ingeniería QORE (NO certificación autoral TTrades). Prohibido MERGE/main/LIVE/VPS/FundedNext/lotaje Trader/OMS/holdout/replay económico. M5 broker fills M6 #897 y M7 #900 aún abiertos. 