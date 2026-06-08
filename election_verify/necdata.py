# -*- coding: utf-8 -*-
"""
공용 데이터 로더 — nec_download.py 출력(nec_data/<선거종류>/_combined.csv)을
tidy 스키마로 읽고, race(후보 집합이 일정한 단위)별로 분리한다.

원본 CSV 컬럼:
  선거종류, 시도, 구시군, 선거구, 읍면동명, 구분,
  선거인수, 투표수, 후보자별 득표수_<후보>, ..., 후보자별 득표수_계, 무효 투표수, 기권자수

race 정의 (후보 집합이 동일한 최소 단위):
  시도지사·광역비례·교육감  → (선거종류, 시도)
  구시군의장·기초비례        → (선거종류, 시도, 구시군)
  시도의원·구시군의원        → (선거종류, 시도, 구시군, 선거구)
"""
import sys
from pathlib import Path
import pandas as pd

# Windows 콘솔에서도 한글/기호가 안 깨지게 (그리고 cp949 인코딩 크래시 방지)
for _stream in ("stdout", "stderr"):
    try:
        getattr(sys, _stream).reconfigure(encoding="utf-8")
    except Exception:
        pass

CAND_PREFIX = "후보자별 득표수_"
TOTAL_COL = "후보자별 득표수_계"

# race 키 (선거종류별)
RACE_KEYS = {
    "시도지사": ["선거종류", "시도"],
    "광역비례": ["선거종류", "시도"],
    "교육감":   ["선거종류", "시도"],
    "구시군의장": ["선거종류", "시도", "구시군"],
    "기초비례":   ["선거종류", "시도", "구시군"],
    "시도의원":   ["선거종류", "시도", "구시군", "선거구"],
    "구시군의원": ["선거종류", "시도", "구시군", "선거구"],
}
# 구분(투표 종류) 표준값
GUBUN_EARLY = "관내사전투표"
GUBUN_DAYOF = "선거일투표"
GUBUN_SUBTOTAL = "계"


def base_dir(base="nec_data"):
    here = Path(__file__).resolve().parent
    for cand in (Path(base), here / ".." / base, here.parent / base):
        if Path(cand).exists():
            return Path(cand)
    return Path(base)


def _coerce_nums(df):
    for c in df.columns:
        if c.startswith(CAND_PREFIX) or c in ("선거인수", "투표수", "무효 투표수", "기권자수"):
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.replace("-", ""),
                errors="coerce")
    return df


def long_path():
    """커밋된 long 데이터셋(data/processed/nec_2026_local.csv[.gz]) 경로."""
    here = Path(__file__).resolve().parent
    roots = (here / ".." / "data", here.parent / "data", Path("data"))
    for d in roots:
        for sub in ("processed", ""):
            for name in ("nec_2026_local.csv.gz", "nec_2026_local.csv"):
                p = Path(d) / sub / name
                if p.exists():
                    return p
    return None


def load_from_long(election_type):
    """raw wide가 없을 때, 커밋된 long 데이터에서 wide(per-type)로 복원."""
    lp = long_path()
    if lp is None:
        return None
    long = pd.read_csv(lp, dtype={"선거구": str}, low_memory=False)
    sub = long[long["선거종류"] == election_type].copy()
    if sub.empty:
        return None
    name = (sub["정당"].fillna("").astype(str) + " " + sub["후보명"].fillna("").astype(str)).str.strip()
    sub["_cand"] = CAND_PREFIX + name
    sub["선거구"] = sub["선거구"].fillna("")
    key = ["선거종류", "시도", "구시군", "선거구", "읍면동", "구분"]
    # 관측 조합만 (groupby+unstack — 데카르트 곱 방지)
    votes = sub.groupby(key + ["_cand"])["득표수"].first().unstack("_cand")
    meta_cols = [c for c in ("선거인수", "투표수", "무효투표수", "유효합계") if c in sub.columns]
    meta = sub.groupby(key)[meta_cols].first()
    wide = meta.join(votes).reset_index()
    wide = wide.rename(columns={"읍면동": "읍면동명", "유효합계": TOTAL_COL,
                                "무효투표수": "무효 투표수"})
    return _coerce_nums(wide)


def load_type(election_type, base="nec_data"):
    """선거종류 1개 합본 로드. raw wide(nec_data/) 우선, 없으면 커밋된 long에서 복원."""
    fp = base_dir(base) / election_type / "_combined.csv"
    if fp.exists():
        df = pd.read_csv(fp, dtype={"선거구": str})
        df.columns = [c.replace("정당별 득표수_", CAND_PREFIX) for c in df.columns]
        return _coerce_nums(df)
    df = load_from_long(election_type)
    if df is None:
        raise FileNotFoundError(
            f"{fp} 도, long 데이터(data/nec_2026_local.csv.gz)도 없음 — "
            f"nec_download.py 또는 make_dataset.py 먼저 실행")
    return df


def cand_cols(df):
    """후보 득표 컬럼(계 제외) — 해당 부분집합에서 값이 존재하는 것만."""
    cols = [c for c in df.columns
            if c.startswith(CAND_PREFIX) and c != TOTAL_COL]
    return [c for c in cols if df[c].notna().any()]


def iter_races(df, election_type):
    """race 키별 (key_dict, race_df) 생성.
    race 안에서 전부 빈(다른 race 후보) 컬럼은 제거 → 의원/비례 wide 가속."""
    keys = RACE_KEYS[election_type]
    cand_all = [c for c in df.columns if c.startswith(CAND_PREFIX)]
    meta = [c for c in df.columns if c not in cand_all]
    for vals, sub in df.groupby(keys, dropna=False):
        if not isinstance(vals, tuple):
            vals = (vals,)
        keep_cand = [c for c in cand_all if sub[c].notna().any()]
        yield dict(zip(keys, vals)), sub[meta + keep_cand].reset_index(drop=True)


def race_label(key_dict):
    return " ".join(str(v) for k, v in key_dict.items() if k != "선거종류" and pd.notna(v))


def units(race_df, gubun):
    """특정 구분(관내사전투표/선거일투표/계)의 읍면동 단위 행만.
       반환: 읍면동명 인덱스 + 후보 컬럼 + 선거인수/투표수."""
    sub = race_df[race_df["구분"] == gubun].copy()
    # 읍면동명이 합계/거소/관외 등 집계행이 아닌 실제 읍면동만 (구분이 채워진 행 = 읍면동 하위)
    sub = sub[sub["읍면동명"].notna()]
    return sub.reset_index(drop=True)


def winner_col(race_df, cc=None):
    """전체 합계 기준 1위 후보 컬럼."""
    cc = cc or cand_cols(race_df)
    if not cc:
        return None
    tot = race_df[cc].sum(numeric_only=True)
    return tot.idxmax() if len(tot) else None
