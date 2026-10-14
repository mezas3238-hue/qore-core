# VT31 — L1/M5: auditoría stop C2 versus referencia pre-MSS de TTrades · 14-OCT-2026

**Resultado: SOURCE_STOP_REFERENCE_DIVERGENCE_OBSERVED / TTRADES_AUTHOR_SWING_UNDETERMINED.** No metodología ni Trader certificado. PR #943 DRAFT: https://github.com/mezas3238-hue/qore-core/pull/943

## Fuentes y reglas diferentes
Fuente primaria TTrades del 19 de junio de 2025: https://ttrades.com/the-am-silver-bullet-strategy-on-nq/ — requiere stop más allá del swing que originó el displacement. No define en texto un algoritmo determinista universal de pivote M1, ni dice que siempre sea la vela media de un FVG.
Acta G3 r1.3 no firmada: docs/research/VT31_G3_DECISION_METODOLOGICA_STOP_FRAMEWORK_FVG_EXIT_V1_2026-10-12.md — elige, como formalización original QORE y NO doctrina certificada del autor, stop basado en la mecha completa de C2 con un tick adicional del símbolo homologado. Ambas reglas no son intercambiables ni pueden fusionarse tácitamente.
La otra familia de investigación de entradas en PR #906 abarca desplazamiento directo, FVG, OB, Breaker, pero usa otra cohorte / especificación. Sus 212/205/116/84 propuestas exploratorias NO son 119 operaciones de este censo.

## Experimento ejecutado y trazable
- Pre-registro anterior al código y lectura 3Y: bd5a6f48345c974232a0a914f1a83b583952b9cf. Documento: docs/research/VT31_L1_M5_C2_VS_TTRADES_SWING_STOP_PREREG_2026-10-14.md.
- CI SUCCESS: https://github.com/mezas3238-hue/qore-core/actions/runs/38645656775, **213/213 pruebas** PASS, Ruff, compilación, 3 blobs originales G3 congelados y SHA256 de fuente real comprobados. Commit de código/test certificado por CI: d45be575ba20eae055b700f25da78b8f21f77678.
- Artifact JSON detallado de 119 casos y pruebas: https://github.com/mezas3238-hue/qore-core/actions/runs/38645656775/artifacts/11931708697; ZIP SHA256 a3b40e57cc0f8d9d0aedbcf87f2763a17dd42070c9f4523b562097f9b8c8072f.
- Original NAS100 CFD 3Y: 1.059.784 velas M1, SHA256 0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa. **Desarrollo histórico ya examinado, NO fresh holdout**.
- Población no optimizada y fija: 775 días NY; 128 contextos cognitivos M2/M3 de PR #934; 119 primeros FVG M4 (8 sin FVG, 1 en cierre 11am). Para cada uno se reconstruyó solo H1 9am y prefijo de 10am cerrado en C3, con primera vela de sweep, primer MSS y FVG/CE/C2 a fecha/hora causal. NO se examinó retorno/M5 para elegir los 119.

## Resultados cuantitativos: referencias estructurales, NO stops de operación

| C2 full wick comparado con extremo observado desde primer raid hasta **ANTES** del MSS | Casos |
|---|---:|
| C2 queda dentro del extremo previo (más cerca del precio que ese extremo) | **116** |
| C2 coincide con extremo previo | **2** |
| C2 sobrepasa extremo previo | **1** |
| Total | **119** |

| C2 contra extremo exclusivamente de la PRIMERA vela de raid | Casos |
|---|---:|
| Dentro | **73** |
| Coincide | **1** |
| Sobrepasa | **45** |
| Total | **119** |

Las 119 referencias C2 están del lado de riesgo correcto respecto de CE: LONG C2.low menor que CE / SHORT C2.high mayor que CE. Pero sin tick/origen/cotizaciones/restricciones de bróker NO son stops negociables. Estos datos prueban que C2 no coincide normalmente con los **proxies observados**: **NO** prueban que 116 stops incumplan TTrades, porque ninguno de los proxies ha sido identificado de forma independiente como el swing exacto que originó displacement. La diferencia 73/1/45 muestra que ni siquiera los proxies de primer raid vs todo el tramo pre-MSS son equivalentes.

## Gates
| Gate | Estado comprobado |
|---|---|
| M0–M3 | contexto H1 TTrades, 128 MSS QORE, fuente M1 causal, no validación autoral completa |
| M4 | primeras FVG QORE 119/128; las otras 4 familias de #906 separadas sin política de selección aprobada |
| **M5** | **NO CERTIFIED**: swing autoral no identificado, C2 QORE es variante de ingeniería; falta broker stop/OMS |
| M6 | G3_PENDING_DUAL_SIGNATURE (issue #897) |
| M7/L7 | 0 órdenes, 0 ACK fills, PF/DD/Sharpe/Sortino indeterminados; BID/ASK NAS100 exact-symbol pendiente #857/#900 |
| L1 oficial | candidato Trader Lab DRAFT #939, sin ResearchEvaluationFreezeEvidence válido de doctrina íntegra |
| L2–L10 | siguen pendientes/bloqueados como matriz oficial PR #936 |

## Trabajo obligatorio siguiente
1. Identificar mediante ejemplos primarios TTrades verificables (video/instante + condiciones positivo/negativo) qué swing exacto origina desplazamiento y cuándo puede conocerse su pivote M1, incluyendo familias OB/Breaker. Si la fuente sigue indeterminada, conservar SOURCE_UNDERDETERMINED y certificar únicamente una formalización QORE separada.
2. Congelar ex ante selector de familias (no sumar cohortes #906 y #935 ni elegir ganador tras ver retornos), stop, entrada, salidas, y G3 con firmas distintas COG/OPS SHA exactos #897. No modificar G3 legado sin orden.
3. Confirmar NAS100 vs USTEC contrato del mismo bróker, tick/stop constraints, BID/ASK durante toda operación hasta 15:55 NY, OMS/ACK/fills/fees, antes de iniciar replay económico L2/L7. No usar contactos CE como trades.
4. Con versión completa congelada ejecutar L2 replay, L3 oficial, L4 OOS previamente intocado, L5 stress, L6 MC y atestaciones externas L8/L9/L10. No sizing en VT31; CMA/CIBO/QDLE administran riesgo.

**Prohibido MERGE, LIVE, VPS, FundedNext LIVE, OMS, lotaje propio o publicación de PF inventado.** Este informe documental es posterior a la CI; la verificación de pruebas se refiere exactamente al commit d45be575ba20eae055b700f25da78b8f21f77678, no al nuevo HEAD que agrega este texto.