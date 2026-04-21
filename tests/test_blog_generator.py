import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("TOPIC_SUGGEST_COUNT", "5")

from src.blog_generator import generate_post, suggest_topics, _parse_blog_post, _parse_topics


def _make_response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


def _blog_response(title: str, content_md: str, tags: list[str]) -> str:
    tags_str = ",".join(tags)
    return f"===TITLE===\n{title}\n===CONTENT===\n{content_md}\n===TAGS===\n{tags_str}"


@patch("src.blog_generator._make_client")
def test_generate_post_success(mock_make_client):
    title = "Python 비동기 프로그래밍 완벽 가이드"
    content = ("## 시작하며\n비동기는 어렵지 않아요.\n" * 20).strip()
    tags = ["Python", "asyncio", "비동기"]
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response(
        _blog_response(title, content, tags)
    )

    result = generate_post("Python 비동기", category="Backend", memo="짧게")

    assert result["title"] == title
    assert result["content_md"] == content
    assert result["tags"] == tags


@patch("src.blog_generator._make_client")
def test_generate_post_no_category_memo(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response(
        _blog_response("제목", "본문", [])
    )

    generate_post("Python 비동기")

    call_kwargs = client.models.generate_content.call_args.kwargs
    assert "일반" in call_kwargs["contents"]
    assert "없음" in call_kwargs["contents"]


@patch("src.blog_generator._make_client")
def test_generate_post_missing_delimiter_raises(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response("올바르지 않은 응답")

    with pytest.raises(ValueError, match="구분자"):
        generate_post("Python 비동기")


@patch("src.blog_generator._make_client")
def test_generate_post_content_with_code_block(mock_make_client):
    """코드 블록이 포함된 마크다운도 깨지지 않고 파싱돼요."""
    content = "## 예시\n\n```python\nasync def main():\n    await asyncio.sleep(1)\n```\n\n끝이에요."
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response(
        _blog_response("코드 블록 테스트", content, ["Python"])
    )

    result = generate_post("Python 비동기")

    assert "```python" in result["content_md"]
    assert "await" in result["content_md"]


def test_parse_blog_post_tags_optional():
    raw = "===TITLE===\n제목\n===CONTENT===\n본문\n===TAGS===\n"
    result = _parse_blog_post(raw)
    assert result["tags"] == []


def test_parse_blog_post_multiline_content():
    content = "줄1\n줄2\n줄3"
    raw = f"===TITLE===\n제목\n===CONTENT===\n{content}\n===TAGS===\n태그1,태그2"
    result = _parse_blog_post(raw)
    assert result["content_md"] == content


@patch("src.blog_generator._make_client")
def test_suggest_topics_returns_list(mock_make_client):
    topics = ["Docker 최적화", "FastAPI 비교", "타입 힌트", "Git 전략", "Redis 캐싱"]
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response("\n".join(topics))

    result = suggest_topics(["Python 비동기"])

    assert result == topics


@patch("src.blog_generator._make_client")
def test_suggest_topics_empty_recent(mock_make_client):
    topics = ["토픽1", "토픽2", "토픽3", "토픽4", "토픽5"]
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response("\n".join(topics))

    result = suggest_topics([])

    assert len(result) == 5
    call_kwargs = client.models.generate_content.call_args.kwargs
    assert "없음" in call_kwargs["contents"]


@patch("src.blog_generator._make_client")
def test_suggest_topics_trims_to_count(mock_make_client):
    """모델이 더 많이 반환해도 count만큼만 잘라요."""
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response(
        "토픽1\n토픽2\n토픽3\n토픽4\n토픽5\n토픽6\n토픽7"
    )

    result = suggest_topics([])

    assert len(result) == 5


@patch("src.blog_generator._make_client")
def test_suggest_topics_empty_response_raises(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.models.generate_content.return_value = _make_response("   \n\n  ")

    with pytest.raises(ValueError, match="비어"):
        suggest_topics([])


def test_parse_topics_skips_blank_lines():
    result = _parse_topics("토픽1\n\n토픽2\n  \n토픽3", 5)
    assert result == ["토픽1", "토픽2", "토픽3"]
