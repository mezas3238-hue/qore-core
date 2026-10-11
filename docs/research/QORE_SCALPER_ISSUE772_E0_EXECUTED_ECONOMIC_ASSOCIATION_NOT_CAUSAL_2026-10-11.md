# Scalper Issue #772 — Gate E0 ejecutado: asociación económica C0, sin prueba de causalidad

**Fecha:** 2026-10-11. **Dictamen:** `E0_EXPLORATORY_ASSOCIATION_NO_ROBUST_DIFFERENCE`. NO MERGE / NO LIVE / NO VPS / NO CERTIFICATION.

## Evidencia auditada y orden temporal

- [Prerregistro antes de cargar outcomes](https://github.com/mezas3238-hue/qore-core/blob/3ed51055dbc57d810b7f7b2119cf6d40960cc88a/docs/research/QORE_SCALPER_ISSUE772_C0_ECONOMIC_ASSOCIATION_PREREG_2026-10-11.md); commit prereg `3ed51055dbc57d810b7f7b2119cf6d40960cc88a`.
- [GitHub Actions #38143687671 — **11/11 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38143687671); código del run `ae85f16a69fad58c0efb334d731a41624fcda6cd`; [artefacto conjunto JSON + 2.020 filas por fuente](https://github.com/mezas3238-hue/qore-core/actions/runs/38143687671/artifacts/11702824987).
- [PR Draft #774](https://github.com/mezas3238-hue/qore-core/pull/774), rama independiente de #773. Usa original V49 2020 A sin cambiar entrada, dirección, stop, target, MAX3, salida de sesión ni adjudicación STOP_FIRST; cruza por `source_opportunity_id` las etiquetas C0 y el replay original a partir de M1 nativa. No incorpora nuevo filtro, no remuestrea para seleccionar trades.
- Contrato de calidad y los 9 jobs de mercados más agregado: `SUCCESS`. El código fail-closed reprodujo 2.876 fuentes /2.020 A, V49 PF bruto `0.6644630742`, DD bruto `236.134284R`, resultado bruto `−233.269327R`, 1.167 ganadoras, 852 perdedoras y 1 plana; cualquier diferencia fuera de tolerancia abortaría.
- Costa `0.025R/trade` es **supuesto**, NO ejecución real BID/ASK/slippage.

## Gate E0-a — Diferencia parcial vs intacta

**Exposición:** 382/2.020 con `EITHER_DIRECT_PARTIAL` y 1.638 sin exposición directa a H1 C2/C3 o M15 swing/CISD no estrictas según C0. NO equiparar con la firma H1 divergente, que también tiene N=382 pero diferente membresía.

| Métrica | 382 H1/M15 directa parcial | 1.638 sin parcial directo |
|---|---:|---:|
| PF bruto | 0.629748 | 0.673090 |
| WR bruto | 57.85% | 57.75% |
| Esperanza bruta por trade | **−0.134128R** | **−0.111131R** |
| PnL bruto acumulado | **−51.236887R** | **−182.032440R** |
| PF con coste supuesto 0.025R | 0.573427 | 0.611779 |
| Esperanza tras ese coste supuesto | −0.159128R | −0.136131R |

Diferencia de medias **sin ajuste**: `−0.022997R/trade` (parcial−intacta).

**Prueba primaria preregistrada**: diferencia de medias dentro de cada símbolo, ponderación por `n_partial*n_intacto/(n_partial+n_intacto)`, excluyendo los símbolos sin uno de los dos grupos (NAS100), media **−0.055824R/trade**. Bootstrap circular **2.000 réplicas de 5 jornadas observadas**; 313 fechas, los nueve símbolos viajan en bloque por fecha, semilla `77220261011`: IC percentil 95% **[−0.156391R, +0.043326R]**. Incluye cero. El contraste alternativo exploratorio de símbolo×sesión×H1 inherited fue `−0.059978R` por operación, tampoco es atribución causal ni test predecisional de edge.

**Interpretación correcta:** el grupo de exposición parcial tuvo esperanza bruta inferior, pero no hay evidencia robusta de diferencia a este nivel de incertidumbre. Ambos grupos pierden. La suma acumulada −51.24R de las 382 explica ~21.97% de la pérdida total **observada**, frente a 18.91% de las operaciones; eso **no estima el impacto contrafactual** de corregir velas, porque las señales y cupos pueden cambiar completamente con first-online.

## Gate E0-b — Asociación por mercado, NO selección

| Mercado | N parcial / A | Esperanza bruta parcial | Esperanza bruta sin parcial | Delta parcial−sin (R) |
|---|---:|---:|---:|---:|
| AUDJPY | 70 / 181 | −0.1646 | −0.0862 | −0.0785 |
| AUDUSD | 103 / 171 | −0.1187 | −0.0782 | −0.0405 |
| EURUSD | 25 / 285 | −0.0882 | −0.1175 | **+0.0292** |
| GBPJPY | 85 / 194 | −0.1532 | −0.0806 | −0.0726 |
| GBPUSD | 6 / 288 | −0.3294 | −0.1747 | −0.1547 |
| NAS100 | **0 / 258** | NO APLICA | −0.1567 | NO APLICA |
| USDCAD | 7 / 215 | −0.1371 | −0.0067 | −0.1305 |
| USDJPY | 84 / 179 | −0.1177 | −0.0475 | −0.0701 |
| XAUUSD | **2 / 249** | +0.2819 | −0.1305 | +0.4125 (N=2, NO INTERPRETAR) |

Los mercados AUD/JPY muestran tendencia descriptiva negativa en celdas expuestas, pero EURUSD revierte el signo y algunas muestras son demasiado pequeñas. **NAS100 no tiene trades A expuestos y aun así pierde −0.1567R/trade bruto**; refuta que la exposición directa a velas parciales sea condición necesaria del rendimiento negativo V49. No implica que el feed sea irrelevante para otras partes del algoritmo.

**Contraste de calidad de feed vs incidencia en oportunidades:** AUDUSD tiene **614 H1 legacy no estrictas /6.401 (9.6%)** y 103/171 A expuestas (60.2%); EURUSD tiene **684/6.420 (10.7%)** pero solo 25/285 A expuestas (8.8%). El mecanismo requiere estudiar calendario/horario **y** selección Candle2/Candle3/POI/inherited; no es evidencia suficiente de que “AUD/JPY tiene peor proveedor”.

## Cruce secundario preregistrado: parcial × firma H1 strict divergente

| Parcial H1/M15 directa | Firma H1 estricta divergente | N | Esperanza bruta R | PF bruto |
|---|---|---:|---:|---:|
| NO | NO | 1.590 | −0.11072 | 0.67320 |
| NO | SÍ | 48 | −0.12475 | 0.66970 |
| SÍ | NO | 48 | −0.11754 | 0.67249 |
| SÍ | SÍ | 334 | −0.13651 | 0.62367 |

La exposición directa, la sensibilidad a firma strict y el resultado económico son conceptos **diferentes**. El patrón es descriptivo y ya consumido; no usar la celda 334 como filtro o criterio de reparación optimizado.

## Límites importantes y decisión

1. **Asociación ≠ causa.** Una diferencia robusta en la misma muestra tampoco demostraría que las velas incompletas causaron pérdidas: hora, símbolo, sesión, sesgo heredado, volatilidad, eventos simultáneos, gaps de fin de mercado y mecanismo de selección son confusores.
2. **No-diferencia ≠ inocuidad causal.** Bootstrap CI incluye diferencias negativas materialmente relevantes. Ausencia de significancia no prueba que una reconstrucción fiel tenga el mismo PnL.
3. **No existe intervención consistente “borrar 382 trades”.** El detector first-online estricto puede producir nuevas oportunidades, cambiar la selección MAX3, mover stops y cambiar el sesgo H1. Ninguno de esos contrafactuales fue estimado por E0.
4. **No hay prueba de outage de proveedor.** Las H1 incompletas incluyen faltas leading/internal/trailing; requerimos calendario de negociación y sesiones por símbolo/timestamp (incluida zona horaria) antes de clasificar causa física.
5. **Historia consultada**: aun con prereg previo a mirar estos grupos, E0 es diagnóstico posthoc en la cohorte V49 ya conocida, no certificación fuera de muestra. Coste 0.025R/trade hipotético, BID/ASK broker no disponible.
6. **No adjudica** Candle2/Candle3, POI, swing derecho M15, CISD M1 ni H1 inherited contra fuentes autorales. Eso sigue siendo objetivo prioritario de [Gate C independiente #772](https://github.com/mezas3238-hue/qore-core/issues/772).

**DICTAMEN:** `E0_COMPLETED_ASSOCIATION_INCONCLUSIVE`. No recomendar arreglar el feed basado en PF, no activar strict-bar ni TTL, no invertir V49 ni crear veto C0. **Gate C first-online sigue siendo necesario por fidelidad metodológica y prueba causal**, no porque hayamos demostrado que velas parciales expliquen PnL. Mantener VPS, producción, cuentas, V49 y DCVC intactos.
