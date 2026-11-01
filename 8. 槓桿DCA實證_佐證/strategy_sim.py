"""
Strategy simulator for "deep-drawdown DCA into leveraged ETF".

User's real strategy (NOT the old lump/one-shot backtests):
  - Always DCA a fixed amount each month.
  - State machine on the UNDERLYING drawdown vs running ATH:
      NORMAL    : new monthly money -> buy PROTOTYPE (1x underlying total return)
      LEVERAGED : new monthly money -> buy LEVERAGED ETF (2x/3x daily-reset, calibrated)
  - NORMAL -> LEVERAGED when drawdown <= -trigger.
  - LEVERAGED -> NORMAL when underlying recovers to >= recover * priorPeak.
  - Each sleeve (prototype units, leveraged units) accumulates and is HELD (B&H), never swapped.
  - Baseline = same DCA but ALWAYS into prototype (the thing the strategy must beat).

Frequency:
  - daily csv  -> month-start DCA mapped to nearest trading day.
  - monthly csv (Shiller) -> DCA every row; leverage modeled at monthly step with
    analytic vol-drag note (monthly understates daily-reset drag -> OPTIMISTIC for leverage).
"""
import argparse, sys
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding="utf-8")

p = argparse.ArgumentParser()
p.add_argument("--under", required=True, help="underlying total-return csv")
p.add_argument("--name", required=True)
p.add_argument("--lev", type=float, required=True)
p.add_argument("--exp", type=float, default=0.0091)
p.add_argument("--calib", type=float, required=True, help="2x:0.0065  3x:0.012")
p.add_argument("--trigger", type=float, required=True, help="entry drawdown, e.g. 0.30")
p.add_argument("--recover", type=float, required=True, help="exit threshold vs prior peak, e.g. 0.80 or 1.00")
p.add_argument("--fixrate", type=float, default=None, help="override financing rate (e.g. Japan ZIRP 0.005)")
p.add_argument("--freq", choices=["daily", "monthly"], default="daily")
p.add_argument("--out", required=True)
args = p.parse_args()

def load(path, col):
    df = pd.read_csv(path); df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose": col})

u = load(args.under, "u")
if args.fixrate is not None:
    u["irx"] = args.fixrate
else:
    irx = load(r"C:\tmp\inv\irx.csv", "irx")
    u = u.join(irx, how="left"); u["irx"] = u["irx"].ffill() / 100.0
    u["irx"] = u["irx"].fillna(0.04)  # pre-1954 / gaps: assume 4% short rate

per = 252.0 if args.freq == "daily" else 12.0
L = args.lev
df = u.copy()
df["r_u"] = df["u"].pct_change()
# leveraged daily/monthly return, calibrated
df["r_l"] = L*df["r_u"] - (args.exp + (L-1.0)*df["irx"] + args.calib)/per
df = df.dropna(subset=["r_u", "r_l"]).copy()

# continuous index levels for prototype (1x TR) and leveraged sleeve
df["L_u"] = (1+df["r_u"]).cumprod()
df["L_l"] = (1+df["r_l"]).cumprod()
df["ath"] = df["u"].cummax()
df["dd"]  = df["u"]/df["ath"] - 1.0

idx = df.index
# DCA schedule
if args.freq == "daily":
    months = pd.date_range(idx[0], idx[-1], freq="MS")
    buy_days = [idx[idx.get_indexer([m], method="nearest")[0]] for m in months]
    buy_days = sorted(set(buy_days))
else:
    buy_days = list(idx)

Lu = df["L_u"]; Ll = df["L_l"]; dd = df["dd"]; u_px = df["u"]; ath = df["ath"]

# state machine + DCA
state = "NORMAL"
proto_units = 0.0   # strategy prototype sleeve
lev_units   = 0.0   # strategy leveraged sleeve
base_units  = 0.0   # baseline: always prototype
invested = 0.0
months_in_lev = 0
switches = 0
buyset = set(buy_days)

for dt, row in df.iterrows():
    # update state on this bar (use today's dd / recovery)
    if state == "NORMAL" and row["dd"] <= -args.trigger:
        state = "LEVERAGED"; switches += 1
    elif state == "LEVERAGED" and row["u"] >= args.recover * row["ath"]:
        state = "NORMAL"
    if dt in buyset:
        invested += 1.0
        base_units += 1.0 / Lu.loc[dt]
        if state == "LEVERAGED":
            lev_units += 1.0 / Ll.loc[dt]
            months_in_lev += 1
        else:
            proto_units += 1.0 / Lu.loc[dt]

T = idx[-1]
strat_val = proto_units*Lu.loc[T] + lev_units*Ll.loc[T]
base_val  = base_units*Lu.loc[T]

# strategy portfolio path for max drawdown (mark-to-market of accumulated units is complex;
# report terminal stats + sleeve split which is what matters for the thesis)
out = []
yrs = (T - idx[0]).days/365.25
out.append(f"==== {args.name} | {L:.0f}x | trig -{int(args.trigger*100)}% | recover {int(args.recover*100)}% | {args.freq} ====")
out.append(f"period {idx[0].date()}..{T.date()} ({yrs:.1f}y)  | switches into leverage: {switches}  | months bought-in-lev: {months_in_lev}/{int(invested)}")
out.append(f"invested ${invested:.0f}")
out.append(f"  STRATEGY total: ${strat_val:7.1f}  ({strat_val/invested:.2f}x)   [proto ${proto_units*Lu.loc[T]:.1f} + lev ${lev_units*Ll.loc[T]:.1f}]")
out.append(f"  BASELINE 100% prototype DCA: ${base_val:7.1f}  ({base_val/invested:.2f}x)")
edge = (strat_val/base_val - 1)*100
out.append(f"  >>> STRATEGY vs BASELINE: {edge:+.1f}%   {'WIN' if edge>0 else 'LOSE'}")
txt = "\n".join(out)
with open(args.out, "w", encoding="utf-8") as f: f.write(txt)
print(txt)
