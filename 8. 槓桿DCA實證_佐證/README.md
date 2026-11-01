# Leverage DCA Proof — 歸檔說明（給未來的 AI 讀）

## 1. 這是什麼

這個資料夾是「**大跌後 DCA 槓桿 ETF**」投資策略的回測佐證歸檔。
主報告是上層目錄的 `8. 槓桿DCA實證.md`（即 `0. 投資心法總綱.md` 第 4 點的實證附件），2026-11-01 起是白話精簡版；
改寫前的完整技術版（全部表格、兩個旋鈕的測試、1929 情境、世代穩健性、候選標的完整比較）在本資料夾的 `完整技術版.md`。
研究問題：「深跌時把每月新錢改投槓桿、B&H 死抱、回前高再切回原型」這套策略，
在美國（S&P）、全球（VT）、日本（日經）三個市場、橫跨 1929 大蕭條與日本失落世代，
是否、以及在什麼條件下，能贏過「全程只 DCA 原型」的基準。

## 2. 策略機制（state machine）

- 兩個狀態，依 underlying 相對 running ATH 的 drawdown 切換：
  - `NORMAL`：每月新錢買 **prototype**（1x underlying total return）。
  - `LEVERAGED`：每月新錢買 **leveraged ETF**（2x / 3x，每日重置，已校準）。
- `NORMAL → LEVERAGED`：drawdown 跌破 `-trigger`（推薦 -30%）時進場。
- `LEVERAGED → NORMAL`：underlying 回到 `recover × priorPeak`（推薦 80%）時切回。
- 兩個 sleeve（prototype units、leveraged units）各自累積、各自 **B&H，永不互換**（不 swap、不賣原型換槓桿）。
- **基準（baseline）= 全程只 DCA 原型**，就是策略必須打敗的對象。
- 槓桿日報酬模型：`r_l = lev × r_u − (expense + (lev−1)×financing + calib) / periods`。

## 3. 每個檔案的角色

### 腳本（.py）

| 檔案 | 做什麼 | 輸出 |
|---|---|---|
| `strategy_sim.py` | 單組設定的狀態機模擬（吃 `--under` underlying csv + 槓桿參數） | 單一情境比較文字檔 |
| `matrix.py` | 全矩陣回測：市場 × 槓桿 × trigger × recover | 一張總比較表（含 lev$% 真實曝險） |
| `cohort.py` | 世代穩健性：滾動多個起始日各跑到資料末，算勝率與中位 edge，擋「單一好運起點」偏誤 | 各市場勝率/中位 edge 表 |
| `cap_test.py` | 硬上限熔斷測試（鐵則④）：對最慘路徑（日經 1970 起、坐在 1989 泡沫頂）測上限能否鎖住曝險、犧牲多少報酬 | 上限前後曝險/報酬對比 |
| `validate_lev.py` | 引擎校準：模擬槓桿 vs 真實 LETF 逐日對帳（相關性、tracking error、終值差） | 校準報告文字檔 |
| `tier_sgov.py` | 實際執行規則：10% SGOV 乾火藥、-20/-30/-50% 三段動用 + 新錢切換 + 現金上限；含「SGOV 改買 1x」對照組與滾動世代 | 各市場 A/B/C/D 比較表 + 世代表（`--exp 0.0075` 為 WLDU 費用率） |
| `fetch_yahoo.py` | 輔助：從 Yahoo Finance 抓全歷史日頻 adjclose（產生 vt/spy/n225/sso/upro/irx 等） | 標的 csv（`Date,AdjClose`） |
| `shiller_to_tr.py` | 輔助：把 Shiller 原始月頻資料（`shiller_raw.csv`）轉成 S&P 月頻 total-return 指數 | `spx_tr_monthly.csv` |

### 資料（.csv，統一欄位 `Date,AdjClose`）

| 檔案 | 內容 | 時間範圍 | 來源 |
|---|---|---|---|
| `vt.csv` | VT 全球股票（total return proxy） | 2008– | Yahoo (`fetch_yahoo.py`) |
| `spy.csv` | SPY，S&P 500 日頻，校準與日頻美股回測用（腳本標籤 `S&P 1993`） | 1993-01-29– | Yahoo |
| `spx_tr_monthly.csv` | S&P 500 月頻含股息 total return | 1927– | Shiller (`shiller_to_tr.py`) |
| `shiller_raw.csv` | Shiller 原始月頻資料（SP500 價格 + Dividend），`spx_tr_monthly.csv` 的輸入 | 1871– | Robert Shiller 資料集 |
| `n225.csv` | 日經 225 價格指數（不含股息），測失落世代最慘路徑；融資成本固定用 0.5% | 1970– | Yahoo |
| `irx.csv` | 13 週美國國庫券利率（融資成本 proxy） | 長歷史 | Yahoo |
| `sso.csv` | 真實 2x S&P LETF（ProShares SSO），校準對照 | ~2006– (20y) | Yahoo |
| `upro.csv` | 真實 3x S&P LETF（ProShares UPRO），校準對照 | ~2009– (17y) | Yahoo |

## 4. 怎麼重跑

**環境**：Python 3.9+（以 3.11 重跑驗證過）、pandas + numpy。
所有腳本用 `argparse`，輸出走 `--out`，**不要用 shell 重導向**。

範例（在本資料夾內執行；資料 csv 一律從腳本所在資料夾讀取，從別的目錄執行也可以）：

```bash
# 引擎校準（2x vs SSO）
python validate_lev.py --under spy.csv --real sso.csv --lev 2 --exp 0.0091 --calib 0.0065 --name SSO --out validate_2x.txt

# 單組狀態機（S&P 月頻、2x、-30% 進場、80% 切回）
python strategy_sim.py --under spx_tr_monthly.csv --name SP --lev 2 --calib 0.0065 --trigger 0.30 --recover 0.80 --freq monthly --out sim_sp_2x.txt

# 全矩陣 / 世代 / 硬上限
python matrix.py --out matrix.txt
python cohort.py --out cohort.txt
python cap_test.py --out cap.txt

# 實際執行規則（三段 SGOV + 新錢，WLDU 費用率）
python tier_sgov.py --exp 0.0075 --out tier.txt
# 同樣的規則，槓桿腳改用真實 SSO 價格（觸發與原型仍用 VT）
python tier_sgov.py --market vt --leg-csv sso.csv --out tier_vt_sso.txt
# 槓桿腳用「另一個指數的 2x 模型」：XS2D（2x S&P，費用 0.60%）；--exp 0.0091 可驗證模型 vs 真實 SSO
python tier_sgov.py --market vt --leg-under spy.csv --exp 0.0060 --out tier_vt_xs2d.txt
```

資料路徑：`matrix.py`、`cohort.py`、`cap_test.py` 的市場資料與所有腳本的 `irx.csv` 都從**腳本所在資料夾**讀取；
`strategy_sim.py` / `validate_lev.py` 的 underlying / real csv 由 `--under` / `--real` 傳入（相對於目前工作目錄）。

## 5. 校準可信度

引擎與真實 LETF 逐日對帳：**2x vs SSO 日報酬相關 0.9956**、**3x vs UPRO 0.9983**（皆 >0.99）。
這是整份報告的命脈：模擬的槓桿報酬**逐日行為**幾乎完全貼合真實 ETF。
終值：2x（calib 0.65%）與 SSO 差 **+0.0%**；3x（calib 1.20%）與 UPRO 差 **+0.2%**（119.80x vs 119.56x）。
calib 是用 SSO / UPRO 的實際終值反推的，所以終值吻合是校準結果、不是獨立驗證；獨立證據是逐日相關性。
3x 若誤用 2x 的 calib 0.65%，終值會高估約 10%（131.5x）——回測腳本的 `CALIB = {2: 0.0065, 3: 0.012}` 已分開設定，3x 數字沒有系統性偏樂觀。

## 6. 關鍵結論

- **報酬靠 recover、風險靠現金硬上限，兩旋鈕分工。** `recover=100%` 報酬明顯較高（S&P 1993、2x：+51% vs 80% 的 +34%），但 80% 在正常市場的曝險低很多 → 選 80%（少賺一截換睡得著），而且它**擋不住最慘路徑**。
- **現金硬上限 10% 才鎖得住曝險**：累積丟進槓桿的錢 ≤ 總投入 10%、丟滿就停。**市值上限會在長熊自我失靈**（日經投入槓桿的現金仍達 23.8%），現金上限才把日經鎖在 9.5%。
- **代價**：10% 現金上限下，edge 剩美股 +12.0% / +30.4%（2x / 3x）、**全球 VT +2.2% / +5.2%**、日經 +0.5% / +0.2%。
- **世代表**：所有「沒贏」的世代都是從沒買過槓桿（edge = 0），沒有任何世代輸給基準（`cohort.py` 的 `edge min` / `no-trig` 欄）。日經 recover 80% 的槓桿現金佔比中位數 45.6%。
- **日經最慘路徑**（1989 泡沫頂起跌）：光靠 recover=80% 曝險仍從失控的 **59% 暴衝**，加上現金硬上限後壓到 **9.5%**。
- **資料限制**：`shiller_raw.csv` 自 2023-07 起股息欄為 0（最後約 35 個月只有價格報酬）；日經全程用 0.5% 融資利率，低估 1970–95 的融資成本。
- **槓桿必須是衛星、不可主體化**：DCA 救得了新錢救不了存量，報酬遞減但風險線性放大，主體化會在最低點逼人砍倉。核心永遠是原型。
