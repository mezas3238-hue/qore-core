# QORE Native — adjudicación final de autenticación DEMO (doble comprobación)

**11-oct-2026.** [PR #800](https://github.com/mezas3238-hue/qore-core/pull/800). **No se descargaron barras históricas EURJPY/USDCHF.**

Intento 1: [Actions #38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086), commit `c5854f6c5e18b4e5bde52b82eea4d5e1349adef3`. Tests calidad SUCCESS, jobs EURJPY y USDCHF FAILURE: `CTraderDemoAccountDiscoveryError: cTrader access token invalid and refresh failed`. No se ejecutó `ProtoOAGetTrendbarsReq`.

Intento 2 (único fallback seguro): [Actions #38172295246](https://github.com/mezas3238-hue/qore-core/actions/runs/38172295246), commit `dc47805a8ec0eaa5a15d628250dd5e334ddf3584`. Se priorizaron `QORE_CTRADER_DEMO_*` sobre los `QORE_CTRADER_*` genéricos **sin exponer sus valores**. Tests calidad SUCCESS; jobs EURJPY y USDCHF FAILURE con **el mismo error**. La lectura histórica volvió a figurar SKIPPED. Esto descarta un rescate simple por prioridad de secret; **NO** demuestra por sí solo cuál de los dos grupos de secretos está configurado o cuál fue revocado.

**Acción necesaria que requiere dueño de OAuth:** reautorizar QORE Open API en cTrader ID sobre **cuenta DEMO**, privilegio `accounts` de solo lectura, generar NUEVO par access/refresh token por flujo oficial, depositarlo PRIVADAMENTE en GitHub Settings → Secrets and variables → Actions usando `QORE_CTRADER_DEMO_ACCESS_TOKEN` y `QORE_CTRADER_DEMO_REFRESH_TOKEN` (y client ID/secret de la misma aplicación cuando correspondan). No enviar secretos aquí ni subirlos a archivos GitHub. CTrader renueva/rota el par de tokens y puede invalidar tokens antiguos: https://help.ctrader.com/open-api/account-authentication/ .

Después de actualizar ambos secretos, el dueño puede rerun el workflow #38172295246, o solicitar al arquitecto GitHub volver a ejecutar esos jobs. **Una actualización de secrets no re-ejecuta automáticamente Actions**. La descarga sigue bloqueada hasta que la API autentique y proporcione manifiestos, raw M5 y SHA de ambos mercados.

**Estado:** `CREDENTIALS_REAUTH_REQUIRED`, `0_OF_2_MARKET_DATASETS_ACQUIRED`, `NO_SIGNALS`, `NO_EDGE`, `NO_PRODUCTION`, `NO_MT5`, `NO_LIVE`. El Atlas original de 12 mercados permanece intacto y es evidencia distinta.
