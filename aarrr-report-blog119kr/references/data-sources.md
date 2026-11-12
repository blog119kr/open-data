# MCP 방식: 필드·필터 대응표

MCP로 GA4를 조회할 때 쓰는 이름이다. MCP마다 이름 형식이 달라서, 결과 행의 키가 snake_case여도 camelCase(GA4 Data API)여도 `scripts/build_report.py`가 모두 받는다. 조회한 행 배열을 그대로 `results.json`에 넣으면 된다. 빅쿼리는 `bigquery.md`를 본다.

## 필드 이름

| 의미 | snake_case 형식 (일부 MCP) | GA4 Data API 형식 (공식 GA MCP 등) |
|---|---|---|
| 날짜 | `date` | `date` (YYYYMMDD → 스크립트가 변환) |
| 활성 사용자 | `active_users` | `activeUsers` |
| 새 사용자 | `newusers` (MCP에 따라 `new_users`) | `newUsers` |
| 세션수 | `sessions` | `sessions` |
| 참여 세션수 | `engaged_sessions` | `engagedSessions` |
| 평균 세션 시간(초) | `average_session_duration` | `averageSessionDuration` |
| 주요 이벤트(전환) | `conversions` | `keyEvents` |
| 신규/재방문 | `new_vs_returning` | `newVsReturning` |
| 세션 소스/매체 | `session_source_medium` | `sessionSourceMedium` |
| 기기 카테고리 | `devicecategory` (MCP에 따라 `device_category`) | `deviceCategory` |
| 페이지 제목 | `pagetitle` | `pageTitle` |
| 조회수 | `screen_page_views` | `screenPageViews` |
| 방문 페이지 | `landing_page` | `landingPage` |
| 세션 구글애즈 캠페인 | `session_google_ads_campaign_name` | `sessionGoogleAdsCampaignName` |
| 세션 수동 캠페인 | `session_manual_campaign_name` | `sessionManualCampaignName` |
| 광고비 | `advertiser_ad_cost` | `advertiserAdCost` |

필드 이름이 맞는지 모르겠으면, MCP에 필드 목록을 조회하는 도구가 있는지 먼저 확인하고 그 결과를 따른다.

## 필터 예시

### snake_case 형식 MCP (조건 배열)

```json
{"date_from": "2026-11-02", "date_to": "2026-11-08",
 "fields": ["session_source_medium", "new_vs_returning", "sessions"],
 "filters": [["landing_page", "contains", "<KEY>"]]}
```

- 조건 연결: `[["a","contains","x"],"and",["b","gt",0]]`
- 부정: `ncontains`

### GA4 Data API 형식 (`runReport`)

```json
{
  "dateRanges": [{"startDate": "2026-11-02", "endDate": "2026-11-08"}],
  "dimensions": [{"name": "sessionSourceMedium"}, {"name": "newVsReturning"}],
  "metrics": [{"name": "sessions"}, {"name": "engagedSessions"}],
  "dimensionFilter": {"filter": {"fieldName": "landingPage",
    "stringFilter": {"matchType": "CONTAINS", "value": "<KEY>"}}},
  "limit": 10000
}
```

- 측정항목 조건(광고비 > 0, 조회수 > 2)은 `metricFilter` + `numericFilter`(`GREATER_THAN`)로 건다.
- "google 미포함"은 `notExpression`으로 감싼다.
- 응답의 `rows[].dimensionValues` / `metricValues`는 `dimensionHeaders` / `metricHeaders` 이름을 키로 붙여 행 객체로 펴서 저장한다.

## 주의

- 사용자 수(활성·새 사용자)는 기간 고유값이다. 일별 값을 더하면 기간 값과 맞지 않으므로 KPI 숫자는 반드시 기간 전체 조회(tot / nvr)를 쓴다. 일별 조회는 스파크라인용이다.
- `averageSessionDuration`을 합칠 때는 세션 가중 평균을 쓴다(스크립트가 처리).
- 광고비 데이터가 하나도 없으면 REVENUE는 자동으로 '세션 주요 이벤트 비율' 모드가 된다.
