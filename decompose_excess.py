# -*- coding: utf-8 -*-
"""
초과의 정체: '민주 승리' 때문인가, '압승=지역 동질성' 때문인가.
각 매칭을 (지역·선거·승자정당·승자 race-wide 득표율=압승도)로 분해.
"""
import sys, os; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
# repo 루트로 이동(data/past_elections 있는 곳)
if not os.path.exists('data/past_elections') and os.path.exists('nec-election-verify/data/past_elections'):
    os.chdir('nec-election-verify')
sys.path.insert(0, '.')                 # compare_xlsx
sys.path.insert(0, 'election_verify')   # necdata
import compare_xlsx as cx
import necdata as nd

SHEET2TYPE = {'시·도지사': '시도지사', '교육감': '교육감', '광역의원비례대표': '광역비례'}


def matches_xlsx(f):
    """xlsx 한 해: 매칭별 (선거, 시도, 승자정당, 승자득표율, 1위, 2위)."""
    out = []
    for sheet in cx.SHEETS:
        try:
            recs, names = cx.parse_sheet(f, sheet)
        except Exception:
            continue
        by = defaultdict(list)
        for sido, gu, emd, gubun, tu, vals in recs:
            if gubun == '관내사전투표':
                by[sido].append((emd, vals))
        for sido, rows in by.items():
            if len(rows) < 2:
                continue
            V = np.array([r[1] for r in rows])
            tot = V.sum(0); ti = list(np.argsort(tot)[::-1][:2])
            share = tot[ti[0]] / max(tot.sum(), 1)      # 승자 race-wide 득표율
            g = defaultdict(list)
            for emd, vals in rows:
                key = (vals[ti[0]], vals[ti[1]])
                if key[0] >= 100: g[key].append(emd)
            for key, em in g.items():
                if len(em) >= 2:
                    nm = names.get(sido, [''])
                    party = (nm[ti[0]].split()[0] if ti[0] < len(nm) and nm[ti[0]] else '교육감')
                    out.append((SHEET2TYPE.get(sheet, sheet), sido, party, share, key[0], key[1]))
    return out


def matches_2026():
    out = []
    for et in ['시도지사', '교육감', '광역비례']:
        df = nd.load_type(et)
        for key, race in nd.iter_races(df, et):
            cc = nd.cand_cols(race)
            if len(cc) < 2: continue
            order = race[cc].sum().sort_values(ascending=False).index[:2].tolist()
            ti = [cc.index(c) for c in order]
            tot = race[cc].sum(); share = tot[order[0]] / max(tot.sum(), 1)
            u = nd.units(race, '관내사전투표')
            if len(u) < 2: continue
            g = defaultdict(list)
            for _, row in u.iterrows():
                k = (int(row[order[0]]), int(row[order[1]]))
                if k[0] >= 100: g[k].append(row['읍면동명'])
            for k, em in g.items():
                if len(em) >= 2:
                    party = order[0].replace(nd.CAND_PREFIX, '').split()[0]
                    if et == '교육감': party = '교육감'
                    out.append((et, nd.race_label(key), party, share, k[0], k[1]))
    return out


YEARS = [
    ('2018', lambda: matches_xlsx('data/past_elections/중앙선거관리위원회_제7회 전국동시지방선거 개표결과_20180613.xlsx')),
    ('2022', lambda: matches_xlsx('data/past_elections/중앙선거관리위원회_제8회 전국동시지방선거 개표결과_20220601.xlsx')),
    ('2026', matches_2026),
]
for yr, fn in YEARS:
    ms = fn()
    print(f"=== {yr} — 매칭 {len(ms)}건 ===")
    reg = Counter(m[1] for m in ms)
    par = Counter(m[2] for m in ms)
    lop = [m[3] for m in ms]
    print(f"  지역: {dict(reg)}")
    print(f"  승자정당: {dict(par)}")
    print(f"  매칭 race 승자 득표율(압승도) 평균: {np.mean(lop):.2f}  (전부 압승 race면 높음)")
    for m in sorted(ms, key=lambda x: -x[3]):
        print(f"    {m[0]:<7} {m[1]:<6} 승자={m[2]:<7} 득표율={m[3]:.2f}  ({m[4]}·{m[5]})")
    print()
