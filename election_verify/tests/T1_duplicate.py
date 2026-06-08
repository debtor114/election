# -*- coding: utf-8 -*-
"""
T1 — 동일 득표 전수 검정
race(후보집합 동일 단위) 안에서, 특정 구분(기본 관내사전투표)의 읍면동들 사이
동일 득표 쌍을 ①한 후보 ②상위2후보 ③전후보+계(복제) 기준으로 집계하고,
'총표 고정 + 득표율 부트스트랩' null과 비교해 몇 σ인지 출력한다.

판정(FLAG): 상위2 동일쌍 z>+3  또는  방향성 z>+3  또는  복제쌍 ≥ 1.
"""
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

SIGMA_FLAG = 3.0
N_SIM = 2000


def pair_count(values):
    """동일값 쌍 수 = Σ C(k,2)."""
    return sum(c * (c - 1) // 2 for c in Counter(values).values())


def run(race_df, election_type, gubun=nd.GUBUN_EARLY, seed=0):
    cc = nd.cand_cols(race_df)
    u = nd.units(race_df, gubun)
    n = len(u)
    if n < 4 or len(cc) < 2:
        return None  # 표본 부족

    V = u[cc].fillna(0).to_numpy(dtype=int)        # (n, c)
    totals = V.sum(axis=1)

    # ① 한 후보 단독 동일
    single = {cc[i]: pair_count(V[:, i]) for i in range(len(cc))}
    # ② 상위2후보 동시 동일
    top2 = [tuple(sorted(r)[-2:]) for r in V]
    top2_pairs = pair_count(top2)
    # ③ 전후보+계 동일(복제)
    full = [tuple(int(x) for x in V[i]) + (int(totals[i]),) for i in range(n)]
    dup_pairs = pair_count(full)

    # null: 총표 고정 + 득표율 부트스트랩
    rng = np.random.default_rng(seed)
    safe = totals.copy(); safe[safe == 0] = 1
    shares = V / safe[:, None]
    sims = np.empty(N_SIM)
    for k in range(N_SIM):
        idx = rng.integers(0, n, n)
        sim = np.round(totals[:, None] * shares[idx]).astype(int)
        sims[k] = pair_count([tuple(sorted(r)[-2:]) for r in sim])
    mu, sd = sims.mean(), sims.std()
    z = (top2_pairs - mu) / sd if sd > 0 else 0.0

    # 방향성: 상위2 동일쌍에서 '전체 1위 후보'가 두 단위 모두 1위인 비율
    win = race_df[cc].sum().idxmax()
    wi = cc.index(win)
    groups = {}
    for i, k in enumerate(top2):
        groups.setdefault(k, []).append(i)
    favor = M = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        for i, j in combinations(members, 2):
            M += 1
            if V[i].argmax() == wi and V[j].argmax() == wi:
                favor += 1
    # 경험적 기준선 p = 단위에서 승자가 1위일 확률 (정파성 통제)
    p1 = float((V.argmax(axis=1) == wi).mean())
    mu_d, sd_d = M * p1 * p1, (M * (p1 * p1) * (1 - p1 * p1)) ** 0.5
    zd = (favor - mu_d) / sd_d if sd_d > 0 else 0.0

    flag = (z > SIGMA_FLAG) or (zd > SIGMA_FLAG) or (dup_pairs >= 1)
    return {
        "test": "T1", "race": "",
        "n_units": n, "n_cand": len(cc),
        "single_max": max(single.values()),
        "top2_obs": top2_pairs, "top2_mu": round(mu, 2), "top2_sd": round(sd, 2),
        "top2_sigma": round(z, 2),
        "dir_obs": favor, "dir_M": M, "dir_sigma": round(zd, 2),
        "dup_pairs": dup_pairs,
        "verdict": "FLAG" if flag else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "구시군의장"
    gubun = sys.argv[2] if len(sys.argv) > 2 else nd.GUBUN_EARLY
    df = nd.load_type(etype)
    print(f"[T1 동일득표] {etype} / 구분={gubun}\n")
    hdr = f"{'race':<22}{'n':>4}{'상위2관측':>8}{'기대':>8}{'σ':>7}{'방향σ':>7}{'복제':>5}  판정"
    print(hdr); print("-" * len(hdr))
    flags = 0
    for key, race in nd.iter_races(df, etype):
        res = run(race, etype, gubun)
        if not res:
            continue
        res["race"] = nd.race_label(key)
        if res["verdict"] == "FLAG":
            flags += 1
        print(f"{res['race'][:21]:<22}{res['n_units']:>4}{res['top2_obs']:>8}"
              f"{res['top2_mu']:>8.1f}{res['top2_sigma']:>7.1f}{res['dir_sigma']:>7.1f}"
              f"{res['dup_pairs']:>5}  {res['verdict']}")
    print(f"\nFLAG {flags}건 / 나머지 PASS. "
          f"(PASS=우연 모델 기대 범위 내, FLAG=기대치 초과→추가 확인. 어느 쪽도 결론 아님)")


if __name__ == "__main__":
    main()
