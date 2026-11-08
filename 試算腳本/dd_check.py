"""Print start/end dates and the maximum drawdown (peak, trough, recovery) of each Date,AdjClose csv."""
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
    s = df.set_index("Date")["AdjClose"]
    dd = s / s.cummax() - 1
    t = dd.idxmin()
    pk = s[:t].idxmax()
    rec = s[t:][s[t:] >= s[pk]]
    lines.append(f"{path.split('/')[-1]}: start {s.index[0].date()} end {s.index[-1].date()} "
                 f"yrs {(s.index[-1]-s.index[0]).days/365.25:.1f} | maxDD {dd.min():.1%} peak {pk.date()} trough {t.date()} "
                 f"recovered {rec.index[0].date() if len(rec) else 'never'}")
txt = "\n".join(lines)
with open(a.out, "w", encoding="utf-8") as f:
    f.write(txt)
print(txt)
