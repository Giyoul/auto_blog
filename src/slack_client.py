import logging
import os
from datetime import date

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

logger = logging.getLogger(__name__)


def _make_client() -> WebClient:
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


def notify_published(topic: str, url: str) -> None:
    """블로그 글 발행 완료 알림을 Slack으로 전송해요."""
    today = date.today().isoformat()
    text = (
        "✅ 블로그 글 생성 완료!\n"
        f"📝 주제: {topic}\n"
        f"🔗 Notion: {url}\n"
        f"📅 작성일: {today}"
    )
    _send_message(text)


def notify_topic_suggestions(topics: list[str]) -> None:
    """토픽 선택지를 Slack으로 전송해요."""
    db_url = os.environ.get("NOTION_DATABASE_URL", "https://notion.so")
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(topics))
    text = (
        "📋 내일 블로그 토픽을 선택해 주세요!\n\n"
        f"{numbered}\n\n"
        f"👉 원하는 토픽을 Notion에서 내일 날짜로 설정해 주세요:\n"
        f"{db_url}"
    )
    _send_message(text)


def _send_message(text: str) -> None:
    channel = os.environ["SLACK_CHANNEL_ID"]
    client = _make_client()
    try:
        client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as e:
        logger.error("[slack] 메시지 전송 실패: %s", e.response["error"])
