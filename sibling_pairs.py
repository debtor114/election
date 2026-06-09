# -*- coding: utf-8 -*-
"""
sibling_pairs.py — '같은 이름 + 연번' 형제 동(송도1동·송도2동류) 쌍만 따로 검정.

질문: per-pair는 드물어도 비교한 쌍이 많다. 그중에서도 '거의 쌍둥이'인
      연번 형제 동만 모으면, 동시일치(top2)가 관측 vs 우연 기대로 몇 건인가?

- 형제 정의: 같은 race(관내사전) 안에서, 읍면동명 끝의 숫자만 다르고
  나머지(접두 이름)가 같은 쌍.  예) 송도1동/송도2동, 정자1동/정자2동.
- 관측: 형제 쌍 중 top2 동시 일치 & 1위>=MINVAL 건수.
- 기대(twin-null): 두 형제가 '진짜 쌍둥이(공통 득표율)'라 가정하고 각자
  자기 투표수로 다항추출 → 동시일치 확률을 합산(=look-elsewhere 보정된 기대).
  쌍둥이 가정은 일치에 *유리*하므로 기대의 상한에 가깝다.
"""
import re, sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd

TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]
TOPK, MINVAL = 2, 100

NUM = re.compile(r"(\d+)")


def base_key(name):
    """연번 제거한 접두 이름. 숫자가 있어야 형제 후보."""
    s = str(name)
    if not NUM.search(s):
        return None
    # 끝쪽 숫자(연번)만 제거: 송도1동→송도동, 정자3동→정자동
    return NUM.sub("", s)


def twin_pmatch(Ti, Tj, Vi, Vj, top_idx):
    """쌍둥이(공통 득표율) 가정 top2 동시 일치 확률 — compute_8과 같은 닫힌식.
       P ≈ 1/(2π(T1+T2)√(pA·pB·pO)).  일치에 유리한 가정이라 기대의 상한."""
    if Ti <= 0 or Tj <= 0:
        return 0.0
    a, b = top_idx
    pA = (int(Vi[a]) + int(Vj[a])) / (Ti + Tj)
    pB = (int(Vi[b]) + int(Vj[b])) / (Ti + Tj)
    pO = max(1 - pA - pB, 1e-9)
    if pA <= 0 or pB <= 0:
        return 0.0
    return 1.0 / (2 * np.pi * (Ti + Tj) * np.sqrt(pA * pB * pO))


def main():
    sib_pairs = 0          # 형제 쌍 총수
    elig = 0               # 양쪽 1위>=MINVAL (자격 쌍)
    obs = 0                # 형제 쌍 중 top2 동시 일치
    exp_twin = 0.0         # 쌍둥이 가정 기대(동시 일치)
    hits = []
    for et in TYPES:
        try:
            df = nd.load_type(et)
        except FileNotFoundError:
            continue
        for key, race in nd.iter_races(df, et):
            cc = nd.cand_cols(race)
            if len(cc) < TOPK:
                continue
            order = race[cc].sum().sort_values(ascending=False).index[:TOPK].tolist()
            top_idx = [cc.index(c) for c in order]
            u = nd.units(race, nd.GUBUN_EARLY)
            if len(u) < 2:
                continue
            # race별 numeric 행렬을 미리 만든다(행 단위 object 슬라이싱 회피 → 경고 없음 + 빠름)
            V = u[cc].apply(lambda s: s.fillna(0)).to_numpy(dtype=int)
            T = u["투표수"].fillna(0).to_numpy(dtype=int)
            names = u["읍면동명"].tolist()
            a0, a1 = top_idx
            groups = defaultdict(list)
            for r in range(len(u)):
                b = base_key(names[r])
                if b is not None:
                    groups[b].append(r)
            for b, idxs in groups.items():
                if len(idxs) < 2:
                    continue
                for a in range(len(idxs)):
                    for c in range(a + 1, len(idxs)):
                        i, j = idxs[a], idxs[c]
                        sib_pairs += 1
                        vi = (int(V[i, a0]), int(V[i, a1]))
                        vj = (int(V[j, a0]), int(V[j, a1]))
                        # 관측과 동일 조건(1위>=MINVAL 가능)인 쌍에만 기대 합산
                        if vi[0] >= MINVAL and vj[0] >= MINVAL:
                            elig += 1
                            exp_twin += twin_pmatch(int(T[i]), int(T[j]), V[i], V[j], top_idx)
                        if vi == vj and vi[0] >= MINVAL:
                            obs += 1
                            hits.append((et, nd.race_label(key), names[i], names[j], vi))
    print(f"형제(연번) 동 쌍 총수: {sib_pairs:,}  (양쪽 1위>={MINVAL} 자격 쌍: {elig:,})")
    print(f"  관측 top2 동시 일치(1위>={MINVAL}): {obs}")
    print(f"  쌍둥이-가정 기대(상한, 닫힌식 합): {exp_twin:.2f}")
    print(f"  → 관측 {obs} {'<' if obs < exp_twin else '≥'} 기대 {exp_twin:.2f}")
    for h in hits:
        print(f"    {h[0]} {h[1]} {h[2]}·{h[3]} {h[4]}")


if __name__ == "__main__":
    main()
