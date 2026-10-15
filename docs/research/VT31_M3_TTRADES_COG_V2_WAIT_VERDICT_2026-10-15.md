# VT31 — V2 COG TTrades WAIT PERSISTENTE: VEREDICTO METODOLÓGICO Y COGNITIVO
**15-OCT-2026.** Expediente Owner **METODOLOGÍA + COGNITIVA**, no certificación económica. Repositorio `mezas3238-hue/qore-core`, PR #954 DRAFT child del #952; G3 COG/OPS congelados no modificados, sin MERGE/LIVE/DEMO/VPS/FundedNext, sin sizing propio VT31.

## 1. Resultado VERIFICADO en GitHub
- [CI #38708842316 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38708842316), código probado `7f0754e94d76ccf0c7675fd45d46020b36091238`, **Ruff + 80/80 pytest PASS** (regresiones solapadas, no 80 trades).
- [Artifact de decisiones #11960250598](https://github.com/mezas3238-hue/qore-core/actions/runs/38708842316/artifacts/11960250598), ZIP SHA256 `1075448ea2ff17b8e245421daac0d23b368c12ae844b3406931076ea6190fc52`. Contiene JSON con cada caso real, estado al primer regreso, primer evento y estado final de ventana. Mantener custodia: artifact Actions retention 90d.
- [Prerregistro anterior al código](https://github.com/mezas3238-hue/qore-core/blob/2d0cae42542892caff398c4d68d33cecf107f395/docs/research/VT31_M3_COG_V2_WAIT_PREREG_2026-10-15.md), SHA `2d0cae42542892caff398c4d68d33cecf107f395`. Emisor original #933 y verificador fuente independiente #929 pinneados; G3 original SHA inmutable. M1 NAS100 1.059.784 fuente desarrollo YA estudiada, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, **NO OOS**.
- Componente nuevo y aislado `scripts/vt31_m3_ttrades_cog_wait_v2_20261015.py`: **`TTradesAmWaitCognitionV2` no crea `CognitiveDecision`, no manda órdenes, no recomienda lotaje ni promueve metodología**. Es exclusivamente testigo/COG de investigación de estados.

## 2. Hallazgo cognitivo, NO datos de performance
Sobre exactamente **483** casos históricos del censo #934 con primer regreso H1 válido y sin `_mss_proxy` QORE en esa primera M1:

| Estado cognitivo | Casos | Interpretación |
| --- | ---: | --- |
| Primer `QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED` posterior al regreso | **449** | El primer raid/return permanece válido hasta la observación de un **proxy QORE**, NO señal válida del autor |
| `EXPIRED` sin proxy antes de 11 NY | **34** | No se observó confirmación de ese proxy dentro de ventana |
| **TOTAL** | **483** | No son trades ni entradas |
  
La V2 **sigue procesando M1 después del primer evento**, en vez de considerar confirmación proxy como aprobación final irrevocable. Estado al fin 11:00 NY:

| Estado al fin de ventana | Casos | Lectura de método |
| --- | ---: | --- |
| `QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED` | **401** | Existe evidencia proxy posterior sin fuente #929 invalidada después en ese horizonte; todavía NO aprobada autoralmente |
| `INVALIDATED_OPPOSITE_RAID` | **48** | Se observó barrido contrario DESPUÉS del primer proxy; V2 **revoca el contexto de espera**, no reorienta por conveniencia |
| `EXPIRED` | **34** | Sin confirmación proxy dentro de la ventana |
| **TOTAL** | **483** | Un solo caso por día del censo congelado |

**Las 48 invalidaciones son una prueba cognitiva importante:** la V2 no confunde *confirmación observada en algún momento* con *contexto aún vigente*. Bajo este análisis, los 449 son eventos de primera observación, no señales persistentes ni ganadoras; 401 es inventario de estados al cierre de esa ventana, no oportunidades de trading.

## 3. Razón y origen de las decisiones
- El COG TTrades de investigación #933 exigía coincidencia de regreso al H1 y pivote3+cuerpo≥1,25×mediana5 en la **misma M1**; cuando faltaba, pasaba a `UNKNOWN` y descartaba una confirmación posterior. [Auditoría #952](https://github.com/mezas3238-hue/qore-core/pull/952) verificó este defecto de **capacidad de espera**, no un resultado económico.
- `TTradesAmWaitCognitionV2` mantiene el primer raid, su dirección, el primer regreso y el DOL opuesto de la H1 previa desde el verificador fuente #929; devuelve explícitamente `WAIT_FOR_SWEEP`, `WAIT_FOR_RETURN`, `WAIT_FOR_CONFIRMATION` o `INVALIDATED_OPPOSITE_RAID`/UNKNOWN/EXPIRED. Fuente ambigua y falta de H1 quedan abstención. Las nuevas velas M1 no modifican la identidad del primer barrido.
- El estado `QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED` es una **etiqueta QORE**, no decisión autoral `TRADE_INTENT`; aun cuando aparezca el proxy, V2 **NO emite DTO, stop, TP, orden ni fill**.
- La [fuente TTrades AM original (19-JUN-2025)](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) exige barrido y confirmación dentro de 10–11 NY, y menciona displacement, FVG, OB y breaker. El artículo **no especifica** ni valida `pivot3 + 1.25×median5` ni la exigencia de misma vela: no confundir formalización QORE con doctrina ICT/TTrades.
- **Caso límite descubierto en CI y corregido con test adicional:** primer regreso con cierre exactamente a las **11:00 NY** debe dar `EXPIRED` inmediatamente (no `WAIT` después de sesión). Preservado en QA adversarial; no cambia el COG original.

## 4. Certificación M0–M6 (misión Owner)
- **M0 identidad TTrades NY AM:** en alcance de testigo separado, fuente documentada; falta selector/integración perfil original del trader único.
- **M1 causalidad:** V2 consume solo M1 cerradas, H1 09–10, fechas NY con DST; pruebas de secuencia, doble-sweep ambiguo, gapped H1, futuro/duplicado y no-trade. **ENGINEERING_PASS en esta pieza**.
- **M2:** primer barrido y sesgo opuesto/target H1 quedaron en alcance del testigo #929/#949; no se reorienta con barrido posterior. **EVIDENCIA CONTEXTUAL**, no certificado completo ICT general.
- **M3 COG WAIT:** **capacidades esperadas de retener contexto y revocar ante invalidación demostradas en V2 investigación**. Todavía **NOT CERTIFIED** como metodología TTrades, porque su supuesto MSS no es fuente autoral completa y ni siquiera implementa desplazamiento+entrada.
- **M4:** displacement directo, FVG, order block, breaker block y priorización por evidencia causal del autor: **NOT_IMPLEMENTED/NOT_CERTIFIED** en V2; principal P0 siguiente.
- **M5:** invalidación de tesis swing causante del displacement, stops por perfil, expiración del setup, secuencia OHLC/ACK: **PARTIAL TIME EXPIRED**, falta fuente swing/salida completa.
- **M6:** firma COG+OPS y aprobación genuinamente independiente [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) **PENDING**. Ningún técnico con la única cuenta puede duplicar firma.
- **Expediente económico Trader Lab L1–L10** separado del mandato método/COG. No se declara `LAB_CERTIFIED`, `DEMO_ELIGIBLE`, `TRADER_CERTIFIED`, `LIVE_AUTHORIZED`, ni sizing propio VT31.

## 5. Prioridad de continuación concreta
1. Preregistrar **M4 source-authored** con libro de casos semánticos adversariales y negativos: displacement directo, FVG, OB y breaker por separado. Documento del autor tiene nombres y geometría cualitativa, no un algoritmo inequívoco para desempates: `AUTHOR_AMBIGUITY` donde no se puede decidir sin revisión.
2. Diseñar política separada `CONFIRMATION_PENDING -> ENTRY_FAMILY_EVIDENCED` solo cuando la evidencia M4 fuente está presente tras el regreso. **No sustituir esa transición con el proxy QORE para fabricar órdenes**.
3. Definir cancelación de tesis y stop swing causante para TTrades (vs C2 QORE); pedir evidencia M1/tick para ambigüedad intrabar sin convertir touch en fill.
4. M6 revisión realmente independiente, luego certificado perfil/version/fuente M0–M6, **no necesariamente permiso operativo**.

**Dictamen:** mejora COG real implementada como propuesta V2 de investigación, replays y regresiones verificadas, G3 no mutado; `VT31_METHOD_COG_CERTIFICATION_PENDING`.
