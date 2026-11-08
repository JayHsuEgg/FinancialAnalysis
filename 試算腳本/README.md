# 試算腳本

各篇文件裡「自行計算」的數字,由這裡的腳本產生(2026-11 勘誤時使用)。槓桿回測的腳本另在 [`8. 槓桿DCA實證_佐證/`](../8.%20槓桿DCA實證_佐證/)。

所有腳本都用 `argparse` 傳入輸入與輸出路徑,不要用 shell 重導向。環境:Python 3.11、pandas(只有讀 csv 的腳本需要)。

| 腳本 | 對應文件 | 產生的數字 | 範例 |
|---|---|---|---|
| `f2_recalc.py` | 檔 2 | 0050 vs 連結基金 10 年內扣、交易、稅務成本;各稅率級距總成本;二代健保門檻本金 | `python f2_recalc.py --out f2.txt`(預設殖利率 1.24%;`--yld 0.025` 為敏感度) |
| `f3_case_recalc.py` | 檔 3 換股案例 | VWRA 換 VALU 三條路線 10 年終值 | `python f3_case_recalc.py --tv 0.14 --ta 0.07 --out valu.txt` |
| `f4_recalc.py` | 檔 4 | AVGS vs AVUV+AVDV 年拖累(含 AVDV 來源國那層)、10 年情境 | `python f4_recalc.py --out f4.txt` |
| `f_misc.py` | 檔 0、1、4、6、8、Sin A Little | 雜項驗算:BTC 換倉 10 年優勢、槓桿耗損公式、BTC 權重漂移、XBI 報酬等 | `python f_misc.py --out misc.txt` |
| `f8_2008.py` | 檔 8 | 2007-10 → 2009-03 SPY / SSO 跌幅、衛星部位對總資產的額外拖累 | `python f8_2008.py --spy "../8. 槓桿DCA實證_佐證/spy.csv" --sso "../8. 槓桿DCA實證_佐證/sso.csv" --out f8.txt` |
| `allin_n225.py` | 檔 8 | 日經 -30% / -50% 時 all-in 原型 vs 2x / 3x 的終值與最大回檔 | `python allin_n225.py --n225 "../8. 槓桿DCA實證_佐證/n225.csv" --out allin.txt` |
| `dd_check.py` | 檔 8 | 各資料序列的起訖日與最大回檔(如月頻含息 S&P 1929 回檔 -81.8%、`spy.csv` 起始 1993-01-29) | `python dd_check.py --csv "../8. 槓桿DCA實證_佐證/spx_tr_monthly.csv" --csv "../8. 槓桿DCA實證_佐證/spy.csv" --out dd.txt` |
| `withdrawal_sim.py` | 檔 11、1 | 美股百年(Shiller,實質)各種提領方式 30 / 40 年錢花光的機率、期末財富、最低收入 | `python withdrawal_sim.py --shiller "../8. 槓桿DCA實證_佐證/shiller_raw.csv" --out wd.txt`(`--cash-real 0.01` 為現金報酬敏感度) |
| `claims_check.py` | 檔 1、6、8 | 各序列 20% 以上的跌幅與回到前高的時間、VT 與 SPY 的相關性與年化報酬、irx 2020 低點 / 2023 高點 | `python claims_check.py --dir "../8. 槓桿DCA實證_佐證" --out claims.txt` |
| `vol_check.py` | 檔 6 | 各資料序列的年化波動:全期、近 1 / 5 年、單一曆年分布(如 VT 全期 20.6%、近 5 年 16.2%) | `python vol_check.py --csv "../8. 槓桿DCA實證_佐證/vt.csv" --out vol.txt` |

> `f_misc.py` 是勘誤時的驗算腳本,部分輸入是舊版文件的數字(用來檢查舊版算式能否重現),讀輸出時請對照註解。
