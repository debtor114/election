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
    sim_exch = np.zeros(NSIM)
    sim_param = np.zeros(NSIM)
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
            T = u["투표수"].fillna(0).to_numpy(dtype=int)   # 투표수(=총표) 기준
            o = census_pairs(V, top_idx, MINVAL)
            obs_total += o
            n = len(V)
            # null 1: 교환식(득표율을 풀에서 재추출) — 같은 율 재사용으로 충돌 부풀 수 있음
            safe = T.copy(); safe[safe == 0] = 1
            sh = V / safe[:, None]
            # null 2: 모수식(각 동을 자기 총표·자기 득표율에서 다항추출) — 크기·분포 보존, 더 충실
            res = (T - V.sum(1)).clip(min=0)
            P = np.concatenate([V, res[:, None]], 1) / np.maximum(T, 1)[:, None]
            for k in range(NSIM):
                idx = rng.integers(0, n, n)
                sim1 = np.round(T[:, None] * sh[idx]).astype(int)
                sim_exch[k] += census_pairs(sim1, top_idx, MINVAL)
                M = np.array([rng.multinomial(T[t], P[t]) for t in range(n)])
                sim_param[k] += census_pairs(M[:, :V.shape[1]], top_idx, MINVAL)

    def report(name, obs, sims):
        mu, sd = sims.mean(), sims.std()
        z = (obs - mu) / sd if sd > 0 else float("nan")
        p = float((sims >= obs).mean())
        print(f"  {name}: 관측 {obs} | 기대 {mu:.2f} ± {sd:.2f} | {z:+.1f}σ | p(관측이상)={p:.4f}")

    print(f"기준: 상위{TOPK}후보 동시 동일 & 1위>={MINVAL}  (부트스트랩 {NSIM}회)\n")
    print("[null 1 — 교환식(득표율 풀 재추출): 율 재사용으로 기대 부풀 수 있음]")
    report("전국 전체", obs_total, sim_exch)
    print("\n[null 2 — 모수식(각 동 자기 크기·득표율 보존): 더 충실]")
    report("전국 전체", obs_total, sim_param)
    print("\n※ 두 기대가 다르면 null 선택에 결과가 의존 = 개수 검정은 약함.")
    print("  관측이 충실(모수식) 기대를 넘으면 '8≤기대' 결론은 흔들림 — 방향성/복제 검정으로 보강 필요.")


if __name__ == "__main__":
    main()
