import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TOPIC_SUGGEST_COUNT", "5")

from src.blog_generator import generate_post, suggest_topics


def _make_message(text: str) -> MagicMock:
    content = MagicMock()
    content.text = text
    message = MagicMock()
    message.content = [content]
    return message


@patch("src.blog_generator._make_client")
def test_generate_post_success(mock_make_client):
    payload = {
        "title": "Python 비동기 프로그래밍 완벽 가이드",
        "content_md": "## 시작하며\n비동기는 어렵지 않아요.\n" * 20,
        "tags": ["Python", "asyncio", "비동기"],
    }
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message(json.dumps(payload))

    result = generate_post("Python 비동기", category="Backend", memo="짧게")

    assert result["title"] == payload["title"]
    assert result["content_md"] == payload["content_md"]
    assert result["tags"] == payload["tags"]


@patch("src.blog_generator._make_client")
def test_generate_post_strips_markdown_fence(mock_make_client):
    payload = {"title": "제목", "content_md": "본문", "tags": []}
    client = MagicMock()
    mock_make_client.return_value = client
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    client.messages.create.return_value = _make_message(wrapped)

    result = generate_post("Python 비동기")

    assert result["title"] == "제목"


@patch("src.blog_generator._make_client")
def test_generate_post_no_category_memo(mock_make_client):
    payload = {"title": "제목", "content_md": "본문", "tags": []}
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message(json.dumps(payload))

    generate_post("Python 비동기")

    _, kwargs = client.messages.create.call_args
    prompt = kwargs["messages"][0]["content"]
    assert "일반" in prompt
    assert "없음" in prompt


@patch("src.blog_generator._make_client")
def test_generate_post_invalid_json_raises(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message("올바르지 않은 JSON")

    with pytest.raises(json.JSONDecodeError):
        generate_post("Python 비동기")


@patch("src.blog_generator._make_client")
def test_suggest_topics_returns_list(mock_make_client):
    topics = ["Docker 최적화", "FastAPI 비교", "타입 힌트", "Git 전략", "Redis 캐싱"]
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message(json.dumps(topics))

    result = suggest_topics(["Python 비동기"])

    assert result == topics


@patch("src.blog_generator._make_client")
def test_suggest_topics_empty_recent(mock_make_client):
    topics = ["토픽1", "토픽2", "토픽3", "토픽4", "토픽5"]
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message(json.dumps(topics))

    result = suggest_topics([])

    assert len(result) == 5
    _, kwargs = client.messages.create.call_args
    assert "없음" in kwargs["messages"][0]["content"]


@patch("src.blog_generator._make_client")
def test_suggest_topics_non_list_response_raises(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.messages.create.return_value = _make_message('{"error": "unexpected"}')

    with pytest.raises(ValueError, match="리스트"):
        suggest_topics([])
