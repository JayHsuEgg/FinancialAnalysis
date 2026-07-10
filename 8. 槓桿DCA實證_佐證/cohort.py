"""
Cohort robustness: start the strategy DCA at many rolling start dates,
run each to the data end, compare strategy vs baseline (pure prototype DCA).
Reports win rate and median edge across cohorts -> guards against
"single lucky start date" survivorship bias.

Tests the RECOMMENDED-zone configs only (to stay focused):
  recover 80% vs 100%, trigger -30%, lev 2x and 3x.
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
    df = pd.read_csv(path); df["Date"]=pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose":"u"})
    if fixrate is not None:
        df["irx"]=fixrate
    else:
        df["irx"]=get_irx().reindex(df.index, method="ffill").fillna(4.0)/100.0
    per = 252.0 if freq=="daily" else 12.0
    df["r_u"]=df["u"].pct_change()
    df["r_l"]=lev*df["r_u"]-(exp+(lev-1.0)*df["irx"]+calib)/per
    df=df.dropna(subset=["r_u","r_l"]).copy()
    df["L_u"]=(1+df["r_u"]).cumprod()
    df["L_l"]=(1+df["r_l"]).cumprod()
    df["ath"]=df["u"].cummax(); df["dd"]=df["u"]/df["ath"]-1.0
    return df

def run_from(df, start, trigger, recover, freq):
    sub = df[df.index>=start]
    if len(sub) < (60 if freq=="daily" else 24):
        return None
    idx = sub.index
    if freq=="daily":
        months=pd.date_range(idx[0],idx[-1],freq="MS")
        buyset=set(idx[idx.get_indexer([m],method="nearest")[0]] for m in months)
    else:
        buyset=set(idx)
    Lu=sub["L_u"]; Ll=sub["L_l"]
    # recompute ath/dd RELATIVE to this cohort's own start (peak resets at entry)
    run_peak=-1e9; state="NORMAL"; proto=lev_u=base=inv=0.0; lev_cash=0.0
    px=sub["u"]
    for dt,row in sub.iterrows():
        run_peak=max(run_peak,row["u"]); dd=row["u"]/run_peak-1.0
        if state=="NORMAL" and dd<=-trigger:
            state="LEVERAGED"
        elif state=="LEVERAGED" and row["u"]>=recover*run_peak:
            state="NORMAL"
        if dt in buyset:
            inv+=1.0; base+=1.0/Lu.loc[dt]
            if state=="LEVERAGED": lev_u+=1.0/Ll.loc[dt]; lev_cash+=1.0
            else: proto+=1.0/Lu.loc[dt]
    T=idx[-1]
    strat=proto*Lu.loc[T]+lev_u*Ll.loc[T]; bse=base*Lu.loc[T]
    return dict(edge=(strat/bse-1)*100, levpct=lev_cash/inv*100)

MARKETS=[
    ("VT 全球",        r"C:\tmp\inv\vt.csv",            "daily",  None),
    ("S&P 1970",       r"C:\tmp\inv\spy.csv",           "daily",  None),
    ("S&P 1927(月)",   r"C:\tmp\inv\spx_tr_monthly.csv","monthly",None),
    ("日經 ZIRP",      r"C:\tmp\inv\n225.csv",          "daily",  0.005),
]
CALIB={2:0.0065,3:0.012}
CONFIGS=[(2,0.30,0.80),(2,0.30,1.00),(3,0.30,0.80),(3,0.30,1.00)]

L=[]
L.append("COHORT ROBUSTNESS: rolling start dates (every 12 months), trigger -30%")
L.append("win = strategy beats pure-prototype DCA at that cohort's horizon\n")
for mname,path,freq,fr in MARKETS:
    L.append(f"################ {mname} ({freq}) ################")
    L.append(f"{'cfg':>14} | {'cohorts':>7} | {'winrate':>7} | {'edge med':>9} {'edge p25':>9} {'edge p75':>9} | {'lev$% med':>9}")
    for lev,tr,rc in CONFIGS:
        df=prep(path,lev,CALIB[lev],freq,fr)
        starts=pd.date_range(df.index[0],df.index[-1],freq="12MS")
        res=[run_from(df,s,tr,rc,freq) for s in starts]
        res=[r for r in res if r]
        if not res:
            L.append(f"  {lev}x rec{int(rc*100)}% | no cohorts"); continue
        edges=np.array([r["edge"] for r in res]); levp=np.array([r["levpct"] for r in res])
        wr=(edges>0).mean()*100
        L.append(f"  {lev}x t30 r{int(rc*100):>3} | {len(res):>7} | {wr:>6.1f}% | "
                 f"{np.median(edges):>+8.1f}% {np.percentile(edges,25):>+8.1f}% {np.percentile(edges,75):>+8.1f}% | {np.median(levp):>7.1f}%")
    L.append("")
txt="\n".join(L)
with open(args.out,"w",encoding="utf-8") as f: f.write(txt)
print(txt)
