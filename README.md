# open-data

풀스택마케터(blog119.co.kr)가 공개하는 마케팅·데이터 분석용 자료입니다.

## 스킬

| 폴더 | 설명 |
|---|---|
| [`aarrr-report-blog119kr`](./aarrr-report-blog119kr) | GA4 데이터로 AARRR 퍼널 리포트(유입·행동·재방문·CPA·추천유입)를 루커스튜디오 스타일 HTML 한 장으로 만드는 에이전트 스킬 |

## aarrr-report-blog119kr 사용법

[미리보기 (가상 데이터)](./aarrr-report-blog119kr/examples/sample-report.html) — 파일을 내려받아 브라우저로 열면 됩니다.

### 필요한 것
- GA4 데이터 연결: MCP나 빅쿼리(GA4 내보내기)
- Python 3 실행 환경(표준 라이브러리만 사용)

### LLM별 설치

| 도구 | 방법 |
|---|---|
| Claude (claude.ai / Claude Code) | `aarrr-report-blog119kr` 폴더를 zip으로 묶어 스킬로 업로드하거나, `~/.claude/skills/`에 복사 |
| 그 밖의 에이전트(Agent Skills 지원) | 폴더를 각 도구의 스킬 폴더에 복사 |
| ChatGPT / Gemini 등 | `SKILL.md` 내용을 시스템 프롬프트(맞춤 지침)에 붙여 넣고, `assets/template.html`, `scripts/build_report.py`, `references/` 파일을 첨부 |

### 실행

```
aarrr-report 지난7일
```

처음 실행하면 에이전트가 먼저 데이터를 어디서 가져올지(커넥터) 묻고, 고른 방식에 필요한 값(속성 ID, 빅쿼리 프로젝트·데이터셋 등)만 이어서 묻습니다. 속성 정보는 스킬에 저장하지 않습니다.

### 직접 실행

```bash
cd aarrr-report-blog119kr
python3 scripts/build_report.py examples/config.sample.json examples/results.sample.json out.html
```

## 라이선스

MIT
