"""Annualised volatility of each Date,AdjClose csv: full period, per calendar year, and last 1 / 5 years."""
import argparse
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--csv", action="append", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
lines = []
for path in a.csv:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    r = df.set_index("Date")["AdjClose"].pct_change().dropna()
    ann = lambda x: x.std() * 252 ** 0.5
    end = r.index[-1]
    yearly = r.groupby(r.index.year).apply(ann)
    full_years = yearly[(yearly.index > r.index[0].year) & (yearly.index < end.year)]
    lines.append(f"{path.replace(chr(92), '/').split('/')[-1]}: {r.index[0].date()}..{end.date()} | "
                 f"full {ann(r):.1%} | last 1y {ann(r[r.index > end - pd.DateOffset(years=1)]):.1%} | "
                 f"last 5y {ann(r[r.index > end - pd.DateOffset(years=5)]):.1%} | "
                 f"calendar years: median {full_years.median():.1%}, "
                 f"p25 {full_years.quantile(0.25):.1%}, p75 {full_years.quantile(0.75):.1%}, "
                 f"min {full_years.min():.1%} ({full_years.idxmin()}), max {full_years.max():.1%} ({full_years.idxmax()})")
txt = "\n".join(lines)
with open(a.out, "w", encoding="utf-8") as f:
    f.write(txt)
print(txt)
