import argparse, sys
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
p = argparse.ArgumentParser()
p.add_argument("--under", required=True, help="underlying total-return csv (SPY)")
p.add_argument("--real", required=True, help="real LETF csv (SSO or UPRO)")
p.add_argument("--lev", type=float, required=True)
p.add_argument("--exp", type=float, required=True, help="LETF expense ratio (annual decimal)")
p.add_argument("--calib", type=float, default=0.0065, help="empirical extra drag")
p.add_argument("--name", required=True)
p.add_argument("--out", required=True)
args = p.parse_args()

def load(path, col):
    df = pd.read_csv(path); df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose": col})

u = load(args.under, "u")
real = load(args.real, "real")
irx = load(r"C:\tmp\inv\irx.csv", "irx")
df = u.join(real, how="inner").join(irx, how="left")
df["irx"] = df["irx"].ffill() / 100.0
df["r_u"] = df["u"].pct_change()
df["r_real"] = df["real"].pct_change()
df = df.dropna(subset=["r_u", "r_real"])

L = args.lev
df["r_model"] = L*df["r_u"] - (args.exp + (L-1.0)*df["irx"] + args.calib)/252.0
df["cum_real"]  = (1+df["r_real"]).cumprod()
df["cum_model"] = (1+df["r_model"]).cumprod()

corr = df["r_real"].corr(df["r_model"])
te = (df["r_real"] - df["r_model"]).std() * np.sqrt(252)
final_real = df["cum_real"].iloc[-1]; final_mdl = df["cum_model"].iloc[-1]
yrs = (df.index[-1]-df.index[0]).days/365.25

out = []
out.append(f"=== ENGINE VALIDATION: model {L:.0f}x vs real {args.name} (calib={args.calib*100:.2f}%) ===")
out.append(f"period: {df.index[0].date()} .. {df.index[-1].date()} ({yrs:.1f}y, {len(df)} days)")
out.append(f"daily-return correlation : {corr:.5f}")
out.append(f"annualized tracking error: {te*100:.2f}%")
out.append(f"total growth  real {args.name:5}: {final_real:.3f}x  (CAGR {(final_real**(1/yrs)-1)*100:.2f}%)")
out.append(f"total growth  model {L:.0f}x   : {final_mdl:.3f}x  (CAGR {(final_mdl**(1/yrs)-1)*100:.2f}%)")
out.append(f"final gap                : {(final_mdl/final_real-1)*100:+.1f}%")
txt = "\n".join(out)
with open(args.out, "w", encoding="utf-8") as f: f.write(txt)
print(txt)
