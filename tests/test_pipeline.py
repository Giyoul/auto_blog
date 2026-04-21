import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("NOTION_API_KEY", "test-key")
os.environ.setdefault("NOTION_DATABASE_ID", "test-db-id")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_CHANNEL_ID", "C1234")

_TODAY_TOPIC = {
    "id": "page-1",
    "topic": "Python 비동기",
    "category": "Backend",
    "memo": "짧게",
}
_GENERATED_POST = {
    "title": "Python 비동기 완벽 가이드",
    "content_md": "## 시작\n내용이에요.",
    "tags": ["Python"],
}


@patch("src.pipeline.slack_client")
@patch("src.pipeline.notion_writer")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_with_today_topic(mock_nc, mock_bg, mock_nw, mock_sc):
    mock_nc.get_today_topic.return_value = _TODAY_TOPIC
    mock_bg.generate_post.return_value = _GENERATED_POST
    mock_nw.create_blog_page.return_value = "https://notion.so/abc"

    from src.pipeline import run
    run()

    mock_nc.update_status.assert_called_once_with("page-1", "생성중")
    mock_bg.generate_post.assert_called_once_with(
        topic="Python 비동기", category="Backend", memo="짧게"
    )
    mock_nw.create_blog_page.assert_called_once_with(
        topic_page_id="page-1",
        title=_GENERATED_POST["title"],
        content_md=_GENERATED_POST["content_md"],
    )
    mock_nc.update_published_info.assert_called_once()
    mock_sc.notify_published.assert_called_once_with(
        topic="Python 비동기", url="https://notion.so/abc"
    )


@patch("src.pipeline.slack_client")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_no_today_topic_no_tomorrow_topic(mock_nc, mock_bg, mock_sc):
    mock_nc.get_today_topic.return_value = None
    mock_nc.get_tomorrow_topic.return_value = False
    mock_nc.get_recent_topics.return_value = ["이전 토픽"]
    mock_bg.suggest_topics.return_value = ["토픽1", "토픽2", "토픽3", "토픽4", "토픽5"]

    from src.pipeline import run
    run()

    mock_nc.get_recent_topics.assert_called_once()
    mock_bg.suggest_topics.assert_called_once_with(recent_topics=["이전 토픽"])
    mock_sc.notify_topic_suggestions.assert_called_once_with(
        ["토픽1", "토픽2", "토픽3", "토픽4", "토픽5"]
    )


@patch("src.pipeline.slack_client")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_no_today_topic_has_tomorrow_topic(mock_nc, mock_bg, mock_sc):
    mock_nc.get_today_topic.return_value = None
    mock_nc.get_tomorrow_topic.return_value = True

    from src.pipeline import run
    run()

    mock_bg.suggest_topics.assert_not_called()
    mock_sc.notify_topic_suggestions.assert_not_called()


@patch("src.pipeline.slack_client")
@patch("src.pipeline.notion_writer")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_generate_post_failure_sets_status_failed(mock_nc, mock_bg, mock_nw, mock_sc):
    mock_nc.get_today_topic.return_value = _TODAY_TOPIC
    mock_bg.generate_post.side_effect = Exception("API 오류")

    from src.pipeline import run
    with pytest.raises(SystemExit):
        run()

    mock_nc.update_status.assert_any_call("page-1", "실패")
    mock_nw.create_blog_page.assert_not_called()


@patch("src.pipeline.slack_client")
@patch("src.pipeline.notion_writer")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_slack_failure_does_not_stop_pipeline(mock_nc, mock_bg, mock_nw, mock_sc):
    mock_nc.get_today_topic.return_value = _TODAY_TOPIC
    mock_bg.generate_post.return_value = _GENERATED_POST
    mock_nw.create_blog_page.return_value = "https://notion.so/abc"
    mock_sc.notify_published.side_effect = Exception("Slack 오류")

    from src.pipeline import run
    run()

    mock_nc.update_published_info.assert_called_once()


@patch("src.pipeline.slack_client")
@patch("src.pipeline.notion_writer")
@patch("src.pipeline.blog_generator")
@patch("src.pipeline.notion_client")
def test_pipeline_status_not_set_to_published_before_page_saved(mock_nc, mock_bg, mock_nw, mock_sc):
    """update_published_info가 페이지 저장 후에 호출돼야 해요 (상태 불일치 방지)."""
    call_order = []
    mock_nw.create_blog_page.side_effect = lambda **kw: call_order.append("page_saved") or "https://notion.so/abc"
    mock_nc.update_published_info.side_effect = lambda **kw: call_order.append("info_updated")
    mock_nc.get_today_topic.return_value = _TODAY_TOPIC
    mock_bg.generate_post.return_value = _GENERATED_POST

    from src.pipeline import run
    run()

    assert call_order.index("page_saved") < call_order.index("info_updated")
