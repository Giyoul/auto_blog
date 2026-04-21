import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def _make_client() -> Client:
    return Client(auth=os.environ["NOTION_API_KEY"])


def _db_id() -> str:
    return os.environ["NOTION_DATABASE_ID"]


def get_today_topic() -> Optional[dict]:
    """오늘 날짜의 '대기' 상태 토픽 페이지를 반환해요. 없으면 None."""
    today = date.today().isoformat()
    client = _make_client()
    response = client.databases.query(
        database_id=_db_id(),
        filter={
            "and": [
                {"property": "status", "select": {"equals": "대기"}},
                {"property": "scheduled_date", "date": {"equals": today}},
            ]
        },
    )
    results = response.get("results", [])
    if not results:
        return None
    page = results[0]
    title_list = page["properties"]["topic"]["title"]
    if not title_list:
        return None
    return {
        "id": page["id"],
        "topic": title_list[0]["text"]["content"],
        "category": _get_select(page, "category"),
        "memo": _get_rich_text(page, "memo"),
    }


def get_tomorrow_topic() -> bool:
    """내일 날짜에 예약된 토픽이 있는지 여부를 반환해요."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client = _make_client()
    response = client.databases.query(
        database_id=_db_id(),
        filter={"property": "scheduled_date", "date": {"equals": tomorrow}},
    )
    return len(response.get("results", [])) > 0


def get_recent_topics(limit: int = 10) -> list[str]:
    """최근 발행완료된 토픽 목록을 반환해요. 토픽 제안 시 중복 방지에 사용해요."""
    client = _make_client()
    response = client.databases.query(
        database_id=_db_id(),
        filter={"property": "status", "select": {"equals": "발행완료"}},
        sorts=[{"property": "published_at", "direction": "descending"}],
        page_size=limit,
    )
    topics = []
    for page in response.get("results", []):
        title_list = page["properties"]["topic"]["title"]
        if title_list:
            topics.append(title_list[0]["text"]["content"])
    return topics


def update_status(page_id: str, status: str) -> None:
    """토픽 페이지의 status를 업데이트해요."""
    client = _make_client()
    client.pages.update(
        page_id=page_id,
        properties={"status": {"select": {"name": status}}},
    )


def update_published_info(page_id: str, url: str, published_at: datetime) -> None:
    """발행 완료 후 notion_page_url, published_at, status를 한 번에 기록해요."""
    client = _make_client()
    client.pages.update(
        page_id=page_id,
        properties={
            "status": {"select": {"name": "발행완료"}},
            "notion_page_url": {"url": url},
            "published_at": {
                "date": {"start": published_at.astimezone(timezone.utc).isoformat()}
            },
        },
    )


def create_topic(topic_name: str, scheduled_date: str) -> str:
    """Notion DB에 새 토픽 페이지를 생성하고 page_id를 반환해요."""
    client = _make_client()
    response = client.pages.create(
        parent={"database_id": _db_id()},
        properties={
            "topic": {"title": [{"text": {"content": topic_name}}]},
            "status": {"select": {"name": "대기"}},
            "scheduled_date": {"date": {"start": scheduled_date}},
        },
    )
    return response["id"]


def _get_select(page: dict, prop: str) -> Optional[str]:
    select = page["properties"].get(prop, {}).get("select")
    return select["name"] if select else None


def _get_rich_text(page: dict, prop: str) -> str:
    texts = page["properties"].get(prop, {}).get("rich_text", [])
    parts = []
    for t in texts:
        if t.get("type") == "text":
            parts.append(t["text"]["content"])
    return "".join(parts)
