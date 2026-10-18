"""Backtest stejné logiky jako bot.py.
Použití: python backtest.py btc.json eth.json   (TradingView JSON export: bars.t/o/h/l/c/v)
"""
import json, sys
import strategy as S


def load(path):
    b = json.load(open(path))["bars"]
    return [[b["t"][i], b["o"][i], b["h"][i], b["l"][i], b["c"][i], b["v"][i]] for i in range(len(b["t"]))]


def run(files, start=50.0):
    data = {f: load(f) for f in files}
    ind = {f: S.indicators(c) for f, c in data.items()}
    st = {"cash": start, "positions": {}, "trades": []}
    n = min(len(c) for c in data.values())
    peak, maxdd = start, 0
    for i in range(S.TREND, n):
        prices = {f: data[f][i][4] for f in files}
        alloc = S.equity(st, prices) / len(files)
        for f in files:
            S.step(st, f, data[f], i, ind[f], alloc)
        eq = S.equity(st, prices)
        peak = max(peak, eq); maxdd = max(maxdd, (peak - eq) / peak)
    sells = [t for t in st["trades"] if t["action"] == "SELL"]
    wins = [t for t in sells if t["pnl"] > 0]
    final = S.equity(st, {f: data[f][n - 1][4] for f in files})
    hold = sum((data[f][n - 1][4] / data[f][S.TREND][4]) for f in files) / len(files) * start
    print(f"Obchodů: {len(sells)} | win rate: {len(wins) / max(1, len(sells)) * 100:.0f} %")
    print(f"Start ${start:.2f} -> konec ${final:.2f} ({(final / start - 1) * 100:+.1f} %) | max drawdown {maxdd * 100:.1f} %")
    print(f"Pro srovnání buy & hold: ${hold:.2f} ({(hold / start - 1) * 100:+.1f} %)")
    reasons = {}
    for t in sells:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    print("Důvody výstupu:", reasons)
    return final


if __name__ == "__main__":
    run(sys.argv[1:])
