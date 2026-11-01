import argparse, csv, sys
sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("--inp", required=True)
p.add_argument("--out", required=True)
p.add_argument("--log", required=True)
p.add_argument("--start", default="1927-01-01", help="trim start date")
args = p.parse_args()

rows = list(csv.reader(open(args.inp, encoding="utf-8")))
hdr = rows[0]
di = hdr.index("Date"); pi = hdr.index("SP500"); divi = hdr.index("Dividend")

data = []
for r in rows[1:]:
    try:
        d = r[di]; px = float(r[pi]); dv = float(r[divi]) if r[divi] else 0.0
    except (ValueError, IndexError):
        continue
    data.append((d, px, dv))

# Build total-return index: monthly TR = (P_t + D_t/12) / P_{t-1}
# D is annualized dividend per share -> monthly cash = D/12
out = ["Date,AdjClose"]
tr = 1.0
prev_px = None
n = 0
log = open(args.log, "w", encoding="utf-8")
for d, px, dv in data:
    if d < args.start:
        prev_px = px
        continue
    if prev_px is None:
        prev_px = px
        out.append(f"{d},{tr:.6f}")
        n += 1
        continue
    monthly_ret = (px + dv / 12.0) / prev_px - 1.0
    tr *= (1.0 + monthly_ret)
    out.append(f"{d},{tr:.6f}")
    prev_px = px
    n += 1

with open(args.out, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
log.write(f"rows={n}\nfirst={out[1]}\nlast={out[-1]}\n")
log.close()
print(f"rows={n} first={out[1]} last={out[-1]}")
