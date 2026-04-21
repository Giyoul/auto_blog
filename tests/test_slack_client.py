import os
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_CHANNEL_ID", "C1234567890")
os.environ.setdefault("NOTION_DATABASE_URL", "https://notion.so/test-db")

from src.slack_client import notify_published, notify_topic_suggestions


@patch("src.slack_client._make_client")
def test_notify_published_sends_message(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client

    notify_published("Python 비동기", "https://notion.so/abc")

    client.chat_postMessage.assert_called_once()
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "Python 비동기" in text
    assert "https://notion.so/abc" in text
    assert "✅" in text


@patch("src.slack_client._make_client")
def test_notify_topic_suggestions_sends_numbered_list(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    topics = ["Docker 최적화", "FastAPI 비교", "타입 힌트", "Git 전략", "Redis 캐싱"]

    notify_topic_suggestions(topics)

    client.chat_postMessage.assert_called_once()
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "1. Docker 최적화" in text
    assert "5. Redis 캐싱" in text
    assert "https://notion.so/test-db" in text


@patch("src.slack_client._make_client")
def test_notify_published_slack_error_does_not_raise(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.chat_postMessage.side_effect = SlackApiError(
        message="error", response={"error": "channel_not_found"}
    )

    # SlackApiError가 발생해도 예외가 외부로 전파되지 않아야 해요
    notify_published("토픽", "https://notion.so/abc")


@patch.dict(os.environ, {"SLACK_CHANNEL_ID": "C1234567890"})
@patch("src.slack_client._make_client")
def test_notify_published_correct_channel(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client

    notify_published("토픽", "https://notion.so/abc")

    call_kwargs = client.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "C1234567890"
