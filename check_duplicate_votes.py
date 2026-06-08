#!/usr/bin/env python3
"""
지방선거 '동일 득표' 전수 검증 스크립트
================================================
선관위 선거통계시스템에서 받은 '읍면동별 개표결과'(엑셀/CSV)를 입력으로:
  (1) 동일 득표 쌍을 기준별로 전수 집계 (한 후보 / 상위 2후보 / 전 항목 복제)
  (2) 우연 기대치(null)를 '실제 데이터 기반 몬테카를로'로 만들어 관측값이 몇 σ인지
  (3) 방향성(편향) 검정 — 일치가 특정 정당으로 쏠리는가
  (4) 전 항목+총계까지 동일한 '복제 시그니처' 쌍 탐지 (하나라도 나오면 정밀조사 대상)

사용법:
  pip install pandas numpy openpyxl
  python check_duplicate_votes.py 개표결과.xlsx

※ 아래 '설정' 부분의 열 이름을 실제 파일에 맞게 한 번만 수정하면 됩니다.
"""
import sys
from collections import Counter
import numpy as np
import pandas as pd

# ================= 설정 (실제 파일에 맞게 수정) =================
DONG_COL   = "읍면동"            # 투표단위(동/면) 이름 열
TYPE_COL   = "구분"              # 집계 종류가 들어있는 열
TYPE_VALUE = "관내사전투표"       # 비교할 집계 종류
CAND_COLS  = ["박찬대", "유정복", "이기붕"]  # 후보 '득표수' 열들 (계/투표수/무효 제외)
RULING_PARTY_CAND = "박찬대"     # 방향성 검정 기준이 될 후보(예: 여당 후보)
# =============================================================

def load(path):
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)

def main(path):
    df = load(path)
    sub = df[df[TYPE_COL] == TYPE_VALUE].copy().reset_index(drop=True)
    units = sub[DONG_COL].astype(str).values
    V = sub[CAND_COLS].to_numpy(dtype=int)        # (n, c) 후보별 득표수
    totals = V.sum(axis=1)
    n = len(sub)
    print(f"비교 단위 수: {n}개  ({TYPE_VALUE})\n")

    # ---- (1) 기준별 동일 쌍 전수 집계 (해시로 O(n)) ----
    # 한 후보 동일: 후보별로 같은 값 쌍 수
    print("[관측값]")
    for ci, name in enumerate(CAND_COLS):
        vc = Counter(V[:, ci])
        pairs = sum(c*(c-1)//2 for c in vc.values())
        print(f"  '{name}' 단독 동일 쌍: {pairs}")
    # 상위 2후보 동시 동일
    top2 = [tuple(sorted(row)[-2:]) for row in V]      # (둘째, 첫째)
    t2 = Counter(top2)
    top2_pairs = sum(c*(c-1)//2 for c in t2.values())
    print(f"  상위 2후보 동시 동일 쌍: {top2_pairs}")
    # 전 항목 + 총계 동일 (복제 시그니처)
    full = [tuple(int(x) for x in V[i]) + (int(totals[i]),) for i in range(n)]
    fc = Counter(full)
    dup_pairs = sum(c*(c-1)//2 for c in fc.values())
    print(f"  전 후보+총계 전부 동일(복제) 쌍: {dup_pairs}"
          f"  {'  <-- 정밀조사 대상!' if dup_pairs>0 else ''}")

    # ---- (2) 우연 기대치(null): 총표는 고정, 득표율을 경험분포서 재추출 ----
    rng = np.random.default_rng(0)
    safe = totals.copy(); safe[safe == 0] = 1
    shares = V / safe[:, None]
    def sim_top2():
        idx = rng.integers(0, n, n)               # 득표율 부트스트랩
        sim = np.round(totals[:, None] * shares[idx]).astype(int)
        keys = [tuple(sorted(r)[-2:]) for r in sim]
        c = Counter(keys)
        return sum(v*(v-1)//2 for v in c.values())
    sims = np.array([sim_top2() for _ in range(2000)])
    mu, sd = sims.mean(), sims.std()
    z = (top2_pairs - mu) / sd if sd > 0 else float("nan")
    print(f"\n[상위2 동일 쌍 — 우연 기대치와 비교]")
    print(f"  null 평균 {mu:.1f} ± {sd:.1f}  →  관측 {top2_pairs}개 = {z:+.1f}σ")
    print(f"  (대략 +3σ를 넘으면 우연만으로는 설명하기 어려움)")

    # ---- (3) 방향성(편향) 검정 ----
    try:
        rp = CAND_COLS.index(RULING_PARTY_CAND)
        # 상위2 동일 쌍을 직접 찾아, 그 쌍에서 기준 후보가 1위였는지 집계
        from itertools import combinations
        groups = {}
        for i, k in enumerate(top2):
            groups.setdefault(k, []).append(i)
        favor, M = 0, 0
        for k, members in groups.items():
            if len(members) < 2:
                continue
            for i, j in combinations(members, 2):
                M += 1
                # 두 단위에서 기준 후보가 모두 1위였으면 '기준 후보 우위'로 카운트
                if V[i].argmax() == rp and V[j].argmax() == rp:
                    favor += 1
        if M > 0:
            mu_d, sd_d = M/2, (M**0.5)/2
            zd = (favor - mu_d)/sd_d if sd_d > 0 else float("nan")
            print(f"\n[방향성] 상위2 동일쌍 {M}개 중 '{RULING_PARTY_CAND} 1위' {favor}개"
                  f"  = {zd:+.1f}σ  (중립이면 0 근처)")
    except Exception as e:
        print(f"\n[방향성] 건너뜀 ({e})")

    print("\n결론 판정 기준:")
    print("  · 상위2 동일 쌍 수가 null +3σ 이내  → 우연으로 설명됨")
    print("  · +3σ 초과  또는  방향성이 한쪽으로 +3σ 쏠림  또는  복제 쌍 존재 → 정밀조사")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python check_duplicate_votes.py 개표결과.xlsx")
        sys.exit(1)
    main(sys.argv[1])
