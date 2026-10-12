# VT31 — P0: identificabilidad de economía CE y déficit de contrato de salida

**Fecha:** 2026-10-12 · Sólo investigación; no cambios a metodología, producción, VPS o holdout.

## Nueva pregunta formal
¿Qué puede inferirse de `2,140` candidatos M1 con CE y DOL cuando no se dispone de un stop inicial as-of, política ejecutable de salida, BID/ASK histórico autenticado ni broker ACK? **No se puede estimar un PF neto, expectancy de operaciones ni DD de posiciones** sólo con el ledger de oportunidades.

**Fuente:** ledger original de `11657461650`, Actions run `38018602495`, mismo único VT31 y tres ventanas M1 del handoff #872. Este análisis **no optimiza los candidatos ni cambia su resultado**. Sus cantidades sobre presencia de campos deben salir de CI sobre el artefacto inmutable, no presumirse basándose únicamente en lectura de código.

## Bloqueador de especificación comprobado a nivel de fuente
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/contracts.py::FvgCandidate` incluye `consequent_encroachment`, `target_price`, `projected_index_points`, pero **no** un `stop_loss` inicial ni una política de liquidación.
- `operations.py` confirma en su cabecera que `stop/fill policy not implemented`; `order_lifecycle.py` solo registra cotizaciones/ACK externos, no aplica stop/target ni envía orden. Expiración al final de hora de la **orden pendiente** no constituye cierre automático de una posición.
- El ledger de ofertas original contempla `m1_ce_research_limit`, `draw_target`, `broker_execution_ack=null`, `paper_fill_count=0`. No contiene un libro autónomo de ejecuciones, exposición, comisión y exits. **Aun consiguiendo ticks, falta formalizar STOP+salidas con fuente ICT o etiquetarlos como hipótesis nuevas antes de calcular R.**

## Contraejemplo causal: OHLC M1 idéntico no identifica PnL
Construimos dos caminos MID **enteramente sintéticos** de un minuto, con spread fijo hipotético 1.60, entrada BUY limit CE=100, stop hipotético=98 y target hipotético=103, OHLC idéntico `(102,106,96,101)`:
1. Secuencia MID `102 → 99 → 106 → 96 → 101`: ASK alcanza CE, después BID alcanza target → salida teórica favorable.
2. Secuencia MID `102 → 106 → 99 → 96 → 101`: target alcanzado ANTES de la eventual entrada, luego ASK alcanza CE y BID alcanza stop → salida teórica adversa.

Este ejemplo **NO es un setup real VT31, un fill de broker ni una estimación de profit**; demuestra matemáticamente que ni M1 OHLC ni el mismo spread fijan el orden temporal intravela. Llamar WIN o LOSS histórico a ambos sería dato inventado.

## Gates P0 para estudio CE ejecutable
- **G3 doctrina:** stop inicial, condición exacta de salida y política al tocar DOL deben formalizarse por anticipado con evidencia original, incluyendo precedencia de MSS opuesto, FVG invalidado y expiración de limit. No escoger stop que maximiza PF a posteriori.
- **G5 quote/contrato:** mismo broker, mismo símbolo o equivalencia certificada NAS100↔NDX100, UTC-ms BID/ASK original, cobertura comprobada, tick_value/tick_size/lote/moneda, fees y slippage.
- **G6 ejecución:** orden CE activa sólo después de confirmación FVG, cancel_at causal, ejecución *simulada* marcada como PAPER separada de broker `ExternalExecutionAck`, carreras cancel/ACK, SL/TP con orden de eventos y persistencia de posición más allá de ventana.
- **G7 economía:** una vez completados G3/G5/G6, PF neto/expectancy/DDD/R/Sharpe/Sortino con muestras y riesgo correctos; si falta una pieza declarar `INDETERMINATE_DATA_OR_METHOD`, no cero pérdida, ni cero spread, ni cero trades como estrategia falsada.
- **G8 holdout:** permanece sellado y prohibido hasta metodología y ejecución congeladas.

**Criterio de parada:** si no se puede demostrar fuente de precios ni contrato de salida válido en una fase acotada, adjudicar `DATOS_INSUFICIENTES_PARA_EDGE`; no autorizar live, no expandir cognitiva y no adaptar umbrales retrospectivamente.

## Artefactos nuevos
- `scripts/vt31_p0_ce_economic_witness_audit.py`
- `tests/infrastructure/test_vt31_p0_ce_economic_witness_audit.py`
- `.github/workflows/vt31-p0-ce-economics-witness.yml`

CI recupera el ledger con ID fijo, verifica metadatos de origen, hashes y fuente. No obtiene OOS ni descarga datos privados. **No declarar conteos campo-reales ni PASS hasta obtener workflow satisfactorio**.

### División arquitectos
Esta rama ARCH analiza suficiencia de testigos y ambigüedad económica; la rama OPS #874 produce screen direccional adverso y su revisión #875; ARCH de incertidumbre #876 examina A/B sin falsificar UNKNOWN. Solicitar revisión mutua de contratos, pero no fusionar nada a `main`.
