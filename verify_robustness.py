# -*- coding: utf-8 -*-
"""
검증 보강: (1) 8건이 관내사전인지  (2) 부트스트랩이 실제 분포 보존하는지
          (3) 방향성(한쪽 정당 쏠림)  (4) 복제(전 후보+총계 동일)  검정.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, str(Path('nec-election-verify/election_verify')))
import necdata as nd

TYPES = ['시도지사', '교육감', '광역비례']   # 8건이 전부 여기서 나옴
MINVAL, NSIM = 100, 1500


def dbl(M, ti):
    keys = [(int(M[r, ti[0]]), int(M[r, ti[1]])) for r in range(M.shape[0])]
    return sum(c*(c-1)//2 for c in Counter(k for k in keys if k[0] >= MINVAL).values())


# ---- 8건 찾기 + 방향성/복제 ----
print("="*70)
print("(1) 8건 — 구분(사전투표?) · 방향성 · 복제 검정")
print("="*70)
cases = []
for et in TYPES:
    df = nd.load_type(et)
    for key, race in nd.iter_races(df, et):
        cc = nd.cand_cols(race)
        if len(cc) < 2: continue
        order = race[cc].sum().sort_values(ascending=False).index[:2].tolist()
        u = nd.units(race, nd.GUBUN_EARLY)
        if len(u) < 2: continue
        g = defaultdict(list)
        for idx, row in u.iterrows():
            v = (int(row[order[0]]), int(row[order[1]]))
            if v[0] >= MINVAL: g[v].append(idx)
        for v, idxs in g.items():
            if len(idxs) >= 2:
                cases.append((et, nd.race_label(key), race, u, order, cc, idxs, v))

print(f"{'선거/두 동':<26}{'구분':<10}{'1위 정당':<10}{'전후보+총계 동일?':<14}")
print("-"*64)
party_dir = Counter()
for et, lab, race, u, order, cc, idxs, v in sorted(cases, key=lambda x:-x[7][0]):
    i, j = idxs[0], idxs[1]
    gubun = u.loc[i, '구분']
    win_party = order[0].replace(nd.CAND_PREFIX, '').split()[0]
    party_dir[win_party] += 1
    # 복제: 전 후보 + 총계까지 동일?
    allmatch = all(int(u.loc[i, c]) == int(u.loc[j, c]) for c in cc)
    tot_i = sum(int(u.loc[i, c]) for c in cc); tot_j = sum(int(u.loc[j, c]) for c in cc)
    dup = "복제(전부동일)!" if (allmatch and tot_i == tot_j) else "아니오(상위2만)"
    e1, e2 = u.loc[i, '읍면동명'], u.loc[j, '읍면동명']
    print(f"{et+' '+e1+'·'+e2:<26}{gubun:<10}{win_party:<10}{dup:<14}")

print(f"\n방향성: 1위 정당 분포 = {dict(party_dir)}")
print("  → 한 정당으로 쏠리면 부정 신호, 흩어지면 우연 시그니처.")

# ---- (2) 부트스트랩 분포 보존 검증: 교환식 vs 모수식(각 동 자기 분포) ----
print("\n" + "="*70)
print("(2) 부트스트랩 검증 — 교환식 vs '각 동 자기 크기·득표율 보존' 모수식")
print("="*70)
rng = np.random.default_rng(0)
obs = 0; exp_exch = 0.0; exp_param = 0.0
for et in TYPES:
    df = nd.load_type(et)
    for key, race in nd.iter_races(df, et):
        cc = nd.cand_cols(race)
        if len(cc) < 2: continue
        order = race[cc].sum().sort_values(ascending=False).index[:2].tolist()
        ti = [cc.index(c) for c in order]
        u = nd.units(race, nd.GUBUN_EARLY); n = len(u)
        if n < 2: continue
        V = u[cc].fillna(0).to_numpy(int); T = u['투표수'].fillna(0).to_numpy(int)
        obs += dbl(V, ti)
        safe = T.copy(); safe[safe == 0] = 1; sh = V/safe[:, None]
        # 교환식: 득표율을 풀에서 재추출(동 섞음)
        for _ in range(NSIM):
            idx = rng.integers(0, n, n); sim = np.round(T[:, None]*sh[idx]).astype(int)
            exp_exch += dbl(sim, ti)/NSIM
        # 모수식: 각 동을 자기 (총표, 자기 득표율)에서 다항 추출 — 크기·분포 보존, 안 섞음
        res = (T - V.sum(1)).clip(min=0)
        P = np.concatenate([V, res[:, None]], 1) / np.maximum(T, 1)[:, None]
        for _ in range(NSIM):
            M = np.array([rng.multinomial(T[k], P[k]) for k in range(n)])
            exp_param += dbl(M[:, :len(cc)], ti)/NSIM

print(f"  관측: {obs}건")
print(f"  교환식 부트스트랩 기대: {exp_exch:.2f}건")
print(f"  모수식(분포 보존) 기대:  {exp_param:.2f}건")
print(f"  → 두 기대가 비슷하면 부트스트랩이 분포를 부풀리지 않은 것. 관측이 둘 다 이하인지 확인.")
