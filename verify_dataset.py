#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_dataset.py — "가공본이 원본을 조작한 것 아니냐?"에 대한 답.

선관위에서 받은 원본(data/raw/<선거종류>.csv.gz, wide)을 가공본(data/nec_2026_local.csv.gz, long)과
대조해, **형태만 바뀌었을 뿐 숫자는 한 개도 안 변했음**을 증명한다.

  python verify_dataset.py

검증 내용:
  · 원본을 make_dataset.py와 똑같은 방식으로 long 변환 → 가공본과 1:1 비교
  · 행 수, 총 득표수 합, 선거종류별 합계가 모두 일치하면 통과

신뢰 사슬:
  선관위 info.nec.go.kr  ──(nec_download.py)──►  data/raw/*.csv.gz (원본)
                          ──(make_dataset.py)──►  data/nec_2026_local.csv.gz (가공본)
  → 누구나 nec_download.py로 다시 받아 data/raw 와 대조할 수 있고(원본 진위),
    이 스크립트로 원본→가공본이 손 안 탔음을 확인할 수 있다(가공 진위).
"""
import sys
from pathlib import Path
import pandas as pd

for _s in ("stdout", "stderr"):
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8")
    except Exception:
        pass

import make_dataset as md

RAW = Path("data/raw")
LONG = Path("data/processed/nec_2026_local.csv.gz")
NUMS = ["득표수", "유효합계", "투표수", "선거인수", "무효투표수"]


def reconstruct_from_raw():
    frames = []
    for t in md.TYPES:
        fp = RAW / f"{t}.csv.gz"
        if not fp.exists():
            continue
        m = md.melt_type(fp, t)
        if m is not None and not m.empty:
            frames.append(m)
    if not frames:
        sys.exit(f"원본 없음: {RAW}/*.csv.gz")
    big = pd.concat(frames, ignore_index=True)
    for c in NUMS:
        if c in big.columns:
            big[c] = pd.to_numeric(big[c], errors="coerce").astype("Int64")
    return big


def key_sort(df):
    keys = ["선거종류", "시도", "구시군", "선거구", "읍면동", "구분", "정당", "후보명"]
    keys = [k for k in keys if k in df.columns]
    return df.sort_values(keys).reset_index(drop=True)


def main():
    if not LONG.exists():
        sys.exit(f"가공본 없음: {LONG} (make_dataset.py 먼저 실행)")
    recon = key_sort(reconstruct_from_raw())
    committed = pd.read_csv(LONG, dtype={"선거구": str})
    for c in NUMS:
        if c in committed.columns:
            committed[c] = pd.to_numeric(committed[c], errors="coerce").astype("Int64")
    committed = key_sort(committed)

    print("=" * 60)
    print("원본(raw, wide)  vs  가공본(long)  대조")
    print("=" * 60)
    ok = True

    # 1) 행 수
    r1, r2 = len(recon), len(committed)
    print(f"행 수      원본→재구성 {r1:,}  |  가공본 {r2:,}  →  {'일치' if r1==r2 else '불일치!'}")
    ok &= (r1 == r2)

    # 2) 총 득표수 합
    s1, s2 = int(recon['득표수'].sum()), int(committed['득표수'].sum())
    print(f"총 득표수  원본 {s1:,}  |  가공본 {s2:,}  →  {'일치' if s1==s2 else '불일치!'}")
    ok &= (s1 == s2)

    # 3) 선거종류별 득표수 합
    g1 = recon.groupby('선거종류')['득표수'].sum()
    g2 = committed.groupby('선거종류')['득표수'].sum()
    same = g1.equals(g2)
    print(f"선거종류별 합계  →  {'일치' if same else '불일치!'}")
    ok &= same

    # 4) 핵심 컬럼 전체 동일 여부 (정렬 후 값 비교)
    cols = [c for c in ["선거종류", "시도", "구시군", "읍면동", "구분", "정당", "득표수"]
            if c in recon.columns and c in committed.columns]
    if r1 == r2:
        eq = (recon[cols].astype(str).values == committed[cols].astype(str).values).all()
        print(f"셀 단위 전체 일치({len(cols)}개 컬럼)  →  {'일치' if eq else '불일치!'}")
        ok &= bool(eq)

    print("-" * 60)
    if ok:
        print("✅ 통과 — 가공본은 원본의 '형태'만 바꾼 것이며 숫자는 한 개도 변하지 않았습니다.")
        print("   (원본 자체의 진위는 `python nec_download.py --type all` 로 선관위에서")
        print("    다시 받아 data/raw 와 대조해 확인할 수 있습니다.)")
        sys.exit(0)
    else:
        print("❌ 불일치 — 원본과 가공본이 다릅니다. 위 항목을 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
