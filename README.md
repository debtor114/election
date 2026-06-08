# NEC 개표 데이터 검증 (6·3 지방선거)

대한민국 중앙선거관리위원회 선거통계시스템(info.nec.go.kr)의 **읍면동별 개표결과**를
공개 엔드포인트로 내려받고, 떠도는 개표 의혹을 **재현 가능한 통계 검정**으로 판정한다.

> 📊 **한눈에 보기 →** [`index.html`](index.html) (결과 대시보드)  ·  📄 상세 → [`PUBLIC_REPORT.md`](PUBLIC_REPORT.md)
>
> GitHub Pages를 켜면(Settings → Pages → main 브랜치) `https://<사용자>.github.io/<repo>/` 에서
> 대시보드가 바로 열립니다. 로컬에선 `index.html`을 브라우저로 열면 됩니다.

> ⚠️ **목적은 팩트체크다.** 이 도구는 부정을 "증명"하지 않는다. 각 검정은 (관측값)과
> (우연 기대치)를 함께 내고 **PASS(정상) / FLAG(정밀조사 대상)** 만 표시한다.
> FLAG는 "우연으로 설명하기 어렵다"는 뜻일 뿐, 그 자체가 부정의 증거가 아니다.
> 전국 수백 개 선거를 동시에 보면 우연한 FLAG가 나온다(다중비교)는 점을 항상 감안하라.

## 빠른 시작

```bash
pip install -r requirements.txt

# 1) 데이터 받기 (선관위에서 직접) — 전국·7종 (시간 걸림)
python nec_download.py --type all --out nec_data
#   또는 일부만:  python nec_download.py --type 시도지사 --sido 전라남도

# 2) 검증 배터리 실행
cd election_verify
python run_all.py                 # 전체 요약 리포트
python run_all.py 시도지사         # 특정 선거종류
python tests/T3_turnout_forensics.py 시도지사   # 개별 검정 + 플롯
```

## 구성

```
nec-election-verify/
├── nec_download.py            # T0: 선관위 읍면동별 개표결과 다운로더 (requests 전용)
├── check_duplicate_votes.py  # T1 원형(단일 파일 버전)
├── SPEC_election_verification.md   # 검정 배터리 작업 명세
├── election_verify/
│   ├── necdata.py            # 공용 로더 (tidy 스키마, race/후보 식별)
│   ├── run_all.py            # 일괄 실행 + 요약 리포트
│   ├── README.md            # 검정 상세
│   └── tests/T1..T6.py      # 개별 검정
├── data/shortage_list.example.csv   # T5·T6용 부족 투표소 목록 양식
├── requirements.txt
└── .gitignore               # nec_data/ 등 대용량·생성물 제외
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

## 데이터 출처·라이선스
- 출처: 중앙선거관리위원회 선거통계시스템 (https://info.nec.go.kr) — 공개 데이터.
- 코드: **MIT** ([`LICENSE`](LICENSE)) — 자유 사용·수정·재배포.
- 데이터: 가공본(`data/nec_2026_local.csv.gz`)을 함께 포함. 재배포 시 출처(선관위)를 밝히세요.
