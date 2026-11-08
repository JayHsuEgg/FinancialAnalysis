"""File 8: satellite <=15%, 2008 underlying -50%: what does a 2x satellite do to total assets?"""
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--spy", required=True)
ap.add_argument("--sso", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = []
p = L.append
spy = pd.read_csv(a.spy, parse_dates=["Date"]).set_index("Date")["AdjClose"]
sso = pd.read_csv(a.sso, parse_dates=["Date"]).set_index("Date")["AdjClose"]
w = slice("2007-01-01", "2009-12-31")
s, l = spy[w], sso[w]
pk = s.loc[:"2008-06-01"].idxmax()
tr = s.loc[pk:].idxmin()
du = s[tr] / s[pk] - 1
dl = l[tr] / l[pk] - 1
p(f"SPY peak {pk.date()} trough {tr.date()}: {du:.2%};  SSO same dates: {dl:.2%}")
p(f"SSO own max DD 2007-09: {(l / l.cummax() - 1).min():.2%}")
for sat in (0.10, 0.15):
    core = 1 - sat
    tot = core * du + sat * dl
    base = du
    p(f"sat {sat:.0%}: total {tot:.2%} vs all-core {base:.2%} -> extra {tot-base:.2%}; satellite's own contribution {sat*dl:.2%}")
# stylised -50% underlying
for lev_loss, lab in ((-1.0, "naive 2x = -100%"), (-0.75, "2x ~ -75%"), (dl, "SSO-real")):
    p(f"15% sat, underlying -50%, sat {lab}: total {0.85*-0.5+0.15*lev_loss:.2%}, extra vs unlevered {0.15*(lev_loss+0.5):.2%}, sat contribution {0.15*lev_loss:.2%}")
p(f"15% x -50% = {0.15*-0.5:.2%}")
p(f"spy.csv first date {spy.index[0].date()}, years to last {(spy.index[-1]-spy.index[0]).days/365.25:.1f}")
open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
