# QORE VT08 CRT PURE — N2: 57 contextos H4, 64 micro-CRT M15, auditoría forense completa

**Fecha:** 2026-10-14 · **PR #626 DRAFT; sin merge.**  
**Resultado:** expediente forense cerrado técnicamente; **adjudicación metodológica y económica abierta**. N2 no crea entradas, salidas, R ni lotes.

## 1. Pre-registro, fuente y ejecución

[PRE-REG N2, antes de la primera ejecución](VT08_CRT_PURE_N2_57_CASEBOOK_PRE_REGISTRATION_2026-10-14.md), commit `becd9409eed44b6b2f5f8533dfc54062e69eed86`. Congela el universo de **57 H4 / 64 N1** heredado de N1: alineación H4, siguiente M15 cronológica, target del H4-C1 no tocado al confirmar, ningún trade viejo R2-C en ese parent. **Esta intersección fue exploratoria posterior a N1, NO un setup independiente pre-registrado desde N1.**

[**GitHub Actions N2 #38603974795**](https://github.com/mezas3238-hue/qore-core/actions/runs/38603974795): HEAD `17589a22ed6899555a9358c28786d2adb2b950a6` · 3/3 jobs SUCCESS (quality + AUDUSD + USDJPY) · Ruff PASS · Mypy PASS · **45/45 pruebas**. La primera ejecución falló solo una prueba sintética mal construida (cierre alcista por debajo del midpoint); se corrigió el fixture ANTES del replay histórico aceptado. No se alteró el detector N1.

**Datos**: las mismas 296.372 M5 originales de QORE/CIBO Atlas, por [GitHub Actions fuente #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), con SHA por partición 2024–2026; no Dukascopy/cTrader actual/otros proveedores. Ventana inspeccionada hasta 2026-09-16, no OOS nuevo; sin BID/ASK neto/fill ni costes.

**Artefactos íntegros, con SHA ZIP de GitHub**:
- [AUDUSD artifact #11914039232](https://github.com/mezas3238-hue/qore-core/actions/runs/38603974795/artifacts/11914039232) · `sha256:bc7b8ccc5ae424b048f7eef3d1e52267de7c9f3d63b6eca2476d69ed05c983c1`.
- [USDJPY artifact #11915290989](https://github.com/mezas3238-hue/qore-core/actions/runs/38603974795/artifacts/11915290989) · `sha256:de508a54e0b75fc5a013775dc8bb2b1340858b460932134e7af4fceb92082201`.

Cada ZIP contiene `n2-57-casebook-summary.json`, `n2-57-casebook-full.jsonl`, `n2-57-casebook-stdout.log` y `SHA256SUMS.txt`, más N1 y auditorías anteriores. El JSONL registra **cada H4**, sus 16 OHLC M15 completos (solo para revisión posterior, no input de decisiones), los micro-N1, candidatos de la intersección, timestamps, banderas de target/contexto y solapamiento. No modificarlo retrospectivamente después de conocer PnL.

## 2. Reconciliación de los 57 casos reales

| Medida | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| **H4 contextos únicos en el expediente** | **30** | **27** | **57** |
| Micro eventos N1 de intersección en esos H4 | **34** | **30** | **64** |
| H4 con un único micro evento seleccionado | 26 | 24 | **50** |
| H4 con dos eventos seleccionados temporalmente disjuntos | 4 | 3 | **7** |
| H4 con eventos seleccionados temporalmente solapados | 0 | 0 | **0** |
| Todos los N1 en estos H4, incluidas direcciones contrarias | 69 | 61 | **130** |
| H4 que también contienen algún N1 contrario al H4 | 20 | 17 | **37** |
| H4 donde un candidato seleccionado tenía previamente un N1 contrario | 14 | 10 | **24** |
| H4 de los 88 rechazados antiguos presentes en este subconjunto | 12 | 13 | **25** |

**Interpretación:** los 7 duplicados *seleccionados* no son solapamiento de velas, pero 64 sigue siendo **64 candidatos dentro de 57 ventanas** y los **130 micro-eventos observados en sus parents tienen posible conflicto de familia/dirección**. Un `earliest first` únicamente sirve de ORDEN DE REVISION, no orden ejecutable. En 24/57 H4 ya había aparecido otra señal N1 de dirección contraria antes de la seleccionada: ninguna regla original ha resuelto qué tesis debe prevalecer.

## 3. El punto ciego que N2 descubrió: destino del micro-C1

N1 llama confirmación al cierre del micro-C3 **por encima del punto medio propio** (bullish) o **por debajo** (bearish). Esto es una definición de ingeniería, no el Model #1 de Romeo. Por definición:

| Observación conocida antes o al abrir la siguiente M15 | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| **El midpoint del propio micro-C1 YA fue superado por el cierre confirmatorio** | **34** | **30** | **64** |
| El extremo opuesto del micro-C1 YA fue tocado con mecha del micro-C3 | 20 | 22 | **42** |
| El extremo opuesto YA había sido rebasado por cierre de micro-C3 | 3 | 18 | **21** |
| En el open siguiente el extremo opuesto del micro-C1 NO queda por delante | 3 | 16 | **19** |
| En el open siguiente el extremo opuesto del micro-C1 aún queda por delante | 31 | 14 | **45** |

**Crítico:** un micro-midpoint ya superado no puede reciclarse como objetivo futuro en la misma dirección. Tener el extremo opuesto «por delante» en el siguiente open no significa que siga intacto ni garantiza beneficio, ya que en 42 eventos el extremo opuesto había sido **tocado con mecha** durante C3. Estas son banderas NO excluyentes; NO restar totales para simular una densidad válida. No usar DOL inventado ni modificar la salida R2-C a posteriori.

## 4. Contradicciones y ausencia de independencia doctrinal

| Contexto observable, NO una regla de veto Romeo | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Micro-C2 volvió a barrer el extremo del **C1 H4 original** correspondiente a la dirección | 31 | 20 | **51** |
| El micro-C3 cerró más allá del extremo C1 H4 contrario a la tesis | 26 | 14 | **40** |
| Micro-C1 estaba entero dentro del rango de C1 H4 | 6 | 10 | **16** |
| Candidato elegido tenía algún N1 anterior en ese mismo H4, cualquiera su dirección | 16 | 12 | **28** |
| Candidato elegido tenía un N1 anterior de dirección contraria | 14 | 11 | **25** |

**51/64** vuelven a interactuar con el extremo barrido del rango H4: no se ha demostrado que sean oportunidades económicamente autónomas y distintas del mismo movimiento. **40/64** presentan cierre respecto del antiguo H4 contrario a la tesis: es una **alerta de continuidad H4**, no un veto demostrado en las fuentes. Tampoco basta el timestamp único de micro-C1 para declarar dos CRT independientes.

Que no haya solapamiento entre los **64 seleccionados** no prueba ausencia de solapamiento/conflicto con los **otros 66 N1** presentes en esas mismas H4. El casebook incluye los 130 para una auditoría más amplia. No confundir 64 eventos con 57 trades.

## 5. Autoridad de fuente, certificación y próxima puerta

- [RomeoTPT Model #1 source closure](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md): marco CRT primario H4→M15, old CRTH/CRTL, source candle + body-close; el **N1/N2 de 3 M15 NO está demostrado equivalente**.
- [SpeculatorFL hilo CRT](https://threadreaderapp.com/thread/1784493604473618604.html) y [TraderFlameseN hilo](https://threadreaderapp.com/thread/1790141530461622525.html) sostienen el concepto general micro/macro/nested; son secundarios dependientes. No determinan cuáles de estos 57 son setups originales auténticos ni dan prioridad causal entre opuestos.
- Falta **SOURCE OWNERSHIP** para micro-C1 y far boundary/DOL, validez de la confirmación midpoint vs Model #1 de Romeo, expiración y no-overlap con otras familias, prioridad tras un N1 anterior contrario.
- Antes del próximo replay económico N3, establecer en metodología, **sin ver retornos de N2**, el tipo de destino que de verdad puede quedar por delante después de la confirmación, su origen causal, y qué evidencia permite una operación. Si la doctrina no lo sustenta, **REJECT / RESEARCH ONLY** sin añadir filtros para fabricar PF.
- La palabra «independiente» en N1 se usa para ID de micro-rango diferente, NO como prueba de causalidad/edge. **No hay incremento de density de trades certificados ni beneficios comprobados.**

**Dictamen N2:** `FORENSIC_RECONCILED_57_H4_64_MICRO; OVERLAP_SELECTED_ZERO; PARENT_DIRECTION_CONFLICT_PRESENT; MICRO_MIDPOINT_SPENT_AT_CONFIRMATION; DOCTRINE_GATE_OPEN; NOT_CERTIFIED`.

**Gobernanza:** NO MERGE #626, NO LIVE/DEMO trading, NO VPS, NO FundedNext LIVE, NO sizing/lotaje/capital/volumen en el trader; CIBO/QORE Risk único autorizado. BTCUSD congelado. [Data Vault issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) recuerda que los artifacts expiran y se requiere preservación; el algoritmo y los IDs de fuente permitirán reproducir si se conserva el data lake.
