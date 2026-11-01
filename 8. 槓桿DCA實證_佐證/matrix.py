"""
Full matrix backtest of the deep-drawdown DCA-into-leverage strategy.
Markets x leverage x trigger x recover.  Outputs one comparison table.

Key columns:
  switches      : times strategy flipped into leverage
  lev$%         : share of total contributions that landed in the leveraged sleeve
                  (this is the REAL exposure; user's iron-rule cap is 10-15%)
  strat x       : strategy terminal multiple on invested cash
  base x        : baseline = 100% prototype DCA
  edge          : strategy vs baseline
"""
import argparse, sys
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding="utf-8")

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
args = p.parse_args()

IRX = None
def get_irx():
    global IRX
    if IRX is None:
        d = pd.read_csv(r"C:\tmp\inv\irx.csv"); d["Date"] = pd.to_datetime(d["Date"])
        IRX = d.set_index("Date")["AdjClose"]
    return IRX

def load(path):
    df = pd.read_csv(path); df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose": "u"})

def sim(path, lev, calib, trigger, recover, freq, fixrate=None, exp=0.0091):
    u = load(path)
    if fixrate is not None:
        u["irx"] = fixrate
    else:
        irx = get_irx().reindex(u.index, method="ffill")/100.0
        u["irx"] = irx.fillna(0.04)
    per = 252.0 if freq == "daily" else 12.0
    u["r_u"] = u["u"].pct_change()
    u["r_l"] = lev*u["r_u"] - (exp + (lev-1.0)*u["irx"] + calib)/per
    df = u.dropna(subset=["r_u", "r_l"]).copy()
    df["L_u"] = (1+df["r_u"]).cumprod()
    df["L_l"] = (1+df["r_l"]).cumprod()
    df["ath"] = df["u"].cummax()
    df["dd"]  = df["u"]/df["ath"] - 1.0
    idx = df.index
    if freq == "daily":
        months = pd.date_range(idx[0], idx[-1], freq="MS")
        buyset = set(idx[idx.get_indexer([m], method="nearest")[0]] for m in months)
    else:
        buyset = set(idx)
    Lu = df["L_u"]; Ll = df["L_l"]
    state = "NORMAL"; proto=lev_u=base=inv=0.0; lev_cash=0.0; sw=0
    for dt, row in df.iterrows():
        if state == "NORMAL" and row["dd"] <= -trigger:
            state = "LEVERAGED"; sw += 1
        elif state == "LEVERAGED" and row["u"] >= recover*row["ath"]:
            state = "NORMAL"
        if dt in buyset:
            inv += 1.0
            base += 1.0/Lu.loc[dt]
            if state == "LEVERAGED":
                lev_u += 1.0/Ll.loc[dt]; lev_cash += 1.0
            else:
                proto += 1.0/Lu.loc[dt]
    T = idx[-1]
    strat = proto*Lu.loc[T] + lev_u*Ll.loc[T]
    bse = base*Lu.loc[T]
    return dict(sw=sw, levpct=lev_cash/inv*100, strat_x=strat/inv, base_x=bse/inv,
                edge=(strat/bse-1)*100, yrs=(T-idx[0]).days/365.25,
                start=idx[0].date(), end=T.date())

MARKETS = [
    ("VT 全球",        r"C:\tmp\inv\vt.csv",            "daily",  None),
    ("S&P 1970",       r"C:\tmp\inv\spy.csv",           "daily",  None),
    ("S&P 1927長史(月)", r"C:\tmp\inv\spx_tr_monthly.csv","monthly",None),
    ("日經 ZIRP",      r"C:\tmp\inv\n225.csv",          "daily",  0.005),
]
CALIB = {2: 0.0065, 3: 0.012}
TRIGGERS = [0.20, 0.30, 0.40, 0.50]
RECOVERS = [0.80, 1.00]
LEVS = [2, 3]

L = []
for mname, path, freq, fr in MARKETS:
    L.append(f"\n################ {mname}  ({freq}) ################")
    L.append(f"{'lev':>3} {'trig':>5} {'rec':>4} | {'sw':>3} {'lev$%':>6} | {'strat':>7} {'base':>7} | {'edge':>8}")
    L.append("-"*60)
    for lev in LEVS:
        for tr in TRIGGERS:
            for rc in RECOVERS:
                try:
                    r = sim(path, lev, CALIB[lev], tr, rc, freq, fixrate=fr)
                    L.append(f"{lev:>2}x {int(tr*100):>4}% {int(rc*100):>3}% | {r['sw']:>3} {r['levpct']:>5.1f}% | "
                             f"{r['strat_x']:>6.2f}x {r['base_x']:>6.2f}x | {r['edge']:>+7.1f}%")
                except Exception as e:
                    L.append(f"{lev:>2}x {int(tr*100):>4}% {int(rc*100):>3}% | ERR {e}")
    # header line with period
    r0 = sim(path, 2, CALIB[2], 0.30, 1.00, freq, fixrate=fr)
    L.insert(L.index(f"\n################ {mname}  ({freq}) ################")+1,
             f"  period {r0['start']}..{r0['end']} ({r0['yrs']:.0f}y)")

txt = "\n".join(L)
with open(args.out, "w", encoding="utf-8") as f: f.write(txt)
print(txt)
