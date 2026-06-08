# -*- coding: utf-8 -*-
"""
T4 — 끝자리 균일성 / 벤포드 1st-digit  (⚠ 보조 지표, 약함)
후보별 득표수의 마지막 자리(0~9) 균일성 카이제곱, 첫자리 벤포드 적합도.
※ 개표 득표수는 표본·분포 특성상 신뢰도 낮음 — 단독 근거 금지. 다른 검정 보조로만.

판정(FLAG): p < 0.001 (극단적 이탈)만 표시하되, '약함' 꼬리표 유지.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

P_FLAG = 0.001
BENFORD = np.log10(1 + 1 / np.arange(1, 10))


def collect_counts(df, election_type):
    vals = []
    for _key, race in nd.iter_races(df, election_type):
        cc = nd.cand_cols(race)
        u = nd.units(race, nd.GUBUN_DAYOF)
        if cc and len(u):
            arr = u[cc].to_numpy().ravel()
            vals.extend(arr[np.isfinite(arr)])
    return np.array(vals, dtype=float)


def last_digit_test(v):
    v = v[v >= 10].astype(int)
    if len(v) < 100:
        return None
    obs = np.bincount(v % 10, minlength=10)
    exp = np.full(10, len(v) / 10)
    chi, p = stats.chisquare(obs, exp)
    return {"n": len(v), "chi2": round(float(chi), 1), "p": p}


def benford_test(v):
    v = v[v >= 1].astype(int)
    if len(v) < 100:
        return None
    first = np.array([int(str(x)[0]) for x in v])
    obs = np.bincount(first, minlength=10)[1:10]
    exp = BENFORD * len(v)
    chi, p = stats.chisquare(obs, exp)
    return {"n": len(v), "chi2": round(float(chi), 1), "p": p}


def run(df, election_type):
    v = collect_counts(df, election_type)
    ld = last_digit_test(v)
    bf = benford_test(v)
    if not ld and not bf:
        return None
    flag = ((ld and ld["p"] < P_FLAG) or (bf and bf["p"] < P_FLAG))
    return {
        "test": "T4(약함)", "race": f"{election_type}(전체)",
        "lastdigit_p": round(ld["p"], 4) if ld else None,
        "benford_p": round(bf["p"], 4) if bf else None,
        "n": ld["n"] if ld else (bf["n"] if bf else 0),
        "verdict": "FLAG(약함)" if flag else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "시도지사"
    df = nd.load_type(etype)
    res = run(df, etype)
    print(f"[T4 끝자리/벤포드] {etype}  (주의: 보조·약함)")
    if not res:
        print("  표본 부족"); return
    print(f"  n={res['n']}  끝자리p={res['lastdigit_p']}  벤포드p={res['benford_p']}"
          f"  → {res['verdict']}")
    print("  ※ 단독 근거로 쓰지 말 것.")


if __name__ == "__main__":
    main()
