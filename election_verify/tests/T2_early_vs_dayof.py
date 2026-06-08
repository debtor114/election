# -*- coding: utf-8 -*-
"""
T2 — 사전(관내) vs 본(선거일) 득표율 격차의 '일정함' 검정
읍면동별로 후보의 관내사전 득표율과 선거일 득표율을 구해 회귀(early ~ dayof).
정상 데이터는 흩어짐(잔차)이 크다. 비정상적으로 완벽한 직선(R²≈1 & 잔차≈0)이면 FLAG.

판정(FLAG): 어떤 후보든 R² > 0.999 그리고 잔차표준편차 < 0.005.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

R2_FLAG = 0.999
RESID_FLAG = 0.005


def shares(race_df, gubun, cc):
    u = nd.units(race_df, gubun)[["읍면동명"] + cc + [nd.TOTAL_COL]].copy()
    u = u.set_index("읍면동명")
    tot = u[nd.TOTAL_COL].replace(0, np.nan)
    return u[cc].div(tot, axis=0)


def run(race_df, election_type):
    cc = nd.cand_cols(race_df)
    if len(cc) < 1:
        return None
    se = shares(race_df, nd.GUBUN_EARLY, cc)
    sd = shares(race_df, nd.GUBUN_DAYOF, cc)
    common = se.dropna(how="all").index.intersection(sd.dropna(how="all").index)
    if len(common) < 5:
        return None
    se, sd = se.loc[common], sd.loc[common]

    win = race_df[cc].sum().idxmax()
    worst = {"cand": None, "r2": 0.0, "resid": 1.0}
    gaps = []
    for c in cc:
        x = sd[c].to_numpy(); y = se[c].to_numpy()
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 5 or np.nanstd(x[m]) == 0:
            continue
        x, y = x[m], y[m]
        b1, b0 = np.polyfit(x, y, 1)
        yhat = b1 * x + b0
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        resid = float(np.sqrt(ss_res / len(x)))
        gaps.append(float(np.mean(y - x)))
        # '가장 완벽한 직선' 후보 추적
        if r2 > worst["r2"] or (r2 == worst["r2"] and resid < worst["resid"]):
            worst = {"cand": c.replace(nd.CAND_PREFIX, ""), "r2": r2, "resid": resid}

    win_x = sd[win].to_numpy(); win_y = se[win].to_numpy()
    m = np.isfinite(win_x) & np.isfinite(win_y)
    gap_mean = float(np.mean(win_y[m] - win_x[m])) if m.any() else float("nan")
    gap_std = float(np.std(win_y[m] - win_x[m])) if m.any() else float("nan")

    flag = worst["r2"] > R2_FLAG and worst["resid"] < RESID_FLAG
    return {
        "test": "T2", "race": "", "n_units": len(common),
        "max_r2": round(worst["r2"], 4), "min_resid": round(worst["resid"], 4),
        "r2_cand": worst["cand"],
        "win_gap_mean": round(gap_mean, 3), "win_gap_std": round(gap_std, 3),
        "verdict": "FLAG" if flag else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "구시군의장"
    df = nd.load_type(etype)
    print(f"[T2 사전vs본] {etype}\n")
    hdr = f"{'race':<22}{'n':>4}{'maxR²':>8}{'잔차':>8}{'승자격차μ':>9}{'격차σ':>8}  판정"
    print(hdr); print("-" * len(hdr))
    flags = 0
    for key, race in nd.iter_races(df, etype):
        res = run(race, etype)
        if not res:
            continue
        res["race"] = nd.race_label(key)
        flags += res["verdict"] == "FLAG"
        print(f"{res['race'][:21]:<22}{res['n_units']:>4}{res['max_r2']:>8.3f}"
              f"{res['min_resid']:>8.3f}{res['win_gap_mean']:>9.3f}{res['win_gap_std']:>8.3f}"
              f"  {res['verdict']}")
    print(f"\nFLAG {flags}건 (정상: 잔차가 충분히 흩어짐)")


if __name__ == "__main__":
    main()
