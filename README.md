# Bot T – Trend (paper trading, zdarma na GitHub Actions)

Bot z TikToku: trend following na BTC a ETH. Neobchoduje s penězi, jen to simuluje (paper) se startem $50.

- **Data:** Coinbase, veřejné API bez klíčů, hodinové svíčky
- **Vstup:** EMA20 překříží EMA50 nahoru a cena je nad EMA200
- **Výstup:** SL 2×ATR / TP 4×ATR (RR 1:2), nebo když EMA20 spadne pod EMA50
- **Běh:** GitHub Actions každých 15 min. Stav se ukládá do `state.json`.
- **Report:** každý BUY/SELL se pošle na Make webhook (secret `MAKE_WEBHOOK_URL`), tedy na FOMO floor.

## Co chodí na webhook

```json
{"bot":"Bot T – Trend","symbol":"BTC-USD","action":"BUY","price":83531.44,
 "sl":82531.63,"tp":85531.05,"reason":"...","equity":46.75,"start":50,"paper":true}
```

SELL navíc obsahuje `pnl` a `pnl_pct`.

## Backtest (BTC + ETH, 1h, leden až říjen 2026, start $50)

| Poplatek za stranu | Výsledek | Max DD | Buy & hold |
|---|---|---|---|
| 0,1 % (Binance/Bybit) | **−0,9 %** | 10,8 % | −16,6 % |
| 0,6 % (Coinbase taker) | −32 % | 32 % | −16,6 % |

Na 15m svíčkách to prodělávalo vždycky, proto bot běží na 1h. V padajícím trhu držel nulu a porazil držení, zisková strategie to ale (zatím) není. Před reálnými penězi nech běžet paper aspoň 1–2 měsíce.

Toto není finanční poradenství, jde o experiment.
