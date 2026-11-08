"""Checks for non-numeric claims in the documents, using the csvs in 8. 槓桿DCA實證_佐證/.

  * every drawdown of 20%+ in each Date,AdjClose csv: peak, trough, depth, time to recover the peak
  * VT vs SPY: correlation of daily / monthly returns, annualised return over the common period
  * 13-week T-bill (irx): lowest 2020 and highest 2023 yield

Example:
  python claims_check.py --dir "../8. 槓桿DCA實證_佐證" --out claims.txt
"""
import argparse
import os
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--dir", required=True, help="folder holding vt.csv, spy.csv, n225.csv, spx_tr_monthly.csv, irx.csv")
p.add_argument("--out", required=True)
p.add_argument("--min-dd", type=float, default=0.20)
a = p.parse_args()


def load(name):
    df = pd.read_csv(os.path.join(a.dir, name))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["AdjClose"]


L = []
for name in ("spx_tr_monthly.csv", "spy.csv", "vt.csv", "n225.csv"):
    s = load(name)
    L.append(f"--- {name} {s.index[0].date()}..{s.index[-1].date()}: drawdowns of {a.min_dd:.0%}+ ---")
    peak_val, peak_dt, trough_val, trough_dt = s.iloc[0], s.index[0], s.iloc[0], s.index[0]
    for dt, v in s.items():
        if v >= peak_val:
            if trough_val / peak_val - 1 <= -a.min_dd:
                L.append(f"  peak {peak_dt.date()} trough {trough_dt.date()} depth {trough_val / peak_val - 1:.1%} "
                         f"recovered {dt.date()} ({(dt - peak_dt).days / 365.25:.1f} yr after peak)")
            peak_val, peak_dt, trough_val, trough_dt = v, dt, v, dt
        elif v < trough_val:
            trough_val, trough_dt = v, dt
    if trough_val / peak_val - 1 <= -a.min_dd:
        L.append(f"  peak {peak_dt.date()} trough {trough_dt.date()} depth {trough_val / peak_val - 1:.1%} "
                 f"NOT recovered by {s.index[-1].date()} ({(s.index[-1] - peak_dt).days / 365.25:.1f} yr so far)")

vt, spy = load("vt.csv"), load("spy.csv")
both = pd.concat([vt.rename("vt"), spy.rename("spy")], axis=1, join="inner").dropna()
daily = both.pct_change().dropna()
monthly = both.resample("M").last().pct_change().dropna()
yrs = (both.index[-1] - both.index[0]).days / 365.25
ann = (both.iloc[-1] / both.iloc[0]) ** (1 / yrs) - 1
L.append(f"--- VT vs SPY {both.index[0].date()}..{both.index[-1].date()} ---")
L.append(f"  correlation daily {daily.corr().iloc[0, 1]:.3f}, monthly {monthly.corr().iloc[0, 1]:.3f}")
L.append(f"  annualised total return VT {ann['vt']:.2%}, SPY {ann['spy']:.2%}")

irx = load("irx.csv")
L.append("--- 13-week T-bill yield (irx, %) ---")
for y, f in ((2020, "min"), (2023, "max")):
    x = irx[irx.index.year == y]
    L.append(f"  {y} {f}: {getattr(x, f)():.2f} on {getattr(x, 'idx' + f)().date()}")

txt = "\n".join(L)
with open(a.out, "w", encoding="utf-8") as fh:
    fh.write(txt + "\n")
print(txt)
