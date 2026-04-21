# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated blog pipeline: reads topics from a Notion database → generates posts with Claude API → saves as Markdown pages in Notion → sends Slack notifications. Runs daily via GitHub Actions.

Full design spec: `DESIGN.md`

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
python src/pipeline.py

# Run a single module (for testing/debugging)
python src/notion_client.py
python src/blog_generator.py

# Run tests
pytest

# Run a single test file
pytest tests/test_notion_client.py

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

## Architecture

The pipeline is a linear sequence of four modules orchestrated by `pipeline.py`:

```
pipeline.py
  ├── notion_client.py    → get_today_topic(), get_tomorrow_topic(),
  │                         update_status(), update_published_info()
  ├── blog_generator.py   → generate_post(topic, category, memo),
  │                         suggest_topics(recent_topics)
  ├── notion_writer.py    → create_blog_page(topic_page_id, title, content_md)
  └── slack_client.py     → notify_published(topic, url),
                            notify_topic_suggestions(topics)
```

**Two execution paths in `pipeline.py`:**
1. Today's topic exists (`status=대기`, `scheduled_date=today`) → generate post → save to Notion → Slack completion alert
2. Tomorrow has no topic → suggest 5 topics via Claude → send to Slack for user to pick

## Notion DB Schema

Columns the code reads/writes (must exist in the DB):

| Column | Type | Notes |
|--------|------|-------|
| `topic` | Title | Blog subject |
| `status` | Select | `대기` / `생성중` / `발행완료` / `실패` |
| `scheduled_date` | Date | Target publish date |
| `category` | Select | Optional |
| `memo` | Text | Extra instructions passed to Claude |
| `notion_page_url` | URL | Written by pipeline after generation |
| `published_at` | Date | Written by pipeline after generation |

## Environment Variables

All secrets are in `.env` (gitignored). Required keys:

```
NOTION_API_KEY        # secret_xxxx — from notion.so/my-integrations
NOTION_DATABASE_ID    # 32-char hex from DB URL
ANTHROPIC_API_KEY     # claude-haiku-4-5 used for cost efficiency
SLACK_BOT_TOKEN       # xoxb-xxxx
SLACK_CHANNEL_ID      # Cxxxx
MAX_POSTS_PER_DAY     # default 1
TOPIC_SUGGEST_COUNT   # default 5
```

## Prompts

`prompts/blog_post.txt` and `prompts/topic_suggest.txt` are template files read at runtime by `blog_generator.py`. Edit these to tune tone, length, and format of generated content without touching Python code.

## GitHub Actions

`.github/workflows/daily.yml` runs on `cron: '0 0 * * *'` (09:00 KST). All `.env` keys must be added as GitHub repository secrets for CI to work.

## Commit Scope Convention

Use these scopes in commit messages:
- `notion` — Notion client or writer changes
- `generator` — Claude API / prompt changes
- `slack` — Slack client changes
- `pipeline` — orchestration logic
- `ci` — GitHub Actions workflow
