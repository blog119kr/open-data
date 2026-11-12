# open-data

[행복나무(blog119.co.kr)](https://blog119.co.kr)가 공개하는 마케팅·데이터 분석용 자료입니다.

## 스킬

| 폴더 | 설명 |
|---|---|
| [`aarrr-report-blog119kr`](./aarrr-report-blog119kr) | GA4 데이터로 AARRR 퍼널 리포트(유입·행동·재방문·CPA·추천유입)를 루커스튜디오 스타일 HTML 한 장으로 만드는 에이전트 스킬 |

## aarrr-report-blog119kr 사용법

[미리보기 (가상 데이터)](./aarrr-report-blog119kr/examples/sample-report.html) — 파일을 내려받아 브라우저로 열면 됩니다.

### 필요한 것
- GA4 데이터를 조회할 수 있는 도구 1개: [Windsor.ai MCP](https://windsor.ai), [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1), Google 공식 GA MCP 서버 등
- Python 3 실행 환경(표준 라이브러리만 사용)

### LLM별 설치

| 도구 | 방법 |
|---|---|
| Claude (claude.ai / Claude Code) | `aarrr-report-blog119kr` 폴더를 zip으로 묶어 스킬로 업로드하거나, `~/.claude/skills/`에 복사 |
| 그 밖의 에이전트(Agent Skills 지원) | 폴더를 각 도구의 스킬 폴더에 복사 |
| ChatGPT / Gemini 등 | `SKILL.md` 내용을 시스템 프롬프트(맞춤 지침)에 붙여 넣고, `assets/template.html`과 `scripts/build_report.py`를 파일로 첨부 |

### 실행 예

```
aarrr-report 지난7일
aarrr-report 지난달 123456789
```

속성 이름·ID, 서비스별 필터, 비교 불가 기준일은 스킬에 저장하지 않고 실행할 때 입력합니다. 빠뜨리면 에이전트가 먼저 물어봅니다(`SKILL.md` 1장 참고).

### 직접 실행

```bash
cd aarrr-report-blog119kr
python3 scripts/build_report.py examples/config.sample.json examples/results.sample.json out.html
```

## 라이선스

MIT
