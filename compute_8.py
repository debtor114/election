# -*- coding: utf-8 -*-
"""
compute_8.py — 동일득표 8건 각각의 per-pair 확률을 닫힌 공식으로 계산.

P(두 동에서 상위2 후보가 동시 일치)
  ≈ 1 / ( 2π · (T1+T2) · sqrt(pA · pB · pO) )      ... 이변량 정규 근사
  (pA,pB = 상위2 득표율, pO = 1-pA-pB = 기타+무효, T = 투표인수)

이 공식은 '두 동이 같은 득표율의 표본'이라는 가정의 충돌확률이며, 두 동 크기가
비슷할 때 정확합니다. 크기 차가 크면 정확값은 달라지나 자릿수는 비슷하고,
최종 판단은 per-pair가 아니라 census_significance.py(관측 vs 우연기대)로 합니다.

methodology.html 의 8건 표가 이 출력입니다.
"""
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd

TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]
MINVAL = 100


def find_cases():
    out = []
    for et in TYPES:
        df = nd.load_type(et)
        for key, race in nd.iter_races(df, et):
            cc = nd.cand_cols(race)
            if len(cc) < 2:
                continue
            order = race[cc].sum().sort_values(ascending=False).index[:2].tolist()
            u = nd.units(race, nd.GUBUN_EARLY)
            if len(u) < 2:
                continue
            g = defaultdict(list)
            for idx, row in u.iterrows():
                v = (int(row[order[0]]), int(row[order[1]]))
                if v[0] >= MINVAL:
                    g[v].append(idx)
            for v, idxs in g.items():
                if len(idxs) >= 2:
                    out.append((et, nd.race_label(key), order, u.loc[idxs[0]], u.loc[idxs[1]], v))
    return out


def pair_prob(T1, T2, pA, pB, pO):
    return 1.0 / (2 * np.pi * (T1 + T2) * np.sqrt(pA * pB * pO))


def main():
    cases = find_cases()
    cases.sort(key=lambda x: -x[5][0])
    print(f"{'#':<3}{'선거/두 동':<30}{'동시 일치 값':<26}{'T1,T2':>14}{'per-pair P':>12}")
    print("-" * 88)
    for n, (et, lab, order, r1, r2, v) in enumerate(cases, 1):
        T1, T2 = int(r1["투표수"]), int(r2["투표수"])
        pA = (int(r1[order[0]]) + int(r2[order[0]])) / (T1 + T2)
        pB = (int(r1[order[1]]) + int(r2[order[1]])) / (T1 + T2)
        pO = max(1 - pA - pB, 1e-9)
        P = pair_prob(T1, T2, pA, pB, pO)
        nm = [c.replace(nd.CAND_PREFIX, "").replace("더불어민주당 ", "").replace("국민의힘 ", "")
              for c in order]
        emds = f"{et} {r1['읍면동명']}·{r2['읍면동명']}"
        vals = f"{nm[0]}={v[0]} {nm[1]}={v[1]}"
        print(f"{n:<3}{emds:<30}{vals:<26}{f'{T1},{T2}':>14}{'1/' + format(round(1/P), ','):>12}")
    print("\n전부 1/수백~1/수천 (1/백만이 아님). 송도가 가장 드뭄(투표소 최대 + 두 값 다 큼).")
    print("최종 판단: census_significance.py — 충실 모수식 기대 ~4.2 vs 관측 8 (+1.9σ, p≈0.07 약한 초과);")
    print("           관대한 교환식 기대 ~10.8 기준으론 이내. null에 흔들리는 약한 검정 — 복제·방향성으로 보강.")


if __name__ == "__main__":
    main()
