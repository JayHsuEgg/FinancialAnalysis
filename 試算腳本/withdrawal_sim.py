"""Withdrawal-rule backtest on US monthly data (S&P 500 total return, Shiller), in real terms.

Every 30-year (or --years) window that starts on a month is a separate retiree. Strategies:
  fixed      : withdraw r x initial portfolio per year (inflation-adjusted), 100% stocks
  buffer     : same withdrawal, (1 - b) stocks + b cash; withdraw from cash while stocks are
               20%+ below their (nominal) high, otherwise from stocks; once a year, if stocks are
               not 20%+ down, top cash back up to b of the portfolio (never sold low to refill)
  rebal      : same (1 - b) / b split, plain yearly rebalance, withdrawals pro rata (no trigger)
  cut        : 100% stocks, fixed withdrawal, but 10% less while stocks are 20%+ below their high
  pct        : 100% stocks, withdraw r x CURRENT portfolio each year (never fails; income moves)
  guard      : cut + Guyton-Klinger guardrails: once a year, if this year's withdrawal / portfolio
               is 20%+ above r, the withdrawal is cut 10% for good; 20%+ below r, raised 10%
  full       : guard on the rebal portfolio ((1 - b) stocks, b cash, yearly rebalance) = file 11's rule

Cash earns --cash-real, default 0% real (no T-bill series before 1970 in this repo; US T-bills averaged slightly
above inflation, so this is mildly conservative). Shiller dividends/CPI end in 2023, so windows
end by 2023-06. US-only data is survivorship-biased; see the article for international evidence.

Example:
  python withdrawal_sim.py --shiller "../8. 槓桿DCA實證_佐證/shiller_raw.csv" --out wd.txt
"""
import argparse
import numpy as np
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--shiller", required=True, help="shiller_raw.csv (Date,SP500,Dividend,...,Consumer Price Index,...)")
p.add_argument("--out", required=True)
p.add_argument("--start", default="1927-01-01")
p.add_argument("--rates", default="0.03,0.035,0.04,0.045,0.05")
p.add_argument("--years", default="30,40")
p.add_argument("--buffer", type=float, default=0.20, help="cash share for buffer / rebal strategies")
p.add_argument("--cash-real", type=float, default=0.0, help="annual real return on cash (sensitivity, e.g. 0.005)")
a = p.parse_args()

d = pd.read_csv(a.shiller)
d = d[(d["Dividend"] > 0) & (d["Consumer Price Index"] > 0)]
d["Date"] = pd.to_datetime(d["Date"])
d = d[d["Date"] >= pd.Timestamp(a.start) - pd.DateOffset(months=1)].reset_index(drop=True)
nom = (d["SP500"] + d["Dividend"] / 12).values[1:] / d["SP500"].values[:-1]   # nominal TR factor
cpi = d["Consumer Price Index"].values
real = nom / (cpi[1:] / cpi[:-1])                                             # real TR factor
dates = d["Date"].values[1:]
nom_idx = np.cumprod(nom)
peak = np.maximum.accumulate(nom_idx)
down = nom_idx / peak - 1 <= -0.20                                            # 20%+ below the high
N = len(real)


def run(strategy, r, s, months):
    stock, cash = (1 - a.buffer, a.buffer) if strategy in ("buffer", "rebal", "full") else (1.0, 0.0)
    w = r / 12
    incomes = []
    for m in range(months):
        i = s + m
        if strategy == "pct":
            wm = (stock + cash) * r / 12
        elif strategy in ("cut", "guard", "full") and down[i]:
            wm = w * 0.9
        else:
            wm = w
        incomes.append(wm * 12 / r)
        if stock + cash < wm - 1e-12:                 # cannot pay this month: ruined
            return dict(fail=True, end=0.0, min_inc=min(incomes), fail_year=m / 12)
        if strategy == "buffer":                      # crash: cash first; otherwise stocks first
            take_cash = min(cash, wm) if down[i] else max(0.0, wm - stock)
            cash -= take_cash
            stock -= wm - take_cash
        elif strategy in ("rebal", "full"):
            tot = stock + cash
            stock -= wm * stock / tot
            cash -= wm * cash / tot
        else:
            stock -= wm
        stock *= real[i]
        cash *= (1 + a.cash_real) ** (1 / 12)
        if m % 12 == 11:
            tot = stock + cash
            if strategy in ("guard", "full") and tot > 0:
                if w * 12 / tot > 1.2 * r:
                    w *= 0.9
                elif w * 12 / tot < 0.8 * r:
                    w *= 1.1
            if strategy in ("rebal", "full") or (strategy == "buffer" and not down[i] and cash < a.buffer * tot):
                stock, cash = tot * (1 - a.buffer), tot * a.buffer
    return dict(fail=False, end=stock + cash, min_inc=min(incomes), fail_year=None)


L = [f"US S&P 500 real total return, Shiller monthly {pd.Timestamp(dates[0]).date()}..{pd.Timestamp(dates[-1]).date()}; "
     f"buffer share {a.buffer:.0%}; cash {a.cash_real:.1%} real",
     "fail% = windows that ran out of money; end = real ending wealth / initial portfolio; "
     "min income = lowest real income / planned (pct, cut, guard, full): worst window, 10th percentile, median\n"]
for yrs in [int(x) for x in a.years.split(",")]:
    months = yrs * 12
    starts = range(0, N - months + 1)
    L.append(f"=== {yrs}-year windows: {len(starts)} start months, "
             f"{pd.Timestamp(dates[0]).date()} .. {pd.Timestamp(dates[starts[-1]]).date()} ===")
    L.append(f"{'strategy':<8} {'rate':>5} | {'fail%':>6} {'earliest fail':>13} | {'end p10':>7} {'end med':>7} | {'min income':>10} {'p10':>5} {'median':>6}")
    for strat in ("fixed", "buffer", "rebal", "cut", "pct", "guard", "full"):
        for r in [float(x) for x in a.rates.split(",")]:
            res = [run(strat, r, s, months) for s in starts]
            fails = [x for x in res if x["fail"]]
            ends = np.array([x["end"] for x in res])
            earliest = min((x["fail_year"] for x in fails), default=None)
            L.append(f"{strat:<8} {r:>5.1%} | {len(fails) / len(res):>6.1%} "
                     f"{('%.1f yr' % earliest) if earliest is not None else '-':>13} | "
                     f"{np.percentile(ends, 10):>7.2f} {np.median(ends):>7.2f} | "
                     f"{min(x['min_inc'] for x in res):>10.0%} "
                     f"{np.percentile([x['min_inc'] for x in res], 10):>5.0%} "
                     f"{np.median([x['min_inc'] for x in res]):>6.0%}")
    L.append("")
txt = "\n".join(L)
with open(a.out, "w", encoding="utf-8") as f:
    f.write(txt + "\n")
print(txt)
