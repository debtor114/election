#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_dataset.py — 내려받은 wide CSV(nec_data/)를 투명·경량 long(tidy) 포맷으로 변환.
의원선거 wide는 후보 컬럼이 1,500개 넘게 sparse하게 늘어나 GitHub에 부적합 →
빈칸 없는 long 한 파일로 합쳐 data/nec_2026_local.csv(.gz) 로 저장.

long 스키마(1행 = 한 후보의 한 (읍면동,구분) 득표):
  선거종류, 시도, 구시군, 선거구, 읍면동, 구분,
  정당, 후보명, 득표수, 유효합계, 투표수, 선거인수, 무효투표수
"""
import sys
from pathlib import Path
import pandas as pd

PREFIX = "후보자별 득표수_"
TOTAL = "후보자별 득표수_계"
TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]


def melt_type(fp, etype):
    df = pd.read_csv(fp, dtype={"선거구": str})
    # 비례대표 '정당별 득표수_' → '후보자별 득표수_'로 통일
    df.columns = [c.replace("정당별 득표수_", PREFIX) for c in df.columns]
    cand = [c for c in df.columns if c.startswith(PREFIX) and c != TOTAL]
    idv = ["선거종류", "시도", "구시군", "선거구", "읍면동명", "구분",
           "선거인수", "투표수", "무효 투표수", TOTAL]
    idv = [c for c in idv if c in df.columns]
    long = df.melt(id_vars=idv, value_vars=cand, var_name="후보", value_name="득표수")
    long = long.dropna(subset=["득표수"])
    if long.empty:
        return None
    # 후보 → 정당/후보명 분리 (접두 제거 후 첫 토큰=정당)
    names = long["후보"].astype(str).str.replace(PREFIX, "", regex=False)
    long["정당"] = names.str.split(" ").str[0]
    long["후보명"] = names.str.split(" ", n=1).str[1].fillna("")
    long = long.rename(columns={"읍면동명": "읍면동", TOTAL: "유효합계", "무효 투표수": "무효투표수"})
    cols = ["선거종류", "시도", "구시군", "선거구", "읍면동", "구분",
            "정당", "후보명", "득표수", "유효합계", "투표수", "선거인수", "무효투표수"]
    return long[[c for c in cols if c in long.columns]]


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("nec_data")
    out = Path("data/processed"); out.mkdir(parents=True, exist_ok=True)
    frames = []
    for t in TYPES:
        fp = base / t / "_combined.csv"          # nec_download 출력 구조
        if not fp.exists():
            fp = Path("data/raw") / f"{t}.csv.gz"  # repo 동봉 원본
        if not fp.exists():
            print(f"  - {t}: 없음(스킵)"); continue
        m = melt_type(fp, t)
        if m is None or m.empty:
            print(f"  - {t}: 빈 데이터(스킵)"); continue
        frames.append(m)
        print(f"  - {t}: {len(m):,}행")
    if not frames:
        sys.exit("nec_data 없음 — nec_download.py 먼저 실행")
    big = pd.concat(frames, ignore_index=True)
    # 정수 정리
    for c in ["득표수", "유효합계", "투표수", "선거인수", "무효투표수"]:
        if c in big.columns:
            big[c] = pd.to_numeric(big[c], errors="coerce").astype("Int64")
    csv = out / "nec_2026_local.csv"
    big.to_csv(csv, index=False, encoding="utf-8-sig")
    gz = out / "nec_2026_local.csv.gz"
    big.to_csv(gz, index=False, encoding="utf-8-sig", compression="gzip")
    print(f"\n총 {len(big):,}행")
    print(f"  {csv}  ({csv.stat().st_size/1e6:.1f} MB)")
    print(f"  {gz}  ({gz.stat().st_size/1e6:.1f} MB, 압축본)")


if __name__ == "__main__":
    main()
