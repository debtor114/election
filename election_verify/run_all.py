# -*- coding: utf-8 -*-
"""
run_all — 검정 배터리 일괄 실행 + 요약 리포트
nec_data/ 에 있는 모든 선거종류에 대해 T1~T6를 돌리고, 검정별 PASS/FLAG와
수치 근거를 한 줄씩 출력한다. 결론 문구는 하드코딩하지 않는다(숫자가 말한다).

사용:  python run_all.py            # 전체
       python run_all.py 시도지사    # 특정 선거종류만
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import necdata as nd
from tests import T1_duplicate as T1
from tests import T2_early_vs_dayof as T2
from tests import T3_turnout_forensics as T3
from tests import T4_digits as T4
from tests import T5_shortage_bias as T5
from tests import T6_shortage_turnout as T6

ALL = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]


def available(base="nec_data"):
    root = nd.base_dir(base)
    wide = [t for t in ALL if (root / t / "_combined.csv").exists()]
    if wide:
        return wide
    # raw wide가 없으면 커밋된 long 데이터 사용 (load_type이 자동 복원; 없는 유형은 skip)
    if nd.long_path() is not None:
        return ALL
    return []


def per_race_summary(df, etype, runner, label):
    n_pass = n_flag = 0
    flags = []
    for key, race in nd.iter_races(df, etype):
        res = runner(race, etype)
        if not res:
            continue
        if res["verdict"].startswith("FLAG"):
            n_flag += 1
            flags.append((nd.race_label(key), res))
        else:
            n_pass += 1
    print(f"  {label}: PASS {n_pass} / FLAG {n_flag}")
    for name, res in flags[:20]:
        extra = {k: res[k] for k in res if k not in ("test", "race", "verdict")}
        print(f"      >> {name}  {extra}")
    return n_flag


def main():
    types = [sys.argv[1]] if len(sys.argv) > 1 else available()
    if not types:
        print("nec_data/ 에 데이터가 없습니다. nec_download.py 먼저 실행."); return
    print("=" * 70)
    print("6·3 지방선거 개표 검증 배터리 — 요약 리포트")
    print("원칙: 관측값 + 기대치를 함께. FLAG = 정밀조사 대상(부정 '증거' 아님).")
    print("=" * 70)
    total_flags = 0
    for etype in types:
        try:
            df = nd.load_type(etype)
        except FileNotFoundError:
            continue
        print(f"\n■ {etype}")
        total_flags += per_race_summary(df, etype, lambda r, e: T1.run(r, e), "T1 동일득표(관내사전)")
        total_flags += per_race_summary(df, etype, lambda r, e: T2.run(r, e), "T2 사전vs본")
        # T3/T4 (선거종류 단위)
        r3 = T3.run(df, etype)
        if r3:
            print(f"  T3 투표율포렌식: 꼬리상관={r3['tail_corr']} lift={r3['lift']}"
                  f" → {r3['verdict']}  (plot: {Path(r3['plot']).name})")
            total_flags += r3["verdict"] == "FLAG"
        r4 = T4.run(df, etype)
        if r4:
            print(f"  T4 끝자리/벤포드(약함): 끝자리p={r4['lastdigit_p']} 벤포드p={r4['benford_p']}"
                  f" → {r4['verdict']}")
        # T5/T6 (부족목록 필요)
        r5 = T5.run(df, etype)
        print(f"  T5 부족투표소편향: {r5.get('msg') if r5.get('verdict')=='SKIP' else r5}")
        r6 = T6.run(df, etype)
        print(f"  T6 부족vs투표율: {r6.get('msg') if r6.get('verdict')=='SKIP' else r6}")
    print("\n" + "=" * 70)
    print(f"총 FLAG(정밀조사 후보) 합계: {total_flags}건")
    print("FLAG는 '우연으로 설명 어려움'을 뜻할 뿐, 그 자체가 부정의 증거가 아님.")
    print("=" * 70)


if __name__ == "__main__":
    main()
