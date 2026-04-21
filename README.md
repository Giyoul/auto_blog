# auto_blog

Notion에 등록된 주제를 읽어 AI가 블로그 글을 자동으로 작성하고, Notion 페이지로 저장한 뒤 Slack으로 알림을 보내는 파이프라인이에요. GitHub Actions로 매일 09:00 KST에 자동 실행돼요.

---

## 실행 흐름

파이프라인은 두 가지 경로 중 하나로 동작해요.

### 경로 A — 오늘 발행할 토픽이 있을 때

```
Notion DB 조회
  └─ 오늘 날짜 + status=대기 인 토픽 발견
       │
       ├─ Notion status → "생성중"
       │
       ├─ Gemini 2.5 Flash로 블로그 글 생성
       │    (제목 / 마크다운 본문 / 태그)
       │
       ├─ Notion 하위 페이지로 저장
       │    (마크다운 → Notion 블록 변환)
       │
       ├─ Notion status → "발행완료" + 링크 + 발행일 기록
       │
       └─ Slack 알림: "✅ 블로그 글 생성 완료!"
```

### 경로 B — 오늘 토픽이 없고, 내일 토픽도 없을 때

```
Notion DB 조회
  └─ 오늘 토픽 없음
       │
       └─ 내일 날짜 토픽도 없음
            │
            ├─ 최근 작성된 토픽 목록 조회 (중복 방지용)
            │
            ├─ Gemini 2.5 Flash로 토픽 5개 제안
            │
            └─ Slack 알림: 번호 매긴 토픽 목록 전송
                 (선택 후 Notion DB에 직접 등록 필요)
```

내일 토픽이 이미 있으면 아무 작업 없이 종료해요.

---

## 모듈 구성

```
pipeline.py          두 경로를 오케스트레이션
├── notion_client.py  Notion DB 읽기/쓰기 (토픽 조회, 상태 업데이트)
├── blog_generator.py Gemini API 호출, 응답 파싱
├── notion_writer.py  마크다운 → Notion 블록 변환 후 페이지 생성
└── slack_client.py   발행 완료 알림 / 토픽 제안 전송
```

---

## Notion DB 필수 컬럼

| 컬럼 | 타입 | 용도 |
|------|------|------|
| 제목 | Title | 블로그 주제 |
| 날짜 | Date | 발행 예정일 |
| status | Select | 대기 / 생성중 / 발행완료 / 실패 |
| 카테고리 | Select | 글 분류 (선택) |
| memo | Text | AI에 전달할 추가 지시사항 (선택) |
| 링크 | URL | 생성된 Notion 페이지 URL (파이프라인이 기록) |
| published_at | Date | 발행 시각 (파이프라인이 기록) |

---

## 환경 변수

`.env` 파일 또는 GitHub Secrets에 설정해요.

```
NOTION_API_KEY        # secret_xxxx
NOTION_DATABASE_ID    # DB URL의 32자리 hex
GOOGLE_API_KEY        # Gemini API 키
SLACK_BOT_TOKEN       # xoxb-xxxx
SLACK_CHANNEL_ID      # Cxxxx
NOTION_DATABASE_URL   # Slack 메시지에 링크로 표시할 DB URL
MAX_POSTS_PER_DAY     # 기본값 1
TOPIC_SUGGEST_COUNT   # 기본값 5
```

---

## 로컬 실행

```bash
pip install -r requirements.txt

# 파이프라인 전체 실행
python -m src.pipeline

# 테스트
pytest

# 커버리지 포함
pytest --cov=src --cov-report=term-missing
```

---

## 자동 실행 (GitHub Actions)

`.github/workflows/daily.yml`이 매일 00:00 UTC (09:00 KST)에 실행돼요. 위 환경 변수를 GitHub 저장소 Secrets에 등록하면 돼요.
