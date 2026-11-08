import argparse, sys, time, json
import urllib.request
sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("--sym", required=True)
p.add_argument("--out", required=True)
p.add_argument("--log", required=True)
args = p.parse_args()

# full history daily
url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{args.sym}"
       f"?period1=0&period2=9999999999&interval=1d&events=div%2Csplit")
log = open(args.log, "w", encoding="utf-8")
log.write(f"URL: {url}\n")

data = None
for attempt in range(8):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", "replace")
        data = json.loads(raw)
        log.write(f"attempt {attempt}: OK {len(raw)} bytes\n")
        break
    except Exception as e:
        log.write(f"attempt {attempt}: {e.__class__.__name__} {e}\n")
        time.sleep(8 + attempt * 4)

if not data:
    log.write("FAILED\n"); log.close(); print("FAILED"); sys.exit(1)

res = data["chart"]["result"][0]
ts = res["timestamp"]
ind = res["indicators"]
adj = ind.get("adjclose", [{}])[0].get("adjclose")
close = ind["quote"][0]["close"]
use = adj if adj else close

import datetime
rows = ["Date,AdjClose"]
n = 0
for t, c in zip(ts, use):
    if c is None:
        continue
    d = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
    rows.append(f"{d},{c:.6f}")
    n += 1

with open(args.out, "w", encoding="utf-8") as f:
    f.write("\n".join(rows))

log.write(f"rows={n}\nfirst={rows[1]}\nlast={rows[-1]}\n")
log.close()
print(f"{args.sym}: rows={n} first={rows[1]} last={rows[-1]}")
