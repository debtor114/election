# -*- coding: utf-8 -*-
"""
national_scan.py — 동일득표를 '전국'으로 본다.
민형배·전남 한 곳이 아니라, 7개 선거 전 race(약 1,200개)에서
 ① 승자 단독 동일득표  ② 상위2 동시 동일  의 σ(우연 모델 대비)를 모아
σ 분포가 0(우연)에 모이는지, 양(+)으로 쏠리는지(체계적 신호)를 본다.

우연이라면 σ는 대략 표준정규 → 평균≈0, +2σ 초과 ≈ 2.3%, +3σ 초과 ≈ 0.13%.
체계적 부풀림이 있으면 분포가 통째로 양(+)으로 밀린다.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "election_verify"))
import necdata as nd
from tests import T1_duplicate as T1

T1.N_SIM = 800   # 스윕용(분포 집계엔 충분)
TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]


def main():
    ws, t2, info = [], [], []
    for etype in TYPES:
        try:
            df = nd.load_type(etype)
        except FileNotFoundError:
            continue
        cnt = 0
        for key, race in nd.iter_races(df, etype):
            res = T1.run(race, etype)
            if not res:
                continue
            ws.append(res["win_single_sigma"]); t2.append(res["top2_sigma"])
            info.append((etype, nd.race_label(key), res["win_single_sigma"], res["top2_sigma"]))
            cnt += 1
        print(f"  {etype}: race {cnt}개")
    ws, t2 = np.array(ws), np.array(t2)
    N = len(ws)
    print("\n" + "=" * 64)
    print(f"전국 {N}개 race · 동일득표 σ 분포 (우연이면 평균≈0, +2초과≈2.3%, +3초과≈0.13%)")
    print("=" * 64)
    for name, a in [("① 승자 단독 동일", ws), ("② 상위2 동시 동일", t2)]:
        gt2, gt3 = int((a > 2).sum()), int((a > 3).sum())
        print(f"{name}:")
        print(f"   평균 {a.mean():+.2f}σ (중앙 {np.median(a):+.2f}) | 표준편차 {a.std():.2f}")
        print(f"   +2σ 초과 {gt2}개 ({gt2/N*100:.1f}%, 우연기대 ~{N*0.0228:.0f}개)"
              f" | +3σ 초과 {gt3}개 (우연기대 ~{N*0.00135:.1f}개)")
    print("\n[가장 큰 단일후보 σ race 상위 8]")
    for etype, lab, s, _ in sorted(info, key=lambda x: -x[2])[:8]:
        print(f"   {s:+.1f}σ  {etype} {lab}")
    print("\n[가장 큰 상위2 σ race 상위 8]")
    for etype, lab, _, s in sorted(info, key=lambda x: -x[3])[:8]:
        print(f"   {s:+.1f}σ  {etype} {lab}")
    print("\n해석: 평균이 0 근처면 전국적으로 '동일득표가 우연 기대 수준'.")
    print("      양(+)으로 크게 밀리거나 +3초과가 기대보다 많으면 추가 조사 지점.")


if __name__ == "__main__":
    main()
