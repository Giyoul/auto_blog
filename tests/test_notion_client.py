import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("NOTION_API_KEY", "test-key")
os.environ.setdefault("NOTION_DATABASE_ID", "test-db-id")

from src.notion_client import (
    create_topic,
    get_recent_topics,
    get_today_topic,
    get_tomorrow_topic,
    update_published_info,
    update_status,
)

_TODAY = "2026-04-21"


def _make_page(page_id="page-1", topic="Python 비동기", category="Backend", memo="짧게"):
    return {
        "id": page_id,
        "properties": {
            "제목": {"title": [{"type": "text", "text": {"content": topic}}]},
            "status": {"select": {"name": "대기"}},
            "카테고리": {"select": {"name": category}},
            "memo": {"rich_text": [{"type": "text", "text": {"content": memo}}]},
            "날짜": {"date": {"start": _TODAY}},
        },
    }


@patch("src.notion_client._make_client")
@patch("src.notion_client.date")
def test_get_today_topic_found(mock_date, mock_make_client):
    mock_date.today.return_value.isoformat.return_value = _TODAY
    client = MagicMock()
    mock_make_client.return_value = client
    client.databases.query.return_value = {"results": [_make_page()]}

    result = get_today_topic()

    assert result is not None
    assert result["topic"] == "Python 비동기"
    assert result["category"] == "Backend"
    assert result["memo"] == "짧게"


@patch("src.notion_client._make_client")
@patch("src.notion_client.date")
def test_get_today_topic_not_found(mock_date, mock_make_client):
    mock_date.today.return_value.isoformat.return_value = _TODAY
    client = MagicMock()
    mock_make_client.return_value = client
    client.databases.query.return_value = {"results": []}

    assert get_today_topic() is None


@patch("src.notion_client._make_client")
@patch("src.notion_client.date")
def test_get_today_topic_empty_title_returns_none(mock_date, mock_make_client):
    mock_date.today.return_value.isoformat.return_value = _TODAY
    client = MagicMock()
    mock_make_client.return_value = client
    page = _make_page()
    page["properties"]["제목"]["title"] = []
    client.databases.query.return_value = {"results": [page]}

    assert get_today_topic() is None


@patch("src.notion_client._make_client")
@patch("src.notion_client.date")
def test_get_tomorrow_topic_exists(mock_date, mock_make_client):
    from datetime import date as real_date
    mock_date.today.return_value = real_date(2026, 4, 21)
    client = MagicMock()
    mock_make_client.return_value = client
    client.databases.query.return_value = {"results": [_make_page()]}

    assert get_tomorrow_topic() is True


@patch("src.notion_client._make_client")
@patch("src.notion_client.date")
def test_get_tomorrow_topic_not_exists(mock_date, mock_make_client):
    from datetime import date as real_date
    mock_date.today.return_value = real_date(2026, 4, 21)
    client = MagicMock()
    mock_make_client.return_value = client
    client.databases.query.return_value = {"results": []}

    assert get_tomorrow_topic() is False


@patch("src.notion_client._make_client")
def test_update_status(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client

    update_status("page-1", "발행완료")

    client.pages.update.assert_called_once_with(
        page_id="page-1",
        properties={"status": {"select": {"name": "발행완료"}}},
    )


@patch("src.notion_client._make_client")
def test_update_published_info_sets_status_url_and_date(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    now = datetime(2026, 4, 21, 0, 0, 0, tzinfo=timezone.utc)

    update_published_info("page-1", "https://notion.so/abc", now)

    call_kwargs = client.pages.update.call_args.kwargs
    assert call_kwargs["page_id"] == "page-1"
    props = call_kwargs["properties"]
    assert props["링크"] == {"url": "https://notion.so/abc"}
    assert props["status"] == {"select": {"name": "발행완료"}}
    assert "published_at" in props


@patch("src.notion_client._make_client")
def test_create_topic(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.pages.create.return_value = {"id": "new-page-id"}

    result = create_topic("Docker 최적화", "2026-04-22")

    assert result == "new-page-id"


@patch("src.notion_client._make_client")
def test_get_recent_topics_returns_list(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.databases.query.return_value = {
        "results": [_make_page(topic="토픽A"), _make_page(topic="토픽B")]
    }

    result = get_recent_topics()

    assert result == ["토픽A", "토픽B"]


@patch("src.notion_client._make_client")
def test_get_recent_topics_skips_empty_title(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    page_empty = _make_page(topic="")
    page_empty["properties"]["제목"]["title"] = []
    client.databases.query.return_value = {
        "results": [_make_page(topic="정상"), page_empty]
    }

    result = get_recent_topics()

    assert result == ["정상"]


def test_get_rich_text_ignores_non_text_types():
    from src.notion_client import _get_rich_text
    page = {
        "properties": {
            "memo": {
                "rich_text": [
                    {"type": "text", "text": {"content": "안녕"}},
                    {"type": "mention", "mention": {}},
                    {"type": "text", "text": {"content": "세요"}},
                ]
            }
        }
    }
    assert _get_rich_text(page, "memo") == "안녕세요"


def test_column_names_match_notion_db():
    from src.notion_client import _COL_TITLE, _COL_DATE, _COL_URL, _COL_CATEGORY
    assert _COL_TITLE == "제목"
    assert _COL_DATE == "날짜"
    assert _COL_URL == "링크"
    assert _COL_CATEGORY == "카테고리"
