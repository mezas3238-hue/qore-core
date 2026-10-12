# QORE CORE — QORE-ALPHA 2
# HANDOFF MAESTRO INTEGRAL PARA EL SIGUIENTE ARQUITECTO

**Fecha de corte:** 12 octubre 2026 UTC. **Carácter:** traspaso de contexto científico, técnico, infraestructura y backlog; ningún permiso de trading.
**Repositorio:** https://github.com/mezas3238-hue/qore-core
**Rama:** research/qore-alpha2-original-intermarket-propagation-20261012
**PR dueño:** https://github.com/mezas3238-hue/qore-core/pull/840 — DRAFT, RESEARCH ONLY, NO MERGE.
**Issues:** #838 investigación/owner; #843 volumen W2; #852 economía BIDASK/costes/PIT/OOS; #868 contratos; #837 licencias-vault-expiración; #856 zero spread; #863 relojes first-seen (QORE Native).
**Referencia previa obligatoria:** docs/research/QORE_ALPHA2_RESEARCH_MASTER_CHECKPOINT_THREE_HYPOTHESES_AND_G2_2026-10-12.md. No sustituir ni borrar los antiguos preregistros ni documentos de resultados.
**GitHub PR HEAD inspeccionado antes del traspaso:** cb4490e1f95d46ecf316759c483fd91b7aba51cc; comprobar HEAD actual porque otros arquitectos pueden agregar commits. Este documento es la entrada de lectura más reciente.

> DICTAMEN GLOBAL: QORE-Alpha 2 es un trader NATIVO diseñado para descubrir y certificar metodologías originales mediante pruebas falsables, no para copiar autores o declarar rentabilidad por promesa. W1 PATR, W2 PADE y W3 CMTRL fueron ejecutados sobre 33 mercados y NO demostraron ventaja económica incremental conforme sus reglas congeladas. Fuentes BID/ASK parciales y prospectivas DEMO están verificadas, pero no equivalen a ejecuciones ni resultados NET. **0 traders Alpha2 certificados, 0 órdenes autorizadas, 0 PF/Sharpe/Sortino/DD NET demostrados.** VPS, MT5, Shared, CIBO, QDLE y producción intactos. Toda investigación únicamente en GitHub Trader Lab.

---

## 0. PRIORIDADES EJECUTIVAS Y REGLAS DE PARADA (LEER PRIMERO)

| Nivel | Riesgo/prioridad | Obligación del siguiente arquitecto | Gate de aceptación |
|---|---|---|---|
| P0-A | **Pérdida irreversible de los históricos M5** | Resolver licencia de conservación, aprobar vault PRIVADO autorizado, copiar y restaurar 12 Atlas ANTES del **2026-12-16 00:21:18Z**, luego 21 ICMarkets antes de alrededor de 2027-01-10 | 33 ZIP + SHA original + SHA internos + restauración independiente REAL |
| P0-B | Contratos no homologados | Verificar Atlas12 versus DEMO21, fuente/cuenta/moneda, NAS100↔USTEC y SP500↔US500, NZDUSD/XAGUSD y costes por época | Contratos/efectividad/point value/fees probados o UNKNOWN explícito |
| P0-C | BID/ASK incompleto para entradas y salidas | Fuente legal, sostenible, misma cuenta y timestamps as-of por lado, cobertura por trayectorias | Entry+exit originales plenamente cubiertos, no imputaciones |
| P0-D | Economía y eventos conocidos en el momento | Broker commissions bid/ask, funding/swap, FX/pip, slippage, gaps, rechazo, DST y noticias macro PIT | Modelo económico NET verificable, no stress sintético |
| P0-E | Ningún edge positivo replicado | Mantener congelados W1/W2/W3. Nuevo diseño SOLO sobre muestra realmente nueva con prereg, potencia, control causal y UTC-001 | Nueva señal certificada por todos los años/folds; nunca optimización del histórico explorado |

**CRÍTICO: P0-A es independiente de la rentabilidad.** No esperar al trader ni a P0-B para proteger fuentes que van a caducar. El repositorio GitHub es PÚBLICO: jamás subir los 728 MB de precios originales a main, commits o Releases públicos, ni crear servicios pagados/vault/VPS sin autorización humana y derechos de licencia.

**PARADA CIENTÍFICA:** no probar W4 adaptativo sobre 2016–2024 ya explorado; no retunar ratios, sesiones, stops, morfologías W1/W2/W3 buscando un ganador post-PnL; no convertir un PASS pytest o SHA en un PASS económico. No abrir ticks históricos 2026 reservados ni denominar OOS virgen al diagnóstico 2022–2024 que ya vio QORE.

---

## 1. VISIÓN DEL TRADER Y LÍMITES DEL ECOSISTEMA

**Objetivo original del proyecto:** crear un trader verdaderamente propio QORE-Alpha 2 que descubra relaciones de mercado causales, medibles, robustas y transferibles entre 33 mercados, no un derivado fiel a un autor. La certificación requiere rentabilidad NET reproducible después de todos los costes y con control de drawdown, riesgo de concentración y auditoría independiente. Ultra Fast Runner de Trader Lab es infraestructura para experimentar con el rigor causal; más velocidad/experimentos NO demuestran edge.

Separaciones estrictas: W1/W2/W3 corresponden a Alpha2; QORE Native (231 pruebas de siete metodologías y E1/E2/E3), Scalper, VT31, CIBO y Shared son programas separados. Reutilizar de QORE Native solamente evidencia de fuentes y programas verificadas de nuevo con SHA, sin atribuirle certificación ni alphas al nuevo trader. Shared/CIBO solo entran a una integración bajo aprobación posterior independiente; este handoff no autoriza órdenes en PAPER/DEMO/LIVE, QDLE, VPS o MT5.

Cadena de validación que NO puede saltarse: PREREG → identidad G0 y source SHA → causal PIT/anti-lookahead → densidad y poder → GROSS con comparador → BIDASK completo y contratos/fees por cuenta → NET → folds/años/MonteCarlo y cartera → revisión independiente de riesgos/UTC001 → permiso expreso. Cada estado fuente o test sintético se conserva separado de económicamente ejecutable.

---

## 2. G0 — UNIVERSO, COHORTES, HISTÓRICOS Y P0 ARCHIVO

### 2.1 Universo exacto, 33 instrumentos, no fabricar aliases
- Índices 3: NAS100, SP500, US30.
- Metales 2: XAUUSD, XAGUSD.
- Mayores 7: AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY.
- Cruces 21: AUDJPY, AUDCAD, AUDCHF, AUDNZD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, NZDCAD, NZDCHF, NZDJPY.

**Root manifest fuente33 SHA256:** 1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85.
- Original 12 CIBO Atlas: [GitHub Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), código HEAD ab782b8e9f890f86a2b6500070f0556b4b685e3d; otro broker/account distinto que NO fue homologado frente al nuevo21.
- Nuevo 21 ICMarkets DEMO: [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), HEAD e0ca5a13c866a19d8505c68cffc473598984b340.
- Manifest final33: [#38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960), HEAD dba0e0c3b61e430d3ed51abab562ebd92060a0ff.
- RAW y QUALITY de 11 particiones anuales por fuente validadas por SHA **antes** de leer OHLC.
- Development [2016-09-17,2022-09-17) UTC; diagnóstico [2022-09-17,2024-09-17); embargo de OHLC [2024-09-17,+∞). **Ya existían estudios previos QORE en estas fechas: NO virgin OOS**.

### 2.2 NUEVO P0: vencimiento real del ZIP, NO backup permanente
Prereg de la investigación de caducidad commit cc566b60eaea12d29cedff1314989ff9b4b586c8. Auditor metadata-only src/qore/research/alpha2_source33_artifact_expiry_inventory.py y tests/research/test_alpha2_source33_artifact_expiry_inventory.py; workflow .github/workflows/qore-alpha2-p0-original33-artifact-expiry.yml. [Actions #38302743314](https://github.com/mezas3238-hue/qore-core/actions/runs/38302743314) SUCCESS Ruff/7 tests, HEAD 7e5279eb07a09275a452fc3f57aaf87d75dc1f77, reporte artifact #11771227114.

**33/33 ZIP M5 originales con IDs, digest SHA256, RUN HEAD y expired=false al inventariar; tamaño TOTAL ~728,048 MB comprimidos**: Atlas12 ~260 MB, nueva21 ~468 MB. **PRIMER VENCIMIENTO 2026-12-16 00:21:18 UTC** del Atlas12; 21 vence aproximadamente 2027-01-10. El auditor reportó 64,172 días hasta vencimiento en su corte, pero confirmar fecha restante cuando actúe el nuevo arquitecto. El reporte es solamente metadata: authorised_private_durable_vault_backup_verified=false, archive_restore_rehearsal_verified=false; ARCHIVE_PERMANENTLY NO alcanzado.

**Tareas owner #837:** aclarar derecho contractual/licencias y retención redistribución (incluido cTrader/ICMarkets), aprobación de vault privado cifrado, usuario responsable, gasto, 2 copias y seguridad; exportación ZIP bit-exact de 12 (antes fecha límite) y 21; tabla de artifact_id/digest/HEAD/retención/símbolo/origen y SHA de RAW/QUALITY por año; restauración muestra anual con auditor distinto y sha original; añadir M1 con inventario propio. Nunca subir datasets sensibles o sujetos a licencia al repositorio PÚBLICO/Release ni a buckets no autorizados. Enlaces: docs/research/QORE_ALPHA2_P0_33_ORIGINAL_M5_728MB_ARTIFACT_EXPIRY_VERDICT_2026-10-12.md; [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837).

### 2.3 Volumen en 33 archivos no es volumen transado
[Source all33 #38273144621](https://github.com/mezas3238-hue/qore-core/actions/runs/38273144621) SUCCESS 35/35, **19.496.136/19.496.136** barras M5 preembargo tienen volume como entero positivo. cTrader ProtoOATrendbar.volume significa volumen en ticks/actividad, NO tamaño de compras/ventas ejecutadas en bolsa. Procedencia técnica original productor→datos auditada como source-code/AST en [#38287282241](https://github.com/mezas3238-hue/qore-core/actions/runs/38287282241), pero origen contractual entre cuentas cohortes por resolver.

---

## 3. TRES METODOLOGÍAS NATIVAS ORIGINALMENTE INVESTIGADAS, HOY CERRADAS

### W1 — PATR, propagación intermercados H4
Prereg docs/research/QORE_ALPHA2_ORIGINAL_PATR_METHOD_AND_UTC001_PREREG_2026-10-12.md. Engine en src/qore/research/alpha2_intermarket.py, alpha2_ultrafast.py, alpha2_lab_h4_extract.py, alpha2_signal_census.py y replay M5 alpha2_g1a_native_m5_gross.py/alpha2_g1a_panel_stats.py/alpha2_g1a_posthoc_anatomy.py. Vectorización/incremental O(T×N²), paridad vs implementación lenta en tests.
- [GHA señales33 #38268654596](https://github.com/mezas3238-hue/qore-core/actions/runs/38268654596) PASS 35/35, **224 señales**.
- [GHA gross M5 #38270999595](https://github.com/mezas3238-hue/qore-core/actions/runs/38270999595) PASS 35/35, 176 parejas evaluables (130 DEV,46 DIAG), 48 trayectorias censuradas. DEV gross −0,1674348 bps, diferencial vs benchmark −0,7287646; DIAG gross −3,4236609 bps, diferencial 0.
- Problema lógico: comparador con momentum propio H4 frecuentemente coincide con señal casi tautológicamente. Muestra insuficiente.
**Dictamen:** UNDERPOWERED_NO_SUPPORT. No retunar.

### W2 — PADE, actividad de ticks y desplazamiento H1
Prereg anterior al outcome commit 43688569fa8d9c5ba93a127ff6ae66f9091aeede, docs/research/QORE_ALPHA2_W2_PADE_FIRST_ECONOMIC_PREREG_2026-10-12.md. Código src/qore/research/alpha2_w2_pade_native_m5.py, alpha2_w2_pade_panel.py, alpha2_w2_volume_full33.py, alpha2_w2_volume_source_probe.py, alpha2_w2_posthoc_census.py. Control causal lagged trend.
- [GHA gross33 #38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547) PASS 35/35, **265 señales, 265 parejas**, 134 decisiones opuestas control. DEV n220, gross −1,7980456 bps, delta −4,5586313; DIAG n45, gross +3,3942738 bps, delta −1,9727721; DIAG falla tamaño mínimo 50.
- [Posthoc #38283910730](https://github.com/mezas3238-hue/qore-core/actions/runs/38283910730) CI calendario 4 semanas DEV delta [−13,5758;+1,6414] bps, DIAG [−8,1538;+2,4867], ambos atraviesan 0. **6 activos con 0 señales (3 índices,2 metales,1 más)** por requisitos de H1 consecutivas/sesiones; no extrapolar a índices/metales.
**Dictamen:** UNDERPOWERED_NO_SUPPORT. No aflojar reglas tras mirar resultados.

### W3 — CMTRL, posterior bayesiano online morfología H1
Prereg anterior al outcome commit a18cb43a6fb69eab948d840c6e6101c6a7251906, docs/research/QORE_ALPHA2_W3_CMTRL_LAST_EXPLORATORY_PREREG_2026-10-12.md. 8 estados de H1, aprendizaje solo con etiquetas ya maduras, 240 transiciones/Laplace, 20 H1 observadas en 72h, máximo 1 señal/día/símbolo, M5 gross y benchmark retardado. Código src/qore/research/alpha2_w3_cmtrl_native_m5.py, alpha2_w3_cmtrl_panel.py, alpha2_w3_posthoc_census.py.
- [GHA gross 33 #38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503) PASS 35/35, HEAD e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c, **24.487 señales, 24.399 pareadas, 88 censuradas, 10.841 decisiones opuestas benchmark**, 0 mercados sin señales. DEV n18.266 gross +0,18659759 bps, delta **−0,0151645**; DIAG n6.133 gross +0,06924182, delta +0,53515728.
- [Posthoc #38285345503](https://github.com/mezas3238-hue/qore-core/actions/runs/38285345503) CI 4 semanas DEV delta [−0,444306;+0,425179] bps; DIAG [−0,241776;+1,278238] bps. Familias 2.178 índices,1.623 metales,5.137 majors,15.549 cruces. IC incluyen 0.
**Dictamen:** NO_SUPPORT_PREDECLARED_GROSS. Más señales no equivalen a mejor edge. Es retorno GROSS mínimo antes de fricción; no declarar NET positivo/negativo no medido.

**CIERRE CIENTÍFICO:** Tres espacios de búsqueda W1/W2/W3 agotados y congelados sin superar hipótesis original. NO W4 oportunista sobre los mismos datos vistos. El próximo arquitecto investigará datos genuinamente nuevos/preregistros y potencia, no buscará rentabilidad por ajuste retrospectivo.

---
