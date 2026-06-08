# -*- coding: utf-8 -*-
"""
census_significance.py — "전국 8건"이 우연보다 많은가?
census_duplicates.py와 똑같은 기준(상위2후보 동시 동일 & 1위>=MINVAL)으로,
각 race에서 관측 건수와 부트스트랩 null(득표율 재추출) 건수를 구해 전국 합을 비교한다.

출력: 관측 총건수 vs 우연 기대 분포(평균±sd), σ, p. + 인천만 따로.
"""
import sys
from pathlib import Path
from collections import Counter
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd

TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]
TOPK, MINVAL, NSIM = 2, 100, 1500


def census_pairs(M, top_idx, minval):
    """상위2(고정 후보) 동시 동일 & 1위>=minval 인 쌍 수."""
    keys = [tuple(int(M[r, c]) for c in top_idx) for r in range(M.shape[0])]
    groups = Counter(k for k in keys if k[0] >= minval)
    return sum(n * (n - 1) // 2 for n in groups.values())


def main():
    rng = np.random.default_rng(0)
    obs_total = 0
    sim_total = np.zeros(NSIM)
    obs_incheon = 0
    sim_incheon = np.zeros(NSIM)
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
            top_idx = [cc.index(c) for c in order]
            u = nd.units(race, nd.GUBUN_EARLY)
            if len(u) < 2:
                continue
            V = u[cc].fillna(0).to_numpy(dtype=int)
            T = u[nd.TOTAL_COL].fillna(0).to_numpy(dtype=int)
            o = census_pairs(V, top_idx, MINVAL)
            obs_total += o
            is_incheon = (etype == "시도지사" and nd.race_label(key) == "인천")
            if is_incheon:
                obs_incheon += o
            # 부트스트랩 null
            safe = T.copy(); safe[safe == 0] = 1
            sh = V / safe[:, None]
            n = len(V)
            for k in range(NSIM):
                idx = rng.integers(0, n, n)
                sim = np.round(T[:, None] * sh[idx]).astype(int)
                c = census_pairs(sim, top_idx, MINVAL)
                sim_total[k] += c
                if is_incheon:
                    sim_incheon[k] += c

    def report(name, obs, sims):
        mu, sd = sims.mean(), sims.std()
        z = (obs - mu) / sd if sd > 0 else float("nan")
        p = float((sims >= obs).mean())
        print(f"{name}: 관측 {obs}건 | 우연 기대 {mu:.2f} ± {sd:.2f} | {z:+.1f}σ | p(이상 발생) = {p:.4f}")

    print(f"기준: 상위{TOPK}후보 동시 동일 & 1위>={MINVAL}  (부트스트랩 {NSIM}회)\n")
    report("전국 전체", obs_total, sim_total)
    report("인천 시도지사만", obs_incheon, sim_incheon)
    report("인천 제외 전국", obs_total - obs_incheon, sim_total - sim_incheon)


if __name__ == "__main__":
    main()
