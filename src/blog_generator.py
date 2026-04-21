import os
import re
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_MODEL = "gemini-2.5-flash"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_NO_THINKING = types.GenerateContentConfig(
    max_output_tokens=8192,
    thinking_config=types.ThinkingConfig(thinking_budget=0),
)

_TITLE_RE = re.compile(r"===TITLE===\s*(.*?)\s*===CONTENT===", re.DOTALL)
_CONTENT_RE = re.compile(r"===CONTENT===\s*(.*?)\s*===TAGS===", re.DOTALL)
_TAGS_RE = re.compile(r"===TAGS===\s*(.*?)$", re.DOTALL)


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _make_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _parse_blog_post(raw: str) -> dict:
    title_match = _TITLE_RE.search(raw)
    content_match = _CONTENT_RE.search(raw)
    if not title_match or not content_match:
        raise ValueError(f"응답 형식이 올바르지 않아요 (구분자 없음): {raw[:300]}")
    title = title_match.group(1).strip()
    content_md = content_match.group(1).strip()
    tags_match = _TAGS_RE.search(raw)
    tags = (
        [t.strip() for t in tags_match.group(1).strip().split(",") if t.strip()]
        if tags_match
        else []
    )
    return {"title": title, "content_md": content_md, "tags": tags}


def _parse_topics(raw: str, expected_count: int) -> list[str]:
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"토픽 제안 응답이 비어 있어요: {raw[:200]}")
    return lines[:expected_count]


def generate_post(
    topic: str,
    category: Optional[str] = None,
    memo: Optional[str] = None,
) -> dict:
    """블로그 글을 생성해요. {"title": str, "content_md": str, "tags": list} 반환."""
    template = _load_prompt("blog_post.txt")
    prompt = template.format(
        topic=topic,
        category=category or "일반",
        memo=memo or "없음",
    )
    client = _make_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_NO_THINKING,
    )
    return _parse_blog_post(response.text)


def suggest_topics(recent_topics: list[str]) -> list[str]:
    """최근 토픽을 참고해 중복 없는 토픽 목록을 제안해요."""
    count = int(os.environ.get("TOPIC_SUGGEST_COUNT", "5"))
    template = _load_prompt("topic_suggest.txt")
    recent_str = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "없음"
    prompt = template.format(recent_topics=recent_str, count=count)
    client = _make_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_NO_THINKING,
    )
    return _parse_topics(response.text, count)
