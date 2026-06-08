# -*- coding: utf-8 -*-
"""
T6 — 부족 = 당일 투표율 초과로 설명되나?   [data/shortage_list.csv 필요]
읍면동별 '당일(선거일) 투표율'을 계산하고, 투표지 부족이 났던 읍면동이
'당일 투표율 상위 꼬리'에 몰리는지 본다. 정상 투표율인데 부족했던 읍면동을
별도 리스트로 출력(= 단순 과실로 설명 안 되는 이상치 후보).

shortage_list.csv 컬럼: [시도, 시군구, 읍면동, 투표소]
판정(FLAG): 부족 읍면동의 당일투표율 중앙값이 전체 상위 25%(75퍼센타일) 미만인데도
            부족이 다수 발생(= 투표율로 설명 안 됨) → 이상치 리스트 비어있지 않음.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

DATA = Path(__file__).resolve().parent.parent / ".." / "data" / "shortage_list.csv"
OUT = Path(__file__).resolve().parent.parent / "out"


def dayof_turnout(df, election_type):
    rows = []
    for _key, race in nd.iter_races(df, election_type):
        u = nd.units(race, nd.GUBUN_DAYOF)
        if not len(u):
            continue
        elec = u["선거인수"].replace(0, np.nan)
        t = u["투표수"] / elec
        for i in range(len(u)):
            rows.append((u["시도"].iloc[i], u["구시군"].iloc[i],
                         u["읍면동명"].iloc[i], float(t.iloc[i])))
    return pd.DataFrame(rows, columns=["시도", "구시군", "읍면동", "당일투표율"]).dropna()


def run(df, election_type, shortage_path=DATA):
    sp = Path(shortage_path)
    if not sp.exists():
        return {"test": "T6", "verdict": "SKIP",
                "msg": f"부족 투표소 목록 없음: {sp}"}
    short = pd.read_csv(sp).rename(columns={"시군구": "구시군"})
    base = dayof_turnout(df, election_type)
    if base.empty:
        return {"test": "T6", "verdict": "SKIP", "msg": "당일 투표율 계산 불가"}

    key = ["시도", "구시군", "읍면동"]
    base["k"] = base[key].astype(str).agg("|".join, axis=1)
    short["k"] = short[[c for c in key if c in short]].astype(str).agg("|".join, axis=1)
    hit = base[base["k"].isin(set(short["k"]))].copy()
    if len(hit) < 3:
        return {"test": "T6", "verdict": "SKIP", "msg": f"매칭 {len(hit)}개"}

    p75 = base["당일투표율"].quantile(0.75)
    # 정상 투표율(상위25% 미만)인데 부족했던 읍면동 = 과실로 설명 안 됨
    anomalies = hit[hit["당일투표율"] < p75].sort_values("당일투표율")
    OUT.mkdir(exist_ok=True)
    fp = OUT / f"T6_anomalies_{election_type}.csv"
    anomalies[["시도", "구시군", "읍면동", "당일투표율"]].to_csv(fp, index=False, encoding="utf-8-sig")
    return {
        "test": "T6", "race": election_type, "n_short": len(hit),
        "p75": round(float(p75), 4),
        "short_median": round(float(hit["당일투표율"].median()), 4),
        "n_anomaly": len(anomalies), "anomaly_file": str(fp),
        "verdict": "FLAG" if len(anomalies) > 0 else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "구시군의장"
    df = nd.load_type(etype)
    res = run(df, etype)
    print(f"[T6 부족 vs 당일투표율] {etype}")
    if res.get("verdict") == "SKIP":
        print("  SKIP:", res["msg"]); return
    print(f"  부족 {res['n_short']}개  부족중앙값={res['short_median']}  전체75%={res['p75']}")
    print(f"  투표율로 설명 안 되는 이상치 {res['n_anomaly']}개 → {res['anomaly_file']}")
    print(f"  → {res['verdict']}")


if __name__ == "__main__":
    main()
