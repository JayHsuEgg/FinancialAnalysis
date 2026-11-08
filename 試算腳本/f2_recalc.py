"""Recompute file 2 (0050 vs feeder fund) cost table with one consistent model.

Model: NT$3,000 at each month end for 120 months, 8% effective annual total return.
Fees  : TER x sum(month-end balances)/12 (balance-years), not compounded.
Divs  : semi-annual (months 1 and 7 of each year), each = yield/2 x balance.
Tax   : taxable dividends x (bracket - 8.5% credit), combined-taxation option.
Trade : buy fee 0.1425% x discount on each purchase; at the end sell fee
        0.1425% x discount + 0.1% ETF securities transaction tax on terminal value.
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--ret", type=float, default=0.08)
ap.add_argument("--yld", type=float, default=0.0124)
ap.add_argument("--ter0050", type=float, default=0.0022)
ap.add_argument("--terfeeder", type=float, default=0.00234)
ap.add_argument("--taxable", type=float, default=0.33)
ap.add_argument("--disc", type=float, default=0.6)
a = ap.parse_args()

M, PMT = 120, 3000.0
r = (1 + a.ret) ** (1 / 12) - 1
b, bal = 0.0, []
for _ in range(M):
    b = b * (1 + r) + PMT
    bal.append(b)
fv = bal[-1]
bal_years = sum(bal) / 12

L = []
p = L.append
p(f"inputs: ret={a.ret:.2%} yld={a.yld:.2%} ter0050={a.ter0050:.3%} terfeeder={a.terfeeder:.3%} taxable={a.taxable:.0%}")
p(f"FV={fv:,.0f}  balance-years={bal_years:,.0f}")

fee0 = a.ter0050 * bal_years
fee1 = a.terfeeder * bal_years
p(f"fees: 0050={fee0:,.0f} feeder={fee1:,.0f} diff={fee1-fee0:,.0f}")

pays = [bal[m] * a.yld / 2 for m in range(M) if m % 12 in (0, 6)]
div = sum(pays)
taxable = div * a.taxable
p(f"dividends: n={len(pays)} total={div:,.0f} taxable={taxable:,.0f} max single payment={max(pays):,.0f}")
p(f"NHI threshold principal: 20,000/(yld/2) = {20000/(a.yld/2):,.0f}")

buy = M * PMT * 0.001425 * a.disc
sell = fv * 0.001425 * a.disc + fv * 0.001
trade = buy + sell
p(f"trade: buy fees={buy:,.0f} sell fee+tax={sell:,.0f} total={trade:,.0f}")

for br in (0.05, 0.12, 0.20, 0.30, 0.40):
    tax = taxable * (br - 0.085)
    tot0 = fee0 + trade + tax
    p(f"bracket {br:.0%}: 0050 tax={tax:,.0f} 0050 total={tot0:,.0f} feeder total={fee1:,.0f} feeder saves={tot0-fee1:,.0f}")

# break-even bracket where feeder == 0050
be = 0.085 + (fee1 - fee0 - trade) / taxable
p(f"break-even bracket: {be:.2%}")
p(f"credit cap: 80,000/8.5% = {80000/0.085:,.0f} dividends/yr")

open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
