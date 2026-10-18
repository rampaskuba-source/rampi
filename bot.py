"""Paper trading bot – spouští ho GitHub Actions každých 15 min.

Stáhne hodinové svíčky z Coinbase (veřejné API, bez klíčů), zpracuje nové uzavřené
svíčky, uloží stav do state.json a obchody pošle na Make webhook (FOMO floor).
"""
import json, os, time, datetime as dt
import requests
import strategy as S

SYMBOLS = os.getenv("SYMBOLS", "BTC-USD,ETH-USD").split(",")
START_BALANCE = float(os.getenv("START_BALANCE", "50"))
WEBHOOK = os.getenv("MAKE_WEBHOOK_URL", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "Bot T – Trend")
GRAN = 3600  # 1h svíčky (15m v backtestu prodělávaly)
STATE_FILE = "state.json"


def fetch(sym, pages=3):
    """~900 hodinových svíček (3 × 300), aby se EMA200 ustálila."""
    rows, end = {}, int(time.time())
    for _ in range(pages):
        start = end - 300 * GRAN
        iso = lambda x: dt.datetime.fromtimestamp(x, dt.timezone.utc).isoformat()
        r = requests.get(f"https://api.exchange.coinbase.com/products/{sym}/candles",
                         params={"granularity": GRAN, "start": iso(start), "end": iso(end)},
                         timeout=20, headers={"User-Agent": "trend-bot"})
        r.raise_for_status()
        for x in r.json():
            rows[x[0]] = x
        end = start
        time.sleep(0.3)
    rows = sorted(rows.values())                  # [t, low, high, open, close, vol]
    c = [[x[0], x[3], x[2], x[1], x[4], x[5]] for x in rows]   # -> [t, o, h, l, c, v]
    now = time.time()
    return [x for x in c if x[0] + GRAN <= now]  # jen uzavřené svíčky


def load():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"cash": START_BALANCE, "start": START_BALANCE, "positions": {}, "trades": [], "last": {}}


def send(payload):
    print(json.dumps(payload, ensure_ascii=False))
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json=payload, timeout=15)
        except Exception as e:
            print("webhook chyba:", e)


def main():
    st = load()
    prices = {}
    for sym in SYMBOLS:
        try:
            c = fetch(sym)
        except Exception as e:
            print(sym, "data chyba:", e); continue
        if len(c) < S.TREND + 5:
            print(sym, "málo dat"); continue
        ind = S.indicators(c)
        prices[sym] = c[-1][4]
        last = st["last"].get(sym, c[-2][0])      # první běh: jen poslední svíčka
        alloc = S.equity(st, {**{s: p["entry"] for s, p in st["positions"].items()}, **prices}) / len(SYMBOLS)
        for i in range(S.TREND, len(c)):
            if c[i][0] <= last:
                continue
            for ev in S.step(st, sym, c, i, ind, alloc):
                eq = S.equity(st, {**{s: p["entry"] for s, p in st["positions"].items()}, **prices})
                send({"bot": BOT_NAME, **ev,
                      "time": dt.datetime.fromtimestamp(ev["t"], dt.timezone.utc).isoformat(),
                      "equity": round(eq, 2), "start": st["start"], "paper": True})
        st["last"][sym] = c[-1][0]

    eq = S.equity(st, {**{s: p["entry"] for s, p in st["positions"].items()}, **prices})
    st["equity"] = round(eq, 2)
    st["updated"] = dt.datetime.now(dt.timezone.utc).isoformat()
    json.dump(st, open(STATE_FILE, "w"), indent=1, ensure_ascii=False)
    print(f"Equity ${eq:.2f} (start ${st['start']}), pozice: {list(st['positions'])}")


if __name__ == "__main__":
    main()
