"""Recompute file 3 section 6 (VWRA -> ACWD switch) with VWRA TER 0.14%.

Convention reproduces the original table exactly when tv=0.19%:
monthly rate (1+g-TER)^(1/12)-1, contribution at month start, 0.15% fee on
each buy and on the swap (sell+buy, multiplicative), no final sale.
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--tv", type=float, default=0.14)
ap.add_argument("--ta", type=float, default=0.12)
a = ap.parse_args()
C = 0.0015


def sim(g, route, tv, ta):
    rv = (1 + g - tv / 100) ** (1 / 12) - 1
    ra = (1 + g - ta / 100) ** (1 / 12) - 1
    if route == 3:
        v, acc = 0.0, 1_000_000 * (1 - C) * (1 - C)
    else:
        v, acc = 1_000_000.0, 0.0
    for _ in range(120):
        net = 10000 * (1 - C)
        if route == 1:
            v += net
        else:
            acc += net
        v *= 1 + rv
        acc *= 1 + ra
    return v + acc


L = []
for tv in (0.19, a.tv):
    L.append(f"VWRA TER {tv}% vs ACWD {a.ta}%")
    for g in (0.05, 0.07, 0.09):
        r = [sim(g, k, tv, a.ta) for k in (1, 2, 3)]
        L.append(f"  g={g:.0%}: r1={r[0]:,.0f} r2={r[1]:,.0f} ({r[1]-r[0]:+,.0f}) r3={r[2]:,.0f} ({r[2]-r[0]:+,.0f})")
open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
