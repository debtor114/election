# -*- coding: utf-8 -*-
"""2022 vs 2026 지방선거 — 동일득표 관측 vs 우연기대 비교 (시도단위 3종)."""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, str(Path('nec-election-verify/election_verify')))
import necdata as nd

TYPES = ['시도지사', '교육감', '광역비례']
MINVAL, NSIM = 100, 1000


def dbl(M, ti):
    keys = [(int(M[r, ti[0]]), int(M[r, ti[1]])) for r in range(M.shape[0])]
    return sum(c*(c-1)//2 for c in Counter(k for k in keys if k[0] >= MINVAL).values())


def analyze(base, label):
    rng = np.random.default_rng(0)
    obs = 0; exp = 0.0; pairs = 0; cases = []
    for et in TYPES:
        try:
            df = nd.load_type(et, base=base)
        except FileNotFoundError:
            print(f"  ({label}) {et} 없음 — 스킵"); continue
        for key, race in nd.iter_races(df, et):
            cc = nd.cand_cols(race)
            if len(cc) < 2:
                continue
            order = race[cc].sum().sort_values(ascending=False).index[:2].tolist()
            ti = [cc.index(c) for c in order]
            u = nd.units(race, nd.GUBUN_EARLY)
            n = len(u)
            if n < 2:
                continue
            pairs += n*(n-1)//2
            V = u[cc].fillna(0).to_numpy(int); T = u['투표수'].fillna(0).to_numpy(int)
            o = dbl(V, ti); obs += o
            if o:
                g = defaultdict(list)
                for idx, row in u.iterrows():
                    v = (int(row[order[0]]), int(row[order[1]]))
                    if v[0] >= MINVAL: g[v].append(row['읍면동명'])
                for v, em in g.items():
                    if len(em) >= 2:
                        nm = [c.replace(nd.CAND_PREFIX,'') for c in order]
                        cases.append(f"{et} {nd.race_label(key)} {'·'.join(em)} ({nm[0]}={v[0]},{nm[1]}={v[1]})")
            safe = T.copy(); safe[safe == 0] = 1; sh = V/safe[:, None]
            for _ in range(NSIM):
                idx = rng.integers(0, n, n); sim = np.round(T[:, None]*sh[idx]).astype(int)
                exp += dbl(sim, ti)/NSIM
    return obs, exp, pairs, cases


print("동일득표(상위2 동시일치, 1위>=100) — 시도지사·교육감·광역비례\n")
print(f"{'선거':<16}{'비교쌍':>10}{'관측':>7}{'우연기대':>10}")
print('-'*45)
for base, label in [('nec_data', '2026 지방선거'), ('nec_2022', '2022 지방선거')]:
    o, e, p, cases = analyze(base, label)
    print(f"{label:<16}{p:>10,}{o:>7}{e:>10.1f}")
    for c in cases: print(f"      · {c}")
print('-'*45)
print("\n두 선거 모두 관측이 기대 근처면 → '동일득표 몇 건'은 선거 무관 정상 우연.")
