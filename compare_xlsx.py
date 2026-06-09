# -*- coding: utf-8 -*-
"""
과거 지방선거(선관위 공개 xlsx) 동일득표 대조군 분석.
시도지사·교육감·광역비례 3종에서: 관측 / 교환식·모수식 기대 / 방향(승자 정당).
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
from collections import Counter, defaultdict
import numpy as np, pandas as pd

SHEETS = ['시·도지사', '교육감', '광역의원비례대표']
MINVAL, NSIM = 100, 1500


def num(x):
    s = str(x).replace(',', '').strip()
    if s in ('', 'nan', '-', 'None'):
        return 0
    try:
        return int(float(s))
    except Exception:
        return 0


def parse_sheet(f, sheet):
    """헤더명·후보명행으로 컬럼을 동적 탐지 (2018·2022 형식 모두 지원)."""
    raw = pd.read_excel(f, sheet_name=sheet, header=None)
    nrows, ncols = raw.shape
    hdr = [str(x).strip() for x in raw.iloc[0].tolist()]
    idx = lambda n: hdr.index(n) if n in hdr else None
    emd_col, gubun_col, tu_col, gu_col = idx('읍면동명'), idx('구분'), idx('투표수'), idx('구시군명')
    # 시도 후보 컬럼들(행마다 채워진 첫 값 사용 — 선거구명/시도/시도명이 시트·연도마다 다름)
    sido_candcols = [idx(n) for n in ('선거구명', '시도', '시도명') if idx(n) is not None]
    cand_start = idx('후보자별 득표수') or idx('정당별 득표수')   # 후보/정당
    # 후보 끝 = cand_start 이후 첫 '계' 또는 '무효투표수' 컬럼 (행0·후보명행 모두 탐색)
    headrows = [[str(x).strip() for x in raw.iloc[i].tolist()] for i in range(0, min(6, nrows))]
    end = ncols
    for c in range(cand_start, ncols):
        labels = {hr[c] for hr in headrows}
        if '계' in labels or '무효투표수' in labels:
            end = c; break
    cand = list(range(cand_start, end))

    def sido_of(r):
        for c in sido_candcols:
            if pd.notna(r[c]) and str(r[c]).strip():
                return str(r[c]).strip()
        return ''

    def clean(s):
        return str(s).replace('_x000D_', '').replace('\r', '').replace('\n', ' ').strip()

    recs, names = [], {}
    for i in range(1, nrows):
        r = raw.iloc[i].tolist()
        sido = sido_of(r)
        gubun = str(r[gubun_col]).strip() if pd.notna(r[gubun_col]) else ''
        if gubun == '' and isinstance(r[cand_start], str) and r[cand_start].strip():
            if sido and sido not in names:
                names[sido] = [clean(r[c]) for c in cand]
        if gubun == '관내사전투표':
            recs.append((sido, str(r[gu_col]).strip(), str(r[emd_col]).strip(),
                         num(r[tu_col]), [num(r[c]) for c in cand]))
    return recs, names


def dbl(M, ti):
    keys = [(int(M[r, ti[0]]), int(M[r, ti[1]])) for r in range(M.shape[0])]
    return sum(c*(c-1)//2 for c in Counter(k for k in keys if k[0] >= MINVAL).values())


def analyze(f, label):
    rng = np.random.default_rng(0)
    obs = 0; exch = 0.0; param = 0.0; cases = []
    party_dir = Counter()
    for sheet in SHEETS:
        try:
            recs, names = parse_sheet(f, sheet)
        except Exception as e:
            print(f"  {sheet}: 파싱 실패 {e}"); continue
        by_sido = defaultdict(list)
        for sido, gu, emd, tu, vals in recs:
            by_sido[sido].append((gu, emd, tu, vals))
        for sido, rows in by_sido.items():
            if len(rows) < 2:
                continue
            V = np.array([r[3] for r in rows]); T = np.array([r[2] for r in rows])
            tot = V.sum(0)
            ti = list(np.argsort(tot)[::-1][:2])
            obs_c = dbl(V, ti); obs += obs_c
            if obs_c:
                g = defaultdict(list)
                for k, (gu, emd, tu, vals) in enumerate(rows):
                    key = (vals[ti[0]], vals[ti[1]])
                    if key[0] >= MINVAL: g[key].append(emd)
                for key, em in g.items():
                    if len(em) >= 2:
                        nm = names.get(sido, [''])
                        wname = nm[ti[0]] if ti[0] < len(nm) else '?'
                        party = wname.split()[0] if wname else '?'
                        party_dir[party] += 1
                        cases.append(f"{sheet} {sido} {'·'.join(em)} ({wname}={key[0]},2위={key[1]})")
            safe = T.copy(); safe[safe == 0] = 1; sh = V/safe[:, None]
            res = (T - V.sum(1)).clip(min=0)
            P = np.concatenate([V, res[:, None]], 1) / np.maximum(T, 1)[:, None]
            n = len(V)
            for _ in range(NSIM):
                idx = rng.integers(0, n, n)
                exch += dbl(np.round(T[:, None]*sh[idx]).astype(int), ti)/NSIM
                M = np.array([rng.multinomial(T[t], P[t]) for t in range(n)])
                param += dbl(M[:, :V.shape[1]], ti)/NSIM
    return obs, exch, param, cases, party_dir


if __name__ == "__main__":
    files = sys.argv[1:] or [
        'data/past_elections/중앙선거관리위원회_제7회 전국동시지방선거 개표결과_20180613.xlsx',
        'data/past_elections/중앙선거관리위원회_제8회 전국동시지방선거 개표결과_20220601.xlsx',
    ]
    print("동일득표(상위2 동시일치, 1위>=100, 관내사전) — 시도지사·교육감·광역비례\n")
    for f in files:
        label = '2018' if '20180613' in f else ('2022' if '20220601' in f else f)
        o, e1, e2, cases, pd_ = analyze(f, label)
        print(f"=== {label} ===")
        print(f"  관측 {o} | 교환식 기대 {e1:.2f} | 모수식 기대 {e2:.2f}")
        print(f"  방향(1위 정당): {dict(pd_)}")
        for c in cases: print(f"    · {c}")
        print()
