"""
Backtest of the leverage rule as actually written in files 0 and 1 (errata B2):

  * The portfolio keeps an SGOV "dry powder" bucket: each month's contribution of 1.0
    is split (1 - sgov_share) to the prototype index and sgov_share to SGOV
    (SGOV earns the 13-week T-bill yield).
  * SGOV tiers: when the index first falls -20% / -30% / -50% below its all-time high
    in a drawdown episode, one batch of SGOV goes into the 2x leveraged ETF
    (1/3, then 1/2 of what is left, then all of what is left = equal thirds).
    Tiers re-arm only after the index makes a new all-time high.
  * New-money switch (the rule tested in matrix.py / cap_test.py): while the index is
    at or below -30% from its high, the prototype part of each month's money buys the
    leveraged ETF instead, until the index recovers to 80% of the high.
    (-30% / 80% gives hysteresis; a -20% entry with an 80% exit would flip every day.)
  * Cash cap: cumulative cash sent to leverage (SGOV batches + new money) must stay
    <= cap x cumulative contributions. Whatever the cap blocks stays where it was
    (SGOV stays in SGOV; new money goes to the prototype).
  * Nothing is ever sold: no swap, no selling prototype for leverage.
  * Control D sends the same SGOV batches into the 1x prototype instead, to separate
    "spending idle cash in a crash" from "using 2x leverage for it" (B minus D).

Baseline = the same contributions and the same SGOV share, never using leverage.

Leveraged daily return: r_l = 2*r_u - (exp + irx + calib)/periods  (same engine as matrix.py).
All inputs/outputs via argparse; data csvs are read from this script's folder.
"""
import argparse, os, sys
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)) + os.sep  # data csvs live next to this script

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--exp", type=float, default=0.0091, help="leveraged ETF annual expense ratio (e.g. 0.0075)")
p.add_argument("--calib", type=float, default=0.0065, help="extra annual friction, 2x calibrated vs SSO")
p.add_argument("--sgov-share", type=float, default=0.10, help="share of each contribution sent to SGOV")
p.add_argument("--cap", type=float, default=0.10, help="cash cap as share of cumulative contributions")
p.add_argument("--no-cohorts", action="store_true", help="skip the rolling-cohort section")
args = p.parse_args()

IRX = None
def get_irx():
    global IRX
    if IRX is None:
        d = pd.read_csv(HERE + "irx.csv"); d["Date"] = pd.to_datetime(d["Date"])
        IRX = d.set_index("Date")["AdjClose"]
    return IRX

def prep(path, freq, fixrate):
    df = pd.read_csv(path); df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["AdjClose"]].rename(columns={"AdjClose": "u"})
    irx_real = get_irx().reindex(df.index, method="ffill").fillna(4.0) / 100.0
    df["fin"] = fixrate if fixrate is not None else irx_real   # leverage financing rate
    df["cash"] = irx_real                                       # SGOV yield (always the real T-bill)
    per = 252.0 if freq == "daily" else 12.0
    df["r_u"] = df["u"].pct_change()
    df["r_l"] = 2.0 * df["r_u"] - (args.exp + df["fin"] + args.calib) / per
    df["r_s"] = df["cash"] / per
    return df.dropna(subset=["r_u", "r_l"]).copy()

TIERS = (0.20, 0.30, 0.50)
FRACS = (1/3, 1/2, 1.0)

def run(sub, freq, use_tiers, use_newmoney, cap, tier_to_lev=True):
    idx = sub.index
    if freq == "daily":
        months = pd.date_range(idx[0], idx[-1], freq="MS")
        buyset = set(idx[idx.get_indexer([m], method="nearest")[0]] for m in months)
    else:
        buyset = set(idx)
    proto = lev = sgov = 0.0                  # market values
    b_proto = b_sgov = 0.0                    # baseline market values
    inv = lev_cash = 0.0
    peak = -np.inf; fired = set(); state = "NORMAL"
    n_fire = 0; max_lev_share = 0.0
    for dt, row in sub.iterrows():
        proto *= 1 + row["r_u"]; lev *= 1 + row["r_l"]; sgov *= 1 + row["r_s"]
        b_proto *= 1 + row["r_u"]; b_sgov *= 1 + row["r_s"]
        if row["u"] >= peak:
            peak = row["u"]; fired = set()
        dd = row["u"] / peak - 1.0
        if state == "NORMAL" and dd <= -0.30:
            state = "LEVERAGED"
        elif state == "LEVERAGED" and row["u"] >= 0.80 * peak:
            state = "NORMAL"
        if dt in buyset:
            inv += 1.0
            s_part = args.sgov_share; e_part = 1.0 - s_part
            sgov += s_part; b_sgov += s_part; b_proto += e_part
            room = (cap * inv - lev_cash) if cap is not None else np.inf
            if use_newmoney and state == "LEVERAGED" and room >= e_part:
                lev += e_part; lev_cash += e_part
            else:
                proto += e_part
        if use_tiers:
            for t, f in zip(TIERS, FRACS):
                if t not in fired and dd <= -t:
                    fired.add(t)
                    if tier_to_lev:
                        room = (cap * inv - lev_cash) if cap is not None else np.inf
                        amt = min(sgov * f, max(room, 0.0))
                        if amt > 0:
                            sgov -= amt; lev += amt; lev_cash += amt; n_fire += 1
                    else:  # control: same SGOV batches into the 1x prototype
                        amt = sgov * f
                        if amt > 0:
                            sgov -= amt; proto += amt; n_fire += 1
        tot = proto + lev + sgov
        if tot > 0:
            max_lev_share = max(max_lev_share, lev / tot)
    strat = proto + lev + sgov; base = b_proto + b_sgov
    return dict(strat_x=strat / inv, base_x=base / inv, edge=(strat / base - 1) * 100,
                cash_pct=lev_cash / inv * 100, end_pct=lev / strat * 100,
                max_pct=max_lev_share * 100, fires=n_fire)

MARKETS = [
    ("VT 全球 2008-", HERE + "vt.csv", "daily", None),
    ("S&P 1993-", HERE + "spy.csv", "daily", None),
    ("日經 1970-(融資 0.5%)", HERE + "n225.csv", "daily", 0.005),
    ("S&P 1927-(月頻)", HERE + "spx_tr_monthly.csv", "monthly", None),
]
CONFIGS = [  # (label, use_tiers, use_newmoney, tier_to_lev)
    ("A 已回測版:只改新錢(-30%/80%)", False, True, True),
    ("B 只用 SGOV 三段(買 2x)", True, False, True),
    ("C 實際規則:SGOV 三段 + 新錢", True, True, True),
    ("D 對照:SGOV 三段改買原型 1x", True, False, False),
]

L = [f"TIERED SGOV BACKTEST  exp={args.exp:.2%} calib={args.calib:.2%} sgov_share={args.sgov_share:.0%} cash cap={args.cap:.0%}",
     "edge = strategy vs baseline with the same SGOV share and no leverage",
     "cash% = cumulative cash into leverage / contributions; end% / max% = leverage market-value share at end / at worst\n"]
for mname, path, freq, fr in MARKETS:
    df = prep(path, freq, fr)
    L.append(f"################ {mname}  {df.index[0].date()}..{df.index[-1].date()} ################")
    L.append(f"{'config':<34} {'cap':>5} | {'cash%':>6} {'end%':>6} {'max%':>6} | {'strat':>9} {'base':>9} | {'edge':>8} | fires")
    for cname, ut, un, tl in CONFIGS:
        for cap in ((args.cap, None) if tl else (None,)):
            r = run(df, freq, ut, un, cap, tl)
            L.append(f"{cname:<34} {('%.0f%%' % (cap*100)) if cap else 'none':>5} | {r['cash_pct']:>5.1f}% {r['end_pct']:>5.1f}% {r['max_pct']:>5.1f}% | "
                     f"{r['strat_x']:>8.2f}x {r['base_x']:>8.2f}x | {r['edge']:>+7.1f}% | {r['fires']}")
    L.append("")

if not args.no_cohorts:
    L.append("ROLLING COHORTS (start every 12 months, run to data end), config C with cash cap")
    L.append(f"{'market':<26} | cohorts | win%  | edge med   p25    min    max | no-lev")
    for mname, path, freq, fr in MARKETS[:3]:
        df = prep(path, freq, fr)
        starts = pd.date_range(df.index[0], df.index[-1], freq="12MS")
        res = []
        for s in starts:
            sub = df[df.index >= s]
            if len(sub) < 60:
                continue
            res.append(run(sub, freq, True, True, args.cap))
        e = np.array([r["edge"] for r in res]); c = np.array([r["cash_pct"] for r in res])
        L.append(f"{mname:<26} | {len(res):>7} | {(e > 0).mean()*100:>4.0f}% | {np.median(e):>+7.1f}% {np.percentile(e, 25):>+6.1f}% {e.min():>+6.1f}% {e.max():>+6.1f}% | {int((c == 0).sum()):>6}")

txt = "\n".join(L)
with open(args.out, "w", encoding="utf-8") as f:
    f.write(txt + "\n")
print(txt)
