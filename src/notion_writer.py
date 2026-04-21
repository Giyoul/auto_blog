import os

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

_NOTION_MAX_TEXT_LEN = 2000


def _make_client() -> Client:
    return Client(auth=os.environ["NOTION_API_KEY"])


def create_blog_page(topic_page_id: str, title: str, content_md: str) -> str:
    """블로그 글을 Notion 페이지로 저장하고 URL을 반환해요."""
    client = _make_client()
    blocks = _md_to_blocks(content_md)
    response = client.pages.create(
        parent={"page_id": topic_page_id},
        properties={
            "title": {"title": [{"text": {"content": title}}]},
        },
        children=blocks,
    )
    page_id = response["id"].replace("-", "")
    return f"https://notion.so/{page_id}"


def _md_to_blocks(md: str) -> list[dict]:
    """마크다운 텍스트를 Notion API 블록 리스트로 변환해요."""
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            code_lines = []
            lang = line[3:].strip() or "plain text"
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_content = "\n".join(code_lines)
            for chunk in _split_text(code_content):
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            "language": lang,
                        },
                    }
                )
        elif line.startswith("### "):
            blocks.append(_heading_block(3, line[4:]))
        elif line.startswith("## "):
            blocks.append(_heading_block(2, line[3:]))
        elif line.startswith("# "):
            blocks.append(_heading_block(1, line[2:]))
        elif line.startswith("- ") or line.startswith("* "):
            for chunk in _split_text(line[2:]):
                blocks.append(_bullet_block(chunk))
        elif line.strip():
            for chunk in _split_text(line):
                blocks.append(_paragraph_block(chunk))

        i += 1

    return blocks


def _split_text(text: str) -> list[str]:
    """2000자 제한을 넘는 텍스트를 청크로 분할해요."""
    if len(text) <= _NOTION_MAX_TEXT_LEN:
        return [text]
    return [text[i: i + _NOTION_MAX_TEXT_LEN] for i in range(0, len(text), _NOTION_MAX_TEXT_LEN)]


def _heading_block(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text.strip()[:_NOTION_MAX_TEXT_LEN]}}]},
    }


def _paragraph_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text.strip()}}]},
    }


def _bullet_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text.strip()}}]},
    }
