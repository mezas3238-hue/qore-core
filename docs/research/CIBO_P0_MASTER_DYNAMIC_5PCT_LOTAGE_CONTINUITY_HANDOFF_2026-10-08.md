# QORE CORE — HANDOFF MAESTRO P0: LOTAJE REAL FUNDEDNEXT, CUARTETO ECONÓMICO Y RIESGO DINÁMICO 5%

**FECHA:** 2026-10-08  
**ESTADO:** CÓDIGO P0 DINÁMICO IMPLEMENTADO EN RAMA EXPERIMENTAL; 50/50 PRUEBAS CI SUCCESS; REPLAY ECONÓMICO DINÁMICO 3 AÑOS AÚN PENDIENTE; NO CERTIFICADO; PROHIBIDO PROMOVER A PRODUCCIÓN.  
**REPO:** mezas3238-hue/qore-core  
**RAMA BASE CANÓNICA CIBO:** agent/cibo-causal-expectation-leakage-fix-001  
**RAMA P0 INICIAL (TECHO ERRÓNEAMENTE FIJO USD 3):** agent/cibo-p0-fundednext-real-mt5-lotage-financing-001  
**RAMA P0 VIGENTE DE CONTINUIDAD Y CORRECCIÓN:** agent/cibo-p0-dynamic-equity-5pct-lotage-002  
**WORKFLOW VERIFICADO EN LA RAMA ACTUAL:** https://github.com/mezas3238-hue/qore-core/actions/runs/37814146300 (SUCCESS: 43 tests motores/MT5 + 7 Trader pre-send = 50).

## 0. OVERRIDE SOBERANO DEFINITIVO — LEER ANTES DE TOCAR CUALQUIER PARÁMETRO

El usuario corrigió expresamente la decisión anterior. **RIESGO POR ENTRADA = 5% DINÁMICO DE LA CUENTA, NO USD 3 FIJOS.** Los USD 3 se aplican solo al saldo inicial de USD 60. Si crece el capital, el 5% también crece; si disminuye, el riesgo permitido se reduce. Nunca degradar a presupuesto USD 3 fijo sin autorización del usuario y configuración experimental separada.

- USD 60 → presupuesto objetivo USD 3; USD 100 → USD 5; USD 500 → USD 25; USD 1.000 → USD 50; USD 10.000 → USD 500.
- Base causal elegida de forma conservadora: min(MT5 equity actual, MT5 balance realizado). Cuando pérdidas flotantes reducen equity, el riesgo baja; cuando solo existen ganancias flotantes no realizadas, NO incrementan el riesgo hasta asentarse en balance. Es un límite de seguridad mientras no haya política explícita de reinversión flotante.
- **El presupuesto autoriza una pérdida TOTAL MÁXIMA prevista al stop**, incluyendo comisión de apertura y costes adversos, NO obliga a consumir exactamente 5% y NO equivale a 5% de margen.
- Si el saldo y el margen no alcanzan el lote mínimo permitido, se declara NO FINANCIABLE; se conserva el registro de la señal del Trader pero **NO se inventa la orden ejecutada**.
- El ratio 5% es por **nueva entrada**. Un conjunto de posiciones simultáneas exige un límite adicional de riesgo/margen global para no poner en peligro la cuenta. Los porcentajes de concentración actuales son prototipo por validar, NO parámetros certificados.
- Los multiplicadores 1x/10x/10000x de antiguos experimentos no son lotes MT5 ni leverage de FundedNext. DEJAR DE UTILIZARLOS COMO AUTORIDAD FINAL DE VOLUMEN.

**FÓRMULA EN EL CÓDIGO:**
risk_base_usd = min(account.equity, account.balance), información de la misma cuenta y en moneda USD; dynamic_risk_target_usd = risk_base_usd × 0.05.  
risk_authorized = min(dynamic_risk_target_usd; presupuesto cartera, símbolo, Trader, correlación; fuente BANK/CUSHION libre y realizada; solvencia soberana).  
risk_at_stop(lots) = -MT5.order_calc_profit(BUY/SELL,broker_symbol,lots,entry_price,stop_adverso) + comisión + costes adversos.  
Escoger el mayor volumen LEGAL volume_min/volume_step/volume_max que cumpla riesgo_at_stop <= risk_authorized, margin <= margen libre restante y nivel de margen proyectado mínimo. Nunca redondear al alza violando límites.

## 1. ARQUITECTURA Y AUTORIDADES

**Trader** toma la decisión de entrada, dirección, SL y TP; no decide finanzas. Antes de enviar una nueva orden a MT5 solicita al CIBO central el lote económicamente autorizado. Una entrada ya abierta no puede redimensionarse retroactivamente. Si no hay orden viable, se conserva la señal como señal NO EJECUTADA y el motivo físico; CIBO no «rechaza» la estrategia del Trader. No hay orden ni PnL falsos.

**Sizing:** cálculo causal de 5% por entrada, pérdida hasta SL para cada lote vía broker, búsqueda del lote mayor compatible, costes/comisiones, precio Bid/Ask, BUY/SELL y paso mínimo.

**CIBO Compuesto:** BANK tiene capital inicial + ganancias/pérdidas realizadas y liquidadas. Libera MEDIUM solo con capital disponible y reservas; ATTACK nunca toma fondos del banco si pertenece a cushion. Reinversión de ganancias realizadas hace crecer base económica, pero no sustituye el cálculo de 5% de la cuenta y nunca permite fondos inexistentes.

**Portafolio Compuesto:** una sola cuenta compartida, reservas atómicas por id único, riesgo de todas las entradas abiertas, por símbolo/Trader/grupo de correlación, margen abierto, límites y banca soberana. Evitar doble gasto. Límites experimentales actuales: cartera 15% de risk_base, símbolo 10%, Trader 10%, grupo 15%, todos DINÁMICOS sobre la cuenta. Deben estudiarse científicamente frente a DD/stop-out, no son una certificación.

**Adaptive Leverage:** comprueba estrictamente volumen permitido y MT5.order_calc_margin real, equity, margin_free, margin level, restricciones reales de la cuenta. No asume que capital real se multiplica por 10000x. Prioridad absoluta a la capacidad financiera.

**Motor central:** servicio de cotización pura + libro de reservas en una interfaz, no cuatro «calculadores» que impriman cuatro fuentes de efectivo. Todos consumen una única instantánea económica con bloqueo por operación e idempotencia.

**Ciclo de orden:** Trader signal → CIBO economic coordinated quote (5%) → MT5 loss/margin/step validation → funded reservation → Trader broker gateway order_send → confirm fill/price/ticket → monitor/risk-management → broker close receipt → conciliar PnL → liberar reserva → actualizar capital realizado y recalcular 5% en la siguiente orden.

## 2. ARTEFACTOS CREADOS EN GITHUB

A. src/qore/infrastructure/trader_lab/cibo_fundednext_mt5_lotage_p0.py
- Fuente de verdad order_calc_profit, order_calc_margin, instrument symbol_info, Bid/Ask, min/step/max, tick freshness, cuenta USD, margen libre.
- Cambio reciente de RiskPolicy: per_entry_risk_fraction=0.05; valor monetario fijo opcional per_entry_usd=None por defecto; límites de cartera/símbolo/Trader/grupo también pasan de techos USD FIJOS a fractions 0.15/0.10/0.10/0.15.
- Nuevo Quote devuelve risk_base_usd, dynamic_risk_target_usd y effective_risk_budget_usd, para auditoría del 5% solicitado vs restringido.
- Se permite per_entry_usd=3 ÚNICAMENTE como techo adicional experimental/compatibilidad, sin deshabilitar el 5% dinámico.
- Calcula comisiones de referencia y deslizamiento; rechaza si el lote mínimo viola presupuesto o margen.

B. src/qore/infrastructure/trader_lab/cibo_four_motor_fundednext_p0.py
- Coordinación de los cuatro motores y wallets BANK/CUSHION con ganancias realizadas. En la rama vigente utiliza source_available_usd de BANK/CUSHION junto con RiskPolicy dinámica en cada solicitud; se eliminó el min(USD3 fijo,cash).
- MotorDecision("SIZING") informa dynamic_risk_target_usd de la cotización actual, no 3 fijo.
- can_submit_to_broker sigue False por defecto hasta reconciliar posiciones broker auténticas.

C. src/qore/infrastructure/trader_lab/cibo_trader_presend_mt5_p0.py
- Handshake de Trader a CIBO con propuesta de lotaje; no hace order_send, no simula fills.
- Detecta rechazo MT5, lotaje parcial, precio distinto que requiere recálculo de riesgo. AÚN NO conectado al gateway de órdenes productivo; proyecto de laboratorio.

D. scripts/cibo_p0_mt5_specs_readonly_probe.py
- Script read-only a ejecutar en el VPS de MT5 de la cuenta real; recopila specifications de seis símbolos sin exponer credenciales. NAS100 ↔ NDX100 es un mapeo candidato sujeto a verificación en el servidor.

E. scripts/cibo_p0_three_year_offline_lotage_audit.py
- Auditoría histórica SOLO de presupuestos FIJOS USD3/USD2.95, anterior a la corrección. **NO reutilizarla como prueba de rentabilidad ni de cumplimiento 5% dinámico.**
- Workflow: .github/workflows/cibo-p0-offline-3368-fundednext-stop-risk-audit.yml
- Acción: https://github.com/mezas3238-hue/qore-core/actions/runs/37809999723 SUCCESS, artefacto ID 11564337531.

F. tests/trader_lab/test_cibo_fundednext_mt5_lotage_p0.py — base 34 tests anteriores, nuevas pruebas por equity 60/100/1000, ganancias, pérdidas, flotantes, caps porcentuales y prohibición de >100% por entrada.

G. tests/trader_lab/test_cibo_four_motor_fundednext_p0.py — pruebas de reservas, BANK/CUSHION, beneficios asentados, pérdidas no financiables y 5% después de ganancias/pérdidas.

H. tests/trader_lab/test_cibo_trader_presend_mt5_p0.py — Trader no envía orden y conserva SL/TP; añadió caso de 5% dinámico antes del envío.

I. .github/workflows/cibo-p0-fundednext-mt5-lotage-solvency.yml — pruebas CI ambas versiones, versión dinámica verificada en run 37814146300, **50/50 SUCCESS**.

## 3. HISTORIA DEL TRABAJO QUE DEBE PRESERVARSE

**H8 — ALERTA ABSOLUTA P0 DE SOLVENCIA:** handoff canónico base
docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md
y documento
docs/research/CIBO_H8_REAL_CAPITAL_SOLVENCY_BLOCKER_2026-10-08.md
demuestran una entrada mandatory 1x necesitando USD 4.520000 con solo USD 4.215535 de fondos soberanos disponibles; hay estados de BANK negativo en simulación legacy. Por tanto las curvas de capital de aproximadamente USD 670.000, DD 35–36%, etc. **no son certificados de financiamiento real** y no deben convertirse en metas aceptadas sin broker-verification/stop-out.

**H21/H26:** PnL histórico de investigación nominal desde USD60 a USD3589.260487 en tres años, DD ~34.35372258%; en primer año +USD408.14, con multiplicadores y muchos stops infrarriesgados. No era 5% de equity real. H26 demostró que los cuatro motores aportan económicamente: no retirarlos ni limitarse a ATTACK.

**H27:** replay 3368 señales, USD3 riesgo fijo solicitado **NO CUMPLE**: 2.237/3.368 stops < USD3; julio inicial 82/84, primer año 922/1109 bajo USD3. Primera VT31 NAS100 stop 1x USD0.295. El «5% nominal» estaba limitado por política de intensidad/multiplicador y el lote físico no demostrado.

**H28:** adaptador de volumen broker-compatible experimental (6 pruebas) separado del motor CIBO original.

**H29:** primer intento de aproximar USD2.95 mediante intensidad; seguía primera NAS100 a 1x USD0.295: no resolvió el problema.

**H30:** introdujo cuatro calculadoras de lotaje coordinadas sobre la custodia original. Replay 3368/3368 SIGNAL CUSTODY, capital final USD2705.99, DD34.35%, **breach BANK USD74** → RECHAZADO.

**H31:** reserva soberana reforzada y margen descontado, replay 3368/3368 SIGNAL CUSTODY, capital final USD2997.39, DD34.35%, BANK breach0, pero 0/3368 objetivos de USD2.95 exactos y 1124 potencialmente no financiables al mínimo bajo reserva H31 → RECHAZADO para producción; no es 3368 fills MT5.

**P0 MT5 V1 (rama parent):** fuente MT5 real vía interface de prueba, coste por SL USD3 FIXO (esto se CORRIGE ahora); 40 pruebas CI SUCCESS; auditoría read-only 3368 señales a USD3 y USD2.95, no curva PnL/DD genuina.
Tabla OFFLINE HISTÓRICA de riesgo fijo USD3:
|Activo|Señales|Con step/SL/costes matemáticamente posibles|Sin volumen matemáticamente compatible|
|---|---:|---:|---:|
|AUDJPY|673|651|22|
|EURUSD|495|494|1|
|GBPJPY|618|589|29|
|GBPUSD|606|570|36|
|NAS100|484|459|25|
|XAUUSD|492|308|184|
|TOTAL|3368|3071|297|
Con USD2.95 fijo: 3060 potenciales, 308 sin volumen. **ESTA TABLA NO REPRESENTA UNA POLÍTICA DE 5% DINÁMICO, NO ES REPLAY FINANCIERO Y NO SON ÓRDENES EJECUTADAS.** Dejar estos resultados solo como control histórico de errores de lotaje.

**P0 MT5 V2 (ESTADO ACTUAL):** presupuesto 5% dinámico, escalamiento de límites globales, 5% aplicado antes de buscar lote, fondos asignados por cuarteto, más pruebas sobre cuenta creciente y decreciente. **CI 50 pruebas SUCCESS, replay 3 años con esta nueva política NO HECHO**. No inventar mejoras ni ganancias DD.

## 4. SEIS INSTRUMENTOS Y DATOS DEL BROKER

|Core|Referencia contrato público|Leverage público Stellar Instant|Valor min/step/tick/margen servido por MT5|
|---|---|---|---|
|AUDJPY|100k AUD/lot|1:30|PENDIENTE|
|EURUSD|100k EUR/lot|1:30|PENDIENTE|
|GBPJPY|100k GBP/lot|1:30|PENDIENTE|
|GBPUSD|100k GBP/lot|1:30|PENDIENTE|
|NAS100 / NDX100|10 unidades/lot|1:5|PENDIENTE|
|XAUUSD|100 oz/lot|1:7.5|PENDIENTE|

Referencias FundedNext (no sustituyen servidor real):
https://help.fundednext.com/en/articles/8020350-what-is-the-contract-size-of-the-instruments
https://fundednext.com/general-rules/cfds/symbols-and-conditions
https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account

Comisión provisional publicada: Forex USD7/lot al abrir; índice USD0; metales ~0.0016% del nominal de apertura. El sistema real requiere verificar comisión efectiva e histórico sin doble contabilizar spread, además de deslizamiento. Para JPY, conversión a USD **con order_calc_profit del servidor**, nunca tipo de cambio USDJPY actual usado para años antiguos.

**BLOQUEADOR:** VPS vps-vrix se reportó OFFLINE por conexión Remote Desktop Commander; MT5 autenticado no accesible, sin snapshot. No existen seis especificaciones verificadas, ni 3368 fills certificados. Programar verificación del servidor cuando esté conectado, sin que el usuario tenga que facilitar contraseñas.

## 5. PUNTO EXACTO PARA EL SIGUIENTE ARQUITECTO (ORDEN DE TRABAJO)

**P0.1 — REPLAY DINÁMICO:** extender Trader Lab para utilizar el **5% causal por cada decisión**, con capital/timestamps/SL/fees/volume_step actuales (y min(balance,equity) no leaky), no usar $3 constantes ni porcentajes congelados al inicio. Ejecución de 3 años con exactamente 3368 SEÑALES, snapshots de wallet y cálculo de márgenes en cada orden. Si el mínimo no es financiable, conservar señal UNFILLED, cero PNL ficticio. Registrar causa explícita: lote mínimo, coste, margen, banco, DD, concentración, stop-out, no datos MT5. Deben reportarse tanto señales como fills e incl. universo de no financiables.
**P0.2 — MT5 BROKER SOURCE:** verificar VPS, ejecutar probe de solo lectura, recuperar seis especificaciones, tarifas, cuenta Stellar Instant, símbolo NAS100↔NDX100, margen. No certificar nada antes.
**P0.3 — ATOMIC AND RESTART:** reserva durable y reconstrucción tras reinicio; reemplazar broker_execution_proven boolean por comprobación transacción / ticket en MT5; reconciliar partial fills, order rejects, SL/TP y cambios precio; impedir doble gasto de órdenes concurrentes/abiertas históricas.
**P0.4 — RENTABILIDAD CAUSAL:** recomputar PnL y pérdidas para lotes reales a SL/TP y lifecycle, a 1/3/6/12 meses y tres años, capital inicial $60, reinversión acumulada, balance/equity/DD desde máximos, margen, profit factor, pérdida bruta por símbolo/trader/estilo, correlaciones y riesgo de stop-out, no solo suma de liquidaciones post-facto.
**P0.5 — CORRECCIONES DE SOLVENCIA:** reparar H8 mandatory 1x y bank negativo; reinversión de beneficios realizados, buffer sin sobrerreservas, no filtrar señales arbitrariamente.
**P0.6 — BATERÍA CIENTÍFICA:** 3y holdout y OOS fresco, shock de slippage/fees, seis símbolos BUY/SELL, cash collapse, concurrent fills, tiempos causales y reconciliación. Conservar cambios solo si strict Pareto y solvencia reales; DD ideal <=20%, tolerado <=25%, maximizar techo REALMENTE financiado.

## 6. ACEPTACIÓN P0: QUÉ ESTÁ LISTO Y QUÉ FALTA

LISTO EN INVESTIGACIÓN:
- Implementación programática motor unificado MT5, Sizing, CIBO Compound, Portfolio Compound, Adaptive Leverage en una única billetera; 5% dinámico confirmado por tests para $60/$100/$1000, crecimiento y pérdidas.
- Búsqueda del lote mayor legal compatible con stop + comisión + costes adversos, margen libre y límites globales.
- Interfaces de trader-presend, idempotencia en proceso y trazas por motor.
- 50/50 unit/integration tests CI SUCCESS en rama actual.
- Preauditoría antigua 3368 señales con $3 FIJOS, SOLO REFERENCIA.

NO LISTO / CRÍTICO:
- Fuente MT5 de seis instrumentos, autenticada por proveedor — NO.
- Persistencia de reservas con reinicio, conciliación de todos los tickets existentes — NO.
- Integración de pre-send en broker gateway real / fill receipts certificados — NO.
- Replay completo de 3368 SEÑALES con 5% dinámico y verdadera cuenta/broker, PnL, DD — NO.
- Ganancias de $670k certificadas; nuevo techo productivo — NO.
- Banco sin insolvencia en un replay físicamente ejecutable — NO CERTIFICADO.
- DD <=25% y batería científica OOS — NO.

**RELEASE: NO GO para producción. No mezclar los porcentajes con lotes, contratos o multiplicadores. REGLA VIGENTE: 5% DINÁMICO POR NUEVA ENTRADA.**

## 7. COMANDO DE CONTINUIDAD

Abrir mezas3238-hue/qore-core @ agent/cibo-p0-dynamic-equity-5pct-lotage-002 y leer ESTE handoff antes del código. Continuar desde CI 37814146300, luego lanzar el replay físico/casual 3y para 3368 señales con 5% por entrada (no USD3 fijo) y comparar contra los laboratorios de solvencia. No tocar ramas de otros arquitectos; integrar cuando certifique. Evitar prometer resultados hasta ver logs y artefactos reales en GitHub.
