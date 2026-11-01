"""
Hard-cap circuit-breaker test for the deep-drawdown DCA-into-leverage strategy.

The earlier matrix.py only had a state machine deciding WHERE new money goes
(prototype vs leveraged). It had NO enforcement of iron-rule #4 (leverage sleeve
capped at 10-15% of total). This script adds that cap and measures:

  1. Does the cap actually keep leverage exposure <= cap on the WORST single path
     (Nikkei from 1970, which sits on the 1989 bubble top)?
  2. How much terminal return do you give up to stay disciplined?

Cap definition: before buying leverage with this month's money, check the leverage
sleeve's CURRENT MARKET VALUE as a share of the WHOLE portfolio's market value.
If it is already >= cap, this month's money goes to prototype instead (circuit
breaker tripped). This is mark-to-market, the honest version of "<=10-15% of total".
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

def prep(path, lev, calib, freq, fixrate, exp=0.0091):
    df = pd.read_csv(path); df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose": "u"})
    if fixrate is not None:
        df["irx"] = fixrate
    else:
        df["irx"] = get_irx().reindex(df.index, method="ffill").fillna(4.0)/100.0
    per = 252.0 if freq == "daily" else 12.0
    df["r_u"] = df["u"].pct_change()
    df["r_l"] = lev*df["r_u"] - (exp + (lev-1.0)*df["irx"] + calib)/per
    df = df.dropna(subset=["r_u", "r_l"]).copy()
    df["L_u"] = (1+df["r_u"]).cumprod()
    df["L_l"] = (1+df["r_l"]).cumprod()
    df["ath"] = df["u"].cummax(); df["dd"] = df["u"]/df["ath"] - 1.0
    return df

def run(df, trigger, recover, freq, cap=None, captype="mkt"):
    """cap = None -> no circuit breaker (old behavior).
       captype="mkt"  -> leverage sleeve MKT VALUE held <= cap of total portfolio value.
       captype="cash" -> cumulative CASH sent to leverage <= cap of cumulative total invested."""
    idx = df.index
    if freq == "daily":
        months = pd.date_range(idx[0], idx[-1], freq="MS")
        buyset = set(idx[idx.get_indexer([m], method="nearest")[0]] for m in months)
    else:
        buyset = set(idx)
    Lu = df["L_u"]; Ll = df["L_l"]
    state = "NORMAL"
    proto_u = lev_u = base_u = 0.0
    inv = 0.0; lev_cash = 0.0; tripped = 0
    for dt, row in df.iterrows():
        if state == "NORMAL" and row["dd"] <= -trigger:
            state = "LEVERAGED"
        elif state == "LEVERAGED" and row["u"] >= recover*row["ath"]:
            state = "NORMAL"
        if dt in buyset:
            inv += 1.0
            base_u += 1.0/Lu.loc[dt]
            want_lev = (state == "LEVERAGED")
            if want_lev and cap is not None:
                if captype == "mkt":
                    lev_val = lev_u*Ll.loc[dt]
                    tot_val = proto_u*Lu.loc[dt] + lev_val
                    if tot_val > 0 and lev_val/tot_val >= cap:
                        want_lev = False; tripped += 1
                else:  # cash
                    if (lev_cash + 1.0)/inv > cap:
                        want_lev = False; tripped += 1
            if want_lev:
                lev_u += 1.0/Ll.loc[dt]; lev_cash += 1.0
            else:
                proto_u += 1.0/Lu.loc[dt]
    T = idx[-1]
    lev_val = lev_u*Ll.loc[T]; proto_val = proto_u*Lu.loc[T]
    strat = proto_val + lev_val; base = base_u*Lu.loc[T]
    return dict(
        cash_pct=lev_cash/inv*100,                 # cash share that went to leverage
        end_pct=lev_val/strat*100 if strat>0 else 0,  # terminal mkt-value share in leverage
        strat_x=strat/inv, base_x=base/inv,
        edge=(strat/base-1)*100, tripped=tripped)

MARKETS = [
    ("VT 全球",      r"C:\tmp\inv\vt.csv",            "daily",  None),
    ("S&P 1970",     r"C:\tmp\inv\spy.csv",           "daily",  None),
    ("日經 1970",    r"C:\tmp\inv\n225.csv",          "daily",  0.005),
]
CALIB = {2: 0.0065, 3: 0.012}

L = []
L.append("HARD-CAP CIRCUIT BREAKER TEST  (trigger -30%, recover 80%)")
L.append("mkt cap  = leverage sleeve MKT VALUE  held <= X% of total portfolio value")
L.append("cash cap = cumulative CASH to leverage held <= X% of total invested")
L.append("cash% = share of contributions sent to leverage | end% = terminal mkt-value share in leverage\n")
for mname, path, freq, fr in MARKETS:
    L.append(f"################ {mname} ({freq}) ################")
    L.append(f"{'cfg':>26} | {'cash%':>6} {'end%':>6} | {'strat':>7} {'base':>7} | {'edge':>8} | {'trips':>5}")
    L.append("-"*82)
    for lev in (2, 3):
        df = prep(path, lev, CALIB[lev], freq, fr)
        configs = [(None, "mkt", "no cap"),
                   (0.10, "mkt", "mkt cap 10%"),
                   (0.15, "cash", "cash cap 15%"),
                   (0.10, "cash", "cash cap 10%")]
        for cap, ct, capname in configs:
            r = run(df, 0.30, 0.80, freq, cap=cap, captype=ct)
            L.append(f"  {lev}x t30 r80 {capname:>13} | {r['cash_pct']:>5.1f}% {r['end_pct']:>5.1f}% | "
                     f"{r['strat_x']:>6.2f}x {r['base_x']:>6.2f}x | {r['edge']:>+7.1f}% | {r['tripped']:>5}")
    L.append("")
txt = "\n".join(L)
with open(args.out, "w", encoding="utf-8") as f: f.write(txt)
print(txt)
