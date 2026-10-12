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

## 4. G2 — BID/ASK HISTÓRICO ORIGINAL, FUENTE REAL PERO INSUFICIENTE

**El viejo título “sin BID/ASK real” del checkpoint inicial está superado como SOURCE PARTIAL, NO como NET.** Se conservaron fuentes originales verificables de QORE Native G1 para reutilización read-only; no traer su metodología ni certificación Alpha2.

### 4.1 Ventanas cortas históricas 29 exactos
- QORE Native PR #849/#851 produjo ZIP originales BID/ASK; re-admisión Alpha2 SHA [Actions #38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813) SUCCESS. **37.430 observaciones BID y 37.342 ASK** en 29 mercados, SOLO las ventanas originales **2020-09-15** y **2023-09-19** 13:00–13:10 UTC (dos bloques de 10 minutos). Original tercera ventana 2026-09-15 mantenida con precios reservados NO leídos en este estudio.
- Prereg calidad second-grid SHA commit cfd82a0b0e7a36e2bd27181742123bcc137e5430. [Actions #38289175880](https://github.com/mezas3238-hue/qore-core/actions/runs/38289175880) SUCCESS Ruff/14 tests. **29 × 2 × 600 = 34.800 observaciones de segundo**: 27.866 spread positivo; **4.297 BID=ASK cuarentena**; 2.637 ausente/stale; 0 crossed. Archivo estadístico firmado artifact #11764855653. Si BID/ASK es idéntico, no supone spread, comisión o fill gratis.
- Censo QORE Native independiente original [PR #855](https://github.com/mezas3238-hue/qore-core/pull/855): piloto fuente tres ventanas de 10 minutos en los **33 puestos** con 31 símbolos exactos y dos nombres alternos **SP500→US500** y **NAS100→USTEC**, 127.928 eventos nativos. Son 33 slots SOURCE, **NO 33 contratos homologados** ni 33×10 años de bid/ask continuo.

### 4.2 Cruce cuantitativo cobertura vs todas las operaciones W3
El nuevo arquitecto no debe preguntar de nuevo si “las pocas ventanas 2020/2023 bastan”: **ya está demostrado que NO.**
Prereg docs/research/QORE_ALPHA2_G2_W3_EVENT_VS_QUOTE_SOURCE_WINDOW_COVERAGE_PREREG_2026-10-12.md. Código src/qore/research/alpha2_g2_w3_quote_window_coverage.py. [GHA #38297579449](https://github.com/mezas3238-hue/qore-core/actions/runs/38297579449) SUCCESS 9/9 y artifact #11767809883:
- Denominador exacto: 24.487 señales originales W3 / 24.399 pares gross, 33 mercados, incluidas las censuradas.
- **Solo 2 entradas** previstas dentro de alguna ventana SOURCE29 histórica.
- **0 trayectorias completas** que tengan entrada y salida de estrategia Y control en la misma ventana de 10 min.
- Se leyeron timestamps SOURCE, no outcomes PnL ni precios históricos reservados 2026. Cero trayectorias económicamente calificadas.
**Consecuencia:** la mayoría de las operaciones no tiene BID/ASK auténtico en entrada/salida; está PROHIBIDO fabricar PF/Sharpe/Sortino/DD net con spread estimado o aplicar solo a las dos coincidencias.

### 4.3 Semántica Proto/tick y causalidad crítica
- Serie histórica native cTrader ProtoOAGetTickData: primer TIMESTAMP y PRECIO absolutos, valores siguientes como deltas de **tiempo y precio CON SIGNO**; el decoder antiguo del PR #803 era defectuoso. Correcciones de fuente G1 PR #844 en adelante y pruebas SHA enteros/decimales. No revertir al decoder antiguo ni confundir M1 con ticks bid/ask.
- Evento spot prospective puede traer solo un lado. Cada BID y ASK necesita reloj propio first-received, máximo frescura 5s en estos ensayos; reloj de EVENTO DEL PROVEEDOR descargado a posteriori **NO demuestra** dato disponible en decisión. El timestamp after-dequeue del collector es testigo conservador de primera observación por ese runner pero tampoco reloj del matching engine ni fill.
- Los spread cero requieren cuarentena, no ejecución gratuita (Issue #856). Session breaks, rangos sin ticks, crossed/spikes, gap, quotes obsoletas y cuentas no equivalentes son estados SOURCE bloqueantes.

---

## 5. G2 — CAPTURA PROSPECTIVA REAL IC MARKETS DEMO, SIN ÓRDENES

### 5.1 NZDUSD una fuente aislada de 45 segundos
Prereg antes de ejecución commit 14f7b54ed5e1ffd1c179faf500fa8646837a6da9. Collector src/qore/research/alpha2_g2_nzdusd_forward_spot_receipt.py; tests y workflow .github/workflows/qore-alpha2-g2-forward-nzdusd-demo-receipts.yml.
- [Original #38296610948](https://github.com/mezas3238-hue/qore-core/actions/runs/38296610948) SUCCESS, source HEAD ca32ad2311c5c6b4a9312073ca0b4c7b53109a75, original artifact #11767978684, **11 eventos recibidos**, cero órdenes y token-refresh.
- [Auditor independiente #38297614422](https://github.com/mezas3238-hue/qore-core/actions/runs/38297614422) SUCCESS 7/7, artifact #11768424790; verificó SHA del evento/manifest dos veces, clock monotonicidad y calidad por lado. **4 updates BID y 8 ASK** (un mensaje puede actualizar ambos), 4 source spreads positivos, 1 zero cuarentena, 6 stale/missing, 0 crossed. No PnL/fill.

### 5.2 29 instrumentos exactos simultáneos con first-seen, un solo DEMO
Prereg fuente commit 34a2c20d285d86a16c95bac217a0dc9225a6d799; collector src/qore/research/alpha2_g2_29_exact_demo_forward_multispot.py; 29 ID validados contra catálogo autenticado, no aliases. **Excluidos por prereg:** NAS100, NZDUSD, SP500, XAGUSD. Estado independiente distinto de NZDUSD; NUNCA llamarlo “30 simultáneos”.
- [GHA fuente #38298399112](https://github.com/mezas3238-hue/qore-core/actions/runs/38298399112) SUCCESS dos jobs, HEAD 33068c720fedb3d358a2f73e7323508abd8365f6, artifact original #11769446263. **1.033 eventos** en ventana fija 60s, **29/29 símbolos recibieron ambos lados**. One ProtoOASubscribeSpotsReq repeated exact 29 IDs, sin orden/refresh/secret persistido.
- Prereg auditor 29 independiente commit 09c01e6d4c3b05844b7d1638d760efb4bab9fcf4. Código src/qore/research/alpha2_g2_29_forward_original_independent_qa.py. [GHA QA #38298920851](https://github.com/mezas3238-hue/qore-core/actions/runs/38298920851) SUCCESS 7/7, HEAD a80702b40e2242f7da05d392137cc76ce7124b8b, signed artifact #11770276257. Comprobó SHA ledger y global+local sequence original de todos los 1.033: **890 ASK>BID positivo**, **36 ASK=BID cuarentena**, **107 lado missing/stale**, 0 crossed.
- Esto es capacidad de ingestión de datos **60s, after dequeue**, no SLA 24/7 ni cobertura de 10 años, costes, fills, profit ni certificado.

Reportes: docs/research/QORE_ALPHA2_G2_FORWARD_RECEIPT_11_EVENTS_AND_W3_SOURCE_COVERAGE_24487_VERDICT_2026-10-12.md y docs/research/QORE_ALPHA2_G2_29_PROSPECTIVE_BIDASK_1033_INDEPENDENT_QA_VERDICT_2026-10-12.md.

### 5.3 Otros ensayos de fuente, negativo válido
EURCHF DEMO one-minute source pilot [GHA #38287610751](https://github.com/mezas3238-hue/qore-core/actions/runs/38287610751) SOURCE_BLOCKED después de test sintético; no fingir que accedió a ticks. Raw historial/recibo original tiene límites de permisos y sesiones. Separar “pruebas código PASS” de “broker fuente FAIL”.

---

## 6. G2 — MOTOR ECONÓMICO HIPOTÉTICO, PERO SIN NET VALIDADO

Prereg económico commit fff976831ea68502f85322d76e73ebea96d19e2f, docs/research/QORE_ALPHA2_G2_CAUSAL_ECONOMICS_STRESS_ENGINE_PREREG_2026-10-12.md. Código src/qore/research/alpha2_g2_bidask_causal_contract.py y src/qore/research/alpha2_g2_causal_economic_stress.py; tests correspondientes. [GHA #38293812287](https://github.com/mezas3238-hue/qore-core/actions/runs/38293812287) SUCCESS **25/25 tests sintéticos**.

Implementado y probado:
1. Largo: entrada ASK / salida BID. Corto: entrada BID / salida ASK. Fuentes por broker, símbolo y cuenta exacta; as-of de quote conocido en decisión, age <=5s. Cero/cruzado FAIL, no fill gratis.
2. Testigo contrato PIT original con proveedor ID, SHA256, lot/unidades, payout en moneda quote por 1 unidad de precio, fechas de conocimiento y vigencia, payoff lineal verificado, moneda cuenta/quote, conversión as-of. Alias no homologado FAIL.
3. Costes como **6 campos Decimal EXPLÍCITOS**: comisión entrada, comisión salida, financiación, swap, slippage adverso entrada y salida. Float, bool, NaN, missing, valor negativo o timestamps futuros FAIL. Cero solo si la fuente original lo documenta explícitamente, no por default.
4. Calculadora devuelve HYPOTHETICAL_QUOTE_COST_STRESS_NOT_NET_CERTIFICATION, broker_actual_net_attested=false, utc001_certified=false. El resultado sintético puede probar aritmética, NO precios/fees/fills reales. No aplicar slippage estimado dos veces si un fill original ya lo refleja.

Pendiente P0: cantidades reales broker, condiciones por familia/cuenta/año y FX/payout point conversion, comisión contractual swaps, cobertura BIDASK *completa* de cada trayectoria, calendario macro first-published PIT, slippage/latencia y rechazos. El simple hecho de medir spread prospective no resuelve comisiones históricas, ni fuente LEGAL de quotes de toda la década. Issue #852.

---

## 7. P0 — CUATRO PUESTOS CONTRACTUALES Y BLOQUEO REAL DE API (NO OCULTAR FALLAS)

**Canónicos G0:** NAS100, SP500, NZDUSD, XAGUSD. Posibles nombres de proveedor NAS100↔USTEC, SP500↔US500. No tratar parecido de gráficos/nombres como identidad contractual.

Prereg primer request antes de resultados commit 4f2372d4cb96fe40a51c642d27d9ff56131bb190. Lectura src/qore/research/alpha2_g2_four_broker_contract_primitives.py, tests test_alpha2_g2_four_broker_contract_primitives.py, workflow qore-alpha2-g2-four-contract-source.yml. Versiones V2 y V3 **prerregistradas como modificaciones de protocolo** commits e2bc4db9339a07c9d94b303a27661e7a4b5bcbc0 y 26359559301edff5024e8b1cae8d3f514550fb3b. **11/11 pruebas sintéticas en cada versión**, PERO fuente nueva NUNCA pasó:
- [#38300633695](https://github.com/mezas3238-hue/qore-core/actions/runs/38300633695) V1: falla fuente en segundo SymbolsList; [#38300858851](https://github.com/mezas3238-hue/qore-core/actions/runs/38300858851) diagnóstico distinguió P0_CATALOG_RESPONSE_FAILURE.
- [#38301197700](https://github.com/mezas3238-hue/qore-core/actions/runs/38301197700) V2: reutilizar catálogo autenticado eliminó el paso duplicado; consulta SymbolById multi-ID devolvió P0_FULL_SYMBOL_RESPONSE_FAILURE.
- [#38301475947](https://github.com/mezas3238-hue/qore-core/actions/runs/38301475947) V3 prereg máximo seis solicitudes individuales, SIN retries: P0_SYMBOLBYID_SINGLE_REQUEST_FAILED ya en primera. **STOP definitivo de esta ronda.** Causa permisos/rate limit/transporte/endpoint NO demostrada; no más sondeos adaptativos hasta evidencia de proveedor. Manifiestos SOURCE_BLOCKED archivados, cero órdenes y cero datos ficticios.

**Evidencia OFFLINE verdaderamente admitida de otro arquitecto QORE Native:** original [PR #850](https://github.com/mezas3238-hue/qore-core/pull/850) y [source run #38284304699](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699), HEAD 716996e0f893af0aeb2b990ac11d644cf62a5c5f, source artifact #11762018327 y ZIP SHA256 7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e. Nuevo auditor independiente sin conexión broker [Actions #38301861733](https://github.com/mezas3238-hue/qore-core/actions/runs/38301861733) SUCCESS 5/5 + SHA contrastado en GitHub API, audit artifact #11771250981. **USTEC DEMO provider symbolId 10014, digits2, pipPosition1, lotSize raw100, minVolume raw10, stepVolume raw10**. Esto documenta ficha USTEC DEMO anterior; NO equivale a contrato NAS100 G0 histórico ni US$100/punto, cuenta Atlas12 o comisiones.

Matriz a preservar:

| Original canónico | Fuentes externas que SÍ existen | Estado contrato para NET |
|---|---|---|
| NAS100 | USTEC candidato source cat #850, histórico ticks candidato PR #853/QA #854 | ALIAS_CONTRACT_BLOCKED, equivalencia original UNKNOWN |
| SP500 | US500 source histórico PR #847/QA #848 | ALIAS_CONTRACT_BLOCKED, equivalencia original UNKNOWN |
| NZDUSD | source G1 #844/#846, Alpha2 prospective #38296610948/QA | ORIGINAL_ACCOUNT_FEES_POINT_VALUE_BLOCKED |
| XAGUSD | source histórico G1 #847/#848 | ORIGINAL_ACCOUNT_FEES_POINT_VALUE_BLOCKED |

Aunque QORE Native tenga 33 slots con source BIDASK en instantes cortos, **0 de esos 4 contratos están homologados económicamente** entre las cohortes. Reunir original broker account/source, moneda depósito, fechas vigentes, lotSize/step, pip value, cotización/divisa, sessions/DST, swap, comisiones efectivas 2016–2024, puntos de equivalencia exacta y SHA. Issue #868.

Reporte forense: docs/research/QORE_ALPHA2_G2_P0_FOUR_BROKER_CONTRACT_METADATA_AND_PROTOCOL_BLOCKERS_VERDICT_2026-10-12.md.

---
