import logging
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src import blog_generator, notion_client, notion_writer, slack_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run() -> None:
    # 경로 1: 오늘 토픽 처리
    topic = notion_client.get_today_topic()
    if topic:
        logger.info(f"오늘 토픽 발견: {topic['topic']}")
        notion_client.update_status(topic["id"], "생성중")
        try:
            post = blog_generator.generate_post(
                topic=topic["topic"],
                category=topic["category"],
                memo=topic["memo"],
            )
            logger.info(f"글 생성 완료: {post['title']}")

            page_url = notion_writer.create_blog_page(
                topic_page_id=topic["id"],
                title=post["title"],
                content_md=post["content_md"],
            )
            logger.info(f"Notion 페이지 저장 완료: {page_url}")

            notion_client.update_published_info(
                page_id=topic["id"],
                url=page_url,
                published_at=datetime.now(tz=timezone.utc),
            )

            try:
                slack_client.notify_published(topic=topic["topic"], url=page_url)
                logger.info("Slack 알림 전송 완료")
            except Exception as e:
                logger.warning(f"Slack 알림 전송 실패 (무시): {e}")

        except Exception as e:
            logger.error(f"글 생성/저장 실패: {e}")
            notion_client.update_status(topic["id"], "실패")
            sys.exit(1)
        return

    logger.info("오늘 발행할 토픽이 없어요.")

    # 경로 2: 내일 토픽 확인 후 제안
    if notion_client.get_tomorrow_topic():
        logger.info("내일 토픽이 이미 있어요. 종료해요.")
        return

    logger.info("내일 토픽이 없어요. 토픽을 제안할게요.")
    try:
        recent_topics = notion_client.get_recent_topics()
        topics = blog_generator.suggest_topics(recent_topics=recent_topics)
        logger.info(f"토픽 제안 완료: {topics}")

        try:
            slack_client.notify_topic_suggestions(topics)
            logger.info("Slack 토픽 제안 전송 완료")
        except Exception as e:
            logger.warning(f"Slack 전송 실패 (무시): {e}")

    except Exception as e:
        logger.error(f"토픽 제안 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
