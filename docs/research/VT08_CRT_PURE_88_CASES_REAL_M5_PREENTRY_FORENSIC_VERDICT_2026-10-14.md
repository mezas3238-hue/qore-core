# VT08 CRT PURE — 88 casos reales: auditoría previa a la entrada

**Fecha:** 14-OCT-2026. **PR #626 DRAFT, sin merge.**  
**Orden Owner:** investigar los 88 CRT con fuente posterior, sin asumir que son 88 operaciones recuperables ni falsear metodología CRT.

## Evidencia original, GitHub Actions

- [Run #38578534918](https://github.com/mezas3238-hue/qore-core/actions/runs/38578534918): 3/3 jobs SUCCESS (quality, AUDUSD, USDJPY). HEAD ejecutado: f6c85e1e410fdbd5bdf109de472e30036c8a7696. Ruff PASS, Mypy PASS, 25/25 pytest PASS.
- Fuente: históricos originales QORE/CIBO Atlas, [run 35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), particiones RAW_M5_LEDGER 2024/2025/2026 y SHA anual verificadas, sin proveedores ni autenticación externa.
- Se procesaron 148.171 AUDUSD + 148.201 USDJPY = **296.372 velas M5**, fecha máxima 2026-09-16. No equivalen a OOS virgen; falta el tramo originalmente solicitado 17–21 SEP 2026.
- [Artifact AUDUSD #11901687299](https://github.com/mezas3238-hue/qore-core/actions/runs/38578534918/artifacts/11901687299), SHA ZIP 664242f68fe2e74c445c5341277c519c7e238b6e04f390c5a96ea52eb57819b9.
- [Artifact USDJPY #11902117199](https://github.com/mezas3238-hue/qore-core/actions/runs/38578534918/artifacts/11902117199), SHA ZIP 01e6ae2d78e8932d60e166ccd6f8778b9fb5fa83593daca7356b00ec41c2a12a.
- Cada artifact aporta **later-source-forensics.json** y **later-source-forensics-cases.jsonl**: **los 47+41 casos individualizados**, con C1/C2, primera fuente, old pivots e IDs, fuentes posteriores, confirmación, instante potencial de entrada y flags de mercado conocidos antes de ese instante; SHA256SUMS.txt. Estos registros son el expediente revisable uno a uno, NO operaciones.

## 1. Dictamen probado: 88 padres, 120 posibles fuentes, 0 sin advertencias

La anterior auditoría H4/M15 identificó 47 CRT H4 AUDUSD y 41 USDJPY descartados por la política de elegir solamente la primera fuente. Sus fuentes M15 posteriores suman **67 AUDUSD + 53 USDJPY = 120**, porque un parent puede tener múltiples candidatos.

Se reevaluaron, usando solamente M15 cerrados ANTES de una eventual entrada, cinco características: reutilización del antiguo nivel (ID/precio), cierre fuera del lado barrido de C1, toque previo del objetivo del C1, y nuevo contacto del extremo de la primera fuente.

| Categoría prioritaria, mutuamente exclusiva por fuente M15 posterior | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Cierre M15 más allá del lado barrido de C1 ya observado | 61 | 50 | **111** |
| Sin tal cierre, pero objetivo 50% de C1 tocado previamente | 6 | 3 | **9** |
| Misma referencia (ID/precio), como categoría prioritaria | 0 | 0 | **0** |
| Sin advertencia de esas clases | 0 | 0 | **0** |
| **Total candidatas técnicas — no trades** | **67** | **53** | **120** |

**Alertas simultáneas:** en **62/120** el midpoint C1 había sido tocado antes (37 AUDUSD, 25 USDJPY), incluyendo casos clasificados arriba por cierre fuera de C1; en **119/120** hubo retouch posterior del extremo de la primera vela fuente (66 AUDUSD, 53 USDJPY). Ese extremo es testigo contrafáctico: la primera señal nunca fue ejecutada, así que NO afirmar stop-loss real.

Las categorías se eligen por prioridad para no contar una misma fuente dos veces; por eso **111+9=120**. Ninguna clase indica aprobación del autor.

**Corrección obligatoria del lenguaje:** los 221 casos de elegibilidad geométrica previa (133 trades control + 88 parents con alguna fuente posterior) NO representan 221 trades, NO están certificados y NO prueban un aumento operativo de densidad. Los 88 requieren nueva tesis documentada; abrirlos bajo la vieja hipótesis sería rearmar sin respaldo.

## 2. Interpretación metodológica con tres fuentes

- **RomeoTPT**, fuente A: [publicación sobre old CRTH](https://t.me/s/officialRomeotpt/6615). No hay en el registro primario estudiado una autorización verificable para transformar cualquier M15 pivot strength=1 en old CRTH, rearmar después de la primera señal fallida, o un criterio universal de invalidación del C1 por cualquier cierre exterior. Las observaciones C1-outside son banderas **QORE ingeniería**, NO un veto atribuido a Romeo.
- **SpeculatorFL**, fuente secundaria B: [CRT protocolo original](https://threadreaderapp.com/thread/1784493604473618604.html) incluye confluencia macro/micro, CRT anidados, inside bars, TSQ, OTE, CSD, KOD, continuation. [Advanced vs confirmational](https://threadreaderapp.com/scrolly/1794311615535518154) son familias distintas: el conformational espera tercera vela, advanced puede intervenir en segunda o tercera. No mezclarlas en R2-C por densidad.
- **TraderFlameseN**, fuente secundaria B: [hilo CRT mayo 2024](https://threadreaderapp.com/thread/1790141530461622525.html) coincide extensamente con SpeculatorFL y reconoce colaboración. No es una validación independiente. Ambos describen un universo CRT más amplio, pero NO autorizan explícitamente rescatar los 88 usando la misma tesis caducada.

**Resultado conceptual:** todos los 120 candidatos tienen alguna advertencia antes de la eventual entrada respecto del antiguo C1 del control. **Eso NO demuestra que sean 120 fallos de CRT**, porque un CRT nuevo y autónomo podría formarse dentro del mismo segmento. La hipótesis de un nuevo CRT debe contar con referencia, contexto, dirección y objetivo nuevos, sin seleccionar retrospectivamente casos de buen beneficio.

## 3. Estado G-M1..G-M5 y próxima investigación

| Gate | Dictamen |
|---|---|
| Fuente real y cronología de 88 padres | PASS para forense QORE, 47+41 ledger |
| Identidad original old CRTH/CRTL frente a pivot M15 | AMBIGUOUS / fuente A no cerrada |
| Indicadores preentrada de contradicción / destino agotado | PASS observación, regla universal fuente A OPEN |
| Rehabilitar 88 como entradas Model #1 | NO ADMITTED, no autorizadas |
| CRT nuevo independiente/nested macro-micro | CONCEPTO reconocido en fuentes B; contrato cognitivo/ejecutable OPEN |
| G-M1 y G-M3 | PARTIAL; G-M5 certificación NO EMITIDA |

**Próximo trabajo científico:** revisar eventos individuales de ambas clases en el ledger real (no solo cifras), cotejar video original por minutaje para source ownership/rearm, y delimitar hipótesis CRT autónomas (nested, advanced vs confirmational, TSQ) con evidencia y clocks preregistrados antes de cualquier replay económico. No falsificar first-source-only para producir más operaciones.

## 4. Implementación y gobernanza

Código de auditoría: src/qore/infrastructure/trader_lab/vt08_crt_pure_later_source_forensics.py. Tests: tests/infrastructure/trader_lab/test_vt08_crt_pure_later_source_forensics.py. Workflow: .github/workflows/vt08-crt-pure-three-source-insidebar-replay.yml. No órdenes, no modificaciones del trader, NO MERGE, NO VPS, NO operaciones DEMO/LIVE, no FundedNext LIVE, no sizing/capital/lotaje/volumen/apalancamiento de VT08, CIBO/QORE Risk mantiene autoridad. BTCUSD congelado. Data Vault issue #837: artifacts tienen caducidad y no son backup permanente.
