---
name: aarrr-report-blog119kr
description: GA4 데이터로 AARRR 퍼널 리포트(유입·행동·재방문·CPA·추천유입)를 만들어 루커스튜디오 스타일 HTML 한 장으로 출력한다. 어떤 GA4 속성에도 쓸 수 있다. 매개변수는 서비스명(없으면 total), 기간(없으면 지난 7일), 속성 ID.
license: MIT
metadata:
  author: blog119kr (행복나무 · https://blog119.co.kr)
  version: "1.0.0"
---

# AARRR 리포트 (GA4)

GA4 데이터로 AARRR(Acquisition · Activation · Retention · Revenue→CPA · Referral) 리포트를 만든다. 결과는 HTML 파일 한 장이다. 디자인은 `assets/template.html`(루커스튜디오 'AARRR FUNNEL REPORT' 스타일)을 그대로 쓰고, 데이터만 채운다.

이 스킬은 특정 AI 도구에 묶여 있지 않다. GA4 데이터를 조회할 수 있는 도구(Windsor.ai MCP, Google Analytics Data API, 공식 GA MCP 서버 등)와 Python 실행 환경이 있으면 어떤 LLM 에이전트에서도 쓸 수 있다.

## 파일 구성

| 경로 | 내용 |
|---|---|
| `SKILL.md` | 이 문서. 작업 절차와 규칙 |
| `assets/template.html` | 리포트 템플릿. `__TITLE__`, `__DATA__` 두 곳만 바뀐다 |
| `scripts/build_report.py` | 조회 결과(JSON)를 집계해 HTML을 만드는 스크립트 |
| `references/data-sources.md` | Windsor.ai / GA4 Data API별 필드명·필터 대응표 |
| `examples/` | 가상 데이터로 만든 설정·결과·리포트 예시 |

## 0. 매개변수

`aarrr-report [서비스명] [기간] [속성]` — 모두 선택이고 순서는 상관없다.

| 매개변수 | 없을 때 | 받는 값 |
|---|---|---|
| 서비스명 | **total** (서비스 필터 없음) | 설정(1장)에 등록된 서비스명 |
| 기간 | **지난 7일** | 지난7일 / 어제 / 지난주 / 지난달 / `YYYY-MM-DD~YYYY-MM-DD` |
| 속성 | 설정에 적힌 GA4 속성 ID. 없으면 한 줄로 묻는다 | GA4 속성 ID |

기간은 오늘을 빼고 KST(사용자 시간대) 기준으로 계산한다. 현재 기간(cur)과 비교 기간(prev)은 다음과 같다.
- 지난7일: 어제까지 7일 / 그 직전 7일
- 어제: 어제 / 그 전날
- 지난주: 지난주 월~일 / 그 전주 월~일
- 지난달: 지난달 1일~말일 / 그 전달 1일~말일
- 직접 지정: 지정 기간 / 같은 일수의 직전 기간

등록되지 않은 서비스명이 들어오면 시작 전에 "등록된 서비스: …, 또는 total 중 어느 것인가요?"라고 한 줄로 묻는다. 여러 서비스를 한 리포트에 섞지 않는다.

## 1. 설정 (config.json)

속성별 설정은 스킬에 적지 않는다. 사용자의 프로젝트 지침, 시스템 프롬프트, 메시지에서 읽어 `config.json`으로 만든다.

```json
{
  "property_name": "예시 쇼핑몰",
  "property_id": "123456789",
  "service": null,
  "cur": ["2026-11-02", "2026-11-08"],
  "prev": ["2026-10-26", "2026-11-01"],
  "asof": "2026-11-09",
  "block_date": null,
  "block_reason": "전환추적 개편일"
}
```

| 항목 | 없을 때 |
|---|---|
| `property_name` · `property_id` | 속성 ID는 한 줄로 묻는다 |
| `service`: `{"name","key","title","prefix"}` — KEY(방문 페이지·캠페인 필터), TITLE(인기 페이지 제목 필터), PREFIX(캠페인명 표시에서 지울 접두어) | `null` → total |
| `block_date`: 비교 불가 기준일(전환추적 개편일 등) | `null` → 항상 비교 가능 |
| 비용 import가 주 1회인 매체와 갱신 요일 | 6장의 '갱신 전일' 안내를 생략 |

비교 기간 시작일이 `block_date`보다 앞이면 리포트에 `blocked`가 켜진다. 이때 전환·전환율·CPA 증감은 '비교 불가'로 표시되고, 상단에 빨간 안내문이 뜬다.

## 2. 고정 규칙

- GA4 데이터만 쓴다. 광고비는 GA4의 광고 비용 측정항목(`advertiserAdCost`: 구글애즈 연동, 비용 데이터 가져오기 등)을 쓴다. 속성에 따라 광고비 데이터가 없을 수 있다.
- 데이터 조회는 읽기 전용이다. 광고·분석 플랫폼에 쓰기 작업은 하지 않는다.
- 측정기준은 세션 범위를 쓴다(세션 소스/매체, 세션 수동 캠페인, 세션 구글애즈 캠페인).
- 서비스 필터(방문 페이지에 KEY 포함, 세션 캠페인에 KEY 포함)는 서비스가 지정됐을 때만 쓴다. 그 밖에는 필터 없이 total이다.
- 전환 = 주요 이벤트(key events) 전체다. 이벤트 필터는 걸지 않는다.
- newUsers(새 사용자)와 activeUsers(활성 사용자)는 다른 개념이다. 각각 따로 표시하고, 서로 빼서 재방문을 추정하지 않는다.
- 신규/재방문은 GA4 측정기준 `newVsReturning`(new / returning / (not set))을 그대로 쓴다. 재방문은 항상 빨간색, (not set)은 회색이다.
- REVENUE는 매출이 아니라 **CPA = 광고비 ÷ 광고 전환**으로 본다. 광고비 데이터가 전혀 없으면(현재+비교 기간 합계 0) CPA 대신 **세션 주요 이벤트 비율**(전환 ÷ 세션)을 표시한다. 스크립트가 자동으로 고른다.
- REFERRAL은 세션 소스/매체가 `/ referral` 또는 `/ organic`으로 끝나는 세션만 쓴다.
- 모든 표는 10위까지만 표시하고, 하단에 `1 - 10 / 전체행수`를 표시한다.
- 리포트에는 조회 도구 이름, '확인 필요' 같은 표현, 내부 가설을 쓰지 않는다.

## 3. 조회 목록

필드 이름은 Windsor.ai 형식(snake_case)으로 적었다. GA4 Data API 이름과 필터 문법은 `references/data-sources.md`를 본다. 필터 F는 서비스가 있으면 "방문 페이지에 KEY 포함", total이면 없음이다. 서로 의존하지 않는 조회는 한 번에 병렬로 보낸다.

| 키 | 측정기준 + 측정항목 | 기간 | 필터 |
|---|---|---|---|
| tot / totP | active_users, newusers, sessions, engaged_sessions, average_session_duration, conversions | cur / prev | F |
| nvr / nvrP | new_vs_returning + tot의 항목 | cur / prev | F |
| daily | date, new_vs_returning, active_users, sessions, engaged_sessions, average_session_duration, conversions | prev 시작 ~ cur 끝 | F |
| src / srcP | session_source_medium, new_vs_returning, sessions, engaged_sessions, average_session_duration, conversions | cur / prev | F |
| dev | devicecategory, sessions, conversions | cur | F |
| pg | pagetitle, screen_page_views, active_users | cur | 서비스: 페이지 제목에 TITLE 포함 + 조회수 > 2 / total: 조회수 > 2 |
| costG | date, session_google_ads_campaign_name, advertiser_ad_cost, sessions, engaged_sessions, conversions | prev 시작 ~ cur 끝 | 서비스: 구글애즈 캠페인에 KEY 포함 / total: 광고비 > 0 |
| costN | date, session_source_medium, session_manual_campaign_name, advertiser_ad_cost, sessions, engaged_sessions, conversions | prev 시작 ~ cur 끝 | 서비스: 수동 캠페인에 KEY 포함 + 소스/매체에 google 없음 / total: 소스/매체에 google 없음 + 광고비 > 0 |

- 인기 페이지는 **페이지 제목** 기준으로 묶는다. 경로(page_path)로 나누면 같은 페이지가 여러 행으로 쪼개진다.
- total의 광고비·CPA는 광고비 > 0인 모든 캠페인으로 계산한다.

## 4. 결과 저장 → 집계

1. 각 조회 결과의 **행 배열을 그대로** `results.json`에 키별로 저장한다. 수치를 손으로 옮겨 적거나 머릿속으로 계산하지 않는다. 도구 결과가 파일로 저장돼 경로만 온다면 그 파일을 읽어 옮긴다.

   ```json
   { "tot": [ {...} ], "totP": [ {...} ], "nvr": [...], "nvrP": [...], "daily": [...],
     "src": [...], "srcP": [...], "dev": [...], "pg": [...], "costG": [...], "costN": [...] }
   ```

   행의 키는 snake_case(Windsor)나 camelCase(GA4 Data API) 모두 된다. 스크립트가 자동으로 맞춘다. 날짜 `YYYYMMDD`와 빈 측정기준 값(`""` → `(not set)`)도 스크립트가 정리한다.
2. 스크립트를 실행한다.

   ```bash
   python3 scripts/build_report.py config.json results.json aarrr-report.html
   ```

   스크립트가 하는 일:
   - 세션 가중 평균 체류시간, 일별 스파크라인, 상위 6개 + 기타 막대, 퍼널을 집계한다.
   - CPA 표를 만든다. 행은 (소스/매체, 캠페인)이고 CPA 낮은 순, 전환 0건은 아래로 보낸다. 증감과 등급(개선필요 / 효율우수 / 기타)도 붙인다.
   - 광고비가 없으면 rate 모드로 바꾼다.
   - 결과를 템플릿에 채운다.

   Python을 실행할 수 없는 환경이면 스크립트의 `build()` 로직을 그대로 따라 데이터 JSON을 만들고, 템플릿의 `__DATA__`에 넣는다(`</`는 `<\/`로 이스케이프).

## 5. 확인과 전달

- 가능하면 브라우저(Playwright 등)로 한 번 렌더링해 확인한다. 볼 것은 스크립트 오류, 재방문이 빨간색인지, 표가 10행 이하인지다. 고칠 것이 있으면 한 번 고치고 바로 전달한다.
- 템플릿의 디자인과 차트 코드는 바꾸지 않는다.
- HTML 파일을 사용자에게 전달한다. 환경이 웹 페이지 게시를 지원하면(예: Claude Artifact) 게시하고, 서비스·total별로 같은 페이지를 계속 덮어쓴다.
- 차트는 외부 라이브러리 없이 인라인 SVG로 그리므로 오프라인에서도 열린다.

## 6. 답변 형식

- 핵심 결론 1~3줄을 먼저 쓴다. 지정한 서비스(또는 total)만 다룬다.
- 광고비를 말할 때는 항상 전환 수와 CPA를 함께 말한다. 광고비 데이터가 없으면 그 사실을 한 줄로 알리고 세션 주요 이벤트 비율로 말한다.
- 비용 import가 주 1회인 매체의 최근 비용이 0이면 '갱신 전일 가능성'을 먼저 언급하고, 그 매체는 CPA 계산에서 뺀다.
- 표본이 작으면(전환 5건 미만) 그렇게 명시한다.
- 참여율 0%, 체류 0초인 referral이 몰려 있으면 스팸(봇) 유입 가능성을 알린다.
- 하단에 조회 기간과 필터 조건을 짧게 적는다.
- 맨 끝에 `⚠️ 답변의 신뢰도 OO%`를 붙인다.
