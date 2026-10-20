# QORE CORE / VT31 NAS100 — HANDOFF MAESTRO R6 INTEGRAL
## Transferencia a siguiente arquitecto: metodología + cognitiva, tres Silver Bullet, pruebas, problemas, faltantes y ejecución

**Corte documental y verificación GitHub:** 20 de octubre de 2026, zona America/Asuncion.  
**Repositorio:** https://github.com/mezas3238-hue/qore-core  
**Documento anterior obligatorio:** [HANDOFF R5 #975 — completo hasta el 15-OCT](https://github.com/mezas3238-hue/qore-core/blob/6925f8e9c7cad88ccd3b092a9f67509e544ae19f/docs/research/VT31_HANDOFF_MAESTRO_R5_METODOLOGIA_COGNITIVA_COMPLETO_2026-10-15.md) (40,698 caracteres, 263 líneas).  
**Rama de este R6:** docs/vt31-handoff-maestro-r6-integral-20261020; solo agrega este documento, hijo documental de PR #999 HEAD **859c4e59f8a890707efdd3aaedf7ec955f38722a**.  
**Estado a este corte:** los PR VT31 examinados siguen **DRAFT y OPEN, NO integrados a main**. La rama main consultada da SHA **c98d486a760056d9a71173c7041cf6f0c58bd9e9** y fecha de su commit 07-SEP-2026. Se debe volver a verificar antes de fusionar nada.  
**Punto de contacto interarquitectos:** [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727). Cierre tres sesiones [#981](https://github.com/mezas3238-hue/qore-core/issues/981); problemas generales [#957](https://github.com/mezas3238-hue/qore-core/issues/957); firmas humanas [#897](https://github.com/mezas3238-hue/qore-core/issues/897).

> **DICTAMEN ÚNICO AL 20-OCT-2026:** METODOLOGÍA = NO CERTIFICADA; COGNITIVA = NO CERTIFICADA; LONDON = NO CERTIFICADO; NY AM = NO CERTIFICADO; NY PM = NO CERTIFICADO; VT31 = NO CERTIFICADO. Existencia de datos M1 originales, cientos de pruebas PASS y trazabilidad de COG NO acreditan por sí mismos reglas fieles a ICT/TTrades. CERO autorizaciones de broker, órdenes, sizing, fill, OMS, LIVE, DEMO o VPS y CERO merges a main por esta transferencia.

---

## 0. LEER ESTO PRIMERO — ORDEN CONCRETO DE CONTINUACIÓN

1. Abrir el [Handoff R5 #975](https://github.com/mezas3238-hue/qore-core/pull/975) para el historial anterior (G3 r1.3, fuentes TTrades, TraderLab y sus B01–B20). Este R6 lo actualiza pero NO invalida los SHA ya sellados.
2. Revisar **dos ramas independientes**, nunca mezclarlas a ciegas: **línea A de cognitiva/metodología fuente** #971 → #978 → #979 → #983 → #986 → #990 → #991 → #992 → #995 → **#998**; **línea B NAS100 M1/G3/M2** #980 → #982 → #987 → #989 → #993 → #996 → **#999**. Muchos PR son hijos de *ramas no fusionadas*, por lo que un diff a main no representa un cambio aislado.
3. Abrir [PR #999](https://github.com/mezas3238-hue/qore-core/pull/999) y su [CI SUCCESS #39096851001](https://github.com/mezas3238-hue/qore-core/actions/runs/39096851001): define barrera **experimental PRE-OPS** sobre 761 DTO G3 ORIGINALES YA SELLADOS; NO está cableada al runtime nativo.
4. Abrir [PR #998](https://github.com/mezas3238-hue/qore-core/pull/998), [CI SUCCESS #39096941093](https://github.com/mezas3238-hue/qore-core/actions/runs/39096941093): swing M5 y fuente ICT 2023 London/NY PM; sus 12 testigos **WAIT** no certifican stop.
5. Desbloquear con lane versionada la **interfaz nativa** [issue #1000](https://github.com/mezas3238-hue/qore-core/issues/1000): G3 COG original online → M0/M1 source → **gate M2 por fuente** → OPS original con identidad G3. Reproducir en las tres sesiones, con cero bypass/órdenes.
6. Resolver [#994](https://github.com/mezas3238-hue/qore-core/issues/994) sobre política de cash previo: los 18 casos están reconciliados como procedencia de OHLC real, pero NO como doctrina ICT/TTrades. Resolver [#997](https://github.com/mezas3238-hue/qore-core/issues/997): 298 casos G3 deben quedar WAIT/UNKNOWN ante huecos históricos.
7. Obtener fuente primaria autoral, timecodes y ejemplos vela a vela para M2–M5 **separados por perfil**, con casos positivos/negativos y hash de OHLC exacto; no reetiquetar proxies QORE como autor.
8. Obtener perfiles aprobados explícitamente por Owner y **dos firmas humanas verificables distintas** de COG y OPS sobre EXACTAMENTE código, acta y SHA revisados [#897](https://github.com/mezas3238-hue/qore-core/issues/897).
9. Emitir primero una evidencia metodológica y cognitiva **por cada una** de las tres sesiones; solo después un certificado conjunto VT31. Hasta entonces todo WAIT/UNKNOWN mantiene veto.
10. No consumir ningún holdout sellado ni usar PnL/PF/DD/Sharpe/Sortino para reajustar reglas: el usuario ordenó certificar por metodología y cognitiva. No realizar operaciones ni sizing, que depende de otra capa CIBO/CMA.
11. Hacer preregistro de hipótesis y falsadores **ANTES** del código, CI con fuentes M1/SHAs, artefacto inmutable y comentario de coordinación en #727/#981; no confundir tests sintéticos con setups reales.
12. Preservar urgentemente el dataset y pruebas bajo almacenamiento privado autorizado: los **GitHub Actions artifacts son temporales** (frecuentemente retention 90 días); [issue #837 Data Vault](https://github.com/mezas3238-hue/qore-core/issues/837). Obtener expires_at API verdadero, derechos de redistribución/proveedor, copia privada y restore SHA antes de caducar. No subir grandes OHLC, credenciales ni datos restringidos a Git público.

---

## 1. MANDATO DEL OWNER — FRONTERAS OBLIGATORIAS

- VT31 **nuevo desde cero**, no reintroducir el trader viejo defectuoso ni confundir con VT08/CRT. **UN** trader con memoria causal y rutas bien separadas para London 03:00–04:00 NY, New York AM 10:00–11:00 NY y New York PM 14:00–15:00 NY.
- Base operativa de observación **M1 CERRADA**; HTF H1, M15, H4 solamente cuando estén completadas, sin vela futura. Timezone **America/New_York con DST**, no UTC fijo ni hora de Paraguay.
- Identidad metodológica: **ICT_GENERAL_2023** para London y NY PM; **TTRADES_NY_AM_2025** para NY AM. La regla de H1 09:00–10:00 y objetivo lado opuesto H1 de TTrades **NO** se hereda automáticamente a London/PM.
- Evaluar calidad de interpretación, DOL/liquidez, raid, retorno, MSS/CISD, FVG/OB/Breaker, stop/swing causal, LONG/SHORT/WAIT/REJECT, integridad de contexto y abstención. Los resultados económicos no son juez de fidelidad ni deben guiar ajuste oportunista.
- Separar **certificación de metodología** y **certificación cognitiva**; exigir evidencias y firmas independientes. El certificado de un perfil NO sustituye el de otro.
- Investigación veloz en QORE Research / Trader Lab / pytest-xdist, trazas y SHA reproducibles; **Ultra Fast 32× puede representar reloj virtual, no speedup de CPU demostrado**.
- Prohibido sizing propio VT31; broker/trade/risk/OMS, DEMO, LIVE, VPS, funded/producción y merge main requieren autorización independiente no contemplada aquí.

## 2. IDENTIDAD DE FUENTES, G3 PROTEGIDO Y CADENA DE DATOS

### 2.1 Objetos que NO se deben mutar

| Componente original | Ruta | Git blob SHA1 |
|---|---|---|
| COG G3 original | src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py | **d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9** |
| OPS G3/LEGACY original | src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py | **0ce9707314aecb71155de8b57044b6ec028847b2** |
| Acta de metodología G3 r1.3 | docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md | **e99c70b4e018d626fb620d9a21b9314a51abc36d** |

Acta de G3: commit **a446afa17ed6e411b8f0b6fc182b103a78959a97**; implementación/test/workflow **78d4cdac0e09d1a6eef37b99c505ffc5098031fc**; [PR #896](https://github.com/mezas3238-hue/qore-core/pull/896) DRAFT; [CI #38343414831](https://github.com/mezas3238-hue/qore-core/actions/runs/38343414831) SUCCESS 41 pruebas. [Issue #897](https://github.com/mezas3238-hue/qore-core/issues/897) sigue **OPEN** al 20-OCT: dos identidades humanas/roles COG y OPS independientes no firmaron formalmente el contrato revisado. Un solo usuario GitHub y dos agentes que comparten login NO son firmas independientes. Las firmas viejas o sobre SHA distintos no sirven.

**G3 es un candidato QORE, NO la implementación certificada del autor.** Incluye pivote corto causal, desplazamiento body >=1,25×mediana5, un MIN10 de espacio proyectado, fuente DOL QORE y primera FVG. TTrades AM Jun-2025 exige objetivo del extremo opuesto del H1 09 y no automáticamente MIN10; ICT 2023 explica un marco de oportunidad >=10 handles para índices, pero queda ambigüedad doctrinal en interpretación exacta de ese marco (ver PR #995 y B28 de PR #998). Nunca transferir el umbral de un método al otro ni ajustar tras ver PnL.

### 2.2 Datasets originales y custody

- Fuente NAS100 mercado M1: GitHub Actions original **artifact #11459859004**, dentro del ZIP **NAS100/market-evidence.json**; **1.059.784 barras M1**, SHA256 del JSON **0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa**; cohortes **775 días New York**. Fue utilizada reiteradamente en investigación: **NO es OOS/holdout virgen**.
- Fuente secundaria de microestructura distinta: [PR #901](https://github.com/mezas3238-hue/qore-core/pull/901), cTrader USTEC DEMO, **483.103 quotes BID/ASK durante unas 30 horas**; no extrapolar bid/ask, spread, broker calendar o fill a 3 años del NAS100 M1.
- Cobertura independiente por sesión: [PR #980](https://github.com/mezas3238-hue/qore-core/pull/980) y [CI #38792654129](https://github.com/mezas3238-hue/qore-core/actions/runs/38792654129); **artifact #12000338010**, ZIP sha256 **31eda29455dace38086a0f029c9d7568593971931537625734bd9841925467a0**. **SHA256 JSON de 2.325 fichas cobertura:** **7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d**.
- COG online 2.325 ventanas: [PR #982](https://github.com/mezas3238-hue/qore-core/pull/982), [CI #38794839290](https://github.com/mezas3238-hue/qore-core/actions/runs/38794839290), **artifact #12001911740**, ZIP SHA **7c8eb749ca7b64a1c1192cee18890b80c3dc0e75b4a974b9c82072f6936bdeaf**, **SHA JSON G3 casebook 2.325** **cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1**.
- M2 auditor de 2.325 fuentes y 761 DTO primeros M1: [PR #993](https://github.com/mezas3238-hue/qore-core/pull/993), [CI #38975891228](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228), **artifact #12079131643**, ZIP SHA **30de8306225941208ecea73ab4b9ba9b88b625b8b1e9794f47c758ea3fdce07a**, casebook 2.325 extendido SHA256 **d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21**. OJO: casebook más viejo **0429096009dbd1170a79c976fc9ce9167bff12496df3f54debf7df5fff700cab** corresponde a versión **ANTES** de añadir fechas/cierres nominales; no declarar que estos hashes distintos son errores de COG.
- Contrafactual **18** calendarios cash 390 M1: [CI #38976680827](https://github.com/mezas3238-hue/qore-core/actions/runs/38976680827), **artifact #12079207197**, ZIP SHA **7b5a904be6a5c19015e0568d49415f445207cc913eac3dce5298ced43ed490f4**, casebook 18 SHA256 **06d53cc37a88347da0a5e6089acf17dbc84bab7aa79f3fab37ba0d0aec03dc9d**.
- 743 intervalos gap M2: [PR #996](https://github.com/mezas3238-hue/qore-core/pull/996), [CI #39037937522](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522), **artifact #12103380622**, ZIP SHA **6399c3d0666e2628348fa7a3c071928fb16f4846a0497aa7838499f069e918b7**, casebook 743 SHA256 **a546f7c143bb59bce822890d82733e44b8941f990942c83aa9e59823c094bd4d**.
- Barrera PRE-OPS 761 DTO originales: [PR #999](https://github.com/mezas3238-hue/qore-core/pull/999), [CI #39096851001](https://github.com/mezas3238-hue/qore-core/actions/runs/39096851001), **artifact #12124872447**, ZIP SHA **885241c4391bb7fc1e39eaeb2e8c1f56c22bd3813b077042887de56f09ea9174**, casebook 761 SHA **ae07fc4500223a91428377191f849ce3fa19e5bede5e3da1c9ea075105d3fbe3**. **No corresponde a COG ejecutado online en esta última CI**: 761 decisiones G3 fueron fixtures originales previamente sellados, inyectados en su as_of.
- Data Vault/retención [#837](https://github.com/mezas3238-hue/qore-core/issues/837). Los ZIP y pruebas de Actions son **temporales** hasta realizar archivo duradero **privado, licenciado y restore con SHA**; no asumir permanencia por un link. Registrar expires_at real vía API antes de que caduquen (no declarar fecha exacta sin consultar API).

**Ninguna fuente NAS100 M1 OHLC demuestra que hubo fill intrabar**, broker ticks, bid/ask, comisión o swap. No inventar ejecuciones ni trading edge.

## 3. LAS TRES SESIONES Y SU COBERTURA ORIGINAL

| Perfil separado de UN VT31 | NY local y DST | 775 días: ventana de fuente completa | Déficits no homologados |
|---|---|---:|---|
| London **ICT_GENERAL_2023** | 03:00–04:00 | **774/775** | 1 sin cobertura completa |
| NY AM **TTRADES_NY_AM_2025** | 10:00–11:00; **H1 09:00–10:00 previa completa** | **769/775** | 2 parciales 10h + 4 H1 09 incompletos, en días distintos dentro de 6 déficit |
| NY PM **ICT_GENERAL_2023** | 14:00–15:00 | **741/775** | 30 fechas sin M1 14h + 4 parciales |

**Total: 2.325** fecha×sesión; **41** fichas fuente deficitarias = 1+6+34, sin concluir que NAS100 CFD estaba cerrado, abierto o festivo. Se necesita metadata bróker símbolo/proveedor/convenio point-in-time (PIT), incluyendo posibles gaps fuera de ventanas fuente. H1 09 NYAM incompleta en cuatro fechas; dos con M1 10h online vetadas inmediatamente antes de COG y dos sin M1 10h. Un instrumento NQ futuro no equivale automáticamente a NAS100/USTEC CFD, ni un holiday NYSE prueba horario de ese CFD.

La coherencia exacta de las ventanas y source gaps está en [informe #980](https://github.com/mezas3238-hue/qore-core/blob/05f46858b2bf34042c7823a5334809adc141a279/docs/research/VT31_TRISESION_REAL_M1_SOURCE_GAPBOOK_AND_CLOSURE_2026-10-15.md).

---

## 4. INVENTARIO HISTÓRICO R1–R5 QUE NO DEBE PERDERSE

Para evitar duplicar las más de 40 KB de R5, esta tabla enlaza trabajos anteriores con su significado real y estado, y este R6 añade TODO el tramo posterior.

| Documento / PR | Qué se hizo ANTES del R6 | Límite / estado |
|---|---|---|
| Handoff R1 [#931](https://github.com/mezas3238-hue/qore-core/pull/931) | transferencia inicial reconstrucción VT31 | histórico, no certificado |
| Handoff R2 [#940](https://github.com/mezas3238-hue/qore-core/pull/940) | metodología/cognitiva, problemas iniciales | no sustituye R5/R6 |
| Handoff R3 [#959](https://github.com/mezas3238-hue/qore-core/pull/959) | avances cognitivos y fuente | histórico |
| Handoff R4 [#974](https://github.com/mezas3238-hue/qore-core/pull/974) | ~57 KB, 22 bloqueos, COG V5 y TraderLab | histórico |
| **Handoff R5 [#975](https://github.com/mezas3238-hue/qore-core/pull/975)** | 263 líneas, todos los PR hasta #971, 20 bloqueos B01–B20, 12 artifacts/SHAs, pasos M0–M7 | **lectura obligatoria; complementado por R6** |
| G3 original [#896](https://github.com/mezas3238-hue/qore-core/pull/896) | contrato/r1.3 + COG/OPS, CI 41 PASS | DRAFT, sin dos firmas reales #897 |
| cTrader BID/ASK DEMO [#901](https://github.com/mezas3238-hue/qore-core/pull/901) | muestra corta de microestructura USTEC | NO extrapolar 3Y NAS100 |
| NYAM cuatro familias [#906](https://github.com/mezas3238-hue/qore-core/pull/906) | 212 displacement, 205 FVG, 116 OB, 84 breaker *contextos que se solapan* | no trades ni cuatro familias autoralmente probadas |
| Real M2/M3 [#934](https://github.com/mezas3238-hue/qore-core/pull/934) | 128 contextos source-only raid+MSS NAS100 | COG/fuente autoral global pendiente |
| Real M4/M5 [#935](https://github.com/mezas3238-hue/qore-core/pull/935) | 119 FVG elegibles, 61 retests M1, 31 ambiguos intraminuto, 27 expiran | retest NO fill; swing causante NO certificado |
| M4 causality [#938](https://github.com/mezas3238-hue/qore-core/pull/938) | 5.155 prefijos M1 anti-lookahead | fuente parcial |
| TraderLab [#937](https://github.com/mezas3238-hue/qore-core/pull/937), [#939](https://github.com/mezas3238-hue/qore-core/pull/939) | PREP causal 1×/32×; 120 casos congelados | no L1/L3 oficiales |
| M5 [#943](https://github.com/mezas3238-hue/qore-core/pull/943) | diferencia stop C2 wick vs raid/path 119 contextos | stop autoral pendiente |
| Breaker [#945](https://github.com/mezas3238-hue/qore-core/pull/945) | 149 testigos 4 piernas otro corpus (NO comparable 1:1 a 84 #906) | estructura source-only |
| COG LONG/SHORT [#948](https://github.com/mezas3238-hue/qore-core/pull/948), [#953](https://github.com/mezas3238-hue/qore-core/pull/953), [#955](https://github.com/mezas3238-hue/qore-core/pull/955) | original G3 evalúa LONG/SHORT/WAIT/invalidación London, NYAM, NYPM con EST/EDT | sintéticos no fidelidad autor |
| Conflicto TTrades [#950](https://github.com/mezas3238-hue/qore-core/pull/950), [#951](https://github.com/mezas3238-hue/qore-core/pull/951), [#956](https://github.com/mezas3238-hue/qore-core/pull/956) | DOL G3 cash 150 vs TTrades H1 09 HIGH 110; SHORT cash 80 vs LOW 90; 4 casos fuente compatibles, 4 WAIT por MIN10 | **identidad del método** sin resolver |
| OB/Breaker [#961](https://github.com/mezas3238-hue/qore-core/pull/961), swing [#962](https://github.com/mezas3238-hue/qore-core/pull/962) | testigos contrapuestos y negativos | PROXY QORE no doctrina completa |
| Tribunal [#964](https://github.com/mezas3238-hue/qore-core/pull/964), [#969](https://github.com/mezas3238-hue/qore-core/pull/969) | SHA de 8→10 artifacts + COG real, gobernanza | metodología y cognitiva no emitidas |
| UltraFast [#965](https://github.com/mezas3238-hue/qore-core/pull/965), [#967](https://github.com/mezas3238-hue/qore-core/pull/967) | 12 y 24 casos sintéticos trazas LONG/SHORT/WAIT 1× vs 32× iguales | no speedup real CPU ni trading L3 |
| M0 [#971](https://github.com/mezas3238-hue/qore-core/pull/971) | FrozenMethodProfilePolicy PRE-M1, 16 casos, CI 78 PASS | Owner unsigned, research only |
| COG CISD/swing [#968](https://github.com/mezas3238-hue/qore-core/pull/968), [#970](https://github.com/mezas3238-hue/qore-core/pull/970), [#972](https://github.com/mezas3238-hue/qore-core/pull/972), [#973](https://github.com/mezas3238-hue/qore-core/pull/973), [#977](https://github.com/mezas3238-hue/qore-core/pull/977) | FIRST opposing OPEN, 3c swing/intermediate geometry, V6 113 unique/44 multiple/161 none de 318 ambiguos | estructura geométrica NO displacement ni MSS autoral completa |

**Regla:** los números de pytest de CIs diferentes comparten regresiones, **NO deben sumarse** para anunciar miles de pruebas independientes. Los casos sintéticos, prefijos, observaciones M1 y fuentes confirmadas **NO son trades**.

## 5. DOS LÍNEAS COMPLEMENTARIAS POSTERIORES A R5 — MAPA DE PR Y DEPENDENCIAS

### 5.A. Arquitecto de metodología/cognitiva estructural (A)

**DAG de PRs no fusionados:**

Handoff R5 #975 → M0 #971 → [#978](https://github.com/mezas3238-hue/qore-core/pull/978) → [#979](https://github.com/mezas3238-hue/qore-core/pull/979) → [#983](https://github.com/mezas3238-hue/qore-core/pull/983) → [#986](https://github.com/mezas3238-hue/qore-core/pull/986) → [#990](https://github.com/mezas3238-hue/qore-core/pull/990) → [#991](https://github.com/mezas3238-hue/qore-core/pull/991) → [#992](https://github.com/mezas3238-hue/qore-core/pull/992) → [#995](https://github.com/mezas3238-hue/qore-core/pull/995) → [#998](https://github.com/mezas3238-hue/qore-core/pull/998).

| PR | Problema específico abordado | PRUEBA VERIFICADA | Lo que NO autoriza |
|---|---|---|---|
| #978 | ruteo M0 pre-COG, 09h H1 complete NYAM, DST | ver PR/CI y documentación; no firmar selector Owner | fuente ICT general/H1 no equivalente |
| #979 | **lookahead OB/Breaker**: test V1 aceptaba retest abierto en as_of; V2 exige M1 exactamente CERRADA antes del juez | [Actions #38791629969](https://github.com/mezas3238-hue/qore-core/actions/runs/38791629969), **122 PASS** | NO cuarto modelo autoral |
| #983 | Memoria contexto M0→M4 para retests posteriores al retorno que no ocurren en el mismo as_of; SHA del prefijo M1 | [Actions #38795136504](https://github.com/mezas3238-hue/qore-core/actions/runs/38795136504), **173 PASS** | no emite DTO operacional |
| #986 | **bug V2:** solo sello M1 hasta M0 permitía reescritura post-M0; V2 consume as_of incluso en REJECT. V3 sella TODO prefijo M1, REJECT sin nueva evaluación | [Actions #38820088606](https://github.com/mezas3238-hue/qore-core/actions/runs/38820088606), **203 PASS** | V3 usó rollback privado; falta V4 |
| #990 | PREPARE/COMMIT V4: clon temporal; REJECT/excepción sin mutar estado ni acceder a V2._last_assessed | [Actions #38902424162](https://github.com/mezas3238-hue/qore-core/actions/runs/38902424162), **234 PASS** | candidato research y WAIT, no G3 nativo |
| #991 | fuentes primarias TTrades: **MSS ≠ CISD**, 4 familias, swing causante del desplazamiento; documenta negativos | documento [PR #991](https://github.com/mezas3238-hue/qore-core/pull/991) | adjudicación textual sin gráficos no certifica por sí sola |
| #992 | testigo separado geometría MSS (swing+close) vs CISD (serie opuesta+first open), sello V4 M1, sin displacement autoral | [Actions #38975344511](https://github.com/mezas3238-hue/qore-core/actions/runs/38975344511), **268 PASS**, los 16 casos acaban **WAIT** | geometría ≠ método autor |
| #995 | localizó fuente primaria ICT Silver Bullet 2023 **https://www.youtube.com/watch?v=tRq1hyGGtl4**; testigo London/NYPM ICT_GENERAL, MSS/FVG/10 handles fuente primaria pendiente de ejemplos | [Actions #38975936677](https://github.com/mezas3238-hue/qore-core/actions/runs/38975936677), **300 PASS**, todos WAIT/REJECT | no trasladar TTrades 09H a London/PM, no certificar 10 handles por índice secundario |
| **#998** | M5 swing extremo/causal entre contexto y desplazamiento para **las 3 sesiones**, sello V4 NYAM y juez ICT London/NYPM, abstención SL | [Actions #39096941093](https://github.com/mezas3238-hue/qore-core/actions/runs/39096941093) **333 PASS**, **12/12 WAIT**, [artifact #12125027184](https://github.com/mezas3238-hue/qore-core/actions/runs/39096941093/artifacts/12125027184) SHA ZIP **80c62576730ec1d2231e077414c680c9d3397536c1e872fd1f339ed878229255** | stop_tick_price=None, causar displacement sin fuente autoral pendiente |

**Fuente documental primaria relevante:** [TTrades AM Silver Bullet NQ](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), [TTrades MSS vs CISD](https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/), [TTrades Protected Swings](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/), [TTrades Breaker](https://ttrades.com/breaker-blocks-simplified/) y [ICT Silver Bullet 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4). El índice/transcript de terceros es material de apoyo; **verificar timestamps, audio e imágenes originales**. Fuente TTrades 2026 no es enmienda automática de perfil 2025 congelado.

**Problema B28 documentado #998:** fuentes secundarias discrepan si “10 handles” es distancia proyectada DOL o desplazamiento generador FVG. Resolver contra video primario con timecodes y ejemplos; no autorizar una condición operativa por su mera mención.

### 5.B. Arquitecto de replay real NAS100, G3 nativo y barrera M2 (B)

**DAG de PRs no fusionados:**

[#978](https://github.com/mezas3238-hue/qore-core/pull/978) → [#980](https://github.com/mezas3238-hue/qore-core/pull/980) → [#982](https://github.com/mezas3238-hue/qore-core/pull/982) → [#987](https://github.com/mezas3238-hue/qore-core/pull/987) → [#989](https://github.com/mezas3238-hue/qore-core/pull/989) → [#993](https://github.com/mezas3238-hue/qore-core/pull/993) → [#996](https://github.com/mezas3238-hue/qore-core/pull/996) → **[#999](https://github.com/mezas3238-hue/qore-core/pull/999)**. Este R6 se ramifica DOCUMENTALMENTE del HEAD #999, no de main.

| PR / HEAD verificado | Entregables y prueba final | Alcance real |
|---|---|---|
| [#980](https://github.com/mezas3238-hue/qore-core/pull/980) 05f46858... | 2.325 fuentes 775×3, 41 déficits fechados; [CI #38792654129](https://github.com/mezas3238-hue/qore-core/actions/runs/38792654129) 129 PASS | censo temporal source-only, no cierre broker |
| [#982](https://github.com/mezas3238-hue/qore-core/pull/982) cfab0878... | COG G3 original online y OPS originales conectados por **adaptador research**, [CI #38794839290](https://github.com/mezas3238-hue/qore-core/actions/runs/38794839290) 132 PASS, 2.325 parity exact | primer ensayo native falló G3→LEGACY; issue #984 |
| [#987](https://github.com/mezas3238-hue/qore-core/pull/987) 5df19499... | coordinación **nativa research** COG G3→OPS G3 opt-in y política congelada anti-hot-swap, [CI FINAL #38820720852](https://github.com/mezas3238-hue/qore-core/actions/runs/38820720852) **173 PASS**, 2.325 parity exact | aún H1 09 y gaps fuera del runtime en ese corte |
| [#989](https://github.com/mezas3238-hue/qore-core/pull/989) 2de96800... | gate nativo pre-COG H1 09 NYAM y gap inicio/mitad las tres ventanas, [CI #38901532268](https://github.com/mezas3238-hue/qore-core/actions/runs/38901532268) **202 PASS**, 2.325 G3 casebook idénticos | M0-B admisión M1 source only; perfil Owner NO firmado |
| [#993](https://github.com/mezas3238-hue/qore-core/pull/993) 1de03f99... | auditor M2 **seis pools QORE cash previo, Asia, London**, testigos independientes 761 G3 positivos en primera vela de sesión; [CI #38975891228](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228) **127 PASS**, censo 445/298/18 | fuente QORE NO DOL ICT/TTrades homologado |
| [#993 también](https://github.com/mezas3238-hue/qore-core/pull/993) | segundo contrafactual CASH 18 casos prereg, 390 M1/día, [CI #38976680827](https://github.com/mezas3238-hue/qore-core/actions/runs/38976680827) **139 PASS** | reconciliada procedencia precio, NO doctrina selección cash |
| [#996](https://github.com/mezas3238-hue/qore-core/pull/996) 603f73a2... | testigo independiente huecos M1: **445 CONFIRMED sin un solo gap**, **298 UNKNOWN con >0 gap**, [CI #39037937522](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522) **101 PASS** | no demuestra bróker CLOSED ni autor MSS |
| **[#999](https://github.com/mezas3238-hue/qore-core/pull/999) 859c4e59...** | **M2-C** PRE-OPS source WAIT sobre 761 eventos G3 ORIGINALES SELLADOS, [CI FINAL #39096851001](https://github.com/mezas3238-hue/qore-core/actions/runs/39096851001) **96 PASS**, todos 761 sin permiso OPS | **NO está integrado al VT31Trader nativo ni regenera COG G3 live en ese run** |

### 5.C. Auditorías de resultados COG real

[PR #982](https://github.com/mezas3238-hue/qore-core/pull/982) transmitió la cinta cronológica original **1.059.784 M1** a una memoria cognitiva G3, sin leer el futuro ni consultar ledger de cobertura hasta terminar el replay. [PR #987](https://github.com/mezas3238-hue/qore-core/pull/987) y [#989](https://github.com/mezas3238-hue/qore-core/pull/989) demostraron la paridad entre adaptador research y coordinador nativo G3 en esta cinta, **casebook completo 2.325 SHA256 idéntico**:

**cae03ff5faaaebabef4c6f4eed736d802061bfc8598f311fb4a0e27129591de1**

| Sesión | Invocaciones originales G3 M1 (no trades) | Observaciones M1 positivas G3 reiteradas (no trades) | NY días con 1+ G3 positiva |
|---|---:|---:|---:|
| London | **46.440** | **27.986** | 773 |
| NY AM | **46.235** | **19.302** | 745 |
| NY PM | **44.515** | **15.630** | 672 |
| **Total** | **137.190** | **62.918** | días no sumables entre sesiones |

Las **62.918** son repeticiones M1 de hipótesis, no 62.918 setups ni operaciones. **Tres** días tuvieron hipótesis as-of anteriores a una sesión posteriormente incompleta: 2 NY AM y 1 NY PM; no borrar retroactivamente una tesis válida cuando su as-of era anterior al gap, y tampoco convertirla en sesión completa. Esta prevalencia no demuestra selectividad ni fidelidad del autor.

### 5.D. M2 QORE fuente primera vela: población exacta 775×3

[CI #38975891228](https://github.com/mezas3238-hue/qore-core/actions/runs/38975891228) contra 2.325 fichas independientes:

| Sesión | Fuente QORE CONFIRMED | UNKNOWN | REJECTED por calendario nominal | Sin primer M1 | G3 DTO positivo primer M1 |
|---|---:|---:|---:|---:|---:|
| London | **283** | **489** | **2** | **1** | **398** |
| NY AM | **97** | **668** | **8** | **2** | **203** |
| NY PM | **65** | **670** | **8** | **32** | **160** |
| **TOTAL** | **445** | **1.827** | **18** | **35** | **761** |

**Descomposición de los 761 DTO positivos**: 445 fuentes QORE trazables/continua; 298 QORE fuente incierta por huecos; 18 rechazados por la convención previa de cash nominal. De los 1.827 UNKNOWN, **1.529** son casos sin DTO G3 positivo, no 1.529 falsos positivos.

**London a las 03:01 NO puede usar el rango London 03–05 COMPLETO:** el pool London 03–05 es UNKNOWN a esa hora hasta cerrarse. La regla “H1 09 TTrades” no aplica London/NYPM.

[CI #39037937522](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522) reconstruyó por separado los 743 intervalos 445+298 desde el fin de fuente DOL hasta as_of: **London 283 completos/113 gapped; NY AM 97/98; NY PM 65/87**. En los 298, los gaps M1 impiden demostrar que el nivel seguía sin tocarse; status **WAIT/UNKNOWN**, nunca UNCONSUMED PROVEN. 156.331 minutos faltantes **sumados por intervalos que pueden solaparse** y máximo individual aprox. 2.946/2.991/2.946 min; **NO** son M1 ausentes únicas ni prueba de broker cerrado. Issue **[#997](https://github.com/mezas3238-hue/qore-core/issues/997)**.

### 5.E. Las 18 discrepancias del CASH previo — RESUELTAS COMO FUENTE, NO COMO MÉTODO

Inicialmente el auditor [#993](https://github.com/mezas3238-hue/qore-core/pull/993) marcó 18 REJECTED por etiqueta automática **COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE**. El auditor usaba **día hábil nominal inmediatamente anterior** en el rango cash 09:30–16:00; G3 seleccionaba **última sesión cash realmente completa M1**. **No inferir lookahead** a partir del nombre de aquella etiqueta.

El **contrafactual preregistrado de 18 fechas** [CI #38976680827](https://github.com/mezas3238-hue/qore-core/actions/runs/38976680827) comprobó que:
- **18/18** cash que eligió G3 tenían **390/390 M1 09:30–16:00** completas y HIGH/LOW **idéntico** al precio original del DTO.
- **18/18** días nominales anteriores tenían menos de 390 M1 (incluidos 0, 209, 210, 224, 225, 378, 383, 388 o 389 M1).
- **0/18** disponían de otra sesión cash completa más reciente entre origen G3 y día evaluado.
- **0** discordancias precio/familia para esas 18 fuentes. **NO se probó que G3 leyera el futuro**; tampoco que política “último cash completo” sea la correcta doctrina ICT/TTrades o el calendario broker CFD. Issue **[#994](https://github.com/mezas3238-hue/qore-core/issues/994)** sigue abierto para decisión Owner/fuente primaria + PIT.

Fechas y testigos individuales, con NYAM/NYPM/London, en el [INFORME M2 de 18 casos](https://github.com/mezas3238-hue/qore-core/blob/1de03f9946db1b339ca5785a163513adcb08d490/docs/research/VT31_M2_TRISESION_DOL_REAL_PROVENANCE_18_CONTRADICTIONS_2026-10-16.md). **No borrar los 18 REJECTED del expediente anterior**: preservan que la primera versión del auditor tenía otra política; nueva política solo tras versión, prereg y firma.

### 5.F. Barrera experimental M2-C PRE-OPS #999: resultado NO nativo

Se añadió **scripts/vt31_m2c_preops_source_admission_20261018.py** y **tests/infrastructure/test_vt31_m2c_preops_source_admission_20261018.py** con una máquina de estados que recibe M1 cerrada cronológica y **una decisión G3 original congelada** justo al cierre de su primera vela: rechaza as_of incorrecto, OHLC ajeno, familia/price contradictorios, H1 NYAM ausente, fuente posterior, M1 gaps y policy cash unsigned, con independencia DST/3 ventanas.

**[CI #39096851001 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/39096851001)**, Ruff PASS, 96 pytest PASS sobre el M1 original; casebook nuevo 761 SHA **ae07fc4500223a91428377191f849ce3fa19e5bede5e3da1c9ea075105d3fbe3**:

| Perfil | SOURCE_CONTEXT_COMPLETE_UNCERTIFIED | WAIT_SOURCE_M1_GAP | WAIT_CASH_CALENDAR_POLICY_UNSIGNED |
|---|---:|---:|---:|
| London | 283 | 113 | 2 |
| NY AM | 97 | 98 | 8 |
| NY PM | 65 | 87 | 8 |
| **TOTAL** | **445** | **298** | **18** |

**Todos los 761 retornos:** ops_cognition = None, ops_authorized = false, signed = false, certificados = false, órdenes/sizing = 0. Aunque 445 tengan fuente QORE completa, **NO son autorizados a OPS** sin método autoral y firmas. El fixture de G3 ya estaba sellado antes de este run: la barrera es causal respecto de las M1 que observa, pero **este ensayo NO reejecutó COG original live ni integró M2 en VT31Trader**. No declarar M7 PASS.

---

## 6. CATÁLOGO COMPLETO DE PROBLEMAS POST-R5 — CAUSA, EVIDENCIA Y SOLUCIÓN

Leer también **B01–B20** íntegros en R5 y B28 en PR #998. Esta es la ampliación, con ID de este handoff **R6-B21…R6-B49**, prioridad, dueño propuesto y criterio falsable.

| ID / prioridad | Síntoma / raíz | Evidencia o repro exacto | Solución requerida y cierre verificable |
|---|---|---|---|
| **R6-B21 / P0** | Native trader G3 COG→OPS LEGACY por defecto | [run FALLIDO #38794447738](https://github.com/mezas3238-hue/qore-core/actions/runs/38794447738), issue [#984](https://github.com/mezas3238-hue/qore-core/issues/984) | [#987](https://github.com/mezas3238-hue/qore-core/pull/987) corrigió **en rama DRAFT** con opt-in explícito y política interna congelada; 173 PASS. No cerrar en main hasta review de cadena y M2 |
| **R6-B22 / P0** | H1 09 TTrades se validaba solo en driver, no native | [#982](https://github.com/mezas3238-hue/qore-core/pull/982) research gate externo | [#989](https://github.com/mezas3238-hue/qore-core/pull/989) puso H1 NYAM + gap/inicio M1 **antes de COG** native, 202 PASS; no contaminar London/PM y obtener Owner profile |
| **R6-B23 / P0** | M2 source todavía alimenta OPS G3 automáticamente en native, incluso si QORE liquidez UNKNOWN | [#1000](https://github.com/mezas3238-hue/qore-core/issues/1000), [#999](https://github.com/mezas3238-hue/qore-core/pull/999) prueba solo fixtures | Construir integración versionada **COG online original → M2 preOPS → OPS original**, prohibir positivo si UNKNOWN o método unsigned, 1M M1 + 775×3 + anti-bypass, sin tocar blobs |
| **R6-B24 / P0** | 298 DTO positivos con M1 faltantes entre fuente DOL y as_of | [#996 CI #39037937522](https://github.com/mezas3238-hue/qore-core/actions/runs/39037937522), issue [#997](https://github.com/mezas3238-hue/qore-core/issues/997) | M2 WAIT_SOURCE_M1_GAP, no inferir no-toque, exact source-end/as-of, rechazar gap aunque G3 LONG/SHORT; cerrar con versión nativa + unit adversarial |
| **R6-B25 / P0** | 18 niveles cash G3 parecían futuros por política _previous_weekday del testigo | [#993 CI #38976680827](https://github.com/mezas3238-hue/qore-core/actions/runs/38976680827), #994 | Source lineage real 18/18 reconciliado; **PENDIENTE** Owner + autor y calendario CFD PIT para elegir último full cash vs weekday nominal por perfil, nueva política firmable |
| **R6-B26 / P0** | 41 fichas sesión sin fuente completa; 30 NY PM 14h cero | [#980](https://github.com/mezas3238-hue/qore-core/pull/980) 774/769/741; informe gapbook | Conseguir **broker/provider instrument calendar PIT**, source provenance, determinar festivo/gap/early close/limitación feed; no interpolar ni inventar sesiones CFD cerradas |
| **R6-B27 / P0** | TTrades NY AM requiere DOL del extremo opuesto H1 09, G3 cash DOL/MIN10 no coinciden | [#950](https://github.com/mezas3238-hue/qore-core/pull/950)/[#955](https://github.com/mezas3238-hue/qore-core/pull/955)/[#956](https://github.com/mezas3238-hue/qore-core/pull/956) | Acordar política fuente-first NYAM y abstención si <10 QORE, sin cambiar objetivo del autor; validar LONG/SHORT y documento Owner |
| **R6-B28 / P0** | ICT 2023 10 handles: interpretación dividida entre rango proyectado y displacement FVG | [#995](https://github.com/mezas3238-hue/qore-core/pull/995)/[#998](https://github.com/mezas3238-hue/qore-core/pull/998) | Revisar video **primario** con timecodes/screens de ejemplos y contraste longitud DOL/MSS/FVG, firmar una definición distinta por método |
| **R6-B29 / P0** | MSS vs CISD mezclados; pivote de 3 M1 no prueba displacement autoral | [#991](https://github.com/mezas3238-hue/qore-core/pull/991)/[#992](https://github.com/mezas3238-hue/qore-core/pull/992), 268 PASS WAIT | Criterios MSS cierre swing+desplazamiento y CISD first opposing OPEN separados; ejemplos visuales de fuente + M1 original+negativos, esperar validación |
| **R6-B30 / P0** | Swing que causa displacement distinto de extremo cercano/C2 wick; empates | [#943](https://github.com/mezas3238-hue/qore-core/pull/943), [#998](https://github.com/mezas3238-hue/qore-core/pull/998), 12/12 WAIT | Casos primarios M5 etiquetados; swing único causante, tiempo de conocimiento, invalidación; stop_tick_price NULL hasta cert |
| **R6-B31 / P0** | OB single opposing[-1] y breaker pivot único son proxies QORE | [#906](https://github.com/mezas3238-hue/qore-core/pull/906), [#961](https://github.com/mezas3238-hue/qore-core/pull/961), [#945](https://github.com/mezas3238-hue/qore-core/pull/945) | OB serie de velas opuestas + POI HTF + zona/body 50%; Breaker 4 piernas, rango y retest; source screenshots/autenticar M1 |
| **R6-B32 / P0** | Retest OB/Breaker V1 podía leer OHLC de vela abierta | [#979](https://github.com/mezas3238-hue/qore-core/pull/979) reproduce falso PASS de V1 | Preservar gate V2 que exige cierre M1, test ataque que no llama juez antiguo ante error, revisar todas las 4 familias |
| **R6-B33 / P0** | M0 return_inside sólo al as_of del retorno; retest posterior pierde tesis | [#983](https://github.com/mezas3238-hue/qore-core/pull/983) | Mantener memoria SourceContext sellada M0→M4, sin revalidar como presente evento antiguo; revisar caducidad y revocación |
| **R6-B34 / P0** | V2 permite mutación OHLC post-M0 ya observada y consume as_of ante REJECT | [#986](https://github.com/mezas3238-hue/qore-core/pull/986) contraejemplo real unit | V3 sello completo de cinta; usar versión **V4 PREPARE/COMMIT #990**, que no toca estado si REJECT/excepción; no depender de rollback privado V2 |
| **R6-B35 / P0** | El V3 usaba rollback privado de V2._last_assessed | [#986](https://github.com/mezas3238-hue/qore-core/pull/986) deuda documentada | #990 V4 clone+COMMIT después de validación; integrar usando API pública, tests de invariancia estado/retry mismo as_of |
| **R6-B36 / P0** | Fuente London rango 03–05 todavía no cerrada a 03:01 | [#993](https://github.com/mezas3238-hue/qore-core/pull/993) seis pools real | Mantener London source 03–05 UNKNOWN hasta cierre; no promover pool futuro aunque precio parcial parezca válido |
| **R6-B37 / P0** | G3 COG recurrente genera 62.918 positivos M1: contar como setups/trades sería error | [#982](https://github.com/mezas3238-hue/qore-core/pull/982) 137.190 evaluaciones, 62.918 repetidas | Definir identidad de tesis/evento por sesión, origen DOL/MSS y expiración; deduplicar antes de estadísticas de setups; no usar para cert autor |
| **R6-B38 / P0** | Caso primero completo, gap posterior: conservar snapshot OPS research anterior sin nueva actualización | [#989](https://github.com/mezas3238-hue/qore-core/pull/989) informe M0-B | Cancelación/revocación **causal y transaccional** de tesis research pendiente al detectarse gap, sin fingir OMS/cancelación broker; test antes/después |
| **R6-B39 / P0** | No hay perfiles M0 firmados ni contrato de fuente simultáneo entre ramas | [#971](https://github.com/mezas3238-hue/qore-core/pull/971), #978, #989, #957 | Owner confirma perfiles/límites por sesión, política previa PRE-M1 inmutable, CI contra hot-swap y salida de WAIT |
| **R6-B40 / P0** | Faltan **dos revisiones humanas independientes** COG/OPS sobre SHA exactos | [#897](https://github.com/mezas3238-hue/qore-core/issues/897) OPEN | Designar identidades, permisos, revisión y atestaciones con roles/SHAs, riesgos y límites OPS; no autovalidarse con agentes un login |
| **R6-B41 / P0** | Muchas ramas DRAFT entrecruzadas, podrían mezclarse contratos NYAM TTrades y London/PM ICT | cadenas A y B, #981 | Crear merge plan por DAG, fijar bases; resolver conflictos con pruebas de perfil/casos; PR por integración versionada, no merge main sin revisión |
| **R6-B42 / P1** | CI PASS sintética confundida con certificación autor | 96/101/127/139/173/202/268/300/333 pruebas contienen regresiones | Separar unit engineer PASS, fuente real PASS, comparación contra autor firmada, COG autonomías ciegas y certificados |
| **R6-B43 / P1** | Primer intento de CI M2-C falló Ruff snake_case; segundo quedó con KeyError JSON original_G3_draw_family | [Actions FALLIDOS #39096715814](https://github.com/mezas3238-hue/qore-core/actions/runs/39096715814) y [#39096766743](https://github.com/mezas3238-hue/qore-core/actions/runs/39096766743) | Corregido sin mutar fixture, preservando clave exacta original_G3_draw_family; **FINAL #39096851001 SUCCESS 96 PASS**. No borrar los fallos históricos |
| **R6-B44 / P1** | M5 primer CI lint falló; otro CI exigía continuidad artificial a través de cambio de día | [#998](https://github.com/mezas3238-hue/qore-core/pull/998) CI FALLIDOS #39096786803 y #39096870683 | Corregido: V4 sello historico+continuidad post-M0, [#39096941093](https://github.com/mezas3238-hue/qore-core/actions/runs/39096941093) 333 PASS. Evitar relajación que abra gaps post-M0 |
| **R6-B45 / P1** | Los 298 huecos suman 156.331 minutos SOLAPADOS, máximos hasta ~49h | [#996](https://github.com/mezas3238-hue/qore-core/pull/996) | No comparar sumatorio con M1 faltantes únicos ni con horas broker; reconstruir calendario point-in-time y source lineage |
| **R6-B46 / P1** | Datos NAS100 M1 sin equivalencia bid/ask/ticks de cTrader USTEC | [#901](https://github.com/mezas3238-hue/qore-core/pull/901), #980 | No declarar edge neto, fill CE, stop tick ni rollout económico a partir de OHLC |
| **R6-B47 / P0** | Riesgo caducidad de artifacts GitHub Actions, no backups probados | [#837](https://github.com/mezas3238-hue/qore-core/issues/837), IDs fuente #11459859004 y sellos | Consultar expires_at, licencia, Data Vault privado/versionado, backup/restore SHA en lector independiente; no hacer público precio restringido |
| **R6-B48 / P0** | Ninguna prueba acredita trader unificado con **los tres certificados** metodológicos/cognitivos | issue #981 y #957 OPEN | Conectar fuente autoral M0–M5, M6 doble firma y emitir certificados separados por perfil; M7 conjunto solamente si los tres PASS |
| **R6-B49 / P1** | No hay falsador integral de error entre memoria M0→M4 de rama A y DOL M2 de rama B | PR #998 vs #999 en DAGs distintos | PR de integración con replay real G3 vivo y paridad exacta solo donde contratos originales coinciden; exigir REJECT ante conflicto, no reducir número de WAIT con lookahead |

**Controles de auditoría adicionales:** no reutilizar cierres “PASS” de la política LEGACY para G3 opt-in; comprobar Git blob SHA en cada CI; nunca reescribir firmas/acta selladas, ni tocar holdout sellado, ni suponer que editar un DRAFT actualiza main. La vulnerabilidad causal de _last_assessed (R6-B34/35) pertenece a COG V2/V3 experimental de la otra rama; no confundir con un bug reproducido del G3 congelado.

---

## 7. MATRIZ DE ESTADO METODOLÓGICO M0–M7, LONDON / NYAM / NYPM

| Gate | London ICT_GENERAL_2023 | NY AM TTRADES_NY_AM_2025 | NY PM ICT_GENERAL_2023 | Cierre que falta |
|---|---|---|---|---|
| **M0 perfil/clock** | reloj/admisión research | H1 09 + reloj native research PASS | reloj/admisión research | política de perfil aprobada Owner y selección inmutable; independencia 09H |
| **M1 feed causal** | **774/775** source completos | **769/775** con H1 09 | **741/775** source completos | 41 gaps PIT CFD y source sponsor, no calendario inventado |
| **M2 DOL/liquidez** | 283 QORE contexto íntegro / 113 gapped / 2 cash policy | 97 / 98 / 8 | 65 / 87 / 8 | Doctrina DOL fuente ICT/TTrades + los 298 WAIT y 18 policy; native gate #1000 |
| **M3 MSS/displacement** | #995 fuente ICT y #992 testigos WAIT | #977 V6 + #992 CISD/MSS geométrico WAIT | #995 fuente ICT y #992 WAIT | swing relevante y desplazamiento en casos autorales anotados |
| **M4 entradas** | FVG geometría research, OB/Breaker incompletos | cuatro familias TTrades definidas textual, no validadas en OHLC autor | como London | displacement directa/FVG/OB/Breaker con prioridad y retest M1 totalmente cerrado |
| **M5 swing/stop** | #998 testigos source extremum WAIT | #998 testigo V4 WAIT y stop_tick_price=NULL | #998 WAIT | swing causante real, invalidez/stop autoral con ejemplos y negativos |
| **M6 independencia** | NO FIRMADO | NO FIRMADO | NO FIRMADO | dos humanos distintos COG y OPS #897, SHA exacto |
| **M7 tribunal/cert** | NO CERTIFICADO | NO CERTIFICADO | NO CERTIFICADO | integración nativa end-to-end + 3 certificados + firma Owner |

**No emitir sólo un “promedio de tres sesiones”.** Un GATE en FAIL/UNKNOWN de cualquier sesión mantiene esa sesión NO certificada; para certificar el trader conjunto deben existir los tres resultados y una revisión integradora. **COG original LONG/SHORT** no demuestra M3/M4/M5 autoral.

## 8. QUÉ NO SE HA HECHO (TRAZABILIDAD NEGATIVA)

- NO se certificó por metodología ni cognitiva a London, NY AM, NY PM ni al VT31 conjunto.
- NO se firmó por Owner una política completa ICT_GENERAL/TTrades/compatibilidad MIN10 y DOL.
- NO se obtuvo validación dual HUMANA real de COG/OPS, ni se firmó la edición exacta de códigos de los PR nuevos.
- NO se integró M2-C #999 en el VT31Trader nativo; el experimento usa los 761 DTO originales pregrabados.
- NO se ejecutó en el PR #999 el original COG vivo para producir otra vez sus 761 eventos; sí se ha ejecutado original G3 online en #982/#987/#989, que no contienen gate M2 completo.
- NO se demostró que todas las fuentes DOL de QORE fueran la doctrina ICT, ni que 445 CONFIRMED fueran setups/method PASS.
- NO se obtuvo calendario/metadata PIT NAS100 CFD, ni equivalencia feed ticks BID/ASK completa del histórico M1; NO se reconstruyeron velas ausentes, ni se etiquetaron cierres inventados.
- NO se adjudicaron contra gráficos primarios del autor MSS/displacement, CISD serie opuesta, cuatro entradas y swing que produjo displacement para las TRES sesiones.
- NO se ejecutaron fills, órdenes, sizing, Profit Factor, Sharpe, Sortino, drawdown, DEMO/LIVE/OMS/VPS ni merge main.
- NO se afirma que el histórico NAS100 ya explorado sea holdout virgen o que existan pruebas económicas de rentabilidad de esta arquitectura.
- NO se completó backup Data Vault duradero con prueba restore SHA de todos los originales; el riesgo continúa abierto.

## 9. ARCHIVOS Y WORKFLOWS QUE ABRIR EXACTAMENTE

### Código original protegido (leer antes de integrar)

- src/qore/infrastructure/traders/vt31_ict_cleanroom/contracts.py — sesión/timezone, DTO M1, CognitiveDecision, políticas G3 y LEGACY, regla MIN_INDEX_POINTS.
- src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py — original G3, memoria/pivotes/pools, observe_closed_m1 y assess.
- src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py — original OPS, G3 anchor check M1, FVG, invalidación, no broker.
- src/qore/infrastructure/traders/vt31_ict_cleanroom/trader.py — **modificado en PR #987 y PR #989 sin cambiar COG/OPS G3**; G3 opt-in + strict_source_admission preCOG NYAM H1/gap.

### Línea B de M1 real/M2 PRE-OPS — HEAD de PR #999

- scripts/vt31_trisession_online_real_g3_cog_20261015.py — replay G3 online referencia/estricto, 775×3 adjudicación posthoc; NO utilizar source ledger futuro como admission input.
- scripts/vt31_m7a_native_g3_full_m1_parity_20261015.py — comparación native G3/OPS con adaptador anterior.
- scripts/vt31_m0b_native_trisession_source_parity_20261016.py — admisión estricta native H1 09/gaps, doble replay 2.325.
- scripts/vt31_ict_dol_source_v1_20261014.py — auditor SEIS pools QORE, política nominal _previous_weekday **todavía no homologada**, no tocar para maquillar 18 REJECTED.
- scripts/vt31_m2_trisession_real_dol_first_m1_source_20261016.py — tribunal de 2.325 source y 761 DTO G3.
- scripts/vt31_m2_prior_cash_18_real_m1_calendar_triage_20261016.py — 18 fuentes cash 390/390 precio exacto.
- scripts/vt31_m2_298_unknown_closed_m1_gap_forensic_20261017.py — 743 testigos de gap M1, 445+298.
- **scripts/vt31_m2c_preops_source_admission_20261018.py** — gate experimental PRE-OPS M2-C sobre 761 DTO originales previamente sellados.
- tests/infrastructure/test_vt31_m2c_preops_source_admission_20261018.py — adversariales tres sesiones / EST EDT / identidad de as_of / H1 09/ gap/price / sin autorización.
- **.github/workflows/vt31-m2c-preops-original-g3-real-m1-20261018.yml** — última CI de la línea B. Inputs originales y ZIP hash; Artifact final #12124872447.
- docs/research/VT31_M2C_PREOPS_761_ORIGINAL_G3_THREE_SESSION_VERDICT_2026-10-18.md — informe del último gate B.

### Línea A de fuente y cognitiva

- scripts/vt31_cog_v4_transactional_context_20261016.py — COG V4 research clone PREPARE/COMMIT, no rollback V2 privado, source seal M1.
- scripts/vt31_m3_mss_cisd_separate_causal_witness_20261016.py — separa MSS/CISD geométricos causalmente, siempre WAIT sin displacement autoral.
- scripts/vt31_ict2023_london_nypm_causal_source_witness_20261016.py — ICT 2023 fuente London NYPM, FVG/MSS testigos.
- scripts/vt31_m5_three_session_displacement_swing_witness_20261018.py — 12 testigos M5 por las 3 ventanas, candidate_extreme_reference != SL.
- docs/research/VT31_M3_M4_M5_PRIMARY_SOURCE_ADJUDICATION_2026-10-16.md — matriz de fuentes primarias TTrades.
- .github/workflows/vt31-m5-three-session-swing.yml — última CI de línea A, [Actions #39096941093](https://github.com/mezas3238-hue/qore-core/actions/runs/39096941093).

**Aviso:** estos archivos NO están necesariamente todos en main. Para acceder a los de cada lane, especificar ref de HEAD PR #999 (B) o #998 (A). No concluir que faltan solo porque main no los tenga. Algunos nombres/datos históricos deben verificarse con árbol Git al hacer checkout.

## 10. PROTOCOLO DE REPRODUCCIÓN SIN CAMBIAR DATOS

Secuencia recomendada (sin ejecutar tareas económicas, sin empujar main):

~~~bash
# Inspección rápida; sustituir OWN por el repositorio configurado
REPO=mezas3238-hue/qore-core
gh pr view 999 -R "$REPO" --json headRefOid,baseRefName,isDraft,state
gh pr view 998 -R "$REPO" --json headRefOid,baseRefName,isDraft,state

# Doble barrera histórica fuente; las rutas M1 son descargas verificadas,
# NO el nombre de archivos en main:
gh run view 39096851001 -R "$REPO"
gh run view 39096941093 -R "$REPO"
gh run download 39096851001 -R "$REPO" --dir /tmp/vt31-m2c-evidence
gh run download 39096941093 -R "$REPO" --dir /tmp/vt31-m5-evidence

# Fuente M1 original autorizada solamente, no holdout:
gh api "/repos/$REPO/actions/artifacts/11459859004/zip" > /tmp/vt31-source.zip
mkdir -p /tmp/vt31-source && unzip -q /tmp/vt31-source.zip -d /tmp/vt31-source
echo "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa  /tmp/vt31-source/NAS100/market-evidence.json" | sha256sum -c -

# Obtener fixture histórico de 2.325 casos G3/M2. Verificar ZIP SHA
# y manifiesto interno ANTES de usarlo:
gh api "/repos/$REPO/actions/artifacts/12079131643/zip" > /tmp/vt31-m2-original.zip
echo "30de8306225941208ecea73ab4b9ba9b88b625b8b1e9794f47c758ea3fdce07a  /tmp/vt31-m2-original.zip" | sha256sum -c -
mkdir -p /tmp/vt31-m2-original && unzip -q /tmp/vt31-m2-original.zip -d /tmp/vt31-m2-original
(cd /tmp/vt31-m2-original && sha256sum -c SHA256SUMS)

# Al hacer checkout de branch B #999 con dependencias Python instaladas:
PYTHONPATH=src:. pytest -q -n 4 -o addopts='' tests/infrastructure/test_vt31_m2c_preops_source_admission_20261018.py
PYTHONPATH=src:. python scripts/vt31_m2c_preops_source_admission_20261018.py \
  --market /tmp/vt31-source/NAS100/market-evidence.json \
  --original-m2-casebook /tmp/vt31-m2-original/VT31_M2_REAL_QORE_DOL_2325_FIRST_M1_CASEBOOK.json \
  --out /tmp/vt31-m2c-repeat.json
~~~

Estas instrucciones usan GitHub CLI y Python en entorno autorizado, con permisos de lectura a los artifacts **mientras no hayan expirado**. Cualquier copia local de datos se debe gestionar según licencia y seguridad. Versionar **un nuevo SHA si se modifica formato** y conservar el expediente anterior; nunca actualizar objetivos esperados para forzar PASS. El workflow del PR #999 es prueba de referencia completa. El runner QORE Research/Ultra Fast puede acelerar la ejecución sintética; verificar identidad de FULL JSON y source SHA, no solo contadores.

### Tests innegociables para PR M2-D (#1000) y el futuro tribunal

- Un **solo VT31** con una sola COG y sesiones separadas por fecha, reloj NY IANA, sin mezclar estado G3 ni 09H TTrades a ICT.
- Ante M1 NYAM 10h con H1 09 incompleta ⇒ **WAIT antes de COG**; Londres y PM no heredan este requisito.
- Ante primer minuto M1 ausente o salto intraventana ⇒ **SOURCE_START_MISSING_WAIT / SOURCE_GAP_WAIT** y memory-only para datos presentes; no COG/OPS positivo tras gap y sin borrado retroactivo.
- Ante DOL fuente QORE verificada pero con gap entre fuente y as_of ⇒ **M2 WAIT**, aunque COG original emita LONG/SHORT. Todos los 298 casos originales deben demostrar WAIT exacto en la ventana/fecha correspondiente.
- Ante cash 18 con origen OHLC confirmado pero criterio calendario no firmado ⇒ **M2 WAIT_CASH_CALENDAR_POLICY_UNSIGNED**; no llamar lookahead probado ni pasar a OPS sin método Owner.
- Ante 445 con fuente QORE completa ⇒ **SOURCE_CONTEXT_COMPLETE_UNCERTIFIED**, no promoción autoral ni OPS positivo mientras M2, M3, M4, M5 y M6 no estén firmados.
- Ante cambio de política COG/trader sincronizado después del constructor ⇒ REJECT antes de observar M1; mantener identidad congelada #987.
- Ante mutación de M1 post-M0 o REJECT a mitad de transacción ⇒ no mutar ningún sello/observación/estado COG V4 #990, permitir retry legítimo del mismo as_of.
- Fuente y decisiones deben concordar con los SHAs **originales**; una prueba source-only PASS no se convierte en Autor PASS si desaparecen WAIT/UNKNOWN por filtrado posterior.
- Asegurar que OPS research pendiente se invalide/revoque tras fuente desaparecida/gap sin fabricar cancelación de broker, fill, stop o ejecución.

## 11. PLAN DE EJECUCIÓN DEL PRÓXIMO ARQUITECTO — ORDEN Y CRITERIO DE TERMINACIÓN

### P0-A: reconciliar código de dos ramas sin mezclar métodos

1. Abrir branches HEAD exactos #999 y #998; comparar solo scripts/documentos de investigación que cada uno añade, contratos frozen y tests regresivos.
2. Anotar en #727 y #981 quién es arquitecto cognitivo y quién metodológico, evitando editar archivos concurrentes sin compare/review.
3. Preregistrar propuesta **M2-D** del issue #1000. Mantener source core G3/OPS intocable o crear nueva capa de coordinación explícitamente versionada si requiere permiso; **no** cambiar silenciosamente semántica DTO ni fingir certificados.
4. Fijar API de pre-OPS: observation M1 cerrada → COG as_of → witness DOL fuente + M0 → decision WAIT/REJECT/CONTEXT_SOURCE_ONLY → OPS receives None hasta firma. Versionar el caso de OPS research pendiente tras gap y mantener memoria causal.
5. Ejecutar tests unitarios/adversariales EST/EDT, H1 exclusiva NYAM, source_end, as_of, quiebres, cash 18, fuente M1 real y 3 ventanas; CI FAIL si algún positivo llega a OPS. Materializar evidence SHA.

**Salida:** M2-D native engineering RESEARCH PASS o rechazo falsado, nunca certificado del autor. Si no hay firma autorizando cambiar native trader, aislar nuevo coordinator testigo en un PR research separado y dejar M7 bloqueado.

### P0-B: cerrar la FIDELIDAD metodología/COG por sesión

1. ICT London/NYPM: video fuente **https://www.youtube.com/watch?v=tRq1hyGGtl4**; extraer cortes con timecodes sobre DOL, raid, MSS desplazamiento, 10 handles, primera FVG, caducidad/invalidez, stop. Para cada ejemplo, vincular gráfica original + timestamp NY + OHLC M1 autorizado + negativo.
2. NYAM TTrades: leer original **https://ttrades.com/the-am-silver-bullet-strategy-on-nq/**; fijar H1 09 exacta, raid, retorno, objetivo opuesto, cuándo necesita displacement/MSS, y sus **cuatro familias displacement/FVG/OB/Breaker**. No exigir CISD+MSS a todos si el artículo no lo exige. Resolver casos 5/4pt DOL vs MIN10 sin bajar MIN10 por conveniencia.
3. M2 cash: acuerdo firmado sobre última sesión cash íntegra vs weekday nominal; PIT histórico NAS100 CFD por fechas #994; publicar 18/18 clasificación conclusiva o WAIT justificado.
4. M3: cerrar swing relevante, displacement autoral y distinción MSS vs CISD en ambos sentidos, con as_of de derecho a conocerlos. Los 113 geometrías únicas V6 y testigos M3 #992 no prueban MSS sin displacement.
5. M4: dar fuentes positivas y negativas para las cuatro entradas, OB series/mean/POI HTF y Breaker 4 piernas + retest M1 cerrado. Evitar self-confirmation por script que implementa y audita la misma regla.
6. M5: identificar swing que CAUSÓ displacement (no proxy C2 ni wick del raid), invalidación y stop de fuente, con timecodes y M1; mantener stop_tick_price=None hasta resolverlo.
7. Congelar reglas por perfil ANTES de otro replay. No inferir autoría a partir de proporción de positivos G3 o rate de PASS en CI.

**Salida:** para London, NYAM y NYPM, matrices method-specific con criterios trazables, prueba adversarial y veto explícito si falta fuente.

### P0-C: gobernanza independiente y triple certificado

1. Owner aprueba versión de política perfil M0 en documento con SHA y responsabilidades.
2. Designar dos firmantes humanos de identidades distintas y permisos apropiados COG/OPS en [#897](https://github.com/mezas3238-hue/qore-core/issues/897). Firmas individuales sobre *mismos* documento/código/casos/artefactos; revisión técnica explícita no es un “LGTM” de una misma cuenta.
3. COG certifica contexto/as-of/MSS/cambio de tesis/WAIT y responsable de swing+displacement; OPS verifica M1/anchor, método y revocación sin asumir que puede detectar bug de estructura COG.
4. Ejecutar tribunal con **3 sesiones separadas** y después tribunal conjunto; emite **certificado metodología** separado del **certificado cognitiva**, con SHA y problemas residuales. Si solo hay evidencia parcial, estado sigue WAIT/NOT_CERTIFIED y se deja informe con faltantes exactos.
5. Solo después, en proceso DISTINTO, hablar de edge económico o L1–L10 oficiales; no activar trading por este handoff.

### P1: preservación y trazabilidad

- Data Vault [#837](https://github.com/mezas3238-hue/qore-core/issues/837): backup/licencia/restauración SHA de NAS100 M1 y artifacts prioritarios antes de expiración.
- Mantener [issue #727](https://github.com/mezas3238-hue/qore-core/issues/727) como muro de intercambio entre arquitectos, [#981](https://github.com/mezas3238-hue/qore-core/issues/981) como estado de 3 certificados y [#957](https://github.com/mezas3238-hue/qore-core/issues/957) como P0 doctrinal.
- Registrar fecha, runner ID, SHA de código, prereg ancestor y error/contrato al corregir CI; incluir FAIL históricos significativos, no solo runs verdes.
- Evitar mezclar el árbol main con PRs no fusionados o afirmar “integrado” cuando la funcionalidad vive solo en scripts Research.

## 12. SEMÁFORO DE ESTADO FINAL — LEGIBLE POR MÁQUINA / GOBERNANZA

~~~yaml
project: QORE_CORE_VT31_NAS100
as_of: 2026-10-20
source_market: NAS100_1059784_REAL_M1_DEV_NOT_HOLDOUT
trader_identity: VT31_SINGLE
london:
  source_profile_research: ICT_GENERAL_2023
  window_new_york: "03:00-04:00"
  m1_complete_days: "774/775"
  methodology_certified: false
  cognition_certified: false
  session_certified: false
ny_am:
  source_profile_research: TTRADES_NY_AM_2025
  window_new_york: "10:00-11:00"
  h1_09_complete_required: true
  m1_h1_complete_days: "769/775"
  methodology_certified: false
  cognition_certified: false
  session_certified: false
ny_pm:
  source_profile_research: ICT_GENERAL_2023
  window_new_york: "14:00-15:00"
  m1_complete_days: "741/775"
  methodology_certified: false
  cognition_certified: false
  session_certified: false
research_engineering:
  native_G3_OPS_optin_trader_branch: PASS_NOT_MERGED
  native_preCOG_h1_gap_branch: PASS_NOT_MERGED
  original_G3_live_3session_replay: PASS_RESEARCH
  qore_M2_source_confirmed_first_m1: 445
  qore_M2_gap_unknown_first_m1: 298
  qore_M2_cash_policy_disputed_first_m1: 18
  preOPS_fixture_gate_761: PASS_RESEARCH_ONLY_NOT_NATIVE
  native_COG_M2_OPS_end_to_end: PENDING
author_governance:
  method_policy_owner_signed: false
  ict_ttrades_M2_M3_M4_M5_source_certified: false
  M6_independent_COG_OPS_human_signatures: false
  issue_897: OPEN
  issue_994: OPEN
  issue_997: OPEN
  issue_1000: OPEN
trader_methodology_certified: false
trader_cognition_certified: false
trader_certified: false
orders: 0
fills: 0
sizing: 0
PnL_certification_used: false
demo_live_vps_authorized: false
merged_to_main: false
~~~

---

## 13. FIRMA DE HANDOFF Y NORMA DE CONTINUIDAD

Este documento es **un acta documental de transferencia**, NO una firma metodológica o cognitiva y NO modifica el núcleo sellado G3. Los PR anteriores son DRAFT de investigación. Un CI verde indica exclusivamente que sus **asserts y fuentes verificadas** pasaron; no que la estrategia sea fiel al autor, rentable o autorizada para operar.

**Siguiente acción verificable y prioritaria:** [issue #1000](https://github.com/mezas3238-hue/qore-core/issues/1000) — integración versionada G3 COG original online → veto M2 disponibilidad → OPS G3 research dentro del único VT31 con tres sesiones, sin bypass, sin inventar autoría, junto a adjudicación de fuente ICT/TTrades M2–M5 del arquitecto A y cierre de firmas humanas #897.

**No emitir CERTIFICADO_METODOLOGÍA ni CERTIFICADO_COGNITIVA ni CERTIFICADO_VT31 hasta que existan pruebas y firmas independientes para CADA sesión.**
