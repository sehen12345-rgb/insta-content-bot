"""APScheduler 기반 자동 실행 스케줄링 모듈"""

import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from modules.paths import OUTPUT_DIR

load_dotenv()

SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))


def _run_auto_pipeline():
    """자동 파이프라인 실행 (스케줄러 콜백)"""
    from modules.scraper import get_trending_posts
    from modules.generator import generate_content
    from modules.media import generate_tts, download_background
    from modules.editor import create_header_overlay, create_reels_video, create_cardnews
    from modules.uploader import upload_all
    from modules.db import is_duplicate, mark_processed, save_upload

    logger.info(f"[스케줄러] 자동 파이프라인 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    try:
        # 소재 수집
        posts = get_trending_posts()
        if not posts:
            logger.warning("[스케줄러] 소재 없음, 건너뜀")
            return

        # 중복 제거 후 첫 번째 소재 선택
        selected = None
        for post in posts:
            source_text = f"{post['title']}\n\n{post.get('selftext', '')}"
            if not is_duplicate(source_text):
                selected = post
                selected["_source_text"] = source_text
                break

        if not selected:
            logger.warning("[스케줄러] 모든 소재가 중복됨, 건너뜀")
            return

        source_text = selected["_source_text"]
        source_url = selected.get("url", "")
        title = selected.get("title", "")

        # 대본 생성
        content = generate_content(source_text, source_url)
        caption = (
            f"{content['reels_header_title']}\n\n{content['instagram_caption']}"
        )

        # 미디어 생성
        tts_path = generate_tts(
            script=content["tts_script"],
            output_path=str(OUTPUT_DIR / "tts_audio.mp3"),
        )
        bg_path = download_background(
            keywords=content["media_keywords"],
            output_dir=str(OUTPUT_DIR),
        )
        overlay_path = create_header_overlay(
            quote=content["reels_header_quote"],
            title=content["reels_header_title"],
            output_path=str(OUTPUT_DIR / "header_overlay.png"),
        )
        reels_path = create_reels_video(
            bg_video=bg_path,
            overlay_img=overlay_path,
            audio=tts_path,
            output_path=str(OUTPUT_DIR / "reels_final.mp4"),
        )
        cardnews_paths = create_cardnews(
            slides=content["cardnews_slides"],
            output_dir=str(OUTPUT_DIR),
        )

        # 소재 등록 (중복 방지)
        source_hash = mark_processed(source_text, source_url, title)

        # 인스타 업로드
        upload_result = upload_all(
            reels_path=reels_path,
            cardnews_paths=cardnews_paths,
            caption=caption,
        )

        status = "failed" if upload_result["errors"] else "success"
        save_upload(
            source_hash=source_hash,
            reels_url=upload_result.get("reels_url", ""),
            carousel_url=upload_result.get("carousel_url", ""),
            caption=caption,
            status=status,
        )

        if upload_result["errors"]:
            logger.error(f"[스케줄러] 업로드 오류: {upload_result['errors']}")
        else:
            logger.success(
                f"[스케줄러] 완료! Reels={upload_result['reels_url']} "
                f"Carousel={upload_result['carousel_url']}"
            )

    except Exception as e:
        logger.error(f"[스케줄러] 파이프라인 오류: {e}")


class ContentScheduler:
    """APScheduler 래퍼 — 매일 지정 시각 자동 실행"""

    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        self._scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self._trigger = CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone="Asia/Seoul")
        self._job = None
        self._running = False

    def start(self, hour: int = None, minute: int = None):
        """스케줄러 시작"""
        if self._running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return

        h = hour if hour is not None else SCHEDULE_HOUR
        m = minute if minute is not None else SCHEDULE_MINUTE

        from apscheduler.triggers.cron import CronTrigger

        self._job = self._scheduler.add_job(
            _run_auto_pipeline,
            trigger=CronTrigger(hour=h, minute=m, timezone="Asia/Seoul"),
            id="auto_pipeline",
            name=f"자동 파이프라인 ({h:02d}:{m:02d})",
            replace_existing=True,
            misfire_grace_time=300,
        )
        self._scheduler.start()
        self._running = True
        logger.success(f"스케줄러 시작: 매일 {h:02d}:{m:02d} 자동 실행")

    def stop(self):
        """스케줄러 중지"""
        if not self._running:
            return
        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("스케줄러 중지됨")

    def run_now(self):
        """즉시 파이프라인 실행 (테스트용)"""
        logger.info("즉시 실행 요청")
        _run_auto_pipeline()

    @property
    def is_running(self) -> bool:
        return self._running

    def get_next_run(self) -> str | None:
        """다음 실행 예정 시각 반환"""
        if not self._running or not self._job:
            return None
        next_run = self._job.next_run_time
        if next_run:
            return next_run.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def update_schedule(self, hour: int, minute: int):
        """스케줄 시각 변경"""
        from apscheduler.triggers.cron import CronTrigger

        if not self._running:
            logger.warning("스케줄러가 실행 중이지 않습니다.")
            return
        self._job.reschedule(
            trigger=CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul")
        )
        logger.info(f"스케줄 변경: 매일 {hour:02d}:{minute:02d}")


# 싱글톤
_scheduler_instance: ContentScheduler | None = None


def get_scheduler() -> ContentScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ContentScheduler()
    return _scheduler_instance
