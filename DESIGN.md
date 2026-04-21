# Auto Blog System — 설계 문서 v2

## 전체 플로우

```
[매일 09:00 KST]
       │
       ▼
[Notion: 오늘 토픽 있음?]
       │
   Yes │                    No │
       ▼                       ▼
[Claude: 블로그 글 생성]   [Claude: 토픽 5개 제안]
       │                       │
       ▼                       ▼
[Notion: 글 페이지 생성]  [Slack: 토픽 선택지 전송]
(Markdown 형식 저장)            │
       │                       ▼
       ▼               [사용자가 Notion에서 선택]
[Slack: 완료 알림]
(Notion 페이지 링크 포함)
```

> Tistory API 서비스 종료로 인해 **Notion에 Markdown 형식으로 저장**하는 방식으로 변경.

---

## Notion DB 스키마

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `topic` | Title | 블로그 글 주제 |
| `status` | Select | `대기` / `생성중` / `발행완료` / `실패` |
| `scheduled_date` | Date | 발행 예정일 |
| `category` | Select | 블로그 카테고리 (선택) |
| `memo` | Text | 추가 지시사항 (선택) |
| `notion_page_url` | URL | 생성된 글 Notion 페이지 URL (자동 기입) |
| `published_at` | Date | 글 생성 일시 (자동 기입) |

---

## 디렉토리 구조

```
auto_blog/
├── src/
│   ├── notion_client.py      # Notion API: 토픽 조회, 상태/링크 업데이트
│   ├── blog_generator.py     # Claude API: 블로그 글 + 토픽 제안 생성
│   ├── notion_writer.py      # Notion API: 블로그 글 페이지 생성 (MD 형식)
│   ├── slack_client.py       # Slack: 알림 전송, 토픽 선택지 전송
│   └── pipeline.py           # 전체 오케스트레이션
├── prompts/
│   ├── blog_post.txt         # 블로그 글 생성 프롬프트 템플릿
│   └── topic_suggest.txt     # 토픽 제안 프롬프트 템플릿
├── datas/
│   └── auto-blog/            # 생성된 글 로컬 백업
├── tests/
│   ├── test_notion_client.py
│   ├── test_blog_generator.py
│   ├── test_tistory_client.py
│   └── test_slack_client.py
├── .github/
│   └── workflows/
│       └── daily.yml
├── .env.example
├── requirements.txt
├── DESIGN.md
└── CLAUDE.md
```

---

## 기술 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| 언어 | Python 3.11+ | 생태계, 스크립트 친화적 |
| Notion | `notion-client` | 공식 SDK |
| AI | `anthropic` SDK + `claude-haiku-4-5` | 비용 효율 |
| Notion Writer | `notion-client` | 블로그 글을 Notion 페이지로 저장 (Tistory API 종료) |
| Slack | `slack-sdk` | 메시지 전송, Block Kit |
| 스케줄 | GitHub Actions cron | 별도 서버 불필요 |

---

## Slack 토픽 선택 방식 (중요)

### 방식 A — 단순 방식 (권장, 서버 불필요)
- Slack에 토픽 목록 전송 (번호 목록)
- 사용자가 **Notion에서 직접 원하는 토픽의 `scheduled_date`를 내일 날짜로 설정**
- 다음날 cron이 해당 토픽 발견 → 발행

### 방식 B — Slack Interactive (완전 자동화, 서버 필요)
- Slack Block Kit 버튼으로 선택지 제공
- 사용자가 버튼 클릭 → Webhook 서버가 수신 → Notion 자동 업데이트
- **별도 서버(FastAPI 등) 필요** — 복잡도 증가

> **현재 설계는 방식 A로 진행. 방식 B는 Phase 2로 고려.**

---

## 모듈별 책임

### `notion_client.py`
- `get_today_topic()` → 오늘 날짜의 `대기` 상태 토픽 반환
- `get_tomorrow_topic()` → 내일 날짜 토픽 존재 여부 확인
- `update_status(page_id, status)`
- `update_published_info(page_id, url, published_at)`
- `create_topic(topic_name, scheduled_date)` → 토픽 추가

### `blog_generator.py`
- `generate_post(topic, category, memo)` → `{ title, content_html, tags }` 반환
- `suggest_topics(recent_topics)` → 토픽 5개 리스트 반환

### `notion_writer.py`
- `create_blog_page(topic_page_id, title, content_md)` → 생성된 Notion 페이지 URL 반환

### `slack_client.py`
- `notify_published(topic, url)` → 발행 완료 알림
- `notify_topic_suggestions(topics)` → 토픽 선택지 전송 (Notion 링크 포함)

### `pipeline.py`
```
1. get_today_topic()
   - 있으면: 글 생성 → 발행 → Notion 업데이트 → Slack 알림
   - 없으면: 로그 출력 후 종료

2. get_tomorrow_topic()
   - 없으면: 토픽 5개 제안 → Slack 전송
```

---

## Slack 메시지 예시

### 발행 완료 알림
```
✅ 블로그 글 생성 완료!
📝 주제: Python 비동기 프로그래밍 완벽 가이드
🔗 Notion: https://notion.so/xxxx
📅 작성일: 2026-04-21
```

### 토픽 제안 (내일 토픽 없을 때)
```
📋 내일 블로그 토픽을 선택해주세요!

1. Docker 컨테이너 최적화 방법
2. FastAPI vs Django REST Framework 비교
3. Python 타입 힌트 실전 활용법
4. Git 브랜치 전략 완벽 정리
5. Redis 캐싱 패턴 가이드

👉 원하는 토픽을 Notion에서 내일 날짜로 설정해주세요:
https://notion.so/your-database
```

---

## 환경변수 (.env)

```
# Notion
NOTION_API_KEY=secret_xxxx
NOTION_DATABASE_ID=xxxx

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxx

# Slack
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=Cxxxx

# 설정
MAX_POSTS_PER_DAY=1
TOPIC_SUGGEST_COUNT=5
```

---

## 구현 순서 (Phase)

- [ ] Phase 1: 환경설정 + Notion 연동 확인
- [ ] Phase 2: Claude API 블로그 글 생성
- [ ] Phase 3: Notion 글 페이지 생성 (MD 저장)
- [ ] Phase 4: Slack 알림 + 토픽 제안
- [ ] Phase 5: GitHub Actions 자동화
- [ ] Phase 6: 테스트 작성 (80% 커버리지)
- [ ] Phase 7 (선택): Slack Interactive 버튼 방식

---

## 필요한 외부 설정

| 항목 | 발급처 | 비고 |
|------|--------|------|
| Notion API Key | notion.so/my-integrations | DB에 Integration 연결 필요 |
| Notion DB ID | DB URL에서 추출 | |
| Anthropic API Key | console.anthropic.com | |
| Slack Bot Token | api.slack.com/apps | Bot 생성 + 채널 초대 필요 |
| Slack Channel ID | Slack 채널 설정에서 확인 | |
