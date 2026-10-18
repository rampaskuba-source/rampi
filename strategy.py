"""Trend-following strategie (spot, jen LONG) – sdílená pro bota i backtest.

Vstup:  EMA20 překříží EMA50 nahoru  a  cena je nad EMA200 (hlavní trend nahoru)
Výstup: Stop-loss = vstup - SL_ATR * ATR
        Take-profit = vstup + TP_ATR * ATR
        nebo EMA20 spadne pod EMA50 (trend skončil)
"""

FAST, SLOW, TREND, ATR_LEN = 20, 50, 200, 14
SL_ATR, TP_ATR = 2.0, 4.0          # risk:reward 1:2
FEE = 0.001                        # 0,1 % za stranu (Binance/Bybit úroveň; Coinbase 0,6 % = ztrátové!)


def ema(values, n):
    k, out, e = 2 / (n + 1), [], None
    for v in values:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def atr(h, l, c, n=ATR_LEN):
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    out, a = [], None
    for v in tr:
        a = v if a is None else (a * (n - 1) + v) / n   # Wilder
        out.append(a)
    return out


def indicators(candles):
    """candles = list [t, o, h, l, c, v] seřazené od nejstarší."""
    h = [x[2] for x in candles]; l = [x[3] for x in candles]; c = [x[4] for x in candles]
    return ema(c, FAST), ema(c, SLOW), ema(c, TREND), atr(h, l, c)


def step(state, sym, candles, i, ind, alloc):
    """Zpracuje uzavřenou svíčku i. Vrací seznam událostí (obchodů)."""
    f, s, t, a = ind
    _, _, hi, lo, close, _ = candles[i]
    ts = candles[i][0]
    pos = state["positions"].get(sym)
    events = []

    if pos:
        exit_px, reason = None, None
        if lo <= pos["sl"]:
            exit_px, reason = pos["sl"], "stop-loss"
        elif hi >= pos["tp"]:
            exit_px, reason = pos["tp"], "take-profit"
        elif f[i] < s[i]:
            exit_px, reason = close, "trend skončil (EMA20 < EMA50)"
        if exit_px:
            proceeds = pos["qty"] * exit_px * (1 - FEE)
            pnl = proceeds - pos["cost"]
            state["cash"] += proceeds
            del state["positions"][sym]
            tr = {"t": ts, "symbol": sym, "action": "SELL", "price": round(exit_px, 2),
                  "qty": pos["qty"], "pnl": round(pnl, 2), "pnl_pct": round(pnl / pos["cost"] * 100, 2), "reason": reason}
            state["trades"].append(tr)
            events.append(tr)
        return events

    cross_up = f[i - 1] <= s[i - 1] and f[i] > s[i]
    if cross_up and close > t[i]:
        spend = min(state["cash"], alloc)
        if spend < 1:
            return events
        qty = spend * (1 - FEE) / close
        state["cash"] -= spend
        state["positions"][sym] = {"qty": qty, "entry": close, "cost": spend, "t": ts,
                                   "sl": close - SL_ATR * a[i], "tp": close + TP_ATR * a[i]}
        tr = {"t": ts, "symbol": sym, "action": "BUY", "price": round(close, 2), "qty": qty,
              "sl": round(close - SL_ATR * a[i], 2), "tp": round(close + TP_ATR * a[i], 2),
              "reason": "EMA20 překřížila EMA50 nahoru, cena nad EMA200"}
        state["trades"].append(tr)
        events.append(tr)
    return events


def equity(state, prices):
    return state["cash"] + sum(p["qty"] * prices[s] for s, p in state["positions"].items())
