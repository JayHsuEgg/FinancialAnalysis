"""Recompute file 4 (AVGS vs AVUV+AVDV) drag with the AVDV source-country layer."""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = []
p = L.append

TER_AVGS, TER_PAIR = 0.39, (0.25 + 0.36) / 2


def run(label, y_avgs, y_avuv, y_avdv):
    avgs = TER_AVGS + 0.15 * y_avgs
    p(f"[{label}] AVGS drag = {TER_AVGS} + 15%*{y_avgs} = {avgs:.3f}")
    for s in (0.0, 0.10, 0.15):
        gross_avdv = y_avdv / (1 - s)
        pair_tax = 0.5 * y_avuv * 0.30 + 0.5 * y_avdv * 0.30 + 0.5 * gross_avdv * s
        pair = TER_PAIR + pair_tax
        gap = pair - avgs
        fv_a = 100000 * (1 + (8 - avgs) / 100) ** 10
        fv_p = 100000 * (1 + (8 - pair) / 100) ** 10
        p(f"   s={s:.0%}: pair tax={pair_tax:.3f} pair total={pair:.3f} gap={gap:.3f}  "
          f"10y $100k: AVGS {fv_a:,.0f} pair {fv_p:,.0f} diff {fv_a-fv_p:,.0f} ({fv_a/fv_p-1:.2%})  payback 0.15%/gap={0.15/gap:.2f}y")


run("doc yields", 2.0, 2.2, 2.2)
run("doc per-fund yields", 2.0, 1.52, 2.90)
run("2026-10 SEC yields, AVGS scaled", 2.0 * (1.38 + 2.35) / (1.52 + 2.90), 1.38, 2.35)
open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
