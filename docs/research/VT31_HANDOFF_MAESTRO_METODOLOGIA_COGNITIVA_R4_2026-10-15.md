# QORE CORE — VT31 · HANDOFF MAESTRO DE CONTINUIDAD R4
## CERTIFICACIÓN POR METODOLOGÍA Y COGNITIVA — HASTA COG V5 / ULTRA FAST

**Checkpoint:** 15-OCT-2026 · **Repositorio fuente de verdad:** https://github.com/mezas3238-hue/qore-core  
**Titular:** Owner VT31 / próximo arquitecto metodológico y cognitivo  
**Rama de entrega (solo documento):** `docs/vt31-master-handoff-method-cog-r4-20261015`, descendiente EXACTA del HEAD del [PR #973](https://github.com/mezas3238-hue/qore-core/pull/973), commit `baa905d3b0a3d18038855221f7139bfbac46c483`. La PR documental queda DRAFT, **no se fusiona a main**.  
**Documentos antecedentes, conservar todos:** [handoff R1 #931](https://github.com/mezas3238-hue/qore-core/pull/931) · [R2 #940](https://github.com/mezas3238-hue/qore-core/pull/940) · [R3 #959](https://github.com/mezas3238-hue/qore-core/blob/fa4128c6009e7fddd11ccec324fc668426acede8/docs/research/VT31_METHOD_COG_MASTER_GATEBOOK_R3_2026-10-15.md). R4 **complementa y actualiza** R3 hasta #973; NO borra la investigación anterior.  
**Muro de coordinación:** [issue #727](https://github.com/mezas3238-hue/qore-core/issues/727) · **bloqueos de método:** [issue #957](https://github.com/mezas3238-hue/qore-core/issues/957) · **firmas:** [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897).

> **VEREDICTO ACTUAL INALTERABLE POR ESTE DOCUMENTO:** `CERTIFICADO_METODOLOGIA=NO_EMITIDO`, `CERTIFICADO_COGNITIVA=NO_EMITIDO`, `VT31_TRADER_CERTIFICADO=FALSE`, `G3_PENDING_DUAL_SIGNATURE`, `NO_MERGE`, `NO_DEMO/LIVE/VPS/FundedNext`, `NO_ORDERS/FILLS`, `NO_SIZING_VT31`. Cientos de pytest y la paridad Ultra Fast son ingeniería reproducible, **no una certificación doctrinal**.

---

# 0. MANDATO SOBERANO / CLAVE PARA EL PRÓXIMO ARQUITECTO

**El Owner corrigió explícitamente el enfoque:** VT31 debe ser certificado por **la fidelidad de su metodología** y **la calidad causal y fail-closed de su cognitiva**. **NO utilizar Profit Factor, drawdown, Sharpe, Sortino, win rate, densidad de trades ni optimización de PnL como condición de aprobación de los Gates M.** Los Gates de rentabilidad y explotación L1–L10 pueden existir en expedientes económicos independientes: **NO** transformarlos en sustitutos de `CERTIFICADO_METODOLOGIA` o `CERTIFICADO_COGNITIVA`.

Un certificado de **método** exige correspondencia explícita entre fuente/versión y reglas efectivas; uno de **cognitiva** exige que el productor que realmente tomaría decisiones lea información disponible en `as_of`, espere ante evidencia incompleta y anule tesis cuando su propia fuente la contradiga. El script read-only de investigación NO equivale al runtime original integrado.

**Prohibiciones:**
- NO merge a `main` sin orden explícita; ramas de experimento ADD-ONLY y PR DRAFT, no sobrescribir los SHAs congelados de G3; registrar cualquier nueva lane en #727 y leer HEAD antes de cada escritura.
- NO LIVE, DEMO, VPS, OMS, API de órdenes, broker ACK/fills, paper económico ni FundedNext. Cero permiso de simulación con sizing por este expediente.
- **VT31 NO posee sizing propio**: la autoridad de tamaño corresponde a **CIBO CMA**, no certificamos aumentando lotes ni aplicando capital/compounding.
- No confundir Nasdaq futures NQ, NAS100 CFD y cTrader USTEC/NDX100 sin homologación documental del símbolo/bróker/horario/tick size.
- Nada de lookahead: solo M1 realmente cerradas, zona NY y DST según instante, ni inferir orden de high/low dentro de una OHLC M1. Si intrabar es incierto, `UNKNOWN`; un toque CE sin ACK nunca es FILL.
- NO reciclar viejo VT31 R5/R6/R8, ledger B, ensayos OLD o 2.140 fuentes antiguas como si fueran el cleanroom actual.
- **No abrir/contaminar OOS/VPS/holdout sellado**: las 1.059.784 M1 de investigación son desarrollo **ya visto**. Preregistrar código posteriormente NO convierte esos datos en OOS nuevo.
- No diseñar umbrales para subir conteos, “alcanzar 450 trades”, optimizar resultados ni forzar 24/318 a 318/318. Una abstención bien justificada es éxito de cognición, aunque no origine transacción.
- Una única cuenta GitHub o dos agentes que comparten login NO equivalen a **dos firmantes humanos independientes** COG y OPS.

# 1. DATOS, REGLAS ORIGINALES, IDENTIDADES Y FIJACIONES

## 1.1 Fuente real NAS100, identidad y alcance temporal

Fuente: artefacto original de GitHub Actions **#11459859004**, miembro `NAS100/market-evidence.json`; histórico NAS100 M1 desde octubre 2023 hasta octubre 2026, **1.059.784 velas M1**, SHA256:

`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`

GitHub Actions antiguos/documentos: [R2 #940](https://github.com/mezas3238-hue/qore-core/pull/940). Los workflows nuevos descargan ZIP por `gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/11459859004/zip"`, descomprimen `NAS100/market-evidence.json`, aplican `sha256sum -c` y verifican count **1059784** ANTES de procesar decisiones. **No** inventar ticks BID/ASK ni rellenar huecos broker: 3Y es fuente M1 histórica de desarrollo.

Censo NY AM **775 días**, congelado en PR #934 y utilizado por PR #949/#952/#954/#958/#959/#960/#966/#968/#970/#972/#973:

| Estado de contexto cognitivo fuente | Días |
| --- | ---: |
| `MSS_ATTESTED_CONTEXT_ONLY` (QORE proxy en primer retorno, NO trade) | 128 |
| `FIRST_RETURN_NO_QORE_MSS` (cohorte M3/V3/V4/V5) | **483** |
| `SWEEP_NO_RETURN` | 92 |
| `NO_SWEEP` | 65 |
| `INCOMPLETE_M1_HOURS` | 6 |
| `REJECTED_SOURCE` | 1 |
| **TOTAL** | **775** |

**Todos los cálculos 483, 449, 457, 441, 388, 318, 96, 69, 24, 294 se refieren a esta cohorte parcialmente superpuesta** y NO a nuevas operaciones rentables ni a experimentos independientes. 128 no son fills; 483 no son pérdidas.

## 1.2 Tres perfiles de un solo VT31 — jamás mezclar sus leyes

1. **`ICT_GENERAL_2023`**: [video ICT Silver Bullet 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4): ventanas London **03–04**, NY AM **10–11** y NY PM **14–15** todas en **America/New_York**. Un H1 09–10 anterior obligatorio y un DOL H1 opuesto **NO** se pueden importar por defecto a London/NY PM desde TTrades.
2. **`TTRADES_NY_AM_2025`**: [TTrades AM Silver Bullet NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) y [PDF TTrades](https://ttrades.com/wp-content/uploads/2026/01/Silver_Bullet_AM_Session_TTrades_PDF.pdf), solo NY AM 10–11; H1 09–10 completo, primer raid de HIGH → SHORT hacia LOW 09, primer raid de LOW → LONG hacia HIGH 09, regreso y confirmación/desplazamiento, familias displacement/FVG/Order Block/Breaker, límite de invalidación más allá del **swing que causó** desplazamiento.
3. **`QORE_G3_PROPUESTA`**: implementación original cleanroom de QORE r1.3, con sus propias convenciones (pivot3, umbral cuerpo **1,25×mediana5**, `MIN_INDEX_POINTS=10`, FVG y CE, stop mecha C2). Estas elecciones **NO** son automáticamente doctrina TTrades/ICT. Pueden ser reglas QORE explícitas, si se certifica **ese perfil propio**, sin falsas atribuciones.

**Conflicto material real que motivó M0:** PR #950/#955 demuestran que el G3 ORIGINAL puede seleccionar DOL anterior de cash (p. ej. 150/80) donde TTrades exige H1 09 opuesto (110/90). El adaptador **source-first #956** usa COG G3 verdadero para MSS, pero exige DOL H1 de fuente: cuando DOL es válido para autor y `MIN10` no cabe, responde **WAIT**, sin fabricar target. Investigación ≠ cambio aprobado en G3.

## 1.3 Huellas G3 y fuentes congeladas; consultar SIEMPRE

| Pieza | Git blob / ID |
| --- | --- |
| G3 COG original: `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py` | `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9` |
| G3 OPS original: `src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py` | `0ce9707314aecb71155de8b57044b6ec028847b2` |
| Acta `docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md` | `e99c70b4e018d626fb620d9a21b9314a51abc36d` |
| G3 acta r1.3 commit | `a446afa17ed6e411b8f0b6fc182b103a78959a97` |
| G3 code/CI frozen for independent review PR #896 | `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` |
| Testigo fuente TTrades DOL P3 / issue #930 | commit `1c820086339323f79d4ec1cb5954fb53841064b2`, blob `bb11d965e99666957378e9748e710360dc5bb9ac` |
| DOL V1 #932 `scripts/vt31_ict_dol_source_v1_20261014.py` | blob `eb3e39db84f487ac8f2f5cfac00ad3f8247683c2` |
| Source-first TTrades #956 script | blob `9e3a143cfb27db61b3eec99d84a804e6cec55fcc`; commit `8bbee6dfcdc8a75fe52f264947e4195c0800d8da` |
| V2 COG WAIT native script #954 | blob `2ab6a7b0fdbe31de6bef17fb2d8eb8cc4055d751` |
| FIRST_OPEN autoral testigo #968 | blob `f4799d2cbefc980d82e327c7a41e36f29aaacdf9` |
| V3 COG source-first #970 | blob `cc0a8bf80709eaf9a65ec8fcef631b6d1d3f9c17` |
| V4 source swing-close #972 | blob `eacf4053be244a7c7e02b00f7fd9bf030df608fd` |
| V5 intermediate hierarchy #973 | blob `e6fd7de4997534426a024eb9689974c916b189a4` |
| OB/CISD/Breaker 2025 original source bridge #960 | blob `ab35ef4d2446e53bf1513e019776961efc046d80` |

**Invariante:** no copiar un estado `CERTIFIED` de un script testigo; las salidas de scripts M3–M5 indican explícitamente `..._certified=false` y cero órdenes/lotaje.

# 2. GENEALOGÍA COMPLETA Y TRABAJOS REALIZADOS

**Importante:** todas las PR siguientes consultadas el 15-OCT-2026 estaban **OPEN y DRAFT**, no mergeadas; el HEAD del PR documental es diferente del HEAD probado por Actions en ocasiones (se agregaron informes después de CI). Un CI de código anterior NO certifica texto añadido después. Las ramas apiladas son líneas de investigación; NO consolidarlas a main sin contrato de integración.

## 2.1 Hasta R3: origen y código original (mantener trazabilidad)

- **#896** G3 r1.3 original bajo contrato y firma dual pendiente; Actions #38343414831, **41/41** de frontera COG/OPS; [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897). Aprobación de código ≠ aprobación de dos humanos.
- **#926–#930, #932–#938 y #940**: mapeo de fuente y Gates, discrepancia COG original, testigos H1, primer FVG, 5.155 prefijos causales en 128 contextos, 150/150 pruebas de estabilidad; R2 #940 hace inventario detallado, incluirlo como antecedente. FVG 119, 8 sin FVG, 1 justo a 11 NY; touch 61, 31 ambigüedad OHLC, 27 expiraciones; **NO fill** ni autoría de las otras familias.
- **#941/#942**: auditoría sobre COG G3 verdadero y dos testigos DOL 12 fechas M1: **2160 slots**, **1104 emisiones/candidaturas de prefijo**, **441 primeras tesis distintas**, **541 P3 y V1 SUPPORTED**, **485 UNKNOWN/UNKNOWN**, **78 UNKNOWN/REJECTED** del 16-ENE-2024. M2 BLOQUEADO (G3 TESTIGO de investigación, no certificado).
- **#944**: topología forense de los **563 UNKNOWN** M2: **10 intervalos M1 únicos faltantes**, **3727 minutos de fuente ausente**, 1 cruce NY fin de semana, 9 dentro de un día NY; varios 17–18 NY y uno 300min 15-ENE-2024. NO asumir que hueco de fuente significa broker cerrado (Nasdaq cash holiday tampoco acredita sesión CFD). [CI #38650526641 PASS, 111/111](https://github.com/mezas3238-hue/qore-core/actions/runs/38650526641), [informe gap topology](https://github.com/mezas3238-hue/qore-core/blob/169ac0f103b8e58d388ef86da09fc3f9cb14a0c6/docs/research/VT31_M2_NATIVE_G3_563_UNKNOWN_GAP_TOPOLOGY_VERDICT_2026-10-14.md). Falta **calendario histórico PIT certificado por broker** y BID/ASK específico de símbolo para reclasificar.
- **#947** mandato Owner: certificación de método y COG independiente de economía.
- **#948/#950/#951/#953/#955** auditoría COG ORIGINAL Long/Short/Wait/Reject en perfiles, DST invierno/verano. Fuente TTrades NY AM vs DOL cash G3 original **NO CONFORME**; no reescribir historia.
- **#949** COG TTrades H1 fuente, 775 días real; **128 source context / 483 WAIT / 92 /65 /6 /1**. **#952** encuentra **449/483** proxy QORE MSS posterior a primer retorno; otros **34** no llegan hasta 11h; no elevar QORE proxy a autor.
- **#954** V2 COG WAIT fuente real, persiste `WAIT` y anula por raid contrario; casos posteriores QORE proxy 449, **48 invalidaciones**. [R3 #959](https://github.com/mezas3238-hue/qore-core/blob/fa4128c6009e7fddd11ccec324fc668426acede8/docs/research/VT31_METHOD_COG_MASTER_GATEBOOK_R3_2026-10-15.md) da todos los runs/SHAs.
- **#956** source-first H1 DOL con COG G3 ORIGINAL, en 8 fixtures LONG/SHORT invierno/verano 4 research conformant context y 4 `WAIT` por `MIN10`. **CI #38709608789, 58/58**; no autorizar DTO hacia OPS.
- **#958** FVG fuente/4 familias diagnóstico: **457/483** geometrías FVG QORE, 26 no, y 48 invalidados (solapamiento); **NO** autorial 4-model-entry.
- **#959** testigo M5 swing causante: en 483 contextos **189 sin pivot3 candidato, 88 un pivot no causalmente demostrado, 180 múltiples pivots, 26 sin FVG**; prohibido inventar SL. **CI #38711574019 76/76**. También HANDOFF R3.
- **#961 (lane paralela)** testigo OB/Breaker fuente, gated read-only, no completitud. Se dejó comentario de auditoría en PR #961: revisar timestamps naive/as-of (paso timestamp no garante aware) y **testigo de cierre real por FIRST OPEN de secuencia contraria**, no solo aserción `displacement_at` externa. Leer HEAD ACTUAL antes de asumir que está corregido.

## 2.2 NUEVO desde R3: labor efectivamente realizada por esta línea

### [PR #960](https://github.com/mezas3238-hue/qore-core/pull/960) — Nuevas fuentes primarias TTrades, M4/M5

**Script:** `scripts/vt31_m4_m5_author_semantics_bridge_20261015.py`. Se descubrieron cuatro publicaciones ORIGINALES del mismo autor que sí definen piezas de método:

- [CISD vs MSS](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/): CISD es cierre por apertura opuesta, MSS cierre y desplazamiento que rompe swing; no son intercambiables.
- [Order Blocks Simplified](https://ttrades.com/order-blocks-simplified/): serie de velas opuestas, cierre/validación, **50% del CUERPO**, invalidación por cierre adverso (no midpoint de mecha ni FVG CE).
- [Breaker Blocks Simplified](https://ttrades.com/breaker-blocks-simplified/): secuencia de **4 piernas** (bullish LOW → HIGH → LOWER LOW → HIGHER HIGH, bajista inversa), además de **zona y retest** para setup; tener cuatro piernas ≠ entrada.
- [Advanced Market Structure](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/): high/low pivot3 de short-term **SÍ es fuente autoral en geometría**; **NO** es automáticamente el swing causal de displacement/stop. R3 decía “todo pivot3 QORE”: la frase era DEMASIADO AMPLIA y esta nueva fuente la corrige explícitamente. Umbral `body>=1.25×median5` continúa siendo QORE.

**[CI #38714295682 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38714295682), Ruff + 80/80**. Sobre los MISMOS 483 contextos: **478** tienen un componente de cierre CISD de **una última vela QORE proxy** y 5 no; **83** patrón geométrico Breaker de cuatro piernas y 400 no. Son **DOS particiones superpuestas**, no sumar 478+83 como oportunidades ni concluir que 478 es CISD correcto para series múltiples. Artifact **#11961966060**, ZIP SHA256 `55ae649c0be0847bec9dcc82f368552f67e4670f680d246d5dd3773f07f2ffe5`. [Veredicto fuente #960](https://github.com/mezas3238-hue/qore-core/blob/677437fc6d470f6bf3eb0af0aff25c7ea1b7ecee/docs/research/VT31_M4_M5_AUTHOR_SOURCES_NEW_COG_VERDICT_2026-10-15.md).

### [PR #963](https://github.com/mezas3238-hue/qore-core/pull/963) — Identidad M0 congelada ANTES de sesión, G3 REAL

**Script:** `scripts/vt31_m0_explicit_source_profile_router_20261015.py`. `PreSessionMethodRouter` fija **un** perfil válido antes de comenzar la ventana NY con DST; tres identidades `ICT_GENERAL_2023` (G3 genuine but QORE research), `TTRADES_NY_AM_2025` (solo AM source-first #956 con H1 DOL opuesto) y `QORE_G3_PROPUESTA` (metodología propia sin falsa autoría). Rechaza selector tardío, TTrades London/NYPM, día/sesión/as-of incompatible, datos futuros. 8 fixtures COG real Long/Short EST/EDT → **4 contexto research, 4 WAIT por MIN10**. Ningún DTO a OPS.

**[CI #38715456385 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38715456385), Ruff + 51/51**; artifact **#11962776871** ZIP `5567a46bc3a466129435282f637bfdbf6fa1e4d92a17f768f5ba0ce7ae2d0b2e`. [Veredicto M0](https://github.com/mezas3238-hue/qore-core/blob/05caf81678512944f50f0eb0365ec9903d3db052/docs/research/VT31_M0_EXPLICIT_PROFILE_ROUTER_COG_VERDICT_2026-10-15.md). **M0 research ENGINEERING PASS; runtime único VT31 todavía NO integrado/firme.**

### [PR #966](https://github.com/mezas3238-hue/qore-core/pull/966) — Ultra Fast Runner adaptado a cuatro Gates cognitivos

Se inspeccionó **[Trader Lab Ultra Fast PR #730](https://github.com/mezas3238-hue/qore-core/pull/730)** (carga fuente única + Linux fork acotado/shared copy-on-write + paridad) y **[QORE Research Ultra-Fast PR #908](https://github.com/mezas3238-hue/qore-core/pull/908)** (acelerador de features/screen/execute, **NO autoridad que certifique COG VT31**). Se adoptó la arquitectura Trader Lab sin usar su motor de economía/órdenes.

**Script:** `scripts/vt31_method_cog_lab_batch_ultrafast_20261015.py`. Una carga fuente 1.059.784 M1 y censo 775/483 compartido; dos procesos `fork`, ejecutan **cuatro testigos originales INMUTABLES** (M3 WAIT V2, M4 family, M5 swing causal, M4/M5 nuevas fuentes), comparan el **SHA256 de todo el JSON** del resultado scalar normal con el batch, no solo conteos.

- [CI de PARIDAD #38741884264 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38741884264): **69/69 pytest**, **4/4 JSON SHA iguales**, 79,546636s scalar vs 20,504293s fork = **3,8795× fase de auditoría**, fuente compartida 15,847363s. Incluyendo fuente, aprox. **2,62×**. Artefacto **#11975564344**, ZIP `274e267480cabb6e31b22983ebb799e3786f65bcc1cca7ccf674d5ac3c0e912a`.
- [CI FAST-ONLY #38742541313 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38742541313): **69/69 tests y 4/4 SHA contra baseline escalar anterior**, 15,941820s fuente + 20,709538s batch ~**36,65s** total. Artifact **#11975919720** ZIP `76daaa6831718178e09a3d24c3325353250b079838ac65b2894ab4abe7dcf758`. Workflow `.github/workflows/vt31-method-cog-ultrafast-fastonly-20261015.yml`, ejecución manual por GitHub Actions en rama #966.
- **ATENCIÓN:** fast-only contiene `all_full_casebook_sha256_scalar_match=false` solo porque NO se ejecuta scalar EN ESA ronda. Su PASS se obtiene comparando los cuatro hashes full JSON contra baseline fijado por CI de PARIDAD. No interpretar false como divergencia. Si cambia el método, **nueva prereg y nuevo scalar-vs-fast**, nunca reetiquetar hash viejo.

[Informe de infraestructura/uso](https://github.com/mezas3238-hue/qore-core/blob/305166618fdf05816418e76852cfd6fcb2954280/docs/research/VT31_METHOD_COG_ULTRAFAST_LAB_PARITY_VERDICT_2026-10-15.md). **Aceleración no cambia decisiones doctrinales ni genera certificados.**

### [PR #968](https://github.com/mezas3238-hue/qore-core/pull/968) — ERROR DE DOCTRINA CISD FIRST OPEN vs última vela QORE

**Fuente primaria NUEVA indispensable:** [TTrades, Understanding CISD, 29-JUN-2025](https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/): si hay **varias velas OPUESTAS CONSECUTIVAS**, nivel CISD es el **OPEN de la PRIMERA vela del run**, NO apertura última vela opuesta, que era aproximación QORE #960. Script `scripts/vt31_m3_cisd_first_series_source_witness_20261015.py` verifica cierre estrictamente FIRST OPEN con as-of y serie contigua. La exigencia de confirmación **inmediata tras la serie** es política TEMPORAL QORE conservadora declarada, NO regla universal del autor.

**[CI #38748169055 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38748169055), Ruff + 38/38**, corpus **483**: **441** con alguna confirmación FIRST_OPEN source-compatible; **22** con solo LAST_OPEN proxy QORE sin FIRST_OPEN (debe permanecer WAIT); **20** sin componente. **388 días** registraron al menos un evento LAST_ONLY prematuro aunque muchos luego confirmaron FIRST_OPEN; **388 no es subgrupo disjunto** ni 388 nuevos trades. JSON full scalar=fork SHA `11d32d1fda356fdcad96093f0e0a30e7ae373d20f5c7069a24631f1b8949644b`. Artifact #11980157368 ZIP `914afc584e7c940df5eb5cb25f399e641463eceb25258b298224eff5aad90aa4`. [Veredicto](https://github.com/mezas3238-hue/qore-core/blob/7a13106c78e537f78cb8d9ae342031d88b4388f7/docs/research/VT31_M3_CISD_FIRST_OPPOSING_SERIES_REAL_M1_VERDICT_2026-10-15.md).

**CONCLUSIÓN:** #960 “478 CISD single candle” NO se puede titular “478 CISD de autor completo”. #968 observó componente más fiel en el tiempo; **CISD distinto de MSS y de setup completo**.

### [PR #970](https://github.com/mezas3238-hue/qore-core/pull/970) — COG V3 STATEFUL FIRST_OPEN con WAIT e invalidación

**Script:** `scripts/vt31_m3_source_first_cisd_cognition_v3_20261015.py`. Compone **V2 verdadero #954** fuente de H1/raid/regreso con **regla FIRST_OPEN #968**, mantiene primer evento, revoca ante raid contrario o target H1 consumido, controla hueco y expira a 11 NY. Cuando CISD aparece, estado se llama `AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED`: **nunca** `READY_FOR_TRADE`. No crea `CognitiveDecision` operativo.

**[CI #38749966309 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38749966309), Ruff + 36/36**; 483/483 mismas primeras confirmaciones que testigo independiente #968; por cierre de ventana **48 `INVALIDATED_OPPOSITE_RAID`** y **435 `EXPIRED_11_NY`**; no hay intención activa posterior. Casebook full SHA scalar=fork `b13482dc8bf5c3bec83e4658bf7a2c0c9e981422ac77038f92edc101df049bf7`. 22,190396s scalar vs 11,391139s fork, carga 15,710840s. Artifact #11981225437 ZIP `f1cf6cd9b6026bb015097c417bea5430699c5cf4257736a99c9e669c3c329994`. [Veredicto COG V3](https://github.com/mezas3238-hue/qore-core/blob/d3362ce7f44b3b1d5535daa4ed75ef9cd94884d3/docs/research/VT31_M3_COG_V3_FIRST_SERIES_WAIT_INVALIDATION_REAL_M1_VERDICT_2026-10-15.md).

### [PR #972](https://github.com/mezas3238-hue/qore-core/pull/972) — COG V4: cierre swing short-term NO basta para MSS

**Script:** `scripts/vt31_m3_mss_structural_close_v4_20261015.py`. Usa la COG V3 real y `short_term_swings` geométrico de TTrades: para LONG cierre nuevo arriba de HIGH ST previamente confirmado (para SHORT bajo LOW), **right M1 ya cerrada ANTES del break**, no wick-only ni reutilización del cierre previo. Más de un swing elegible ⇒ `MULTIPLE_SWINGS_MSS_REFERENCE_UNKNOWN`, NO elige el más cercano ni el más rentable. No afirma displacement o swing protegido.

**[CI #38762765226 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38762765226), Ruff + 37/37**; **96** casos con cierre estructural de referencia única, **318** multireferencia UNKNOWN, **69** sin componente; fin 48 invalidados/435 expirados, identidad V3 intacta. SHA full JSON scalar=fork `6ad621087da3a97c7ad95e85bbcbda88658db9bea049915411706c6cbf002c8e`. 24,043141s scalar vs 12,227207s fork, carga 15,708918s. Artifact #11985579621 ZIP `43c20bb9010dd379e228efe00613ef74aaa111eab97fd183b8e209416c5da6e7`. [Veredicto V4](https://github.com/mezas3238-hue/qore-core/blob/4ce7ce5c5fc494ec903d1c74b4733c2d7fac306a/docs/research/VT31_M3_MSS_STRUCTURAL_CLOSE_V4_REAL_M1_VERDICT_2026-10-15.md).

### [PR #973](https://github.com/mezas3238-hue/qore-core/pull/973) — COG V5 testigo geometría INTERMEDIATE para 318 ambiguos

**ÚLTIMA BASE del presente handoff**: código `scripts/vt31_m3_intermediate_swing_hierarchy_v5_20261015.py` + tests + workflow, documento [veredicto V5](https://github.com/mezas3238-hue/qore-core/blob/baa905d3b0a3d18038855221f7139bfbac46c483/docs/research/VT31_M3_INTERMEDIATE_SWING_V5_REAL_M1_VERDICT_2026-10-15.md).

TTrades [Advanced Market Structure](https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/) describe un intermediate high/low flanqueado por otros **short-term del mismo tipo**. El testigo V5 reconstruye con la parte DERECHA SHORT-TERM **CONFIRMADA antes** del **primer as-of ambiguo** de V4, con extremo central mayor/menor que vecinos (formalización QORE), cruce NUEVO por cierre. No retroajusta ni reemplaza V4.

**[CI #38764379725 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38764379725), Ruff + 35/35 tests**, código CI commit `4aa6b2cbac233275806205b590816443e30d1619`, HEAD con veredicto `baa905d3b0a3d18038855221f7139bfbac46c483`; todos los 483 expedientes full scalar=fork SHA `0999c3d1bb1332645150f613d8bc2cf347c7ac3eb067b53c45c3e38ef94d879b`. Artifact **#11986218764**, ZIP SHA256 `4fcd5acd421beb0a47f7b5313b956c9f0850a33142c0859ac13501cd5545dece`. Source+censo 14,467469s; scalar 25,68708s; fork 13,213514s, ~1,94× cómputo.

**Adjudicación de los 318 casos ambiguos de V4**, verificados en el PR:

| Clasificación V5, mismo primer instante ambiguo | Casos | Qué prueba / qué NO |
| --- | ---: | --- |
| `SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY` | **24** | Existe una sola geometría intermedia fuente-compatible cruzada, confirma vecino derecho *antes* del cierre; **NO** MSS ni stop causal |
| `NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF` | **294** | Sin referencia INTERMEDIATE verificable justo en ese instante; **conservar abstención/UNKNOWN**, no inferir ausencia universal en otro HTF |
| `MULTIPLE_INTERMEDIATE_PIVOTS_UNKNOWN` | **0** | No observado aquí; test adversarial preserva veto si aparece |
| Fuera de cohorte 318 (96 únicos +69 sin V4) | **165** | Permanecen resultados V4 originales |
| **TOTAL** | **483** | **0 órdenes, fills, sizing, certificados o métricas económicas** |

**La mejora real es de precisión de juicio:** frente a los **318** múltiples ST, hay **24** candidatos de nivel intermedio con geometría acotada y otros **294** sin identificación suficiente al reloj causal. **NO** afirmar “294 trades rechazados”, “24 ganadores” ni que se haya hallado *protected swing* o *displacement*.

# 3. MATRIZ MAESTRA DE GATES A FECHA DEL HANDOFF R4

| Gate | Requisito del CERTIFICADO, no de un test unitario | Estado honesto con referencia |
| --- | --- | --- |
| **M0 fuente/identidad** | Un solo trader, perfil ICT/TTrades/QORE fijado antes de sesión, productor COG/OPS real coherente con fuente sin seleccionar outcomes | **RESEARCH ROUTER PASS** #963 (51/51); integración/runtime canónico y política única pendiente. **NO CERTIFICADO** |
| **M1 reloj/M1/DST/as-of** | Solo datos conocidos y cerrados, clock por sesión y perfil, sin extrapolar entre distintas fuentes/instrumentos | **INGENIERÍA VERIFICADA EN SUBCONJUNTOS** #929/#938/#954/#966/#970/#973; cobertura runtime de todas las familias falta |
| **M2 sweep/sesgo/DOL** | TTrades AM primer H1 09 raid y target opuesto; ICT general DOL según su fuente; CFD calendario causal | TTrades research source-first #956; G3 original CASH DOL DIVERGENTE #950/#955. G3 #942/#944 tiene **563 UNKNOWN** explicados por **10 gaps M1**, calendario CFD PIT no certificado. **PARCIAL/BLOCKED** |
| **M3 MSS/desplazamiento/WAIT** | CISD FIRST OPEN si existe, swing de nivel adecuado confirmado antes, *displacement* conforme autor, contexto vigente con WAIT/revocación | V2 WAIT #954; FIRST OPEN #968; COG V3 #970; 96/318/69 ST V4 #972; 24/294 INTERMEDIATE V5 #973. **DESPLAZAMIENTO Y PROTECTED SWING SIN TESTIGO COMPLETO; COG runtime NO CERTIFICADO** |
| **M4 4 familias entradas** | displacement directo, FVG, OB y Breaker con geometría + POI + zona/retest + invalidación + prioridad de coexistencia fiel a autor/perfil | #958 FVG geométrico QORE, #960 fuentes autorales de componentes OB/CISD/Breaker, #961 testigo gate paralelo. Falta suite ENTRADA COMPLETA integrada; **BLOCKED** |
| **M5 swing causante/invalidación** | Elegir exclusivamente swing que causó displacement y validar frontera estructural, no cualquier pivot ni stop C2 atribuido a TTrades | #959 189/88/180/26 casos confusos; V4/V5 jerarquía ayuda pero NO demuestra causalidad. **BLOCKED**. No sizing propio |
| **M6 frontera COG/OPS + atestación** | Testigos independiente COG/OPS con SHAs exactos y dos aprobaciones verificables de personas/revisores realmente distintos | PR #896 G3 r1.3 code testado 41/41, issue #897 OPEN, **API PR #896 reviews = [] al verificar 15-OCT**. NO DESIGNATED/NO DUAL SIGNED; **BLOCKED ADMINISTRATIVO REAL** |
| **M7 acta/cierre integrado** | Convergencia M0–M6 en *misma* versión/produtor con estados y contratos, firma y dos certificados separados | **NOT STARTED AS APPROVED INTEGRATION**, no emitir método ni cognitiva. No desbloquear explotación por inventar gates |
| **L1–L10/Profit/DD/Sortino/etc.** | Expediente de evaluación **ECONÓMICA / explotación separado** | **NO usado ni certificado en esta misión de fidelidad método/COG**; no declarar L1–L10 PASS, ni abrir DEMO/LIVE. Si owner futura autorización, nuevo contrato económico con BID/ASK/holdout/sin sizing VT31 |

**“4/10” comunicado en un intercambio anterior fue una escala orientativa subjetiva de progreso, NO una métrica oficial ni 40% de gates validados.** Aquí rige únicamente la matriz documental por Gate.

# 4. REGISTRO DE PROBLEMAS — SÍNTOMA / CAUSA / SOLUCIÓN / EVIDENCIA DE CIERRE

### P0-01 — G3 original no reproduce DOL TTrades AM
**Síntoma:** cash prior HIGH150 / LOW80 vs DOL H1 09 HIGH110 / LOW90; ambos sides/EST/EDT documentados #950/#955.  
**Causa:** política DOL G3 QORE no es perfil TTrades.  
**Solución:** mantener `ICT_GENERAL`, `TTRADES_NY_AM` y `QORE_G3` distintos; conectar `PreSessionMethodRouter` #963 con el productor COG canónico una sola vez y sin modificar fuente para favorecer outcome. Source-first #956 si se ratifica, SIEMPRE devuelve WAIT cuando MIN10 contradice target autoral.  
**Cierre:** ensayo de integración original **COG→OPS con decisión veto** en LONG/SHORT 09h EST/EDT, perfiles incorrectos rechazados, DOBLE firma de cambios.

### P0-02 — Regla MIN10 QORE contra destino fuente TTrades
**Síntoma:** cuatro contextos de ocho fixtures obtienen H1 destino fuente válido con distancia de 4/5 pts y COG G3 exige 10; fuente no impone ese 10.  
**Causa:** dos doctrinas sin contrato de prioridad.  
**Solución:** firmar explícitamente perfil propio QORE con MIN10 o conservar WAIT en source TTrades; jamás mover DOL ni bajar umbral para obtener PnL.  
**Cierre:** corpus adversarial positivo/negativo source-first, aceptación escrita por metodología, motivo versionado de WAIT.

### P0-03 — Displacement TTrades NO formalizado completamente (M3)
**Síntoma:** FIRST_OPEN CISD #968 y swing CLOSE V4/V5 no demuestran desplazamiento MSS; umbral 1,25×mediana5 es QORE.  
**Causa:** ausencia de regla positiva/negativa autoral suficientemente anotada y criterio causal de displacement/estructura.  
**Solución:** fuentes TTrades/ICT primarias, videos/ejemplos timestamped válidos, describir displacement SIN número inventado; si definición visual/no determinista, usar juicio cognitivo auditado con incertidumbre y contraejemplos, no certificador automático de certeza ficticia.  
**Cierre:** tabla de ejemplos positivos, negativos y límites `UNKNOWN` ratificada por revisor metodológico + motor cognitivo real que emite WAIT hasta tener evidencia coherente con fuente.

### P0-04 — 318 múltiples swings ST; 294 siguen sin geometría intermediate
**Síntoma:** #972: 318 con >1 referencias; #973: 24 con fuente-compatible INTERMEDIATE y 294 sin.  
**Causa:** short-term pivot ≠ intermediate/protected swing; elección del nivel causante no especificada/atestada.  
**Solución:** investigar jerarquía fuente con datos HTF PIT, protected swing, cambios de estructura mayores; comparar los 24 con ejemplos autorales anotados y los 294 contrafactuales; mantener multireferencia `UNKNOWN`.  
**Cierre:** revisor fuente identifica y justifica pivot EXACTO para casos positivos/negativos antes del as-of (incluye por qué otros candidatos son inválidos); sin desempate por “más cerca” o PnL.

### P0-05 — CISD de última vela causaba falsa atribución a autor
**Síntoma:** #960 produjo 478 componentes con última vela QORE, #968 demuestra en 388 días al menos un evento LAST_OPEN prematuro y 22 días sin FIRST_OPEN válido.  
**Causa:** para varias velas TTrades referencia OPEN PRIMERA vela del run.  
**Solución ya investigada:** testigo #968 + COG V3 #970 real source-first, 441/22/20 verificados.  
**Pendiente de cierre:** incorporar la lógica source FIRST_OPEN a runtime final e invalidar activamente LAST_OPEN exclusivamente; probar contra original G3 sin cambiar SHA frozen. Temporalidad “inmediata a serie” sigue QORE conservadora no fuente universal.  
**Cierre:** cero decisiones OPERATIVAS promocionadas solo por LAST_OPEN; reviewer valida casos con retardos temporales.

### P0-06 — Familia M4 OB/CISD incompleta
**Síntoma:** source OB multi-candle y body 50% están disponibles #960, pero los testigos usados pueden recibir `displacement_at` declarado externamente en #961; no se atesta siempre cierre FIRST_OPEN real y POI.  
**Causa:** fragmentos fuente convertidos en proxies sin serie/cierre/zona/causalidad completa.  
**Solución:** OB suite con serie opuesta completa, fuente FIRST_OPEN, displacement/estructura, POI, zona real, body midpoint 50%, test de invalidación de cierre y retest posterior. Probar cierres/no cierres, timestamp aware, SAME_M1 wick/touch ambiguo, sin confundir relleno con ejecución.  
**Cierre:** casos fuente anotados positivos/negativos y ningún `ENTRY_AUTHORIZED` ante combinaciones incompletas.

### P0-07 — Familia M4 Breaker incompleta
**Síntoma:** #960 encontró 83 geometrías 4-leg pero no certificó zona ni retest.  
**Causa:** cuatro piernas por sí solas NO crean breaker trade.  
**Solución:** nivel de breaker/invalidación estructural + zona originadora, mitigación/retest/confirmación as-of, dirección, coexistencia con FVG, sin adjudicar orden intrabar M1.  
**Cierre:** positivos/negativos autorales de formación+retest, reloj y rechazo de retest previo, no fills simulados.

### P0-08 — Familias M4 FVG y displacement directo / prioridad ausente
**Síntoma:** 457/483 FVG geométricos QORE y 26 sin en #958; no confirma cuatro modelos TTrades ni regla “FVG siempre es obligatorio”.  
**Causa:** confundir presencia de geometría 3 M1 con setup completo, método de selección, validación de zona, coexistencia con OB/Breaker.  
**Solución:** especificar catálogo causal de las 4 familias con veto mutuo/precedencia; si autor no determina prioridad, registrar `SOURCE_UNDERDETERMINED` o una **política QORE explícita firmada**.  
**Cierre:** battery source positive/negative, casos simultáneos que producen WAIT o elección firmada de forma estable, sin entrar por llenar conteos.

### P0-09 — M5 “swing que causó displacement” desconocido
**Síntoma:** #959 189/88/180/26 y #973 24 intermediate geometries no resuelven causalidad del SL.  
**Causa:** los niveles M1 de pivote, C2, raid high o primer FVG no prueban qué estructura CAUSÓ desplazamiento.  
**Solución:** construir cadena demostrable PRE-SWING → DESPLAZAMIENTO → RUPTURA → CREACIÓN DE SETUP y limitación de invalidación por perfil; labels declarados de referencia no validada.  
**Cierre:** revisor identifica swing causal correcto sin stop numérico inferido de un wick ambiguo; para múltiples causantes, WAIT. Sizing a CIBO CMA, jamás trader.

### P0-10 — M0 integración en el COG/OPS canónico no hecha
**Síntoma:** #963 router, #970 V3 y #972/#973 testigos V4/V5 son módulos research separados; **NINGUNO** demuestra contrato único runtime bajo fuente/versión.  
**Causa:** preservamos G3 original sin doble firma y no enviamos DTO research a OPS.  
**Solución:** diseñar PR de integración con versioning `(profile,source_commit,method_contract,COG_SHA,OPS_SHA)`, seleccionar perfil antes de cada sesión, conservar WAIT/UNKNOWN/INVALIDATED, mantener frontera COG→OPS, método separado de ejecución.  
**Cierre:** end-to-end sin operaciones reales, fuente original, falsaciones con identidades falsas, no se aceptan DTO no source-bound; revisión dual sin mutar G3 firmado.

### P0-11 — M6 dual firma G3 **DEPENDENCIA HUMANA EXTERNA**
**Síntoma:** [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) abierto; API [PR #896 reviews](https://github.com/mezas3238-hue/qore-core/pull/896) retorna `[]` al corte, **no hay dos approvals independientes verificables**.  
**Causa:** cuentas/roles no designados; la cuenta Owner puede autorizar acciones pero no ser *dos* revisores independientes a la vez.  
**Solución:** Owner designa 2 identidades revisores auténticos `COG` y `OPS`, concede permisos legítimos, atestación formal de SHAs exactos y riesgos residuales que cada uno asume. Si la gobernanza se quiere cambiar, enmienda versionada autorizada, no falsificación. Revisar también integrador nuevo sobre sus SHAs (firmas viejas no cubren código nuevo).  
**Cierre:** dos `APPROVED` de usuarios autorizados distintos o dos atestaciones separadas criptográfica/operativamente verificables, exact docs+code SHA+reloj+alcance y acta, jamás comentarios de un solo agente.

### P0-12 — M2 DOL/CFD PIT y diez gaps sin calendario de bróker
**Síntoma:** 563 P3 UNKNOWN (485/78) localizados en 10 intervalos M1, 3727 min; el 15-ENE-2024 5h sin datos coincide con día de MLK cash holiday, no prueba CFD cerrado.  
**Causa:** ausencia metadata trading sessions del broker NAS100/USTEC vigente por fecha y feed BID/ASK que pruebe si intervalo era “sesión cerrada” o “data faltante”.  
**Solución:** buscar metadata cTrader broker + PIT session per date/instrument y BID/ASK; no extrapolar calendario Nasdaq cash a CFD ni imputar gap.  
**Cierre:** instrumento homologado, fuente PIT broker fechada y checksum del calendario, reconcilia cada uno de los 10 sin promover UNKNOWN arbitrariamente; congela nuevos testigos contra G3 original.

### P0-13 — Caso de timezone/as-of y `displacement_at` declarado en PR #961
**Síntoma:** auditor independiente comentó en [PR #961](https://github.com/mezas3238-hue/qore-core/pull/961) dos puntos: clocks potencialmente naive si `astimezone` sin aware, y desplazamiento pasado solo como argumento en testigo OB sin verificar cierre FIRST_OPEN M1.  
**Causa:** contrato externo del objeto fuente no validado en todas las rutas.  
**Solución:** revisar HEAD **ACTUAL** #961 y si sigue abierto, exigir aware `tzinfo+utcoffset` para as_of/zona/retest, check de M1 cerradas <=as_of y prueba de cierre contra OPEN primera vela real.  
**Cierre:** tests adversariales timestamp naive, future/right swing, supplied fake displacement y REJECT/UNKNOWN sin confirmar.

### P1-14 — Causales M1 vs OHLC intrabar/fill
**Síntoma:** en V1 antiguo 61 TOUCH_NOT_FILL, 31 AMBIGUOUS_M1_SEQUENCE, 27 expired; wick high/low no demuestra qué pasó antes ni fill.  
**Causa:** OHLC M1 sin secuencia BID/ASK/ACK ni stops broker.  
**Solución:** mantener lógica COG WAIT/UNKNOWN ante simultaneidad; información de ejecución pasa a expediente económico separado por bróker autenticado; nunca convertir test de toque en fill o performance.  
**Cierre:** cero afirmaciones de fills sin bróker ACK; simulator no puede adjudicar precio a COG methodology.

### P1-15 — NAS100/USTEC/NDX100/NQ no homologados
**Síntoma:** histórico M1 indexado NAS100; tick data USTEC/cTrader 30h de #899/#901 no cubre 3Y ni contrato homologado.  
**Causa:** símbolo, CFD de broker vs futuros NQ y horarios/reglas potencialmente diferentes.  
**Solución:** broker symbol metadata/version (ticksize, sesión, divisa, retención y microstructure) antes de inferir equivalencia.  
**Cierre:** acta instrument mapping y muestras PIT reconcilian OHLC/quote, sin usar datos externos silenciosos.

### P1-16 — Fuente autoral cualitativa, videos no completamente transcritos
**Síntoma:** algunos comportamientos de displacement/precedencia/stop aparecen en artículo o vídeo y no tienen regla matemática única; vidIQ estaba sin créditos en ronda R3.  
**Causa:** insuficiente evidencia autoral transcrita/anotada.  
**Solución:** recopilar originales disponibles y pasajes con marcas temporales, ejemplos visuales; emplear evaluador con citas de fuente y grado de certeza, no inventar contenido.  
**Cierre:** cada regla M3/M4/M5 con fuente primaria, ejemplo positivo, contraejemplo, as-of y responsable de interpretación humana; diferencias QORE documentadas.

### P1-17 — Ultra Fast puede parecer certificador por velocidad/hashes
**Síntoma:** 3,8795× y 4 SHA idénticos son positivos de ingeniería; un nuevo script V5 usa nuevos hashes distintos de #966.  
**Causa:** comparar checksums es probar **determinismo/paridad** de implementaciones, no validez del concepto de mercado.  
**Solución:** después de CUALQUIER cambio fuente/código/dato, ejecutar nuevo `--parity` y sellar nuevo baseline; usar `fast-only` SOLO en la versión anterior de código/hashes/mercado, nunca “recalibrar” por outcomes.  
**Cierre:** workflow que detecta drift de scripts/baseline y falla ante una sola fecha o decisión alterada; resultado sigue `NOT_CERTIFIED` si faltan Gates.

### P1-18 — Evidencia en artifacts temporales, no almacenamiento soberano
**Síntoma:** artifacts GitHub Actions tienen retención 90 días, los originales podrían caducar; docs tienen receipts pero NO sustituyen data cruda.  
**Causa:** CI artifacts no son archival inmutable de plazo indefinido.  
**Solución:** preservar manifest fuente/hash/versión/license y plan de data-lake autorizada (issue #837 histórico); verificar disponibilidad del artifact fuente #11459859004 antes de emprender pruebas nuevas. No asumir que un artifact viejo seguirá vivo.  
**Cierre:** ubicación durable aprobada con hashes cotejados y controles de acceso, sin subir precios licenciados en PR de documentación.

### P1-19 — Cohortes/denominadores superpuestos generan falsos avances
**Síntoma:** 478 CISD proxy #960 ≠ 441 FIRST_OPEN #968, 388 días con last-only EVENT pueden estar dentro de 441; 24 de 318 V5 ≠ 24 nuevos trades.  
**Causa:** distintos predicados y categorías de evento vs día.  
**Solución:** cada informe dice cohort, definición, unidades y solapamiento; scripts no suman las categorías de diferentes PR como oportunidades.  
**Cierre:** matriz semántica de estados por expediente, primera fecha y condición, recuentos independientes coherentes con 483.

### P1-20 — Reloj de perfil entre source H1 NY y ICT general
**Síntoma:** TTrades solo 10–11 y H1 09, ICT general también London/NYPM; componente de 10 NY puede filtrarse erróneamente a otras ventanas o un selector tardío puede tomar hindsight.  
**Causa:** módulos de research separados sin single source-profile runtime.  
**Solución:** M0 router #963 en entrada a COG original/OPS bajo contrato, rechazo de cambios de perfil después de apertura; DST EST/EDT, closed-M1, no datos fuera de ventana.  
**Cierre:** tests de perfiles cruzados y same-time reversed/late change, CI fail-closed, dos revisiones independientes.

### P2-21 — Estado económico/lab mezclado en muro viejo #727
**Síntoma:** cuerpo inicial del [issue #727](https://github.com/mezas3238-hue/qore-core/issues/727) conserva metas viejas “450 trades”, Pure Edge y R5/R6/R8.  
**Causa:** muro preexistente a nueva orden Owner.  
**Solución:** **prioridad a esta directiva y #957/#947 de metodología+cognitiva** para esta lane; registrar comentario de versión que evite sobrescribir el muro completo. La línea económica separada no autoriza certificar M-Gates por densidad ni sizing.  
**Cierre:** arquitectos usan PRs y documentación versionada al 15-OCT, no metas antiguas como Gate actual.

### P2-22 — Certificado integral exige MAS que testigos de investigación
**Síntoma:** PRs 960/963/968/970/972/973 son verdes y DRAFT; la interfaz trader+COG canónica no ha sido certificada end-to-end ni doble firmada.  
**Causa:** correcto aislamiento científico para evitar cambiar G3 r1.3 sin firma.  
**Solución:** acta M7 versionada con identidad, fuentes, código real COG/OPS, trazas cognición por perfil, respuestas correctas a adversarios y revisión independiente; **solo** emitir los dos certificados correspondientes si M0–M6 probados.  
**Cierre:** acta con `METHOD_CERTIFIED=TRUE` y `COG_CERTIFIED=TRUE` justificadas por evidencia, reviewers reales y SHAs; un CI verde nunca equivale a este cierre.

# 5. PROCEDIMIENTO EXACTO PARA RETOMAR SIN PERDER CONTEXTO

## 5.1 Antes de modificar código (obligatorio, 15 min de lectura, no reiniciar proyecto)

1. Abrir repositorio [qore-core](https://github.com/mezas3238-hue/qore-core), primero [R4 PR documental](https://github.com/mezas3238-hue/qore-core/pulls), leer R3 y R2 enlazados al inicio. **PR #973 HEAD `baa905d3b0a3d18038855221f7139bfbac46c483` es la base exacta de este handoff**, no significa que esté merged a main.
2. Leer issues [#957](https://github.com/mezas3238-hue/qore-core/issues/957) (P0 doctrina) / [#897](https://github.com/mezas3238-hue/qore-core/issues/897) (M6) / [#727](https://github.com/mezas3238-hue/qore-core/issues/727) (concurrencia) y las PR actuales #961, #963, #966, #968, #970, #972, #973. Releer HEAD porque otra lane puede cambiar entre rondas; **NO** sobreescribir código compartido.
3. Anunciar `LANE`, `FILES CLAIMED`, `OBJECTIVE` en #727; prereg doc **PRE-CODE** en rama ADD-ONLY y PR DRAFT (hija del commit de investigación pertinente), reservar paths nuevos. No cherry-pick automático de cuatro ramas divergentes.
4. Ejecutar CI de baseline de esa rama, comprobar SHA original G3 COG/OPS/acta, source NAS100 y 775/483. Diferenciar CABECERA PR HEAD de commit en el cual CORRIÓ CI. Guardar URL del run y artifact ZIP SHA con report.
5. Nunca “arreglar” un Gate cambiando un criterio doctrinal para que pase más observaciones. Source no unívoca => `SOURCE_UNDERDETERMINED`, rechazo => `REJECTED`, falta de secuencia => `UNKNOWN`, contradicción => `INVALIDATED`.

## 5.2 Reproducir la batería Ultra Fast probada y extender a método nuevo

**Runner ya operable — sin PnL:**

- Scripts/code y workflows en **[PR #966](https://github.com/mezas3238-hue/qore-core/pull/966)**:
  - `scripts/vt31_method_cog_lab_batch_ultrafast_20261015.py`
  - `.github/workflows/vt31-method-cog-ultrafast-parity-20261015.yml`
  - `.github/workflows/vt31-method-cog-ultrafast-fastonly-20261015.yml`.
- **PARITY** para método NUEVO: cargar fuente NAS100 original, verificar SHA, censo congelado; ejecutar script referencia escalar y después dos forks con misma fuente; SHA del JSON CANÓNICO completo con fecha, estado, timestamps; QA adversarial y rechazos. No adulterar referencia después de ver output.
- **FAST ONLY** para método SIN CAMBIOS frente baseline anterior: ejecutar en la rama #966 el workflow “VT31 Method Cognitive Ultra Fast Verified Replay No Scalar No PnL”; 4 hashes del CI #38741884264 ya sellados. **No sirve para V4/V5 nuevos** sin crear su propia cadena scalar-vs-fast. Si alguna pareja de hashes diverge ⇒ FAIL y diagnóstico, nunca aprobar por aproximación.
- Otros runners separados ya reproducibles: [#968 Actions #38748169055](https://github.com/mezas3238-hue/qore-core/actions/runs/38748169055), [#970 #38749966309](https://github.com/mezas3238-hue/qore-core/actions/runs/38749966309), [#972 #38762765226](https://github.com/mezas3238-hue/qore-core/actions/runs/38762765226), [#973 #38764379725](https://github.com/mezas3238-hue/qore-core/actions/runs/38764379725). La rama head de cada PR tiene su workflow `workflow_dispatch` o `push` solo sobre esa rama, sin reabrir main/OOS.
- **Script census dependency:** `scripts/vt31_ttrades_am_method_m1_census_20261014.py` (blob `43a219e21237acfddc773a7c78ab6103d3839168`) y `scripts/vt31_ttrades_am_native_cog_v1_20261014.py` (blob `407c5959c8cf2268ff210fbbe8bb07b91d2f4510`) se recuperan desde commits independientes en cada workflow de Actions (por ejemplo `CENSUS_SHA=35bd317ddfed60e09523287de51347683d98e613` y `NATIVE_SHA=1556766c1831190b5459bf93404081412200ba7d`). **NO asumir que viven en HEAD de cada rama**: el workflow ejecuta `git fetch` + `git show` antes del pytest. Si se ejecuta local, replicar esas dos recuperaciones sin cambiar su SHA.
- Python setup del workflow: python3.12, `pip install -e '.[dev]' 'ijson>=3.3,<4'`; `PYTHONPATH=src:. pytest -q -o addopts=''` para suites; Linux fork (no prometer paridad en Windows con spawn). Los workflows oficiales representan la reproducción concreta preferida para evitar cambios de entorno.
- Si no está accesible el artifact fuente #11459859004, **STOP_DATA_MISSING** y resolver archivo/fuente legal con hash original antes de ejecutar; prohibido usar velas sustitutas inventadas o “same symbol” no homologado.

## 5.3 Próxima secuencia de trabajos P0, en orden, con criterio de finalización

| Orden | Entrega específica requerida | Cómo falsarla / aprobarla en alcance |
| --- | --- | --- |
| **A** | Fuente MSS/displacement del autor, serie de ejemplos anotados de referencia swing | Casos positivos, negativos, retardo, doji/wick, múltiples swings y contradicciones. Cualquier cierre sin displacement sigue UNKNOWN |
| **B** | Integrar en COG V5 research la jerarquía INTERMEDIATE/PROTECTED de swing y displacement separados de CISD | Estado `WAIT_CISD` → `CISD_COMPONENT` → `SWING_CLOSE_COMPONENT` → `DISPLACEMENT_CONFIRMED_BY_SOURCE` solo si realmente hay evidencia; revocable. No PnL |
| **C** | M4 OB/CISD primera serie + body 50%, Breaker 4-leg+zona/retest, FVG+displacement directo y prioridad | Casos fuente positivos/negativos y simultaneidad; NO promediar familias arbitrariamente. Reportes por familia y veto global |
| **D** | M5 swing causante del displacement, sin asignar lotaje | Cadena causal temporal identificada por reviewer; ante 2 posibles causas WAIT/UNKNOWN; no stop proxy atribuido al autor |
| **E** | M0 selector antes de sesión + COG nativo VT31 / OPS frontera | Una versión/profile+SHA en eventos de método, semántica COG original y source-first sin contaminación, adversariales autónomos |
| **F** | M2 testigo externo calendario CFD broker PIT NAS100/USTEC para 10 gaps | Discriminar cierre legítimo vs ausencia feed con licencia y SHA; preserve UNKNOWN si falta metadata |
| **G** | M6 dual firmas humanas COG+OPS y cierre M7 | Issue #897 con identidades reales+reviews sobre SHAs, invariantes end-to-end y acta separada método/COG |
| **H** | Solo si Owner lo solicita por separado: economía y L1–L10 | Nuevo contrato OOS/broker y gate económico; sin conceder automáticamente LIVE/DEMO/sizing |

**Regla de éxito científico:** una implementación de un componente se puede validar sin certificar un modelo de entrada completo. Si no se obtiene fuente suficiente para seleccionar protected swing, el resultado correcto es **BLOCKED con evidencia e instrucciones**, no éxito ficticio ni proyecto abortado.

# 6. DEFINICIÓN DE “VT31 CERTIFICADO” Y ANTI-CRITERIOS

Emitir certificados sólo si se cumplen simultáneamente las condiciones firmadas:

**Certificado de metodología** — por versión de fuente y perfil:
- reglas fuente o explícitamente QORE definidas SIN mezclar atribución, relojes y mercado; trazabilidad primaria; listas adversariales positivas/negativas y ambigüedades resueltas o WAIT; familias M4; invalidez M5, DOL; M0–M5 adjudicados.
- se identifica exactamente qué conjunto de reglas se aprueba (ICT GENERAL vs TTrades NYAM vs QORE propios): no escribir “Silver Bullet puro certificado” para heurísticas QORE no aceptadas por la fuente.

**Certificado de cognitiva** — mismo productor/runtime original versionado:
- COG alimentado con solo M1 cerrada/as-of, H1 NY y DST, ante fuente incompleta WAIT, hipótesis invalidada se REVOCa, terminal 11 NY; no autoriza entrada por LAST_OPEN falso ni SWING_CLOSE sin displacement; decisiones coherentes bajo contrafactuales y pruebas autónomas.
- interfaz COG→OPS revisada y firmada por responsables independientes, sin riesgo de que OPS finja validar desplazamiento estructural que sólo COG conoce; fuente/perfil y SHAs coincidientes con contrato doctrinal.

**Gobernanza M6/M7** — dos personas/revisores técnicos legítimos con roles COG y OPS y atestación sobre artefactos exactos, con persistencia de acta; cero bypass por un solo login. Un G3 original todavía sin firmar NO adquiere firma retrospectiva por tests de V5.

**NO son certificados**: “3,88×”, “483 casos”, “24 geometrías”, “441 cierres”, “37/37 tests”, “sin errores CI”, “posibles 450 operaciones” o “PF bonito” (este último ni siquiera se usa en método). **Certificado de método/COG NO autoriza trading real por sí mismo**: explotación, broker, riesgo y economía tienen expediente adicional.

# 7. ENLACES DE ACCESO RÁPIDO PARA EL ARQUITECTO SUCESOR

| Necesidad | Recurso |
| --- | --- |
| Antigua doctrina y todos los problemas hasta M4 14-OCT | [Handoff R2 #940](https://github.com/mezas3238-hue/qore-core/pull/940) |
| Primera misión Owner fuerte y mapa M0–M6 hasta #959 | [Handoff R3 #959](https://github.com/mezas3238-hue/qore-core/blob/fa4128c6009e7fddd11ccec324fc668426acede8/docs/research/VT31_METHOD_COG_MASTER_GATEBOOK_R3_2026-10-15.md) |
| Fuente original G3 y firma pendiente | [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896) · [issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) |
| Problemas P0 de metodología/COG | [issue #957](https://github.com/mezas3238-hue/qore-core/issues/957) |
| Muro multi-arquitecto para reservar archivos | [issue #727](https://github.com/mezas3238-hue/qore-core/issues/727) |
| Identidad M0 y DOL fuente TTrades | [PR #963](https://github.com/mezas3238-hue/qore-core/pull/963) · [#956](https://github.com/mezas3238-hue/qore-core/pull/956) |
| M2 huecos source/CFD calendario | [PR #944](https://github.com/mezas3238-hue/qore-core/pull/944) |
| OB/CISD/Breaker fuentes primarias | [PR #960](https://github.com/mezas3238-hue/qore-core/pull/960) · [#961](https://github.com/mezas3238-hue/qore-core/pull/961) |
| Acelerador Trader Lab/QORE Research adaptado a VT31 | [PR #966](https://github.com/mezas3238-hue/qore-core/pull/966), [ultrafast-fork CI](https://github.com/mezas3238-hue/qore-core/actions/runs/38741884264), [fast-only](https://github.com/mezas3238-hue/qore-core/actions/runs/38742541313) |
| FIRST_OPEN CISD y falso LAST_OPEN | [PR #968](https://github.com/mezas3238-hue/qore-core/pull/968) |
| Máquina COG V3 WAIT/INVALIDATE/EXPIRE | [PR #970](https://github.com/mezas3238-hue/qore-core/pull/970) |
| M3 SWING_SHORT structural close no autor MSS | [PR #972](https://github.com/mezas3238-hue/qore-core/pull/972) |
| M3 V5 jerarquía intermediate, último trabajo | [PR #973](https://github.com/mezas3238-hue/qore-core/pull/973), [run 35/35](https://github.com/mezas3238-hue/qore-core/actions/runs/38764379725) |

# 8. HANDOFF COMPACTO: LECTURA Y PRIMER COMMIT DEL PRÓXIMO ARQUITECTO

**Partir de:** PR #973 HEAD `baa905d3b0a3d18038855221f7139bfbac46c483` (ojo: no de main por accidente). **Consultar PRs paralelos #961 y #963**, no rebasar sobre HEAD sin revisar diffs y firmas. Usar nuevo PR DRAFT ADD-ONLY y reservar script/test/workflow/doc en #727.

**Primera prueba propuesta:** “M3_TTRADES_DISPLACEMENT_DOCTRINE_SOURCE_WITNESS_V1” sobre cohorte fija 483, distinguiendo por evento `FIRST_OPEN_CISD`, `SWING_CLOSE_SHORT`, `INTERMEDIATE_GEOMETRY` y `DISPLACEMENT_SOURCE_VERIFIED`; si no hay pasaje fuente suficiente, mostrar `AUTHOR_UNDERDETERMINED` explícito. PREREG ANTES de ejecutar. P0 no requiere dinero ni mercado nuevo, salvo si la fuente exige HTF/PIT que falten (entonces documentarlo como dependencia).

**Segundo trabajo paralelo permitido:** #961 OB/Breaker: cerrar los dos hallazgos de auditoría (aware timestamps + cierre FIRST_OPEN real), serie y retest, sin usar runner económico. Priorizar arreglos de FALLAS REALES antes de lanzar 100 variantes nuevas.

**Trabajo exclusivamente administrativo del Owner:** resolver [#897](https://github.com/mezas3238-hue/qore-core/issues/897) designando dos revisores independientes. El arquitecto puede dejarles pruebas/documentos listos, **no firmar en nombre de nadie**.

**Evidencias de que se hizo BIEN una ronda:** prereg commit antes de código; código/test/docs/workflow versionados; G3/OPS SHAs estables; corpus e identidad verificados; pytest/Ruff, full JSON SHA escalar = Ultra Fast, casebook cada día y reason; workflow run+artifact digest; dictamen de Gate con contraejemplos; comentario en #727 y #957; no merge/operación ni falsificación de certificado.

---

## ACTA FINAL DEL HANDOFF R4

**Trabajo técnico de esta línea hasta 15-OCT-2026:** source primaria OB/CISD/Breaker y short-term swings #960; selector método M0 G3 real #963; acelerador Trader Lab Ultra Fast #966; detección FIRST_OPEN CISD #968; COG V3 stateful #970; swing close V4 #972; intermediate swing V5 #973. Cada uno con CI real SUCCESS, tests y resultados reproducibles. La rama del R4 es **solo documental** y no cambia ninguno de ellos.

**MAYOR HALLAZGO A TRASLADAR:** en la fuente TTrades no alcanza con una ruptura sobre un pivot3; CISD debe considerar **primera** vela opuesta en series, MSS exige **desplazamiento además de cierre**, y la **jerarquía protected/intermediate** no está resuelta en 294/318 ambigüedades short-term al primer as-of. Ese es el núcleo de la investigación futura. La presencia de 24 intermediate geometries **NO** autoriza promocionarlas a 24 setups MSS.

**CERTIFICADO METODOLOGÍA: NO EMITIDO. CERTIFICADO COGNITIVA: NO EMITIDO. TRADER VT31: NO CERTIFICADO.**  
**M0 research, M1 subcontratos, CISD M3 y componentes estructurales demuestran PROGRESO INGENIERIL Y MEJOR JUICIO COGNITIVO, no cobertura completa de los GATES.** M3 desplazamiento/protected, M4 entradas completas, M5 causa del swing, M0 integración y M6 dual firmas necesitan cierre legítimo y verificado antes de M7.

**NO MERGE · NO LIVE/DEMO/VPS/FundedNext · NO ÓRDENES/ACK/FILLS · NO SIZING VT31 · NO PF/SHARPE/DD COMO CERTIFICACIÓN DE MÉTODO.**
