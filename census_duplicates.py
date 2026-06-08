# -*- coding: utf-8 -*-
"""
census_duplicates.py — 동일득표 '전수조사'
전국 7개 선거 모든 race에서, 같은 선거의 서로 다른 읍면동(관내사전투표) 중
'상위 후보들의 득표가 동시에 똑같은' 경우를 빠짐없이 열거한다.

매칭 기준(설정): 그 선거의 상위 K명 후보 득표가 두 읍면동에서 동시에 정확히 동일,
                 그리고 1위 득표가 MINVAL 이상(자잘한 0~수십표 우연 제외).
출력: 매칭 그룹(2곳 이상)을 일치 후보 수·값 크기 순으로 정렬해 전부 출력 + 총 건수.

※ 동일득표 '존재'가 곧 부정은 아니다(인접·유사 동은 득표율이 비슷). 이건
   '어디에 무엇이 있는지'의 완전한 목록이며, 통계적 유의성은 national_scan.py(σ)가 본다.
"""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd

TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]
TOPK = 2          # 상위 몇 명이 동시에 같아야 '케이스'로 볼지
MINVAL = 100      # 1위 후보 득표 하한(자잘한 우연 제외)


def main():
    topk = int(sys.argv[1]) if len(sys.argv) > 1 else TOPK
    minval = int(sys.argv[2]) if len(sys.argv) > 2 else MINVAL
    cases = []
    for etype in TYPES:
        try:
            df = nd.load_type(etype)
        except FileNotFoundError:
            continue
        for key, race in nd.iter_races(df, etype):
            cc = nd.cand_cols(race)
            if len(cc) < topk:
                continue
            # 그 선거의 상위 K 후보(전체 합 기준)
            top = race[cc].sum().sort_values(ascending=False).index[:topk].tolist()
            u = nd.units(race, nd.GUBUN_EARLY)
            if len(u) < 2:
                continue
            groups = defaultdict(list)
            for _, row in u.iterrows():
                vals = tuple(int(row[c]) if not pd_isna(row[c]) else -1 for c in top)
                if vals[0] >= minval and -1 not in vals:
                    groups[vals].append(row["읍면동명"])
            for vals, emds in groups.items():
                if len(emds) >= 2:
                    cases.append({
                        "type": etype, "race": nd.race_label(key),
                        "cands": [c.replace(nd.CAND_PREFIX, "") for c in top],
                        "vals": vals, "emds": emds, "k": topk, "ncount": len(emds),
                    })

    # 정렬: 일치 읍면동 수↓, 1위 값↓
    cases.sort(key=lambda x: (-x["ncount"], -x["vals"][0]))
    print(f"전수조사: 상위 {topk}후보 동시 동일 & 1위≥{minval}  →  총 {len(cases)} 건\n")
    for i, c in enumerate(cases, 1):
        vs = " · ".join(f"{n}={v}" for n, v in zip(c["cands"], c["vals"]))
        print(f"[{i}] {c['type']} {c['race']} | {c['ncount']}곳: {', '.join(c['emds'])}")
        print(f"     {vs}")
    print(f"\n총 {len(cases)} 건 (상위{topk}후보 동시 동일, 1위≥{minval}표)")
    n3 = sum(1 for c in cases if c["ncount"] >= 3)
    if n3:
        print(f"그중 3곳 이상 동시 동일: {n3} 건")


def pd_isna(x):
    return x != x


if __name__ == "__main__":
    main()
