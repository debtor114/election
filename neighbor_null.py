# -*- coding: utf-8 -*-
"""
neighbor_null.py — '유사-이웃 통제' null
단순 null은 한 선거의 모든 읍면동을 '교환가능'으로 봐서, 인접·유사 동(송도1·2동처럼
유권자·득표율이 거의 같은)에서 같은 값이 나올 확률을 과소평가할 수 있다.

여기서는 정반대로, 닮은-이웃 가설에 *최대한 유리하게* 본다:
  "두 읍면동이 인구학적으로 완전히 똑같다(=진짜 득표율이 동일한 쌍둥이)"고 가정하고,
  각 동의 득표를 다항분포(총 투표수, 공통 득표율)로 뽑아, 관측된 '동시 일치'가
  얼마나 자주 나오는지 본다.
  → 쌍둥이로 가정해도 드물면, 유사성으로 설명되지 않는다(진짜 이상치).
  → 쌍둥이로 가정하니 흔하면, 유사성으로 설명된다.

census_duplicates.py가 찾은 8건 각각에 대해 P(top2 동시 일치 | 쌍둥이) 를 계산.
"""
import sys
import warnings
from pathlib import Path
from collections import defaultdict
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd

TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]
TOPK, MINVAL, NSIM = 2, 100, 200000


def find_cases():
    cases = []
    for etype in TYPES:
        try:
            df = nd.load_type(etype)
        except FileNotFoundError:
            continue
        for key, race in nd.iter_races(df, etype):
            cc = nd.cand_cols(race)
            if len(cc) < TOPK:
                continue
            order = race[cc].sum().sort_values(ascending=False).index[:TOPK].tolist()
            u = nd.units(race, nd.GUBUN_EARLY)
            if len(u) < 2:
                continue
            groups = defaultdict(list)
            for ridx, row in u.iterrows():
                vals = tuple(int(row[c]) for c in order)
                if vals[0] >= MINVAL:
                    groups[vals].append(ridx)
            for vals, idxs in groups.items():
                if len(idxs) >= 2:
                    cases.append((etype, nd.race_label(key), race, cc, order, u, idxs, vals))
    return cases


def twin_pmatch(u, cc, order, i, j, rng):
    """두 동이 쌍둥이(공통 득표율)라 가정했을 때 top2 동시 일치 확률 (MC)."""
    Ti = int(u.loc[i, "투표수"]); Tj = int(u.loc[j, "투표수"])
    Vi = u.loc[i, cc].fillna(0).to_numpy(dtype=int)
    Vj = u.loc[j, cc].fillna(0).to_numpy(dtype=int)
    # 잔여(무효 등) 칸 포함, 두 동 합산으로 공통 득표율 추정 (쌍둥이)
    ri = max(Ti - Vi.sum(), 0); rj = max(Tj - Vj.sum(), 0)
    cnt = np.append(Vi + Vj, ri + rj).astype(float)
    p = cnt / cnt.sum()
    oi = [cc.index(c) for c in order]                  # top2 컬럼 위치
    Xi = rng.multinomial(Ti, p, size=NSIM)             # (NSIM, K+1)
    Xj = rng.multinomial(Tj, p, size=NSIM)
    match = np.ones(NSIM, dtype=bool)
    for c in oi:
        match &= (Xi[:, c] == Xj[:, c])
    return match.mean(), Ti, Tj


def count_national_pairs():
    """전국 unit-쌍(관내사전, 한 선거 안) 총 개수 — 룩-엘스웨어 분모."""
    total = 0
    for etype in TYPES:
        try:
            df = nd.load_type(etype)
        except FileNotFoundError:
            continue
        for _key, race in nd.iter_races(df, etype):
            m = len(nd.units(race, nd.GUBUN_EARLY))
            total += m * (m - 1) // 2
    return total


def main():
    rng = np.random.default_rng(0)
    cases = find_cases()
    cases.sort(key=lambda x: -x[7][0])
    pairs_total = count_national_pairs()
    print(f"유사-이웃(쌍둥이) 통제 null — top{TOPK} 동시 일치 확률 (MC {NSIM:,}회)\n")
    print(f"{'선거/두 동':<34}{'일치값':<24}{'P(쌍둥이여도 일치)':>18}")
    print("-" * 80)
    for etype, lab, race, cc, order, u, idxs, vals in cases:
        i, j = idxs[0], idxs[1]
        p, Ti, Tj = twin_pmatch(u, cc, order, i, j, rng)
        emds = f"{u.loc[i,'읍면동명']}·{u.loc[j,'읍면동명']}"
        names = [c.replace(nd.CAND_PREFIX, '') for c in order]
        vstr = " ".join(f"{n}={v}" for n, v in zip(names, vals))
        odds = f"1/{round(1/p):,}" if p > 0 else f"<1/{NSIM:,}"
        print(f"{etype+' '+emds:<34}{vstr:<24}{odds:>18}")
    print("-" * 80)
    print(f"\n[중요 — 사후 선택(look-elsewhere) 보정]")
    print(f"  위 확률은 '이미 일치한 쌍'만 골라 계산한 per-pair 값이라, 작아 보이는 게 당연하다.")
    print(f"  전국 unit-쌍은 약 {pairs_total:,}개. 이만큼 비교하면 개별적으로 드문 일치도 여러 건 나온다.")
    print(f"  단, 기대는 null에 따라 갈린다(census_significance: 충실 모수식 ~4.2 / 관대 교환식 ~10.8).")
    print(f"  관측 8은 충실 null(~4.2)은 +1.9σ로 다소 넘고, 교환식(~10.8)엔 못 미친다 = 약한 검정.")
    print(f"  → '쌍둥이여도 드물다'가 곧 '이상'은 아니며, 형제(연번) 동만 보면 관측 1 < 기대 2.8로 오히려 적다.")
    print(f"\n  유일하게 per-race null에서 따로 튀는 건 인천(+6σ): 두 값(3030·1440)이 모두 커서다.")
    print(f"  단, 인천도 인접-유사 동을 통제하면 유의성이 약해지며, 이 데이터만으론 단정 불가.")


if __name__ == "__main__":
    main()
