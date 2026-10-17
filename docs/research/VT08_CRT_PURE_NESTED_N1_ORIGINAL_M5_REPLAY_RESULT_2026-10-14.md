# VT08 CRT PURE — N1 CRT M15 ANIDADO DENTRO DE H4: RESULTADO REAL Y DIAGNÓSTICO DE DENSIDAD

**14 OCT 2026 · Investigación, NO certificación.** Repo mezas3238-hue/qore-core · PR #626 DRAFT (sin merge).  
**Mandato:** no recuperar automáticamente los 88 casos de R2-C; investigar oportunidades CRT genuinamente diferenciadas con las enseñanzas RomeoTPT (A) y SpeculatorFL/TraderFlameseN (B), ejecutar pruebas sobre velas originales QORE y preservar CIBO y gobernanza.

## 1. Pre-registro ANTES de mirar nuevos resultados

[PREREG N1](VT08_CRT_PURE_NESTED_M15_SOURCE_PREREG_2026-10-14.md) creado en commit `9da47d579f38eb479c33c90c23f3223ccfca6d23` **antes de correr el N1**. Concepto secundarios B: CRT M15 dentro del contexto CRT H4 y variante confirmacional, pero la máquina exacta de tres barras es **QORE ENGINEERING**, NO fuente primaria Romeo certificada.

Regla fija de **censo** N1:
- Parent original **H4 C1/C2/C3 completo + C2 one-sided Turtle Soup**; los mismos 287/265 parents R2-C. Se conserva exactamente timezone NY e interpretación de 2 triples H4 por día, que **son hipótesis ingeniería**, no censo universal CRT.
- **Micro-C1** es su propio rango M15 H/L; **Micro-C2** M15 siguiente barre uno y solo uno de sus lados, cierra de nuevo dentro o sobre borde de C1; **Micro-C3** M15 siguiente cierra del lado correspondiente del midpoint de micro-C1, una vez transcurrida la vela completa. C1-C2-C3 son contiguas y enteras dentro de la misma H4-C3.
- Identidad nueva estable `market:micro_C1_opened_at:micro_C2_opened_at`; sin vieja referencia OLD pivot strength1 de R2-C, y sin convertir eventos del parent agotado en órdenes.
- Decisión válida solo al cierre del micro-C3; si no hay una siguiente vela M15 dentro de la ventana, se marca `NO_NEXT_BAR_IN_PARENT`. **No se crea ninguna entrada**, SL, TP, PnL, R, sizing, lotaje, volumen, broker fill.
- Doble clasificación descriptiva `SAME_H4_DIRECTION/OPPOSITE`, old R2-C traded/rejected, parent de los 88, histórico del objetivo original H4 tocado/no tocado antes de nueva decisión, período 1/2. **Nada se optimizó por PnL**.
- Estudio secundario de **intersecciones estrictas** añadido después de conocer los conteos G0 como lectura de riesgo de doble contabilización (no parámetro de modelo ni filtro de trading).

## 2. Fuente original: intacta, millones de velas en GitHub Actions

- [QORE Native Atlas 12 originales M5, Actions #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458): AUDUSD artifact `10475697610`, USDJPY `10475389415`. Ledger M5, manifiesto, SHA anual 2024–2026 verificados por lector `vt08_crt_pure_original_atlas_reader.py`.
- **AUDUSD 148.171 + USDJPY 148.201 = 296.372 M5** en ventana recortada 2024-09-20→2026-09-16. No completan 2026-09-17→21 pedido del ensayo antiguo. Mismo histórico previamente consumido: no OOS virgen ni broker BID/ASK comparable.
- No se utilizó Dukascopy, GetData Finance ni servicio broker, MT5 o VPS.

## 3. Ejecución real y SHA

[**GitHub Actions #38602113794**](https://github.com/mezas3238-hue/qore-core/actions/runs/38602113794): **3/3 jobs SUCCESS**; **Ruff/Mypy PASS y 34/34 pytest PASS**. Código ejecutado HEAD `5c6fab51191d2af3b5b80d8e5dcb9f8a2be11c95`; N1 pre-registrado antes de la primera corrida [#38601758533](https://github.com/mezas3238-hue/qore-core/actions/runs/38601758533), 3/3 SUCCESS.

- [AUDUSD artifacts #11914310446](https://github.com/mezas3238-hue/qore-core/actions/runs/38602113794/artifacts/11914310446), ZIP SHA256 `594ec7ea0867a674edc7831b746045037e2136681e2dd6781f0675a79d8efb8d`.
- [USDJPY artifacts #11914325385](https://github.com/mezas3238-hue/qore-core/actions/runs/38602113794/artifacts/11914325385), ZIP SHA256 `3ce310a24d473a28ba72e67fe7a2f99a06d21434774ca4c1f138ec1dc254b261`.
- Contienen `nested-m15-census.json`, `nested-m15-ledger.jsonl` y `nested-m15-stdout.log`, además del censo/forensics viejo e índices `SHA256SUMS.txt`. **Cada uno de los 939 patrones** tiene ID propio, timestamps de C1/C2/C3, su OHLC de referencia/confirmación, H4 source, clasificación y flag `is_trade=false`.

## 4. Hallazgo central: mucha densidad estructural, pocas hipótesis limpias al cruzar contexto

| Censo sobre ventana ~2 años | AUDUSD | USDJPY | SUMA |
|---|---:|---:|---:|
| Parents H4 C2 TS preexistentes | 287 | 265 | **552** |
| Triples M15 internos observados (no necesariamente CRT) | 4.018 | 3.710 | **7.728** |
| N1 micro-CRT con 3 velas confirmadas | 521 | 418 | **939** |
| Parents H4 únicos con al menos un N1 | 257 | 222 | **479** |
| Parents H4 con múltiples N1 | 165 | 131 | **296** |
| N1 dirección concordante con H4 | 248 | 220 | **468** |
| N1 dirección contraria a H4 | 273 | 198 | **471** |
| N1 con siguiente M15 disponible dentro de H4 | 488 | 389 | **877** |
| N1 en parents de los 88 antiguos rechazados | 87 | 68 | **155** |
| Parents de los 88 con >=1 N1 | 40 | 35 | **75** |
| N1 donde target 50% de H4-C1 ya tocado al decidir | 363 | 283 | **646** |

**Importante:** 939 es N de observaciones M15, NO trades (varias por mismo H4); 479 parents únicos NO equivalen a contextos independientes porque los tres M15 pueden superponerse e incluso contradecir la tesis H4. El 155 en parents de 88 NO es «recuperación» autorizada: tienen **nuevo micro-C1** pero no regla de independencia doctrinal aprobada.

### Embudo simultáneo *observacional*, sin convertir filtros en autorización

| Intersección de condiciones PREREG + flags descriptivos | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Todos N1 | 521 | 418 | **939** |
| Alineados al padre H4 **y** siguiente M15 dentro de C3 | 230 | 209 | **439** |
| Además, midpoint H4-C1 anterior NO tocado al cierre del micro-C3 | 72 | 65 | **137** |
| Además, sin operación R2-C simulada en el mismo padre H4 | **34** | **30** | **64** |
| **Parents H4 únicos** que albergan esa última intersección | **30** | **27** | **57** |

**La cifra honesta es 57 contexts que ameritan auditoría adicional bajo esta lectura cautelosa, no 939 trades adicionales.** Incluso los 57 **NO** son entradas, oportunidades independientes comprobadas, source-adjudicated Model #1 ni rentabilidad neta. El conteo 34/30 son micro event-IDs, distinto de 30/27 parent H4.

### Distribución por períodos (sin seleccionar mejores días)

- AUDUSD N1: **278 período 1**, **243 período 2**.
- USDJPY N1: **218 período 1**, **200 período 2**.
- La suma 496 vs 443 indica persistencia de apariciones de patrones, NO validación económica.
- El parent R2-C previo sigue 69 AUDUSD / 64 USDJPY; NO se recalculó R ni PnL del N1.

## 5. Diferencias documentales entre tres fuentes y decisión metodológica

- **RomeoTPT (A)** [source closure Model #1](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md): relación H4 CRT→M15 Model #1, pero **no** certifica que tres M15 de la nueva detección N1 constituyan exactamente su modelo. Su testigo old CRTH/CRTL, fuente candle y body-close pertenece a *otra* familia. No afirmar «939 Model #1 válidos».
- **SpeculatorFL (B)** [hilo](https://threadreaderapp.com/thread/1784493604473618604.html): admite la noción de CRT anidado/micro dentro de macro; describe CT y modalidades. N1 toma esta inspiración conceptual, NO hereda autoridad de Romeo.
- **TraderFlameseN (B)** [hilo](https://threadreaderapp.com/thread/1790141530461622525.html): coincide en macro/micro/CRT y está vinculado a SpeculatorFL. No es un experimento independiente ni una validación estadística duplicada.
- **Resolución QORE:** mantener N1 como familia prospectiva `QORE_MICRO_CRT_CONFIRMATIONAL_CANDIDATE`, sin reemplazar ni mezclar Model #1 Romeo R2-C, sin variar ventanas por rendimiento ni cambiar la norma FIRST_SOURCE_ONLY del experimento viejo. Su C1 propio evita el error de reutilizar como destino el midpoint del C1 antiguo, pero no prueba independencia causal ni mecanismo de beneficio.

## 6. Gates y continuidad del próximo arquitecto

**Completado:** prereg antes de data outcomes; detector N1 + tests + GitHub workflow; 296.372 M5 SHA auditadas; conteo completo y casos ledger; comparación por contexto y dos períodos; investigación sin ninguna orden; gestión de BTCUSD freeze.

**Aún abierto P0:**
1. Revisar **casos individuales** del ledger N1, con cartas de vela H4/M15, contra primarias originales Romeo y secundarias SpeculatorFL/FlameseN, con criterio `new_micro_reference_independent?`, contradicción del parent, model-family y fecha exacta.
2. Reglas si N1 confirma contra H4 vs a favor (hoy 471 contrarios y 468 alineados): no descartar por PF; justificar por metodología y macro contexto.
3. Fuente original Romeo old-level-ownership y elección entre pivots sigue ambigua. No equiparar micro-C1 independiente con nivel «old CRTH» sin testigo.
4. Definir experimento N2 *no solapado* con un solo evento micro candidato por parent **antes** de examinar PnL, respetar overlap y reglas de vigencia; requiere gates metodológicos para pasar de contador a replay económico.
5. Certificación económica requiere muestra realmente no consumida, histórico costes/BID-ASK, capacidad de financiar costes, DD, PF neto; el presente N1 **NO ha medido rentabilidad**.

**G-M1/G-M3 PARTIAL**, **GLOBAL CERTIFIED FALSE**. BTCUSD congelado; Trader sin sizing; CIBO soberano. NO MERGE, NO LIVE/DEMO trading, NO VPS, NO FundedNext LIVE, NO producción. Preservar GH original data artifacts antes de vencer (Issue #837).
