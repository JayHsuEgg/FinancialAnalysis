"""Attempt to reconstruct the 'Nikkei -50% lump sum, hold to today' claim (1x 3.58x vs 2x 1.04x)."""
import argparse
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--n225", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()

df = pd.read_csv(a.n225)
df["Date"] = pd.to_datetime(df["Date"])
df = df.set_index("Date")
u = df["AdjClose"]
r_u = u.pct_change().dropna()
ath = u.cummax()
dd = u / ath - 1.0
lines = []
for lev, calib in ((2, 0.0065), (3, 0.012)):
    for thr in (0.30, 0.50):
        entry = dd[dd <= -thr].index[0]
        ru = r_u[r_u.index > entry]
        rl = lev * ru - (0.0091 + (lev - 1) * 0.005 + calib) / 252.0
        cu = (1 + ru).cumprod()
        cl = (1 + rl).cumprod()
        mdd_u = (cu / cu.cummax() - 1).min()
        mdd_l = (cl / cl.cummax() - 1).min()
        lines.append(f"lev={lev} entry dd<=-{thr:.0%} on {entry.date()} px={u[entry]:.0f}: "
                     f"1x final {cu.iloc[-1]:.2f}x (maxDD {mdd_u:.1%}) | {lev}x final {cl.iloc[-1]:.2f}x (maxDD {mdd_l:.1%}) | end {cu.index[-1].date()}")
# also: same but stop at an earlier end date, in case the claim was produced on older data
for end in ("2024-12-31", "2025-06-30"):
    entry = dd[dd <= -0.5].index[0]
    ru = r_u[(r_u.index > entry) & (r_u.index <= end)]
    rl = 2 * ru - (0.0091 + 0.005 + 0.0065) / 252.0
    lines.append(f"2x entry {entry.date()} end {end}: 1x {(1+ru).prod():.2f}x  2x {(1+rl).prod():.2f}x")
txt = "\n".join(lines)
with open(a.out, "w", encoding="utf-8") as f:
    f.write(txt)
print(txt)
