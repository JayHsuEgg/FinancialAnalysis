# 圖表

各篇文件裡的長條圖、折線圖都由 `make_charts.py` 產生,**不要手改 SVG**。

```
python 圖表/make_charts.py --outdir 圖表            # 重畫全部
python 圖表/make_charts.py --outdir 圖表 --check    # 列出缺少或比腳本舊的圖
python 圖表/make_charts.py --outdir <暫存目錄> --format png   # 只用來預覽
```

- 數字寫在腳本的 `CHARTS` 裡,從文件抄過來,每張圖底下註明出處。**改文件的數字時,這裡也要改、重畫,並在同一個 commit 更新 [`資料來源紀錄.md`](../資料來源紀錄.md)。**
- 文字轉成路徑輸出(`svg.fonttype=path`),沒裝中文字型也能正常顯示。
- 背景是不透明淺色,在 GitHub 深色模式下也看得清楚。
- 環境:Python 3.11 + matplotlib;字型 Noto Sans TC(沒有時改用微軟正黑體)。

| 圖 | 用在 |
|---|---|
| `allocation_main` | 檔 0、1 |
| `allocation_parents` | 檔 1 |
| `paper_savings` | 檔 0、10、README |
| `paper_ruin`、`paper_variance_ratio`、`paper_us_belief` | 檔 10 |
| `paper_ruin_conditional` | 檔 1、10 |
| `f2_total_cost` | 檔 2 |
| `f3_annual_cost`、`f3_switch` | 檔 3 |
| `f4_drag`、`f4_geo` | 檔 4 |
| `f6_btc_etf`、`f6_drawdown` | 檔 6 |
| `f8_leverage` | 檔 0、8 |
| `f9_blv_bnd` | 檔 9 |
