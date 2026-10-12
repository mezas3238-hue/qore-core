# QORE Native G1 — PREREG de fidelidad protobuf cTrader / spread cero y ampliación temporal — 2026-10-12

Fuente de referencia original [PR #849](https://github.com/mezas3238-hue/qore-core/pull/849), [run 38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706): 29 mercados, 3×10 minutos por mercado, 111451 ticks, SHA aprobado y 5727 snapshots BID=ASK en QA #851. El forense #858 encontró 4320 de esos ceros con ambos timestamps en el mismo milisegundo. **Problema de calidad de fuente, NO pregunta de rentabilidad.** Cualquier interpretación como coste cero ejecutable queda prohibida.

## Hipótesis instrumentales y observaciones congeladas ANTES de consultar cotizaciones nuevas

Cohorte fija de **cinco**: EURUSD, GBPUSD, USDJPY (*tres FX con muchos ceros*) y XAGUSD y SP500→US500 (*control metal e índice*). Selección dirigida por anomalía conocida: esta muestra **NO ES INDEPENDIENTE** para probar universalidad ni tiene poder de inferencia de trading. Sí permite intentar falsar un bug de serialización y estudiar persistencia descriptiva. No añadir símbolos basándose en el resultado.

Dos ventanas nuevas de **30 minutos** (sin solapamiento con las originales) en UTC:
1. 2021-03-16T13:00:00Z a 2021-03-16T13:30:00Z;
2. 2023-03-21T13:00:00Z a 2023-03-21T13:30:00Z.

Total 5 símbolos ×2 ventanas ×2 lados = **20 solicitudes mínimas**; <1 semana de ventana API por solicitud, límite de 64 fragmentos por cada lado/ventana y 300ms entre requests. Si `hasMore` dividir rangos milisegundo sin inventar datos. Límite 100.000 ticks por lado/ventana, máximo 30MB de wire por instrumento y fail-closed en exceso. Una sesión DEMO read-only, `ProtoOAGetTickDataReq` únicamente, nombre proveedor e ID exactos (SP500→US500 requires confirmed native broker symbol; no USTEC/NAS100 aquí).

## Nueva frontera de integridad

Además de los testigos enteros 1e5, guardar **bytes serializados originales de cada elemento `ProtoOATickData`** de la respuesta del SDK, en orden **newest-first por página** (sin `ctidTraderAccountId`, token, broker-secret ni otros metadatos personales del mensaje envolvente), con tamaño delimitado y SHA256. El manifiesto de cada `batch` incluirá rango request, `hasMore`, número de ticks y digest del wire-frame; los batches `hasMore` solo son testigo, NO se usan como fuente de ticks finales hasta resolver paginación. Estos bytes son representación field-level de tick original, no prueba independiente de autenticidad del proveedor TLS; describirlos correctamente.

El **segundo auditor** reconstruirá enteros usando un decoder separado directamente desde Protobuf framing (primera marca/valor absolutos, diferencias signed acumulativas) y comparará **byte-exact** el JSONL entero/decimal de los batches aceptados, cronología UTC, `hasMore`, SHA, duplicate timestamp y reloj sin mirar retornos. Todos los archivos raw provider prices únicamente en GitHub Actions artifacts temporales (repo Git es público; licencias pendientes), jamás commit de datasets.

## Resultado válido y NO GO

Comparar descriptive BID=ASK, crossed, missing, stale por `last known as-of` con umbral 5s predeterminado, y same-ms vs delayed 1–100/101–500/501–1000/1001–5000ms. **No proponer cambiar umbrales para optimizar PnL.** No imputar comisión, spread, slippage, fills, Sharpe, PF ni DD.

**G1_PROTO_RAW_DELTA_PARITY_PASS** exige dos lados reales en ambas ventanas de los cinco instrumentos, SHA por fichero, protobuf replay exacto con origen independiente y sin ambigüedad intra-ms. Si parcial => documentar bloqueo real. Incluso con PASS = observación descriptiva 2×30min/5 activos, nunca serie histórica 10 años/33 mercados, coste NET o certificación. Todos los 231 ensayos originales mantienen NO_SUPPORT. Ningún cambio VPS/MT5/LIVE/CIBO/Shared/QDLE.
