# QORE VT08 CRT PURE — N3/N3B: reloj de confirmación M15-C2 y observación M5-C3, fuente y resultados

**Corte 14-OCT-2026** · **PR #626 DRAFT, sin merge**. Investigación no económica, cero operaciones nuevas. **Estado:** resultados reproducidos sobre velas originales, equivalencia metodológica con Romeo/SpeculatorFL NO CERTIFICADA.

## PRE-REG y procedencia

1. **N3** [Pre-reg C2-close→M5](VT08_CRT_PURE_N3_C2_CLOSE_M5_CAUSAL_BRIDGE_PREREG_2026-10-14.md), creado ANTES de observar conteos, commit `3b3dcd814d85adb1753b1fc09234470b8c748370`.
2. **N3B** [Pre-reg nuevo M5 vs persistencia de C2](VT08_CRT_PURE_N3B_NEW_INFORMATION_M5_PREREG_2026-10-14.md), commit `bc6f9ed688047cfc316673c8d45bb56ad28e6e67`, creado **DESPUÉS** de conocer los primeros agregados N3 pero antes de leer conteos nuevos N3B. Tratar N3B como investigación EXPLORATORIA DE SEGUNDA RONDA, no como hipótesis independiente virgen ni resultado OOS nuevo.
3. Fuente: **296.372 velas M5 originales** AUDUSD 148.171 / USDJPY 148.201, [GitHub Actions Atlas #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), IDs original `10475697610` y `10475389415` respectivamente; `MANIFEST_SHA256SUMS.txt`, RAW ledger años 2024–26, productor `ab782b8e9f890f86a2b6500070f0556b4b685e3d`. Hasta 2026-09-16 inclusive; septiembre 17–20 no presentes en replay aunque solicitados en el replay R2C viejo. Sin APIs externas, sin proveedor nuevo, sin broker auth ni orden.
4. [**GitHub Actions N3/N3B #38608270651**](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651): HEAD probado `3aaeef4fcbd21ca74473ec274510b4657c14cd94`, **3/3 jobs SUCCESS**, Ruff PASS, Mypy PASS, **60/60 pytest PASS**. Los dos mercados conciliaron por programa el antiguo N1 original 521 AUDUSD / 418 USDJPY SIN mutar R2C.
5. Evidencia íntegra por market:
   - [AUDUSD artifact **#11917121744**](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11917121744), digest GitHub ZIP `sha256:a64d90e375278291c749b887d52eb0847b4e0e33aa3c9413fd0c2ebccc0d227c`.
   - [USDJPY artifact **#11916482628**](https://github.com/mezas3238-hue/qore-core/actions/runs/38608270651/artifacts/11916482628), ZIP `sha256:f82ffa8e5b61c6e249439065dc77dd829218bcb414ab4f0ac69958ce1135ef5d`.
   - Dentro: `n3-c2-m5-summary.json` y `n3-c2-m5-ledger.jsonl` con todos **2.634 micro-eventos** y sus 3 M5 testigo y timestamps, `SHA256SUMS.txt`, además de casos N2 y artefactos anteriores. Permite revisión causal por fecha y precio. El hash de ZIP es metadata de GitHub; hashes SHA256SUMS generados en runner para contenido.

## 1. Discrepancia doctrinal que inspiró N3

[SpeculatorFL, original 25-MAY-2024](https://threadreaderapp.com/scrolly/1794311615535518154): `Conformational CRT` espera cierre de la segunda vela para estudiar operaciones en tercera o posterior. Además, con un CRT de temporalidad superior describe formar referencia en vela inferior y refinar aún más abajo. [SpeculatorFL 28-APR](https://threadreaderapp.com/thread/1784493604473618604.html) reconoce a RomeoTPT como creador y describe CRT macro/micro. [TraderFlameseN](https://threadreaderapp.com/thread/1790141530461622525.html) comparte conceptos y no cuenta como segunda autoridad independiente.

**RomeoTPT autoridad A**: [Model #1 source closure](VT08-CRT-PURE-MODEL1-SOURCE-CLOSURE-001.md) autoriza conceptualmente un old high/low, un stab y confirmación corporal, M15 sobre H4; **NO** da permiso para llamar Model #1 al nuevo C2 detector.

- **N1 anterior**: H4 parent + M15 C1/C2/C3 + C3 cierre por midpoint -> después M15 C4. Su primer disparador de tiempo es tardío y no coincide por definición con una entrada en C3.
- **N3 QORE ingeniería**: H4 parent ORIGINAL ya admitido, par de M15 `C1 rango` y `C2 sweep estricto de UN lado y cierre de retorno al rango`; al `C2.close` ya conoce el candidato. Después OBSERVA las 3 velas M5 de M15-C3; no usa el desenlace de C3 como condición de admisión. Midpoint y extremo son instrumentos diagnósticos, no triggers ni DOL certificados.
- **N3B**: exige que nuevo primer cierre M5 en slot 1/2 al otro lado del midpoint sea información realmente NUEVA respecto de C2, y registra si el extremo lejano seguía sin tocarse a ese cierre; subgrupo solo descriptivo alineado a H4 con viejo H4 midpoint aún sin tocar en el instante de C2. Los cálculos usan únicamente el prefijo M5 **ya cerrado**, no todo el C3, para determinar estado N3B.

## 2. Resultado N3: denominador completo NO condicionado al éxito posterior

| Censo durante ~2 años, M15 C2 y 3 M5 de C3 | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Parents H4 TS completos usados | 287 | 265 | **552** |
| Pares C1/C2 con una siguiente M15 disponible, todos | 4.018 | 3.710 | **7.728** |
| **Micro C2 con barrido unilateral y retorno de cierre, sin condicionar C3** | **1.374** | **1.260** | **2.634** |
| C2 alineados con dirección H4 | 662 | 652 | **1.314** |
| C2 dirección opuesta H4 | 712 | 608 | **1.320** |
| C2 donde antiguo H4 midpoint ya tocado ANTES del cierre C2 | 919 | 849 | **1.768** |
| C2 donde su propio midpoint ya estaba superado al terminar C2 | 272 | 268 | **540** |
| M15 C3 final confirma según antiguo N1 | 521 | 418 | **939** |
| M15 C3 final NO confirma según N1 | 853 | 842 | **1.695** |

**Reconciliación exacta**: `1.374=521+853`; `1.260=418+842`; el antiguo N1 queda totalmente contabilizado como subgrupo y no se fabrica densidad por comparar poblaciones distintas.

### Momento M5 observado DESPUÉS de C2 (no una orden)

| Primera M5 dentro de C3 cuyo CLOSE cae del lado esperado de midpoint de micro-C1 | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Slot 1 (5 min desde apertura C3) | 423 | 382 | **805** |
| Slot 2 (10 min) | 167 | 137 | **304** |
| Slot 3 (15 min / micro C3 close) | 93 | 73 | **166** |
| Ninguna M5 cierra del lado esperado | 691 | 668 | **1.359** |
| **Slots 1/2 juntos (llegó antes de terminar M15-C3)** | **590** | **519** | **1.109** |

Esto no significa 1.109 cruces nuevos: puede ser persistencia de C2. En **422/2.634** contextos, el primer cierre del lado esperado y la primera mecha en extremo lejano están dentro del MISMO M5 (222 AUDUSD, 200 USDJPY): orden temporal de high/low vs close no demostrable con M5 OHLC.

## 3. N3B: excluir confirmación que ya estaba presente en C2

| Subconjunto **EXPLORATORIO** prereg N3B | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Cierre M5 nuevo en slot1/2 (C2 no había cerrado ya del lado del midpoint) | **392** | **330** | **722** |
| Esos 722 con extremo lejano tocado antes o en la MISMA vela M5 | 103 | 78 | **181** |
| Esos 722 cuyo extremo lejano NO se había tocado hasta cerrar esa M5 | **289** | **252** | **541** |
| Además, micro dirección alineada H4 y antiguo objetivo H4-C1 aún intacto al cierre C2 | **45** | **50** | **95** |
| **Padres H4 únicos** que albergan esos 95 eventos | **40** | **43** | **83** |
| Reparto de los 95 eventos en período 1 / período 2 | 28 / 17 | 29 / 21 | **57 / 38** |

**Advertencias**:
- **95 NO son trades ni densidad operable nueva**. Algunos eventos pueden coexistir con los **133 trades históricos R2-C**, y varios eventos pueden estar en el mismo parent H4. **83 es número de contextos distintos, no ganancias**.
- El condicionamiento H4-aligned/target-pristine es una decisión de diagnóstico derivada de N3, prereg solo en la segunda ronda N3B. NO usar `83` como estimador imparcial de edge, ni optimizar C2/M5. No hubo independencia económica ni OOS.
- Que micro-C1 far boundary esté sin tocar en un instante dado no demuestra que sea un **DOL original**; faltan HTF PD array, priorización de niveles, caducidad, entrada source-first, spread/costes reales, conflictos macro y riesgo/lotaje soberano.
- Midpoint de micro-C1 podría haberse tocado por mecha en C2 sin cerrar beyond: la clasificación N3B exige solo un **nuevo cierre M5** y no certifica que todo tipo de liquidez siga disponible.
- El universo sigue recortado a dos triplas H4 NY de R2-C; no prueba la densidad natural de todo CRT, ni abarcar los 33 instrumentos de QORE.

## 4. Estado de G-M1..G-M5 y próxima decisión

| Gate | Estado y razón |
|---|---|
| SHA fuente y temporalidad | PASS QORE ingeniería, 60 tests, 3/3 CI |
| C2 testigo PIT sin C3 futuro | PASS ingeniería, eventos `C2_CLOSED_PURGE_RETURN` |
| Prueba lower-TF M5 y ambigüedad OHLC | PASS instrumentación causal, casos 422 misma vela intrabar indeterminados |
| Equivalencia original Romeo Model #1 y SpeculatorFL conformational | **OPEN / NOT CERTIFIED**; source C2 exacto, H4→M15→M5 entrada sin regla definitiva |
| Ownership y estado de old high/low, HTF PD array, timing | **OPEN** |
| DOL / objetivo y orden de invalidación macro-micro | **OPEN**, no inventar midpoint como target futuro |
| Replay económico, costes BID/ASK, OOS | **NOT STARTED** para N3/N3B |
| Certificación global | **FALSE** |

**Siguiente actividad razonable:** adjudicar si la forma `C2 close returns inside C1` es realmente la confirmación doctrinal en los ejemplos, y cuál de las 3 M5 sería un gatillo source-authorized H4→M15→M5; definir por escrito nivel antiguo/PD array, DOL/cancelación y resolver superposición con R2-C. SOLO entonces prereg de modelo económico con datos y costes, sin mezclar fuentes.

**Gobernanza:** PR #626 DRAFT, NO MERGE, no demo/live orders, no VPS, no FundedNext LIVE, BTCUSD freeze, sin sizing/lotaje/volumen del trader; CIBO/QORE Risk mantiene soberanía. El almacenamiento histórico GitHub Actions tiene caducidad; atender issue #837.
