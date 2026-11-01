"""Audit files 4, 6, 0, 1, Sin, 8, 10 arithmetic."""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = []
p = L.append

p("== File 4 AVGS vs AVUV+AVDV ==")
p(f"weighted TER (0.25+0.36)/2 = {(0.25+0.36)/2:.4f}")
p(f"AVGS drag 15%*2.0 = {0.15*2.0:.3f}; AVUV/AVDV 30%*2.2 = {0.30*2.2:.3f}")
avgs, av2 = 0.39 + 0.30, 0.305 + 0.66
p(f"totals {avgs:.3f} vs {av2:.3f}; net {av2-avgs:.3f}")
p(f"tax saving 0.66-0.30 = {0.66-0.30:.2f} (doc says 0.33); fee gap 0.39-0.305={0.39-0.305:.3f}")
p(f"blended yield 50/50 of 1.52 & 2.90 = {(1.52+2.90)/2:.2f}%")
for rA, rB, lab in ((0.0731, 0.0703, "rounded 7.31/7.03"), (0.0731, 0.07035, "unrounded 7.31/7.035")):
    A, B = 1e5 * (1 + rA) ** 10, 1e5 * (1 + rB) ** 10
    p(f"{lab}: AVGS {A:,.0f}  AVUV+AVDV {B:,.0f}  diff {A-B:,.0f} ({A/B-1:.2%})")
# AVDV double layer: distribution yield 2.90 is after source tax; gross ~ 2.90/(1-s)
for s in (0.10, 0.15):
    gross = 2.90 / (1 - s)
    extra = 0.5 * gross * s
    p(f"AVDV source layer s={s:.0%}: gross yield {gross:.2f}%, extra blended drag 0.5*{gross:.2f}*{s:.2f} = {extra:.3f}% -> AVUV+AVDV total {av2+extra:.3f}, gap {av2+extra-avgs:.3f}")
# per-leg with stated yields
leg = 0.5 * 1.52 * 0.30 + 0.5 * 2.90 * 0.30
p(f"per-leg 30%: 0.5*1.52*0.3 + 0.5*2.90*0.3 = {leg:.3f}")
p(f"payback 0.15% / 0.275 = {0.15/0.275:.2f} yr")

p("\n== File 6 BTC fee advantage ==")
def fv(g, fee, lump, pmt, months=120):
    r = (1 + g - fee) ** (1 / 12) - 1
    v = lump
    for _ in range(months):
        v = v * (1 + r) + pmt
    return v
for lump_share in (1.0, 0.75, 0.5, 0.25, 0.0):
    # lump:monthly by total contributions: lump = s*T, monthly = (1-s)*T/120
    T = 1.0
    lump, pmt = lump_share * T, (1 - lump_share) * T / 120
    b, i = fv(0.30, 0.0015, lump, pmt), fv(0.30, 0.0025, lump, pmt)
    p(f"lump share of contributions {lump_share:.0%}: BTC/IBIT - 1 = {b/i-1:.3%}")
p(f"pure lump closed form (1.2985/1.2975)^10-1 = {(1.2985/1.2975)**10-1:.3%}")
for g in (0.10, 0.15):
    p(f"g={g:.0%} lump: {(1+g-0.0015)**10/(1+g-0.0025)**10-1:.3%}  DCA-only: {fv(g,0.0015,0,1)/fv(g,0.0025,0,1)-1:.3%}")

p("\n== File 0 vol drag / BTC weights ==")
for L_, s in ((2, 0.2), (2, 0.5), (3, 0.2), (3, 0.5)):
    p(f"L={L_} sigma={s:.0%}: 0.5*L*(L-1)*s^2 = {0.5*L_*(L_-1)*s*s:.2%}")
for mv, lab in ((3.0, "+200%"), (0.5, "-50%"), (0.3, "-70%")):
    w = 13 * mv / (13 * mv + 87)
    p(f"BTC {lab} others flat: weight {w:.2%}")

p("\n== File 1 ==")
p(f"52+13+12+13+10 = {52+13+12+13+10}; stocks 52+13+12 = {52+13+12}; risk = {52+13+12+13}")
p(f"parents 50+25+20+5 = {50+25+20+5}; 25/75 = {25/75:.2%}")
p(f"20/4 = {20/4}; 20/5 = {20/5}; 13/65 = {13/65:.1%}; 13/77 = {13/77:.1%}; 5%*70% = {0.05*0.70:.1%}")
p(f"paper: 16.1/10-1 = {16.1/10-1:.0%}; 14.9/7.0 = {14.9/7.0:.2f}")

p("\n== Sin A Little ==")
def ann_fv(r, n=10, due=False, monthly=False):
    if monthly:
        rm = (1 + r) ** (1 / 12) - 1
        f = ((1 + rm) ** (12 * n) - 1) / rm
        return f * (1 + rm) if due else f
    f = ((1 + r) ** n - 1) / r
    return f * (1 + r) if due else f
for base in (0.07, 0.08):
    lump = 0.04 * (((1 + base + 0.05) / (1 + base)) ** 10 - 1)
    p(f"base {base:.0%} lump: +{lump:.2%}")
    for due in (False, True):
        for monthly in (False, True):
            rat = ann_fv(base + 0.05, due=due, monthly=monthly) / ann_fv(base, due=due, monthly=monthly)
            p(f"   DCA due={due} monthly={monthly}: +{0.04*(rat-1):.2%}")
p(f"NATO (3.5/2)^(1/10)-1 = {(3.5/2)**0.1-1:.2%}")
p(f"MSTR/IBIT -62.78/-31.03 = {62.78/31.03:.3f}")
p(f"SpaceX float 595.18/13570 = {595.18/13570:.2%}; implied shares 1.92T/141.50 = {1.92e12/141.5/1e9:.3f}B; 13.57B*141.50 = {13.57e9*141.5/1e12:.3f}T")
p(f"XBI 162.38/89.33-1 = {162.38/89.33-1:.2%} (doc +80.67%)")
p(f"IPO 135 -> 141.50 = {141.5/135-1:.2%}")

p("\n== File 8 ==")
p(f"131.5/119.6-1 = {131.5/119.6-1:.2%}")
p(f"exposure 30/5 = {30/5:.1f}; edge 41/15 = {41/15:.2f}")
p(f"+985% edge -> {1+9.85:.2f}x baseline")
for s, b, lab in ((11.50, 8.60, "S&P 2x80"), (12.97, 8.60, "S&P 2x100"), (15.75, 8.60, "S&P 3x80"), (8.27, 7.00, "N225 2x80"), (7.97, 7.00, "N225 2x100")):
    p(f"{lab}: {s}/{b}-1 = {s/b-1:.1%}")
open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
