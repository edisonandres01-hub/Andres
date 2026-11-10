# Dónde validar cada chequeo

Salen de la hoja **IPG fundamental** del Power Pack, del resumen del Factor X7 (lección 14) y de las lecciones de gráfico en Interactive Brokers. El corto no usa las tres primeras filas.

| Chequeo | Dónde se abre | Qué tiene que cumplirse |
| --- | --- | --- |
| EPS trimestral y anual | [Nasdaq, resultados](https://www.nasdaq.com/market-activity/stocks/aapl/earnings) | Trimestre contra el mismo trimestre del año anterior, mayor a 15% (mejor si pasa de 30%). Año contra año, mayor a 25% (mejor si pasa de 50%). |
| Oferta/demanda y volumen de 3 meses | [Yahoo Key Statistics](https://finance.yahoo.com/quote/AAPL/key-statistics?p=AAPL) | Shares outstanding y average volume. El ratio es acciones en circulación / volumen promedio. Más pequeño es mejor. El día de la señal, el volumen supera ese promedio. |
| Propiedad institucional | [Yahoo Holders](https://finance.yahoo.com/quote/AAPL/holders?p=AAPL) | Mayor a 50% y menor a 90%. |
| Líderes y productos | No hay página en el curso | Lo confirmas tú. |
| Tendencia, medias, RSI y volumen | [Interactive Brokers](https://www.interactivebrokers.com/sso/Login) | Gráfico diario de la acción y de SPY. Largo: ambos alcistas unos 3 meses, SMA 5 cruza sobre SMA 10, RSI menor a 70. Corto: ambos bajistas, SMA 10 cruza sobre SMA 5, RSI mayor a 30. |
| Pivotes diarios y semanales | El gráfico en Interactive Brokers, con el indicador Pivot Points, y el [histórico de Yahoo](https://finance.yahoo.com/quote/AAPL/history?p=AAPL) | P = (H + L + C) / 3, con el día anterior y otra vez con la semana anterior. R1 = (P x 2) - L. R2 = P + (H - L). S1 = (P x 2) - H. S2 = P - (H - L). El stop y el objetivo se apoyan en esos niveles. |
| Smart Picks largos | [Finviz, sin sector fijo](https://finviz.com/screener.ashx?v=111&f=fa_epsqoq_o15,fa_epsyoy_o25,sh_avgvol_o200,sh_instown_o50,ta_beta_o0.5,ta_sma20_sa50,ta_sma200_sb50,ta_sma50_sa200&ft=4) | EPS trimestral over 15%, EPS de este año over 25%, volumen over 200K, institucional over 50%, beta over 0.5, SMA20 sobre SMA50 y SMA50 sobre SMA200. El video agregó `sec_technology` porque ese día el sector líder era Technology. |
| Smart Picks cortos | [Finviz, ordenado por volumen](https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o200,sh_instown_o50,ta_beta_o0.5,ta_sma20_sb50,ta_sma200_sa50,ta_sma50_sb200&ft=4&o=-volume) | Volumen over 200K, institucional over 50%, beta over 0.5 y las medias al revés. Sin EPS y sin sector. |
| Sector líder | [Sector Tracker](https://www.sectorspdrs.com/sectortracker) | El sector que se agrega al filtro de largos. La tabla Sectores Ferrari de la lección 36 es un ejemplo de esa clase, no una lista permanente. |
| GAP de SPY | [Histórico de SPY](https://finance.yahoo.com/quote/SPY/history?p=SPY) y el gráfico de SPY en Interactive Brokers | Apertura de hoy contra el cierre de ayer. Hueco arriba: corto. Hueco abajo: largo. Probabilidad mayor a 70% y hueco entre 20% y 40% del rango de ayer. |
| Precio de la opción | [Cadena de Yahoo](https://finance.yahoo.com/quote/AAPL/options?p=AAPL). El video abre `finance.yahoo.com/quote/MSFT/options` y elige la fecha en el menú. | Se compra el call en un largo y el put en un corto. La pérdida de esa compra es la prima. La venta se explica en la lección 34 y no se simula. Los ejemplos de la lección 35: acción 525, call de junio strike 600 a 1.10; acción 354, call de junio strike 400 a 1.05. |
| Análisis de operaciones | El diario `data/journal.csv` y la [red privada](https://inviertaparaganar.ning.com/) | Lección 27: últimos 30 días, entrar con la señal, salir en stop u objetivo, y expectativas 60-40, 50-50 o 40-60. El comando es `analisis`. |
| 10 mandamientos | Lección 36, dentro del [curso](https://inviertaparaganar.mykajabi.com/products/tradercoach-4-vip-platinum) | SPY a 12 y 3 meses, dirección, sectores, primero las operaciones abiertas, diario y plan. `analisis` los imprime. |
| Fórmulas del Power Pack | [Curso TraderCoach 4](https://inviertaparaganar.mykajabi.com/products/tradercoach-4-vip-platinum) | Archivo `Power_Pack_Invierta_Para_Ganar_para_alumnos.xls`, hojas IPG fundamental, Admon. capital y GAP. |
| Comentario de la práctica | [Red privada](https://inviertaparaganar.ning.com/) | Ejercicio de la lección 14. No cambia la señal. |

La hoja escribe el EPS como `www.nasdaq.com/symbol/TICKER/revenue-eps`. Esa ruta ya no responde. El acceso que abre es la página actual de resultados de Nasdaq, cambiando `aapl` por el símbolo en minúsculas.

Para otro símbolo:

```powershell
py -3 -m tradercoach.cli fuentes MSFT --abrir
```

Eso crea `data/accesos-MSFT.html` y lo abre en el navegador, con el símbolo ya puesto en cada enlace.
