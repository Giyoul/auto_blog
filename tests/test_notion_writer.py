import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("NOTION_API_KEY", "test-key")

from src.notion_writer import _md_to_blocks, _split_text, create_blog_page


@patch("src.notion_writer._make_client")
def test_create_blog_page_returns_url(mock_make_client):
    client = MagicMock()
    mock_make_client.return_value = client
    client.pages.create.return_value = {"id": "abcd-efgh-1234"}

    url = create_blog_page("parent-id", "제목", "# 본문\n내용이에요.")

    assert url == "https://notion.so/abcdefgh1234"
    call_kwargs = client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"page_id": "parent-id"}
    assert call_kwargs["properties"]["title"]["title"][0]["text"]["content"] == "제목"


def test_md_to_blocks_heading1():
    blocks = _md_to_blocks("# 큰 제목")
    assert blocks[0]["type"] == "heading_1"
    assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "큰 제목"


def test_md_to_blocks_heading2():
    assert _md_to_blocks("## 중간 제목")[0]["type"] == "heading_2"


def test_md_to_blocks_heading3():
    assert _md_to_blocks("### 작은 제목")[0]["type"] == "heading_3"


def test_md_to_blocks_paragraph():
    blocks = _md_to_blocks("일반 텍스트예요.")
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "일반 텍스트예요."


def test_md_to_blocks_bullet():
    blocks = _md_to_blocks("- 항목 하나")
    assert blocks[0]["type"] == "bulleted_list_item"
    assert blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "항목 하나"


def test_md_to_blocks_code():
    md = "```python\nprint('hello')\n```"
    blocks = _md_to_blocks(md)
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
    assert "print('hello')" in blocks[0]["code"]["rich_text"][0]["text"]["content"]


def test_md_to_blocks_empty_lines_skipped():
    blocks = _md_to_blocks("줄 하나\n\n또 다른 줄")
    assert [b["type"] for b in blocks] == ["paragraph", "paragraph"]


def test_md_to_blocks_mixed():
    md = "# 제목\n\n내용이에요.\n\n- 리스트\n\n```py\ncode\n```"
    types = [b["type"] for b in _md_to_blocks(md)]
    assert "heading_1" in types
    assert "paragraph" in types
    assert "bulleted_list_item" in types
    assert "code" in types


def test_md_to_blocks_unclosed_fence_does_not_raise():
    md = "```python\nprint('hello')"
    blocks = _md_to_blocks(md)
    assert any(b["type"] == "code" for b in blocks)


def test_split_text_short_text_returns_single_chunk():
    assert _split_text("짧은 텍스트") == ["짧은 텍스트"]


def test_split_text_long_text_splits_into_chunks():
    long = "a" * 4500
    chunks = _split_text(long)
    assert len(chunks) == 3
    assert all(len(c) <= 2000 for c in chunks)


def test_md_to_blocks_long_paragraph_creates_multiple_blocks():
    long_line = "x" * 4500
    blocks = _md_to_blocks(long_line)
    assert len(blocks) >= 2
    assert all(b["type"] == "paragraph" for b in blocks)
