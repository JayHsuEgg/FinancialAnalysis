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
  * Annual rebalance (--rebalance annual, the default since 2026-11-01): on the first
    trading day of each year, SGOV is brought back to sgov_share of (prototype + SGOV).
    The leveraged sleeve is excluded and never sold. The rebalance runs only while all
    three tiers are armed (none used since the last all-time high) and the new-money
    switch is off; after a tier has been used, SGOV is refilled by new money only, so
    no prototype is sold near a low to rebuild the dry powder.
    The baselines rebalance to the same weights every year.
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
p.add_argument("--leg-csv", help="use a REAL leveraged ETF's daily prices (csv in this folder, e.g. sso.csv) "
                                 "for the leveraged leg instead of the 2x model; triggers and prototype stay on --market")
p.add_argument("--leg-under", help="model the leveraged leg as 2x of ANOTHER index (csv in this folder, e.g. spy.csv) "
                                   "with --exp/--calib; triggers and prototype stay on --market")
p.add_argument("--market", choices=["all", "vt", "spy", "n225", "spx"], default="all")
p.add_argument("--rebalance", choices=["annual", "none"], default="annual",
               help="annual: yearly SGOV rebalance as described above; none: the pre-2026-11-01 runs")
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
    leg_path = args.leg_csv or args.leg_under
    if leg_path:
        leg = pd.read_csv(HERE + leg_path); leg["Date"] = pd.to_datetime(leg["Date"])
        df = df.join(leg.set_index("Date")["AdjClose"].rename("leg"), how="inner")
    df["r_u"] = df["u"].pct_change()
    if args.leg_csv:
        df["r_l"] = df["leg"].pct_change()      # real ETF: all fees and frictions already inside
    elif args.leg_under:
        df["r_l"] = 2.0 * df["leg"].pct_change() - (args.exp + df["fin"] + args.calib) / per
    else:
        df["r_l"] = 2.0 * df["r_u"] - (args.exp + df["fin"] + args.calib) / per
    df["r_s"] = df["cash"] / per
    return df.dropna(subset=["r_u", "r_l"]).copy()

TIERS = (0.20, 0.30, 0.50)
FRACS = (1/3, 1/2, 1.0)

def irr(dates, flows):
    """Money-weighted annual return: solve sum(flow / (1+r)^years) = 0 by bisection."""
    t = np.array([(d - dates[0]).days / 365.25 for d in dates]); f = np.array(flows)
    lo, hi = -0.99, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if (f / (1 + mid) ** t).sum() > 0:
            lo = mid
        else:
            hi = mid
    return mid

def run(sub, freq, use_tiers, use_newmoney, cap, tier_to_lev=True, sgov_share=None):
    idx = sub.index
    if freq == "daily":
        months = pd.date_range(idx[0], idx[-1], freq="MS")
        buyset = set(idx[idx.get_indexer([m], method="nearest")[0]] for m in months)
    else:
        buyset = set(idx)
    s_share = args.sgov_share if sgov_share is None else sgov_share
    rebal_days = set()
    if args.rebalance == "annual":
        years = pd.Series(idx, index=idx).groupby(idx.year).first()
        rebal_days = set(years.iloc[1:])      # first trading day of every year after the start
    n_rebal = 0
    proto = lev = sgov = 0.0                  # market values
    b_proto = b_sgov = 0.0                    # baseline market values
    inv = lev_cash = 0.0
    peak = -np.inf; fired = set(); state = "NORMAL"
    n_fire = 0; max_lev_share = 0.0
    twr = twr_peak = 1.0; twr_mdd = 0.0      # time-weighted index: drawdown without the effect of new money
    flow_dates, flows = [], []
    for dt, row in sub.iterrows():
        before = proto + lev + sgov
        proto *= 1 + row["r_u"]; lev *= 1 + row["r_l"]; sgov *= 1 + row["r_s"]
        b_proto *= 1 + row["r_u"]; b_sgov *= 1 + row["r_s"]
        if before > 0:
            twr *= (proto + lev + sgov) / before
            twr_peak = max(twr_peak, twr); twr_mdd = min(twr_mdd, twr / twr_peak - 1.0)
        if row["u"] >= peak:
            peak = row["u"]; fired = set()
        dd = row["u"] / peak - 1.0
        if state == "NORMAL" and dd <= -0.30:
            state = "LEVERAGED"
        elif state == "LEVERAGED" and row["u"] >= 0.80 * peak:
            state = "NORMAL"
        if dt in rebal_days and s_share > 0:
            # baseline: plain yearly rebalance to the target split
            b_tot = b_proto + b_sgov
            b_sgov, b_proto = b_tot * s_share, b_tot * (1 - s_share)
            # strategy: only when every tier is armed and the new-money switch is off
            if not fired and state == "NORMAL":
                target = (proto + sgov) * s_share
                proto -= target - sgov; sgov = target; n_rebal += 1
        if dt in buyset:
            inv += 1.0; flow_dates.append(dt); flows.append(-1.0)
            s_part = s_share; e_part = 1.0 - s_part
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
    flow_dates.append(idx[-1]); flows.append(strat)
    return dict(strat_x=strat / inv, base_x=base / inv, edge=(strat / base - 1) * 100,
                cash_pct=lev_cash / inv * 100, end_pct=lev / strat * 100,
                max_pct=max_lev_share * 100, fires=n_fire, rebal=n_rebal,
                irr=irr(flow_dates, flows) * 100, mdd=twr_mdd * 100)

MARKETS = [
    ("VT 全球 2008-", HERE + "vt.csv", "daily", None, "vt"),
    ("S&P 1993-", HERE + "spy.csv", "daily", None, "spy"),
    ("日經 1970-(融資 0.5%)", HERE + "n225.csv", "daily", 0.005, "n225"),
    ("S&P 1927-(月頻)", HERE + "spx_tr_monthly.csv", "monthly", None, "spx"),
]
MARKETS = [m for m in MARKETS if args.market in ("all", m[4])]
CONFIGS = [  # (label, use_tiers, use_newmoney, tier_to_lev)
    ("A 已回測版:只改新錢(-30%/80%)", False, True, True),
    ("B 只用 SGOV 三段(買 2x)", True, False, True),
    ("C 實際規則:SGOV 三段 + 新錢", True, True, True),
    ("D 對照:SGOV 三段改買原型 1x", True, False, False),
]

if args.leg_csv:
    leg_txt = f"REAL leg {args.leg_csv}"
elif args.leg_under:
    leg_txt = f"2x model of {args.leg_under} exp={args.exp:.2%} calib={args.calib:.2%}"
else:
    leg_txt = f"2x model exp={args.exp:.2%} calib={args.calib:.2%}"
L = [f"TIERED SGOV BACKTEST  {leg_txt} sgov_share={args.sgov_share:.0%} cash cap={args.cap:.0%} rebalance={args.rebalance}",
     "edge = strategy vs baseline with the same SGOV share and no leverage",
     "cash% = cumulative cash into leverage / contributions; end% / max% = leverage market-value share at end / at worst\n"]
for mname, path, freq, fr, _ in MARKETS:
    df = prep(path, freq, fr)
    L.append(f"################ {mname}  {df.index[0].date()}..{df.index[-1].date()} ################")
    L.append(f"{'config':<34} {'cap':>5} | {'cash%':>6} {'end%':>6} {'max%':>6} | {'strat':>9} {'base':>9} | {'edge':>8} | fires")
    for cname, ut, un, tl in CONFIGS:
        for cap in ((args.cap, None) if tl else (None,)):
            r = run(df, freq, ut, un, cap, tl)
            L.append(f"{cname:<34} {('%.0f%%' % (cap*100)) if cap else 'none':>5} | {r['cash_pct']:>5.1f}% {r['end_pct']:>5.1f}% {r['max_pct']:>5.1f}% | "
                     f"{r['strat_x']:>8.2f}x {r['base_x']:>8.2f}x | {r['edge']:>+7.1f}% | {r['fires']}")
    L.append("")
    # absolute view: what each choice actually returned, including "never use leverage"
    L.append(f"  ABSOLUTE  {'choice':<40} | {'end x':>8} | {'IRR/yr':>7} | {'max DD':>7} | {'lev max%':>8}")
    rows = [
        ("0 只買原型 100%(無 SGOV、無槓桿)", run(df, freq, False, False, None, True, 0.0)),
        ("1 原型 90% + SGOV 10%,SGOV 不動用", run(df, freq, False, False, None, True)),
        ("2 SGOV 三段改買原型 1x(不用槓桿)", run(df, freq, True, False, None, False)),
        (f"3 實際規則 + 2x 槓桿({args.cap:.0%} 現金上限)", run(df, freq, True, True, args.cap, True)),
    ]
    for lbl, r in rows:
        L.append(f"  ABSOLUTE  {lbl:<40} | {r['strat_x']:>7.2f}x | {r['irr']:>6.2f}% | {r['mdd']:>6.1f}% | {r['max_pct']:>7.1f}%")
    L.append("")

if not args.no_cohorts:
    L.append("ROLLING COHORTS (start every 12 months, run to data end), config C with cash cap")
    L.append(f"{'market':<26} | cohorts | win%  | edge med   p25    min    max | no-lev")
    for mname, path, freq, fr, _ in [m for m in MARKETS if m[2] == "daily"]:
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
