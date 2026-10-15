# VT31 M0 — PREREGISTRO: perfil fuente inmutable antes de sesion
15-OCT-2026. Antes de código. Mandato Owner: certificación de METODOLOGÍA+COGNITIVA, no PF/DD/Sharpe/sizing. Base PR #956 fuente TTrades/COG original G3.

## Perfiles y fuente
- ICT_GENERAL_2023: London 03–04, NY AM 10–11 y NY PM 14–15 NY. Productor VT31CleanroomCognition G3 real sólo QORE-research, NO autoría ICT completa.
- TTRADES_NY_AM_2025: sólo NY AM 10–11. Fuente https://ttrades.com/the-am-silver-bullet-strategy-on-nq/ ; usar EXACTO adaptador fuente-primero original G3 PR #956, testigo #929 y V2; no reetiquetar DOL cash del COG G3 como TTrades H1. Distancia G3 MIN10 frente a target H1 menor => WAIT, sin cambiar el DOL del autor ni el 10 por PnL.
- QORE_G3_PROPUESTA: ingeniería propia distinta de autor ICT/TTrades; productor mismo G3 original pero sin atribución falsa.
- Selección de perfil/versión/DST DEBE sellarse al inicio de sesión, nunca basada en evento, profits, velas futuras. Una sesión solo usa un perfil. TTrades no puede correr London o PM. Retornos WAIT/UNKNOWN no se elevan a READY.
- Cada input: M1 CERRADA y último closed_at==as_of, no futuro, rechazo de día erróneo y fuera de ventana.
- COG G3, OPS y acta blobs congelados d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9, 0ce9707314aecb71155de8b57044b6ec028847b2, e99c70b4e018d626fb620d9a21b9314a51abc36d. Adaptador PR #956 exact code blob 9e3a143cfb27db61b3eec99d84a804e6cec55fcc, commit 8bbee6dfcdc8a75fe52f264947e4195c0800d8da. No edición de originales.

## Falsaciones acordadas antes del código
- Casos originales source-first del PR #956: Jan/Jul LONG/SHORT con H1 fuente >= MIN10 solo RESEARCH CONTEXT, los otros con 5/4 puntos => WAIT. Ocho fixtures sintéticos alimentan COG real. NO 3Y/out-of-sample.
- Cross-profile TTrades London/PM => reject; auto-elegir perfil post sesión => reject; sesion/día/timestamp fuera clock => reject; historial con barra del futuro => reject; etiqueta genérica ICT no autoriza H1 TTrades en London.
- Retornos se etiquetan COG research y método fuente sin emitir CognitiveDecision hacia OPS, stop, riesgo, lotaje, ACK o fill. Firma M6 en issue #897 externa y pendiente.
- CI verde demuestra contrato M0 research; M3/M4/M5 doctrina, integración efectiva y M6 siguen pendientes. NO MERGE/LIVE/DEMO/VPS/FundedNext.
