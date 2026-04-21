import json
import os
import re
from pathlib import Path
from typing import Optional

from google import genai
from dotenv import load_dotenv

load_dotenv()

_MODEL = "gemini-2.0-flash"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_MD_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _make_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _extract_json(raw: str) -> str:
    """마크다운 코드 펜스로 감싸진 경우 JSON 내용만 추출해요."""
    match = _MD_JSON_FENCE.search(raw)
    return match.group(1).strip() if match else raw.strip()


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
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    raw = _extract_json(response.text)
    result = json.loads(raw)
    return {
        "title": result["title"],
        "content_md": result["content_md"],
        "tags": result.get("tags", []),
    }


def suggest_topics(recent_topics: list[str]) -> list[str]:
    """최근 토픽을 참고해 중복 없는 토픽 목록을 제안해요."""
    count = int(os.environ.get("TOPIC_SUGGEST_COUNT", "5"))
    template = _load_prompt("topic_suggest.txt")
    recent_str = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "없음"
    prompt = template.format(recent_topics=recent_str, count=count)
    client = _make_client()
    response = client.models.generate_content(model=_MODEL, contents=prompt)
    raw = _extract_json(response.text)
    result = json.loads(raw)
    if not isinstance(result, list):
        raise ValueError(f"토픽 제안 응답이 리스트가 아니에요: {type(result)}")
    return result
