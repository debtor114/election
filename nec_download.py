#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
선관위 선거통계시스템(info.nec.go.kr) '읍면동별 개표결과' 전국 다운로더 [requests 전용]
=====================================================================================
지방선거 7종(시도지사·구시군의장·시도의원·구시군의원·광역비례·기초비례·교육감)을
선거종류별 선택 경로에 맞춰 전국/시도 단위로 긁어 CSV로 저장한다. Selenium 불필요.

[선택 경로]  (모두 statementId=VCCP08_#00)
  A 시도단위 (3 시도지사 / 8 광역비례 / 11 교육감)
      cityCode → selectbox_townCodeJson.json{electionId,cityCode} → townCode(구시군)
      report: townCode
  B 구시군단위 (4 구시군의장 / 9 기초비례)
      cityCode → selectbox_getSggCityCodeJson.json{...electionCode,cityCode} → sggCityCode
              → selectbox_townCodeFromSggJson.json{...sggCityCode} → townCodeFromSgg(개표구)
      report: sggCityCode + townCodeFromSgg
  C 선거구단위 (5 시도의원 / 6 구시군의원)
      cityCode → selectbox_townCodeJson.json → townCode(구시군)
              → selectbox_getSggTownCodeJson.json{...electionCode,cityCode,townCode} → sggTownCode(선거구)
      report: townCode + sggTownCode
  데이터 표: /electioninfo/electionInfo_report.xhtml → pandas.read_html

사용법:
  pip install requests pandas lxml
  python nec_download.py --type all                 # 전국·7종 전부 (오래 걸림)
  python nec_download.py --type all --sido 전라남도   # 전남·7종
  python nec_download.py --type 구시군의장            # 전국·단체장
  python nec_download.py --type 시도의원 --sido 서울   # 서울·시도의원

결과:
  out/<선거종류>/<시도>_<구시군>[_<선거구>].csv   +   out/<선거종류>/_combined.csv
  out/_ALL_combined.csv   (모든 선거 합본, 분석용)
"""
import argparse
import sys
import time
from io import StringIO
from pathlib import Path

import requests

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas 필요:  pip install pandas lxml")

BASE = "https://info.nec.go.kr"
REPORT = f"{BASE}/electioninfo/electionInfo_report.xhtml"
SB = f"{BASE}/bizcommon/selectbox/"
JSON_TOWN = SB + "selectbox_townCodeJson.json"            # cityCode → 구시군(townCode)
JSON_SGGCITY = SB + "selectbox_getSggCityCodeJson.json"   # cityCode → 구시군(sggCityCode) [B]
JSON_TOWNFROMSGG = SB + "selectbox_townCodeFromSggJson.json"  # sggCityCode → 개표구
JSON_SGGTOWN = SB + "selectbox_getSggTownCodeJson.json"   # townCode → 선거구(sggTownCode) [C]

SIDO = {
    "서울": "1100", "부산": "2600", "대구": "2700", "인천": "2800", "광주": "2900",
    "대전": "3000", "울산": "3100", "세종": "5100", "경기": "4100", "강원": "5200",
    "충북": "4300", "충남": "4400", "전북": "5300", "전남": "4600", "경북": "4700",
    "경남": "4800", "제주": "4900",
}
SIDO_ALIAS = {  # 풀네임도 허용
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북",
    "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}
ELECTION = {  # 표시이름 → (code, 한글명)
    "시도지사": ("3", "시도지사"), "구시군의장": ("4", "구시군의장"),
    "시도의원": ("5", "시도의원"), "구시군의원": ("6", "구시군의원"),
    "광역비례": ("8", "광역비례"), "기초비례": ("9", "기초비례"),
    "교육감": ("11", "교육감"),
}
PATH_A = {"3", "8", "11"}
PATH_B = {"4", "9"}
PATH_C = {"5", "6"}
ALL_TYPES = ["시도지사", "교육감", "구시군의장", "시도의원", "구시군의원", "광역비례", "기초비례"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Origin": BASE, "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


def new_session(election_id):
    s = requests.Session()
    s.headers.update(HEADERS)
    s.headers["Referer"] = (f"{BASE}/main/showDocument.xhtml?electionId={election_id}"
                            f"&topMenuId=VC&secondMenuId=VCCP08")
    s.get(s.headers["Referer"], timeout=20)
    return s


def options(s, url, **params):
    try:
        r = s.post(url, data=params, timeout=20)
        r.encoding = "utf-8"
        body = r.json().get("jsonResult", {}).get("body", [])
        return [(o["CODE"], o["NAME"]) for o in body]
    except Exception:
        return []


def fetch_report(s, election_id, election_code, city_code,
                 sgg_city="-1", town_from_sgg="-1", town="-1", sgg_town="-1"):
    """읍면동별 개표결과 표 1개 → DataFrame. 데이터 없으면(무투표 등) None."""
    data = {
        "electionId": election_id,
        "requestURI": f"/electioninfo/{election_id}/vc/vccp08.jsp",
        "topMenuId": "VC", "secondMenuId": "VCCP08", "menuId": "VCCP08",
        "statementId": "VCCP08_#00", "electionCode": election_code,
        "cityCode": city_code, "sggCityCode": sgg_city,
        "townCodeFromSgg": town_from_sgg, "townCode": town,
        "sggTownCode": sgg_town, "checkCityCode": "-1",
    }
    try:
        r = s.post(REPORT, data=data, timeout=30)
        r.encoding = "utf-8"
        tables = pd.read_html(StringIO(r.text), flavor="lxml")
    except Exception:
        return None
    # 후보 득표 표: 행 충분 + 열 충분
    cand = [t for t in tables if t.shape[0] >= 3 and t.shape[1] >= 5]
    if not cand:
        return None
    df = flatten_columns(max(cand, key=lambda t: t.shape[0] * t.shape[1]))
    # 무투표/안내문 표 거르기
    head = " ".join(str(x) for x in df.iloc[0].tolist())
    if "무투표" in head or "결과가 없" in head:
        return None
    return df


def flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        cols = []
        for tup in df.columns:
            parts, seen = [str(x) for x in tup if str(x) != "nan"], []
            for p in parts:
                if not seen or seen[-1] != p:
                    seen.append(p)
            cols.append("_".join(seen))
        df = df.copy(); df.columns = cols
    return df


def units_for(s, eid, ecode, city_code):
    """선거종류별 (보고서 1건 단위) 리스트 생성.
    yield (라벨dict, report_kwargs)."""
    if ecode in PATH_A:
        for tcode, tname in options(s, JSON_TOWN, electionId=eid, cityCode=city_code):
            yield {"구시군": tname, "선거구": ""}, dict(town=tcode)
    elif ecode in PATH_B:
        for scode, sname in options(s, JSON_SGGCITY, electionId=eid,
                                    electionCode=ecode, cityCode=city_code):
            tfs = options(s, JSON_TOWNFROMSGG, electionId=eid,
                          electionCode=ecode, sggCityCode=scode)
            if not tfs:
                tfs = [(scode, sname)]
            for tcode, tname in tfs:
                yield {"구시군": sname, "선거구": ""}, dict(sgg_city=scode, town_from_sgg=tcode)
    elif ecode in PATH_C:
        for tcode, tname in options(s, JSON_TOWN, electionId=eid, cityCode=city_code):
            for gcode, gname in options(s, JSON_SGGTOWN, electionId=eid,
                                        electionCode=ecode, cityCode=city_code, townCode=tcode):
                yield {"구시군": tname, "선거구": gname}, dict(town=tcode, sgg_town=gcode)


def run_type(s, eid, etype, ecode, sidos, out_root, delay, limit):
    out_dir = out_root / etype
    out_dir.mkdir(parents=True, exist_ok=True)
    type_frames = []
    for sido, city in sidos:
        units = list(units_for(s, eid, ecode, city))
        if limit:
            units = units[:limit]
        print(f"  [{etype}/{sido}] 단위 {len(units)}개")
        sido_frames = {}
        for label, rkw in units:
            df = fetch_report(s, eid, ecode, city, **rkw)
            time.sleep(delay)
            if df is None:
                continue
            df.insert(0, "선거구", label["선거구"])
            df.insert(0, "구시군", label["구시군"])
            df.insert(0, "시도", sido)
            df.insert(0, "선거종류", etype)
            type_frames.append(df)
            sido_frames.setdefault(label["구시군"], []).append(df)
        # 구시군별 파일 저장
        for gu, frames in sido_frames.items():
            fp = out_dir / f"{sido}_{gu}.csv".replace(" ", "")
            pd.concat(frames, ignore_index=True).to_csv(fp, index=False, encoding="utf-8-sig")
    if type_frames:
        allt = pd.concat(type_frames, ignore_index=True)
        allt.to_csv(out_dir / "_combined.csv", index=False, encoding="utf-8-sig")
        print(f"  → {etype}: {len(allt)}행 저장")
        return allt
    print(f"  → {etype}: 데이터 없음")
    return None


def main():
    ap = argparse.ArgumentParser(description="선관위 읍면동별 개표결과 전국 다운로더")
    ap.add_argument("--election-id", default="0020260603", help="선거 ID (기본 2026 지방선거)")
    ap.add_argument("--type", required=True,
                    help="선거종류 또는 all. (시도지사/구시군의장/시도의원/구시군의원/광역비례/기초비례/교육감/all)")
    ap.add_argument("--sido", help="시도명(생략 시 전국). 예: 전라남도, 서울")
    ap.add_argument("--out", default="nec_data", help="저장 폴더")
    ap.add_argument("--delay", type=float, default=0.25, help="요청 간 딜레이(초)")
    ap.add_argument("--limit", type=int, default=0, help="시도별 단위 개수 제한(테스트용)")
    args = ap.parse_args()

    # 선거종류
    if args.type == "all":
        types = [(n, *ELECTION[n]) for n in ALL_TYPES]
    elif args.type in ELECTION:
        types = [(args.type, *ELECTION[args.type])]
    else:
        sys.exit(f"알 수 없는 선거종류: {args.type}\n  가능: {', '.join(ELECTION)} 또는 all")

    # 시도
    if args.sido:
        key = SIDO_ALIAS.get(args.sido, args.sido)
        if key not in SIDO:
            sys.exit(f"알 수 없는 시도: {args.sido}")
        sidos = [(key, SIDO[key])]
    else:
        sidos = list(SIDO.items())

    out_root = Path(args.out)
    s = new_session(args.election_id)
    master = []
    for etype, ecode, _kr in types:
        print(f"\n===== {etype} (code={ecode}) =====")
        df = run_type(s, args.election_id, etype, ecode, sidos, out_root, args.delay, args.limit)
        if df is not None:
            master.append(df)
    if master:
        big = pd.concat(master, ignore_index=True)
        big.to_csv(out_root / "_ALL_combined.csv", index=False, encoding="utf-8-sig")
        print(f"\n■ 전체 합본: {out_root/'_ALL_combined.csv'}  ({len(big)}행)")


if __name__ == "__main__":
    main()
