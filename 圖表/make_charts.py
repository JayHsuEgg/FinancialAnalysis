"""Generate every chart (SVG) used by the documents in this repo.

All numbers live in CHARTS below, copied from the documents; each chart names its source.
When a number changes in a document, change it here too, re-run, and update
`資料來源紀錄.md` in the same commit.

Usage:
    python make_charts.py --outdir .            # regenerate all charts
    python make_charts.py --outdir . --only f2_total_cost
    python make_charts.py --outdir . --check    # report charts missing or older than this script
"""

import argparse
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Palette: dataviz reference categorical slots 1-4 (validated light mode) + chrome.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BASE = "#b5b3ab"  # neutral bar for "baseline" entries
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

REGEN = "python 圖表/make_charts.py --outdir 圖表"

plt.rcParams.update({
    "font.family": ["Noto Sans TC", "Microsoft JhengHei", "sans-serif"],
    "font.size": 10,
    "svg.fonttype": "path",  # glyphs as outlines: renders without the font installed
    "svg.hashsalt": "financialanalysis",  # deterministic element ids: re-runs stay diff-free
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK,
    "axes.unicode_minus": False,
})

PAPER = "資料:《Beyond the Status Quo》2025-07-10 版"

CHARTS = {
    # ---------- files 0, 1 ----------
    "allocation_main": dict(
        kind="pie",
        title="我的投資組合(2026)",
        labels=["VWRA / VALU", "AVGS", "IBIT(比特幣)", "0050 連結基金", "SGOV(短債)"],
        values=[52, 13, 13, 12, 10],
        fmt="{:.0f}%",
        source="檔 1〈我的實際配置〉",
    ),
    "allocation_parents": dict(
        kind="pie",
        title="父母退休組合(另有 2 年生活費的台幣安全金)",
        labels=["VWRA", "0050 連結基金", "IB01(短債)", "IBIT(比特幣)"],
        values=[50, 25, 20, 5],
        fmt="{:.0f}%",
        source="檔 1〈父母退休組合〉",
    ),
    # ---------- paper (files 0, 1, 10) ----------
    "paper_savings": dict(
        kind="barh",
        title="要得到同樣的退休效用,需要的儲蓄率",
        labels=["最優(依年齡)", "最優(固定 33/67)", "TDF 目標日期基金", "100% 本國股票", "60/40 股債", "100% 國庫券"],
        values=[10.00, 10.07, 16.27, 16.42, 19.44, 56.71],
        value_labels=["10%(基準)", "10.07%", "16.27%(多存 63%)", "16.42%(多存 64%)",
                      "19.44%(多存 94%)", "56.71%(多存 467%)"],
        highlight=[0, 1],
        source=PAPER,
    ),
    "paper_ruin": dict(
        kind="barh",
        title="退休後錢花光的機率(4% 提領,越低越好)",
        labels=["最優(依年齡)", "最優(固定 33/67)", "60/40 股債", "100% 本國股票", "TDF 目標日期基金", "100% 國庫券"],
        values=[6.7, 7.0, 16.9, 17.1, 19.7, 38.9],
        fmt="{:.1f}%",
        highlight=[0, 1],
        source=PAPER,
    ),
    "paper_ruin_conditional": dict(
        kind="grouped",
        title="壞情境下錢花光的機率(越低越好)",
        groups=["活最久的 1/5", "本國股最差的 1/5", "高通膨的 1/5"],
        series={
            "最優": [14.9, 17.7, 15.9],
            "100% 本國股票": [29.4, 52.4, 38.9],
            "60/40 股債": [32.2, 45.9, 51.1],
            "TDF": [41.2, 39.6, 62.8],
        },
        fmt="{:.1f}%",
        source=PAPER + " 網路附錄 Figure C.1",
    ),
    "paper_variance_ratio": dict(
        kind="barh",
        title="30 年變異比:小於 1 = 放越久越穩",
        labels=["國際股票", "債券"],
        values=[0.75, 2.30],
        fmt="{:.2f}",
        refline=1.0,
        source=PAPER,
    ),
    "paper_us_belief": dict(
        kind="line",
        title="越相信「美國會一直贏」,最優美股比重越高",
        x=[0, 50, 90, 100],
        y=[33, 60, 96, 100],
        xlabel="相信美國例外的機率(%)",
        ylabel="最優美股比重(%)",
        fmt="{:.0f}%",
        source=PAPER + " §5.4.5",
    ),
    # ---------- file 2 ----------
    "f2_total_cost": dict(
        kind="grouped",
        title="10 年總成本(元):每月 3,000 元、年化 8%",
        groups=["稅率 5%", "稅率 12%", "稅率 20%", "稅率 30%"],
        series={
            "0050": [6224, 6874, 7616, 8545],
            "連結基金 A 類": [5572, 5572, 5572, 5572],
        },
        fmt="{:,.0f}",
        source="自算:試算腳本/f2_recalc.py",
    ),
    # ---------- file 3 ----------
    "f3_annual_cost": dict(
        kind="stacked",
        title="每年真實成本(%):費用率 + 股息稅 + 手續費",
        labels=["VT(美國註冊)", "IMID", "VWRA", "VALU"],
        components={
            "費用率": [0.06, 0.17, 0.14, 0.07],
            "股息預扣稅拖累": [0.60, 0.27, 0.27, 0.27],
            "手續費(10 年攤提)": [0.0, 0.015, 0.015, 0.015],
        },
        totals=["0.66%", "0.46%", "0.43%", "0.36%"],
        source="檔 3 估算;VT 另有美國遺產稅風險,未計入",
    ),
    "f3_switch": dict(
        kind="grouped",
        title="已有 100 萬 VWRA:改買 VALU 10 年後多出的錢(元)",
        groups=["毛報酬 5%", "毛報酬 7%", "毛報酬 9%"],
        series={
            "VWRA 不動,新錢買 VALU": [5586, 6257, 7005],
            "VWRA 全賣,換成 VALU": [11497, 13154, 15026],
        },
        fmt="{:,.0f}",
        source="自算:試算腳本/f3_case_recalc.py(只算費用差)",
    ),
    # ---------- file 4 ----------
    "f4_drag": dict(
        kind="stacked",
        title="每年總拖累(%):費用率 + 股息稅",
        labels=["AVGS", "AVUV+AVDV(低估)", "AVUV+AVDV(高估)"],
        components={
            "費用率": [0.39, 0.305, 0.305],
            "美國層股息稅": [0.30, 0.66, 0.66],
            "AVDV 來源國層": [0.0, 0.16, 0.26],
        },
        totals=["0.69%", "1.13%", "1.22%"],
        source="自算:試算腳本/f4_recalc.py;AVGS 持股股息率 2.0% 為假設",
    ),
    "f4_geo": dict(
        kind="grouped",
        title="地區分布(%):AVGS 比自組更偏美國",
        groups=["美國", "歐洲(含英國)", "日本", "加拿大", "澳洲 / 澳紐", "其他"],
        series={
            "AVGS": [68.6, 13.3, 9.7, 3.1, 2.8, 2.6],
            "AVUV+AVDV 50/50": [50.0, 19.5, 16.5, 5.5, 4.6, 3.9],
            "AVUV+AVDV 60/40": [60.0, 15.6, 13.2, 4.4, 3.7, 3.1],
        },
        fmt="{:.0f}",
        source="AVGS:FT/Morningstar 2026-10-27;AVDV:Avantis 2026-09-30 按比例換算(假設 AVUV 全美國)",
    ),
    # ---------- file 6 ----------
    "f6_btc_etf": dict(
        kind="panels",
        title="三檔比特幣 ETF:本質相同,只差費用與規模",
        panels=[
            dict(title="費用率(%)", labels=["BTC", "BITB", "IBIT"], values=[0.15, 0.20, 0.25], fmt="{:.2f}%"),
            dict(title="規模(億美元)", labels=["BTC", "BITB", "IBIT"], values=[48, 28, 658], fmt="{:.0f}"),
        ],
        source="發行商 fact sheet;規模 2026-10-30",
    ),
    "f6_drawdown": dict(
        kind="barh",
        title="歷史大跌幅(%)",
        labels=["比特幣 2017–18", "比特幣 2021–22", "黃金 1980–99", "全球股票 VT 2008–09", "黃金 2011–15"],
        values=[84, 77, 70, 50, 44],
        value_labels=["-84%", "-77%", "-70%", "-50%", "-44%"],
        source="PortfoliosLab(2026-11-01);黃金 1980–99 與 VT 為自算",
    ),
    # ---------- file 8 ----------
    "f8_leverage": dict(
        kind="panels",
        rows=2,
        title="每月定期定額:只買原型 vs 照規則加槓桿",
        panels=[
            dict(title="全球 2008–2026:最後變幾倍", labels=["只買原型", "+ WLDU", "+ SSO", "+ XS2D"],
                 values=[3.09, 3.17, 3.53, 3.55], fmt="{:.2f}", highlight=[0]),
            dict(title="美股 1993–2026:最後變幾倍", labels=["只買原型", "+ 2x 美股"],
                 values=[8.60, 8.21], fmt="{:.2f}", highlight=[0]),
            dict(title="日經 1970–2026:最後變幾倍", labels=["只買原型", "+ 2x 日經"],
                 values=[7.00, 6.79], fmt="{:.2f}", highlight=[0]),
            dict(title="全球:最慘跌幅", labels=["只買原型", "+ WLDU", "+ SSO", "+ XS2D"],
                 values=[49.8, 47.7, 47.5, 47.4], fmt="-{:.1f}%", highlight=[0]),
            dict(title="美股:最慘跌幅", labels=["只買原型", "+ 2x 美股"],
                 values=[55.2, 53.1], fmt="-{:.1f}%", highlight=[0]),
            dict(title="日經:最慘跌幅", labels=["只買原型", "+ 2x 日經"],
                 values=[81.9, 73.7], fmt="-{:.1f}%", highlight=[0]),
        ],
        source="自算:8. 槓桿DCA實證_佐證/tier_sgov.py(ABSOLUTE 段);10% 現金上限、每年再平衡 SGOV",
    ),
    "f8_decomp": dict(
        kind="panels",
        sharey=True,
        title="跟只買原型比,每年報酬差在哪(百分點)",
        panels=[
            dict(title="全球 2008–2026(WLDU)", kind="delta", values=[-0.85, 0.39, 0.71, 0.25]),
            dict(title="美股 1993–2026", kind="delta", values=[-0.77, 0.38, 0.18, -0.21]),
            dict(title="日經 1970–2026", kind="delta", values=[-0.07, -0.04, 0.03, -0.08]),
        ],
        labels=["① 留 10% SGOV 不動", "② 大跌時 SGOV 買原型", "③ 改買 2 倍槓桿", "合計"],
        source="自算:8. 槓桿DCA實證_佐證/tier_sgov.py(ABSOLUTE 段 0→1→2→3 的差);"
               "美股 2x 費用率 0.60%,其餘 0.75%",
    ),
    # ---------- file 11 ----------
    "f11_fail_30": dict(
        kind="grouped",
        title="30 年內錢花光的機率(美股 1927–2023,實質)",
        groups=["提領 3%", "3.5%", "4%", "4.5%", "5%"],
        series={
            "100% 股票": [0.0, 0.5, 4.0, 11.9, 20.3],
            "100% 股票,股災年少領 10%": [0.0, 0.3, 2.8, 10.4, 18.4],
            "80/20,每年再平衡": [0.0, 0.1, 2.0, 11.4, 20.9],
            "80/20,股災先花現金": [0.0, 0.4, 8.9, 18.6, 25.8],
        },
        fmt="{:g}%",
        source="自算:試算腳本/withdrawal_sim.py(Shiller S&P 500 含息、扣通膨;現金實質 0%;只有美國資料,偏樂觀)",
    ),
    "f11_fail_40": dict(
        kind="grouped",
        title="40 年內錢花光的機率(美股 1927–2023,實質)",
        groups=["提領 3%", "3.5%", "4%", "4.5%", "5%"],
        series={
            "100% 股票": [0.1, 0.7, 9.7, 19.1, 27.5],
            "100% 股票,股災年少領 10%": [0.0, 0.4, 8.4, 17.1, 25.9],
            "80/20,每年再平衡": [0.0, 0.3, 10.3, 23.0, 32.5],
            "80/20,股災先花現金": [0.0, 6.6, 19.1, 30.2, 38.9],
        },
        fmt="{:g}%",
        source="自算:試算腳本/withdrawal_sim.py(同上;40 年窗口 1927–1983 起始)",
    ),
    # ---------- file 9 ----------
    "f9_blv_bnd": dict(
        kind="panels",
        title="BLV(長債)vs BND(總體債)",
        panels=[
            dict(title="年化標準差(%)", labels=["BLV", "BND"], values=[11.65, 5.51], fmt="{:.2f}%"),
            dict(title="最大虧損(%)", labels=["BLV", "BND"], values=[38.29, 18.84], fmt="-{:.1f}%"),
            dict(title="10 年年化報酬(%)", labels=["BLV", "BND"], values=[0.52, 1.43], fmt="{:.2f}%"),
        ],
        source="Morningstar、totalrealreturns.com(2026-10)",
    ),
}


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=0)


def _colors(n, highlight):
    if highlight is None:
        return [SLOTS[0]] * n
    return [BASE if i in highlight else SLOTS[0] for i in range(n)]


def _barh(ax, labels, values, fmt=None, value_labels=None, highlight=None, refline=None):
    ys = list(range(len(labels)))[::-1]
    ax.barh(ys, values, height=0.6, color=_colors(len(values), highlight),
            edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    vmax = max(values)
    ax.set_xlim(0, vmax * 1.32)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    for y, v, i in zip(ys, values, range(len(values))):
        text = value_labels[i] if value_labels else fmt.format(v)
        ax.text(v + vmax * 0.015, y, text, va="center", ha="left", color=INK, fontsize=9.5)
    if refline is not None:
        ax.axvline(refline, color=MUTED, linewidth=1)
        ax.text(refline, ys[0] + 0.55, f" {refline:g}(分界)", color=MUTED, fontsize=8.5, va="bottom")


def _delta(ax, labels, values, show_labels=True, vmax=None):
    """Signed horizontal bars around zero; the last entry is the total. Pass vmax to share one scale."""
    ys = list(range(len(labels)))[::-1]
    colors = [SLOTS[0] if v >= 0 else SLOTS[1] for v in values[:-1]] + [INK_2]
    ax.barh(ys, values, height=0.6, color=colors, edgecolor=SURFACE, linewidth=2)
    vmax = vmax or max(abs(v) for v in values)
    ax.set_xlim(-vmax * 1.7, vmax * 1.7)
    ax.axvline(0, color=AXIS, linewidth=1)
    for y, v in zip(ys, values):
        ax.text(v + (vmax * 0.04 if v >= 0 else -vmax * 0.04), y, f"{v:+.2f}",
                va="center", ha="left" if v >= 0 else "right", color=INK, fontsize=9.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels if show_labels else [])
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)


def _grouped(ax, groups, series, fmt):
    n = len(series)
    width = 0.8 / n
    vmax = max(max(v) for v in series.values())
    for k, (name, vals) in enumerate(series.items()):
        xs = [g + (k - (n - 1) / 2) * width for g in range(len(groups))]
        ax.bar(xs, vals, width=width, color=SLOTS[k], edgecolor=SURFACE, linewidth=2, label=name)
        for x, v in zip(xs, vals):
            ax.text(x, v + vmax * 0.015, fmt.format(v), ha="center", va="bottom", color=INK,
                    fontsize=8.5 if n > 2 else 9)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups)
    ax.set_ylim(0, vmax * 1.18)
    ax.yaxis.set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.legend(frameon=False, loc="upper left", ncol=min(n, 4), fontsize=9,
              bbox_to_anchor=(0, 1.02), labelcolor=INK_2)


def _stacked(ax, labels, components, totals):
    ys = list(range(len(labels)))[::-1]
    left = [0.0] * len(labels)
    for k, (name, vals) in enumerate(components.items()):
        ax.barh(ys, vals, left=left, height=0.6, color=SLOTS[k], edgecolor=SURFACE,
                linewidth=2, label=name)
        left = [a + b for a, b in zip(left, vals)]
    vmax = max(left)
    for y, total, t in zip(ys, left, totals):
        ax.text(total + vmax * 0.015, y, t, va="center", ha="left", color=INK, fontsize=9.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, vmax * 1.2)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.legend(frameon=False, loc="lower center", ncol=len(components), fontsize=9,
              bbox_to_anchor=(0.45, -0.22), labelcolor=INK_2)


def _line(ax, x, y, xlabel, ylabel, fmt):
    ax.plot(x, y, color=SLOTS[0], linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2)
    for a, b in zip(x, y):
        ax.text(a, b + 3, fmt.format(b), ha="center", va="bottom", color=INK, fontsize=9.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 115)
    ax.set_xlim(-5, 105)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _pie(ax, labels, values, fmt):
    wedges, _ = ax.pie(values, colors=SLOTS[:len(values)], startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.42, edgecolor=SURFACE, linewidth=2))
    for w, label, v in zip(wedges, labels, values):
        ang = math.radians((w.theta1 + w.theta2) / 2)
        x, y = math.cos(ang), math.sin(ang)
        ax.annotate(f"{label}  {fmt.format(v)}", xy=(0.79 * x, 0.79 * y), xytext=(1.22 * x, 1.18 * y),
                    ha="left" if x >= 0 else "right", va="center", color=INK, fontsize=10,
                    arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))
    ax.set_aspect("equal")


def render(name, spec, outdir, fmt="svg"):
    kind = spec["kind"]
    if kind == "panels":
        panels = spec["panels"]
        rows = spec.get("rows", 1)
        cols = (len(panels) + rows - 1) // rows
        fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.0 * rows + 0.9),
                                 facecolor=SURFACE, squeeze=False)
        for i, (ax, p) in enumerate(zip([a for row in axes for a in row], panels)):
            _style(ax)
            if p.get("kind") == "delta":
                _delta(ax, spec["labels"], p["values"], show_labels=not spec.get("sharey") or i == 0,
                       vmax=max(abs(v) for q in panels for v in q["values"]))
            else:
                _barh(ax, p["labels"], p["values"], fmt=p["fmt"], highlight=p.get("highlight"))
            ax.set_title(p["title"], fontsize=10, color=INK, loc="left")
        top = 1 - 0.32 / (2.0 * rows + 0.9)
    else:
        height = {"pie": 4.2, "barh": 0.5 * len(spec.get("labels", [])) + 1.3,
                  "stacked": 0.6 * len(spec.get("labels", [])) + 1.8,
                  "grouped": 3.6, "line": 3.4}[kind]
        fig, ax = plt.subplots(figsize=(7.2, height), facecolor=SURFACE)
        _style(ax)
        if kind == "pie":
            _pie(ax, spec["labels"], spec["values"], spec["fmt"])
        elif kind == "barh":
            _barh(ax, spec["labels"], spec["values"], fmt=spec.get("fmt"),
                  value_labels=spec.get("value_labels"), highlight=spec.get("highlight"),
                  refline=spec.get("refline"))
        elif kind == "grouped":
            _grouped(ax, spec["groups"], spec["series"], spec["fmt"])
        elif kind == "stacked":
            _stacked(ax, spec["labels"], spec["components"], spec["totals"])
        elif kind == "line":
            _line(ax, spec["x"], spec["y"], spec["xlabel"], spec["ylabel"], spec["fmt"])
        top = 1 - 0.32 / height
    fig.suptitle(spec["title"], x=0.02, y=0.985, ha="left", va="top", fontsize=12, color=INK, fontweight="bold")
    fig.text(0.02, 0.01, spec["source"], fontsize=8, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.05, 1, top), pad=0.6)
    path = os.path.join(outdir, f"{name}.{fmt}")
    if fmt == "svg":
        fig.savefig(path, format="svg", facecolor=SURFACE,
                    metadata={"Title": spec["title"], "Description": f"Generated by {REGEN}",
                              "Date": None})  # no timestamp: re-runs stay diff-free
    else:
        fig.savefig(path, format="png", facecolor=SURFACE, dpi=110)
    plt.close(fig)
    return path


def check(outdir):
    script_mtime = os.path.getmtime(__file__)
    stale = []
    for name in CHARTS:
        path = os.path.join(outdir, name + ".svg")
        if not os.path.exists(path) or os.path.getmtime(path) < script_mtime:
            stale.append(name)
    for name in stale:
        print("STALE or MISSING:", name)
    print(f"{len(CHARTS) - len(stale)}/{len(CHARTS)} charts up to date")
    return 1 if stale else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", required=True, help="directory to write the SVG files into")
    parser.add_argument("--only", nargs="*", help="chart ids to render (default: all)")
    parser.add_argument("--check", action="store_true", help="only report missing or stale charts")
    parser.add_argument("--format", choices=["svg", "png"], default="svg",
                        help="svg for the repo (default); png only for previewing elsewhere")
    args = parser.parse_args()

    if args.check:
        sys.exit(check(args.outdir))
    unknown = [n for n in (args.only or []) if n not in CHARTS]
    if unknown:
        sys.exit(f"unknown chart id(s): {unknown}")
    os.makedirs(args.outdir, exist_ok=True)
    for name in args.only or CHARTS:
        render(name, CHARTS[name], args.outdir, args.format)
        print("wrote", f"{name}.{args.format}")


if __name__ == "__main__":
    main()
