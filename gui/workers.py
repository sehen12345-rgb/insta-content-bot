"""QThread 기반 파이프라인 워커"""

import asyncio
from pathlib import Path
from loguru import logger

from PyQt6.QtCore import QThread, pyqtSignal


# ──────────────────────────────────────────────
# BotWorker: 텔레그램 봇 QThread 실행
# ──────────────────────────────────────────────

class BotWorker(QThread):
    """
    텔레그램 봇을 QThread에서 asyncio 이벤트 루프로 실행.

    Signals:
        status_changed(str): 봇 상태 변경 메시지
        error_occurred(str): 오류 발생 메시지
    """

    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    def run(self):
        """QThread에서 실행되는 메서드"""
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            from main import main as bot_main
            self.status_changed.emit("텔레그램 봇 시작 중...")
            logger.info("BotWorker: 봇 이벤트 루프 시작")
            self._loop.run_until_complete(self._run_bot())
        except Exception as e:
            logger.error(f"BotWorker 오류: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self._running = False
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self.status_changed.emit("봇 중지됨")
            logger.info("BotWorker: 이벤트 루프 종료")

    async def _run_bot(self):
        """봇을 asyncio로 실행"""
        import os
        from dotenv import load_dotenv
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, Update

        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")

        # main.py 핸들러 임포트
        from main import cmd_start, cmd_trending, handle_text, handle_callback

        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("trending", cmd_trending))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        self.status_changed.emit("텔레그램 봇 실행 중")
        logger.success("BotWorker: 봇 폴링 시작")

        async with app:
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            # stop 신호를 기다리는 루프
            while self._running:
                await asyncio.sleep(1)
            await app.updater.stop()
            await app.stop()

    def stop(self):
        """봇 중지"""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.status_changed.emit("봇 중지 요청됨...")
        logger.info("BotWorker: 중지 요청")


# ──────────────────────────────────────────────
# PipelineWorker: 수동 파이프라인 실행
# ──────────────────────────────────────────────

class PipelineWorker(QThread):
    """
    수동 파이프라인을 QThread에서 실행.
    scraper → generator → media → editor 순서.

    Signals:
        status_changed(str): 진행 상태 메시지
        progress_updated(int): 진행률 (0~100)
        pipeline_completed(dict): 완료 시 결과 dict
        error_occurred(str): 오류 메시지
        step_changed(int, str): (step_index, state) 단계 상태 변경
    """

    status_changed = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    pipeline_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    step_changed = pyqtSignal(int, str)  # (0-based index, 'pending'|'active'|'done')

    def __init__(self, source_text: str, source_url: str = "", parent=None):
        super().__init__(parent)
        self._source_text = source_text
        self._source_url = source_url
        self._output_dir = Path(__file__).parent.parent / "output"
        self._output_dir.mkdir(exist_ok=True)

    def run(self):
        """파이프라인 순차 실행"""
        try:
            result = {}

            # ── Step 0: 중복 체크 + 소재 확인 ──
            self.step_changed.emit(0, "active")
            self.status_changed.emit("소재 확인 중...")
            self.progress_updated.emit(5)
            source_text = self._source_text
            source_url = self._source_url

            # 중복 소재 감지
            from modules.db import is_duplicate, mark_processed
            if is_duplicate(source_text):
                logger.warning("중복 소재 감지 — 이미 처리된 소재입니다. 계속 진행합니다.")
                self.status_changed.emit("⚠ 중복 소재 — 계속 진행")

            self.step_changed.emit(0, "done")
            self.progress_updated.emit(20)

            # ── Step 1: 대본 생성 ──
            self.step_changed.emit(1, "active")
            self.status_changed.emit("Claude AI 대본 생성 중...")
            from modules.generator import generate_content
            content = generate_content(source_text, source_url)
            result["content"] = content
            logger.info(f"대본 생성 완료: {content.get('reels_header_title', '')[:30]}")
            self.step_changed.emit(1, "done")
            self.progress_updated.emit(40)

            # ── Step 2: TTS + 배경 미디어 ──
            self.step_changed.emit(2, "active")
            self.status_changed.emit("TTS 음성 생성 중...")
            from modules.media import generate_tts, download_background
            tts_path = generate_tts(
                script=content["tts_script"],
                output_path=str(self._output_dir / "tts_audio.mp3"),
            )
            result["tts_path"] = tts_path

            self.status_changed.emit("배경 미디어 다운로드 중...")
            bg_path = download_background(
                keywords=content["media_keywords"],
                output_dir=str(self._output_dir),
            )
            result["bg_path"] = bg_path
            self.step_changed.emit(2, "done")
            self.progress_updated.emit(65)

            # ── Step 3: 영상/카드뉴스 합성 ──
            self.step_changed.emit(3, "active")
            self.status_changed.emit("헤더 오버레이 생성 중...")
            from modules.editor import create_header_overlay, create_reels_video, create_cardnews
            overlay_path = create_header_overlay(
                quote=content["reels_header_quote"],
                title=content["reels_header_title"],
                output_path=str(self._output_dir / "header_overlay.png"),
            )

            self.status_changed.emit("Reels 영상 합성 중...")
            reels_path = create_reels_video(
                bg_video=bg_path,
                overlay_img=overlay_path,
                audio=tts_path,
                output_path=str(self._output_dir / "reels_final.mp4"),
            )
            result["reels_path"] = reels_path

            self.status_changed.emit("카드뉴스 생성 중...")
            cardnews_paths = create_cardnews(
                slides=content["cardnews_slides"],
                output_dir=str(self._output_dir),
            )
            result["cardnews_paths"] = cardnews_paths
            self.step_changed.emit(3, "done")
            self.progress_updated.emit(100)

            # 소재를 DB에 등록 (중복 방지용)
            source_hash = mark_processed(source_text, source_url)
            result["source_hash"] = source_hash

            self.status_changed.emit("파이프라인 완료!")
            logger.success("PipelineWorker: 파이프라인 완료")
            self.pipeline_completed.emit(result)

        except Exception as e:
            logger.error(f"PipelineWorker 오류: {e}")
            self.error_occurred.emit(str(e))
            self.status_changed.emit(f"오류 발생: {e}")


# ──────────────────────────────────────────────
# TrendingWorker: Reddit 트렌딩 수집
# ──────────────────────────────────────────────

class TrendingWorker(QThread):
    """
    Reddit 트렌딩 소재를 QThread에서 수집.

    Signals:
        posts_fetched(list): 수집된 게시물 리스트
        error_occurred(str): 오류 메시지
    """

    posts_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            from modules.scraper import get_trending_posts
            logger.info("TrendingWorker: 수집 시작")
            posts = get_trending_posts()
            logger.success(f"TrendingWorker: {len(posts)}개 수집 완료")
            self.posts_fetched.emit(posts)
        except Exception as e:
            logger.error(f"TrendingWorker 오류: {e}")
            self.error_occurred.emit(str(e))


# ──────────────────────────────────────────────
# UploadWorker: 인스타그램 업로드
# ──────────────────────────────────────────────

class UploadWorker(QThread):
    """
    인스타그램 Reels + 카드뉴스 업로드를 QThread에서 실행.

    Signals:
        status_changed(str): 진행 상태 메시지
        upload_completed(dict): {"reels_url": str, "carousel_url": str, "errors": list}
        error_occurred(str): 오류 메시지
    """

    status_changed = pyqtSignal(str)
    upload_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        reels_path: str,
        cardnews_paths: list,
        caption: str,
        source_hash: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._reels_path = reels_path
        self._cardnews_paths = cardnews_paths
        self._caption = caption
        self._source_hash = source_hash

    def run(self):
        try:
            from modules.uploader import upload_all
            from modules.db import save_upload

            self.status_changed.emit("인스타그램 업로드 중...")
            logger.info("UploadWorker: 업로드 시작")

            result = upload_all(
                reels_path=self._reels_path,
                cardnews_paths=self._cardnews_paths,
                caption=self._caption,
            )

            status = "failed" if result.get("errors") else "success"
            if self._source_hash:
                save_upload(
                    source_hash=self._source_hash,
                    reels_url=result.get("reels_url", ""),
                    carousel_url=result.get("carousel_url", ""),
                    caption=self._caption,
                    status=status,
                )

            if result.get("errors"):
                logger.error(f"UploadWorker 오류: {result['errors']}")
                self.status_changed.emit(f"업로드 오류: {result['errors']}")
            else:
                logger.success(
                    f"UploadWorker: 완료! Reels={result.get('reels_url')} "
                    f"Carousel={result.get('carousel_url')}"
                )
                self.status_changed.emit("업로드 완료!")

            self.upload_completed.emit(result)

        except Exception as e:
            logger.error(f"UploadWorker 오류: {e}")
            self.error_occurred.emit(str(e))


# ──────────────────────────────────────────────
# HistoryWorker: DB 업로드 이력 조회
# ──────────────────────────────────────────────

class HistoryWorker(QThread):
    """
    DB에서 업로드 이력과 통계를 조회.

    Signals:
        history_fetched(list, dict): (uploads 리스트, stats 딕셔너리)
        error_occurred(str): 오류 메시지
    """

    history_fetched = pyqtSignal(list, dict)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            from modules.db import get_recent_uploads, get_stats
            uploads = get_recent_uploads(30)
            stats = get_stats()
            logger.debug(f"HistoryWorker: {len(uploads)}건 이력 조회 완료")
            self.history_fetched.emit(uploads, stats)
        except Exception as e:
            logger.error(f"HistoryWorker 오류: {e}")
            self.error_occurred.emit(str(e))
