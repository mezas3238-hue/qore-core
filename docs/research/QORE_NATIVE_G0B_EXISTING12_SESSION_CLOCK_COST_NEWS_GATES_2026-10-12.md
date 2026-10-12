# QORE Native — G0B STRUCTURAL P1, evidencia/puertas de coste — 2026-10-12

**Ámbito exclusivo:** GitHub research, read-only. Issue [#818](https://github.com/mezas3238-hue/qore-core/issues/818), [#815](https://github.com/mezas3238-hue/qore-core/issues/815), upstream 12-source [#816](https://github.com/mezas3238-hue/qore-core/pull/816), no-news governance [#814](https://github.com/mezas3238-hue/qore-core/pull/814). No VPS/MT5/LIVE/CIBO/Shared/QDLE y ningún resultado económico consultado.

## Estado P0 verificado desde GitHub

- Auditoría original cTrader DEMO: 12/12 símbolos, 8.726.985 M5; 132 años/particiones RAW con SHA, run #38196127168; el nuevo G0B revalida los archivos originales antes de extraer **solo timestamps** (2ª lectura). NO afirmar que el origen de los 12 sea la misma cuenta IC Markets usada por la captura de 21.
- Matriz fija: AUDJPY, AUDUSD, EURUSD, GBPJPY, GBPUSD, NAS100/USTEC, SP500/US500, US30, USDCAD, USDJPY, XAGUSD, XAUUSD.
- En consulta a GitHub Actions [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) se observaron **11 artefactos M5 nuevos publicados** (USDCHF, NZDUSD, GBPCAD, EURNZD, EURCHF, EURCAD, EURGBP, GBPCHF, EURJPY, EURAUD, GBPAUD); GBPNZD estaba in_progress y 9 capturas queued. Son **11 artefactos presentes, no 11 series 10Y auditadas**. Sin inspeccionar raw SHA/recuento no constituyen G0 PASS; no relanzar descarga duplicada.
- Fuentes [PR #811](https://github.com/mezas3238-hue/qore-core/pull/811). La matriz 21 pertenece a una rama paralela, no se mezcla ni se incorpora al batch 12.

## Contrato ejecutable G0B: evidencia sí, inferencias no

Código `qore_native_g0b_sessions_cost_gates_v1.py`: descomprime los mismos 12 artifacts originales vía GitHub Actions, aplica íntegramente `audit_symbol` de G0, revalida SHA 11 RAW/year y cuenta únicamente los timestamps `opened_at` del original JSONL. Produce por mercado:

1. Número de barras, días UTC con 288/288 o parcial, discontinuidades entre timestamps M5 y longitud en slots, **siempre UNKNOWN_CLOSURE_OR_FEED_GAP** hasta poseer calendario oficial.
2. Firma estadística *descriptiva* de presencia de barras por día de semana, semana, reloj NY con **offset** de DST. No declara horario IC Markets, spot FX/cierre estadounidense ni swap rollover. DST puede producir horas locales duplicadas y horas inexistentes.
3. Testigos JSON más SHA256, aggregate total 12/12, CI Ruff/Pytest, sin OHLC, retornos, volatilidad, stops, selección de símbolos ni PnL.

**No** inferir vela H4/D1 ejecutable de los 48/288 slots UTC; especialmente NAS100/SP500/US30/XAGUSD/XAUUSD tienen pausas de mercado y 0 días UTC 288/288, condición que NO implica feed corrupto. Este G0B mide frecuencia observada; no distingue cierre regular, feriado, rollover, outage del feed o cambio de sesión. Estado `UNVERIFIED_NOT_INFERRED_FROM_FEED` hasta evidencia primaria.

## Evidencias externas obligatorias antes de G1 NET

Cada símbolo y tipo de cuenta requiere hashes SHA/versiones/fechas válidas de: (1) identidad contractual, lote/tick/tamaño/familia y broker exacto; (2) calendario real de sesión, horarios de cierre/rollover, excepciones históricas, cambios de DST, feriados, fuente as-of y permisos; (3) BID/ASK histórico de **ese mismo broker** por slot con porcentiles y ejecución real lado compra/venta; (4) comisión RT y esquema/versión por fecha y tipo de cuenta; (5) slippage RT, anomalías de spread, stops y costes de salida pre-news; (6) swap/financiación overnight y rollover; (7) calendario noticias as-of y zona horaria/versionado verificable. Cualquier fuente prospectiva actual NO certifica automáticamente historia 2016–2026.

El campo `evidence_gate` falla cerrado: si faltan referencias = `BLOCKED_MISSING_SOURCE_EVIDENCE`; aunque usuario introduzca todas las referencias = `SOURCE_CLAIMS_NEED_INDEPENDENT_VERIFICATION` hasta comprobar bytes, proveedor, fecha efectiva y trazabilidad. NO hay estado PASS por rellenar un formulario ni por disponer de OHLC a mid. Spread desconocido != spread 0. `G1_NET_AUTHORIZED=false` sin todos estos testigos y auditoría metodológica de calidad.

**No-news:** la exclusión 30 minutos antes / 60 después es candidata de la política #814, no filtro probado ni desplegado. Las fuentes históricas retrospectivas NO equivalen a calendario anunciado antes de cada entrada. Posiciones ya abiertas deben tener un protocolo causal de salida/coste previo al evento, no suponer cierre gratis. Blackout de eventos no programados imposible de conocer anticipadamente.

## Contrato de la PRÓXIMA hipótesis (P2), sin abrir PnL

Elegir **solo un mecanismo** de continuación en régimen normal multi-horas (H4) o D1 **después** de aprobar proveedor/rollover, fricción, stop, calendar as-of y potencia. Prerregistrar antes de generar retornos:

- 1 símbolo representante elegido por microestructura/fuentes, NO por rendimiento; modelo económico de persistencia/razón de asumir el riesgo; reglas de señal causal exactas con datos cerrados (sin lookahead); long/short y stop ejecutable y financiación overnight.
- Inicio/término de development, control temporal y factorial equiexpuesto, horizonte de posesión, máximo de posiciones, correlación por cluster, número efectivo de eventos y MDE usando sigma medida solo en development (no millones de M5 como eventos independientes).
- OOS virgen real identificado por procedencia, nunca abrir holdout 2014–2016 sellado; 2016–2026 ya tocado parcialmente para RESET/DRIVE/Londres, registrar dependencia. Si no queda OOS independiente, requerir captura prospectiva o reserva nueva.
- Coste conservador RT <=10% de riesgo de stop como cribado inicial, magnitud >=3× fricción RT conservadora, P99 spread-no-trigger test y limites de estimación; si no verificable `BLOCKED`, no simulación con fricción 0.
- Conservar todas hipótesis fallidas; tests múltiples ajustados, no barridos 33×parámetros ni seleccionar ganadores.
- Congelar commit SHA/config/fechas y umbral ex ante; diseño NO NEWS en regímenes normales; no prometer rentabilidad.

**Estado al crear esta PR:** implementación de G0B preparada para Actions, pero **el calendario y costes históricos todavía no están certificados**, G1 no autorizado, traders Native certificados 0/3. Si CI no produce artefactos de resultados, registrar infraestructura bloqueada y no afirmar que el censo se ejecutó.

## Próximas acciones reproducibles

1. Ejecutar workflow `qore-native-g0b-existing12-observed-clock.yml` y verificar **12/12** resultados, hashes JSON y totales 8.726.985 sin PnL.
2. Obtener testigos proveedor/broker de horarios y cambios históricos y adjudicar cada discontinuidad con clasificación separada SOURCE_GAP / EXPECTED_CLOSURE / UNKNOWN + nivel de evidencia.
3. Obtener BID/ASK, comisiones, swap y slippage para la cuenta y símbolo exactos, separar tarifas actuales de histórico as-of. Publicar matriz de bloqueos sin datos personales.
4. Solo entonces sellar un G1 único, con potencia y verdadero OOS; después evaluar economía neta y eventual certificación.
5. En paralelo auditar uno por uno los 21 archivos según RAW SHA/número de años/IC Markets DEMO sin mezclarlos con los 12 ya acreditados.

**DeepSeek:** opcional para auditoría adversarial de ambigüedades, nunca sustituye fuente de exchange/broker ni evidencia de fills/PnL.
