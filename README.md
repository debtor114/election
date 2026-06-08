# NEC 개표 데이터 검증 도구 (6·3 지방선거)

대한민국 중앙선거관리위원회 선거통계시스템(info.nec.go.kr)의 **읍면동별 개표결과**를
공개 엔드포인트로 내려받아, 개표 데이터를 **재현 가능한 통계 검정**에 넣는 도구다.
출력은 **단서·반증**이지 평결이 아니다.

> 📊 **한눈에 보기(대시보드) → https://debtor114.github.io/election/**  ·  📄 상세 → [`PUBLIC_REPORT.md`](PUBLIC_REPORT.md)

> ⚠️ **이건 "검증 도구"이지 "평결"이 아니다.** 각 검정은 (관측값)과 (우연이라면 나올 기대치)를
> 함께 내고 **PASS(우연 모델로 설명되는 범위) / FLAG(기대치를 통계적으로 초과 → 더 볼 지점)** 만 표시한다.
> **FLAG도 PASS도 그 자체로 부정·결백의 증명이 아니다.** 전국 ~1,245개 선거를 동시에 보면 우연한 FLAG가
> 몇 건 나온다(다중비교). 해석은 읽는 사람의 몫이고, 데이터·코드·임계값을 전부 공개하니 직접 반박·재현하라.

## 빠른 시작

데이터(원본·가공본)가 repo에 동봉돼 있어 **clone만 하면 바로 재현**된다.

```bash
pip install -r requirements.txt

# 1) 무결성 확인 — 가공본이 원본 숫자를 안 건드렸나 (1줄)
python verify_dataset.py

# 2) 검증 배터리 실행 (동봉 데이터로 자동 재현)
cd election_verify
python run_all.py                 # 전체 요약 리포트
python run_all.py 시도지사         # 특정 선거종류
python tests/T3_turnout_forensics.py 시도지사   # 개별 검정 + 플롯

# 3) (선택) 원본을 선관위에서 직접 다시 받기
python nec_download.py --type all --out nec_data
```

## 구성

```
nec-election-verify/
├── index.html                # 결과 대시보드 (GitHub Pages)
├── PUBLIC_REPORT.md          # 공개 리포트 (중립 서술)
├── nec_download.py           # T0: 선관위 읍면동별 개표결과 다운로더 (requests 전용)
├── make_dataset.py           # 원본(wide) → 가공본(long) 변환
├── verify_dataset.py         # 원본 = 가공본(숫자 불변) 무결성 검증
├── check_duplicate_votes.py  # T1 원형(단일 파일 버전)
├── SPEC_election_verification.md   # 검정 명세 (결과 보기 전 고정)
├── data/
│   ├── raw/<선거종류>.csv.gz   # 손대지 않은 원본 (7종) + CHECKSUMS.sha256
│   ├── processed/nec_2026_local.csv.gz   # 가공본 (long, 35만 행)
│   ├── SOURCE.md             # 출처·스냅샷·체크섬·검증법
│   └── shortage_list.example.csv   # T5·T6용 부족 투표소 양식
├── election_verify/
│   ├── necdata.py            # 공용 로더 (원본 없으면 동봉 가공본 자동 사용)
│   ├── run_all.py            # 일괄 실행 + 요약 리포트
│   ├── tests/T1..T6.py      # 개별 검정
│   └── out/T3_*.png          # 포렌식 플롯 7종
├── requirements.txt · LICENSE (MIT) · .gitignore
```

## 데이터 다운로더 (nec_download.py)

선관위 시스템은 JSF/ViewState 기반이라 단순 스크래핑이 어렵다. 이 도구는 내부 JSON
셀렉트박스와 리포트 엔드포인트를 직접 호출해 Selenium 없이 동작한다. 선거종류별 선택 경로:

| 경로 | 선거종류 | 핵심 파라미터 |
|---|---|---|
| 시도단위 | 시도지사·교육감·광역비례 | `townCode`(구시군) |
| 구시군단위 | 구시군의장·기초비례 | `sggCityCode`+`townCodeFromSgg` |
| 선거구단위 | 시도의원·구시군의원 | `townCode`+`sggTownCode`(선거구) |

다른 선거는 `--election-id`로 교체(예: 2024 총선 `0020240410`).

## 검정 요약

| 검정 | 내용 | FLAG 조건 |
|---|---|---|
| T1 동일득표 | 읍면동 간 동일 득표 쌍 vs 부트스트랩 null | 상위2 z>+3 / 방향 z>+3 / 복제쌍≥1 |
| T2 사전vs본 | 사전·본 득표율 회귀의 완벽함 | R²>0.999 & 잔차<0.005 |
| T3 투표율포렌식 | (투표율,승자득표율) 산점·2D히스토 | 꼬리상관>0.45 & lift>0.05 |
| T4 끝자리/벤포드 | 득표수 자릿수 (보조·약함) | p<0.001 (단독 근거 금지) |
| T5 부족투표소 편향 | 부족 읍면동 정당 득표율 순열검정 | 순열분포 ±3σ 밖 |
| T6 부족 vs 투표율 | 부족이 당일 고투표율로 설명되나 | 투표율 정상인데 부족한 읍면동 존재 |

자세한 내용은 [`election_verify/README.md`](election_verify/README.md) 참조.

## 🍴 얼마든지 가져가서 돌려보세요

이 저장소는 **누구나 자유롭게 fork·복제·수정·재현·반박**하라고 공개합니다.
검증은 한 사람의 주장보다 *여러 사람이 각자 돌려본 결과*가 모일 때 신뢰가 생깁니다.

- **Fork** 해서 직접 돌려보고, 결과가 다르면 알려주세요(이슈/PR 환영).
- 검정 임계값·방법이 마음에 안 들면 고쳐서 돌려보세요 — 그게 핵심입니다.
- 다른 선거(총선·대선 등)도 `--election-id`만 바꾸면 같은 도구로 검증됩니다.
- 코드는 **MIT 라이선스**([`LICENSE`](LICENSE)) — 출처만 밝히면 어디든 가져다 쓰세요.

> "내 말을 믿어라"가 아니라 **"직접 확인해봐라"** 가 이 프로젝트의 태도입니다.

## 데이터 출처·투명성

"내 파일을 믿어라"가 아니라 **"공식 출처에서 그대로 다시 만들어 내고, 아무것도 안 건드렸음을
확인할 수 있다"** 를 목표로 구성했다. 자세히: [`data/SOURCE.md`](data/SOURCE.md).

- **출처**: 중앙선거관리위원회 https://info.nec.go.kr (공개 데이터, `electionId=0020260603`, 스냅샷 2026-06-08).
- **원본/가공 분리**: `data/raw/`(손대지 않은 원본) + `data/processed/`(가공본) + 둘을 잇는 변환 코드(`make_dataset.py`).
- **체크섬**: `data/raw/CHECKSUMS.sha256` — 누구나 선관위에서 다시 받아 값 일치를 대조 가능.
- **무결성 검증**: `python verify_dataset.py` — 가공본이 원본 숫자를 안 건드렸음을 1줄로 확인.
- **코드 라이선스**: **MIT** ([`LICENSE`](LICENSE)). 데이터 재배포 시 출처(선관위)·이용약관(공공누리 등) 확인.
