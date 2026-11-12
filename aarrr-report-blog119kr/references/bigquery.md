# 빅쿼리 방식: SQL 템플릿

GA4 → BigQuery 내보내기(`events_*` 테이블)로 조회할 때 쓴다. 쿼리 결과의 열 이름을 MCP 방식과 똑같이 맞췄으므로, 결과 행을 그대로 `results.json`의 각 키에 넣으면 된다.

## 먼저 알아 둘 점

- 빅쿼리 내보내기는 이벤트 단위 원본이라 세션·참여·사용자 수를 직접 계산한다. GA4 화면(보고서)과 보통 몇 % 차이가 난다. 리포트 답변에 이 점을 한 줄로 알린다.
- **광고비가 없다.** 사용자가 별도 광고비 테이블을 알려 주지 않으면 `costG`·`costN`은 빈 배열로 두고, 리포트는 '세션 주요 이벤트 비율' 모드가 된다.
- 세션 소스/매체는 `session_traffic_source_last_click` 필드를 쓴다(2024년 7월 이후 내보내기에 있음). 이 필드가 없는 오래된 테이블이면 `collected_traffic_source`로 바꾸고, 그것도 없으면 사용자에게 알린다.
- `active_users`는 참여 세션이 있거나 참여 시간이 0보다 큰 사용자로 근사한다. `newusers`는 `first_visit`·`first_open` 이벤트가 있는 사용자다.
- 날짜와 기간은 사용자 시간대가 아니라 내보내기 테이블의 `event_date`(속성 시간대) 기준이다.
- 쿼리 실행 위치(리전)가 데이터셋과 다르면 오류가 난다. 그때만 사용자에게 데이터셋 위치를 묻는다.
- 비용이 걱정되면 먼저 드라이런(dry run)으로 스캔량을 확인한다.

## 공통 머리말 (모든 쿼리 앞에 붙인다)

`<PROJECT>`, `<DATASET>`, 날짜, 주요 이벤트, 서비스 KEY만 바꾼다. 서비스가 없으면 `svc_key`는 빈 문자열로 둔다.

```sql
DECLARE d_from   STRING DEFAULT '20261102';     -- 이 쿼리의 시작일 (YYYYMMDD)
DECLARE d_to     STRING DEFAULT '20261108';     -- 이 쿼리의 종료일
DECLARE key_events ARRAY<STRING> DEFAULT ['purchase'];
DECLARE svc_key  STRING DEFAULT '';             -- 서비스 KEY (total이면 '')

CREATE TEMP TABLE ev AS
SELECT
  PARSE_DATE('%Y%m%d', event_date) AS date,
  user_pseudo_id,
  event_name,
  event_timestamp,
  device.category AS device,
  (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')     AS sid,
  (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number') AS snum,
  (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING))
     FROM UNNEST(event_params) WHERE key = 'session_engaged')                        AS engaged,
  (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS eng_ms,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location')  AS page_location,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title')     AS page_title,
  session_traffic_source_last_click.manual_campaign.source        AS src,
  session_traffic_source_last_click.manual_campaign.medium        AS med,
  session_traffic_source_last_click.manual_campaign.campaign_name AS camp
FROM `<PROJECT>.<DATASET>.events_*`
WHERE _TABLE_SUFFIX BETWEEN d_from AND d_to;

CREATE TEMP TABLE sess AS
SELECT
  user_pseudo_id, sid,
  MIN(date) AS date,
  CASE WHEN MIN(snum) IS NULL THEN '(not set)'
       WHEN MIN(snum) = 1 THEN 'new' ELSE 'returning' END AS new_vs_returning,
  COALESCE(CONCAT(ANY_VALUE(src), ' / ', ANY_VALUE(med)), '(direct) / (none)') AS session_source_medium,
  ANY_VALUE(device) AS devicecategory,
  ARRAY_AGG(page_location IGNORE NULLS ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)] AS landing_page,
  LOGICAL_OR(engaged = '1') AS is_engaged,
  SUM(IFNULL(eng_ms, 0)) AS eng_ms,
  (MAX(event_timestamp) - MIN(event_timestamp)) / 1e6 AS dur_sec,
  COUNTIF(event_name IN UNNEST(key_events)) AS conv,
  LOGICAL_OR(event_name IN ('first_visit', 'first_open')) AS is_first
FROM ev
WHERE sid IS NOT NULL
GROUP BY user_pseudo_id, sid
HAVING svc_key = '' OR STRPOS(IFNULL(landing_page, ''), svc_key) > 0;
```

## 키별 쿼리 (머리말 뒤에 하나씩 붙여 실행)

### tot / totP — 기간만 바꿔 두 번

```sql
SELECT
  COUNT(DISTINCT IF(is_engaged OR eng_ms > 0, user_pseudo_id, NULL)) AS active_users,
  COUNT(DISTINCT IF(is_first, user_pseudo_id, NULL))                 AS newusers,
  COUNT(*)                                                           AS sessions,
  COUNTIF(is_engaged)                                                AS engaged_sessions,
  AVG(dur_sec)                                                       AS average_session_duration,
  SUM(conv)                                                          AS conversions
FROM sess;
```

### nvr / nvrP

```sql
SELECT
  new_vs_returning,
  COUNT(DISTINCT IF(is_engaged OR eng_ms > 0, user_pseudo_id, NULL)) AS active_users,
  COUNT(DISTINCT IF(is_first, user_pseudo_id, NULL))                 AS newusers,
  COUNT(*) AS sessions, COUNTIF(is_engaged) AS engaged_sessions,
  AVG(dur_sec) AS average_session_duration, SUM(conv) AS conversions
FROM sess GROUP BY new_vs_returning;
```

### daily — 기간: 비교 시작 ~ 현재 끝

```sql
SELECT
  FORMAT_DATE('%Y-%m-%d', date) AS date, new_vs_returning,
  COUNT(DISTINCT IF(is_engaged OR eng_ms > 0, user_pseudo_id, NULL)) AS active_users,
  COUNT(*) AS sessions, COUNTIF(is_engaged) AS engaged_sessions,
  AVG(dur_sec) AS average_session_duration, SUM(conv) AS conversions
FROM sess GROUP BY date, new_vs_returning ORDER BY date;
```

### src / srcP

```sql
SELECT
  session_source_medium, new_vs_returning,
  COUNT(*) AS sessions, COUNTIF(is_engaged) AS engaged_sessions,
  AVG(dur_sec) AS average_session_duration, SUM(conv) AS conversions
FROM sess GROUP BY 1, 2;
```

### dev

```sql
SELECT devicecategory, COUNT(*) AS sessions, SUM(conv) AS conversions
FROM sess GROUP BY 1;
```

### pg — 페이지 제목 기준 (서비스가 있으면 `svc_title` 조건 추가)

```sql
SELECT
  IFNULL(e.page_title, '(not set)') AS pagetitle,
  COUNT(*) AS screen_page_views,
  COUNT(DISTINCT e.user_pseudo_id) AS active_users
FROM ev e
JOIN sess s USING (user_pseudo_id, sid)
WHERE e.event_name = 'page_view'
  -- AND STRPOS(IFNULL(e.page_title, ''), '<TITLE>') > 0   -- 서비스가 있을 때
GROUP BY 1
HAVING screen_page_views > 2
ORDER BY screen_page_views DESC;
```

### costG / costN

내보내기에는 광고비가 없으므로 빈 배열(`[]`)로 둔다. 사용자가 광고비 테이블(예: Google Ads 데이터 전송, 직접 올린 비용표)을 알려 주면, 그 테이블을 `date`·캠페인 기준으로 `sess`의 세션·전환과 묶어 `references/data-sources.md`의 costG·costN 열 이름으로 만든다.
