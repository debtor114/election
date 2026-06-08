# -*- coding: utf-8 -*-
"""
T5 — 부족 투표소의 정치 편향 (순열검정)   [data/shortage_list.csv 필요]
'투표지 부족' 사전투표소가 있던 읍면동의 특정 정당 관내사전 득표율 평균을,
전체 읍면동에서 동수 무작위표본을 반복 추출한 분포(null)와 비교한다.

shortage_list.csv 컬럼: [시도, 시군구, 읍면동, 투표소]   (투표소는 선택)
판정(FLAG): 관측 평균이 순열분포의 양측 99.7%(±3σ) 밖.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

N_PERM = 20000
PARTY_DEFAULT = "국민의힘"   # --party 로 변경
DATA = Path(__file__).resolve().parent.parent / ".." / "data" / "shortage_list.csv"


def party_share_by_emd(df, election_type, party):
    """읍면동별 (시도,구시군,읍면동) → 해당 정당 관내사전 득표율."""
    rows = []
    for _key, race in nd.iter_races(df, election_type):
        cc = nd.cand_cols(race)
        pcols = [c for c in cc if party in c]
        if not pcols:
            continue
        u = nd.units(race, nd.GUBUN_EARLY)
        if not len(u):
            continue
        valid = u[nd.TOTAL_COL].replace(0, np.nan)
        share = u[pcols].sum(axis=1) / valid
        for i in range(len(u)):
            rows.append((u["시도"].iloc[i], u["구시군"].iloc[i],
                         u["읍면동명"].iloc[i], float(share.iloc[i])))
    return pd.DataFrame(rows, columns=["시도", "구시군", "읍면동", "share"]).dropna()


def run(df, election_type, party=PARTY_DEFAULT, shortage_path=DATA, seed=0):
    sp = Path(shortage_path)
    if not sp.exists():
        return {"test": "T5", "verdict": "SKIP",
                "msg": f"부족 투표소 목록 없음: {sp}  (컬럼: 시도,시군구,읍면동,투표소)"}
    short = pd.read_csv(sp)
    short = short.rename(columns={"시군구": "구시군"})
    base = party_share_by_emd(df, election_type, party)
    if base.empty:
        return {"test": "T5", "verdict": "SKIP", "msg": f"정당 '{party}' 컬럼 없음"}

    key = ["시도", "구시군", "읍면동"]
    base["k"] = base[key].astype(str).agg("|".join, axis=1)
    short["k"] = short[[c for c in key if c in short]].astype(str).agg("|".join, axis=1)
    hit = base[base["k"].isin(set(short["k"]))]
    k = len(hit)
    if k < 3:
        return {"test": "T5", "verdict": "SKIP",
                "msg": f"매칭된 부족 읍면동 {k}개 (목록/명칭 확인 필요)"}

    obs = hit["share"].mean()
    pool = base["share"].to_numpy()
    rng = np.random.default_rng(seed)
    null = np.array([rng.choice(pool, k, replace=False).mean() for _ in range(N_PERM)])
    mu, sd = null.mean(), null.std()
    z = (obs - mu) / sd if sd > 0 else 0.0
    p = float((np.abs(null - mu) >= abs(obs - mu)).mean())
    return {
        "test": "T5", "race": f"{election_type}/{party}", "n_short": k,
        "obs": round(obs, 4), "null_mu": round(mu, 4), "sigma": round(z, 2),
        "p_two": round(p, 4),
        "verdict": "FLAG" if abs(z) > 3 else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "구시군의장"
    party = sys.argv[2] if len(sys.argv) > 2 else PARTY_DEFAULT
    df = nd.load_type(etype)
    res = run(df, etype, party)
    print(f"[T5 부족투표소 편향] {etype} / {party}")
    if res.get("verdict") == "SKIP":
        print("  SKIP:", res["msg"]); return
    print(f"  부족읍면동 {res['n_short']}개  관측={res['obs']}  기대={res['null_mu']}"
          f"  = {res['sigma']:+}σ  (p={res['p_two']})  → {res['verdict']}")


if __name__ == "__main__":
    main()
