"""
insta-content-bot - 텔레그램 봇 메인 파이프라인
python-telegram-bot v21 (asyncio 기반)
"""

import asyncio
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from modules.paths import OUTPUT_DIR as _OUTPUT_DIR

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from modules.scraper import get_trending_posts
from modules.generator import generate_content
from modules.media import generate_tts, download_background
from modules.editor import create_header_overlay, create_reels_video, create_cardnews
from modules.uploader import upload_all
from modules.db import is_duplicate, mark_processed, save_upload, get_recent_uploads, get_stats
from modules.scheduler import get_scheduler

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OUTPUT_DIR = _OUTPUT_DIR

# ──────────────────────────────────────────────
# 파이프라인 실행 함수
# ──────────────────────────────────────────────

async def run_pipeline(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    source_text: str,
    source_url: str = "",
    title: str = "",
) -> dict | None:
    """전체 파이프라인 실행 (generator → media → editor)"""
    chat_id = update.effective_chat.id

    async def send_status(text: str):
        await context.bot.send_message(chat_id=chat_id, text=text)

    # 중복 소재 체크
    if is_duplicate(source_text):
        await send_status("⚠️ 이미 처리한 소재입니다. 다른 소재를 선택해주세요.")
        return None

    try:
        # Step 1: 대본 생성
        await send_status("✍️ 대본 생성 중...")
        content = generate_content(source_text, source_url)
        logger.info(f"대본 생성 완료: {content.get('reels_header_title', '')[:30]}")

        # Step 2: TTS 생성
        await send_status("🎙️ 음성 나레이션 생성 중...")
        tts_path = generate_tts(
            script=content["tts_script"],
            output_path=str(OUTPUT_DIR / "tts_audio.mp3"),
        )

        # Step 3: 배경 미디어 다운로드
        await send_status("🖼️ 배경 미디어 다운로드 중...")
        bg_path = download_background(
            keywords=content["media_keywords"],
            output_dir=str(OUTPUT_DIR),
        )

        # Step 4: 헤더 오버레이 생성
        await send_status("🎨 헤더 이미지 합성 중...")
        overlay_path = create_header_overlay(
            quote=content["reels_header_quote"],
            title=content["reels_header_title"],
            output_path=str(OUTPUT_DIR / "header_overlay.png"),
        )

        # Step 5: Reels 영상 합성
        await send_status("🎬 영상 합성 중...")
        reels_path = create_reels_video(
            bg_video=bg_path,
            overlay_img=overlay_path,
            audio=tts_path,
            output_path=str(OUTPUT_DIR / "reels_final.mp4"),
        )

        # Step 6: 카드뉴스 생성
        await send_status("📰 카드뉴스 생성 중...")
        cardnews_paths = create_cardnews(
            slides=content["cardnews_slides"],
            output_dir=str(OUTPUT_DIR),
        )

        # 소재 중복 방지 등록
        source_hash = mark_processed(source_text, source_url, title or content.get("reels_header_title", ""))

        return {
            "content": content,
            "reels_path": reels_path,
            "cardnews_paths": cardnews_paths,
            "tts_path": tts_path,
            "source_hash": source_hash,
        }

    except Exception as e:
        logger.error(f"파이프라인 오류: {e}")
        await send_status(f"❌ 오류 발생: {e}")
        return None


async def send_results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    result: dict,
):
    """파이프라인 결과물을 텔레그램으로 전송"""
    chat_id = update.effective_chat.id
    content = result["content"]

    # 캡션 전송
    caption_text = (
        f"*{content['reels_header_title']}*\n\n"
        f"{content['instagram_caption']}"
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=caption_text,
        parse_mode="Markdown",
    )

    # Reels 영상 전송
    reels_path = Path(result["reels_path"])
    if reels_path.exists() and reels_path.stat().st_size > 0:
        with open(reels_path, "rb") as f:
            await context.bot.send_video(
                chat_id=chat_id,
                video=f,
                caption="🎬 Reels 영상",
            )

    # 카드뉴스 이미지 전송 (미디어 그룹)
    cardnews_media = []
    for i, path in enumerate(result["cardnews_paths"]):
        p = Path(path)
        if p.exists() and p.stat().st_size > 0:
            cardnews_media.append(open(p, "rb"))

    if cardnews_media:
        media_group = [
            InputMediaPhoto(media=f, caption=f"📰 카드뉴스 {i+1}/5" if i == 0 else "")
            for i, f in enumerate(cardnews_media)
        ]
        await context.bot.send_media_group(chat_id=chat_id, media=media_group)
        for f in cardnews_media:
            f.close()

    # 승인/거절 버튼
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 인스타 업로드 승인", callback_data="approve_upload"),
            InlineKeyboardButton("❌ 폐기", callback_data="reject_content"),
        ]
    ])
    await context.bot.send_message(
        chat_id=chat_id,
        text="콘텐츠를 검토하고 업로드 여부를 결정하세요.",
        reply_markup=keyboard,
    )


# ──────────────────────────────────────────────
# 봇 핸들러
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 명령어 처리"""
    text = (
        "👋 *인스타그램 콘텐츠 자동 생성 봇*\n\n"
        "📌 *사용 방법:*\n"
        "• `/trending` — Reddit 트렌딩 소재 수집\n"
        "• `/stats` — 업로드 통계 및 최근 이력\n"
        "• `/schedule HH:MM` — 자동 실행 시각 설정 (예: `/schedule 09:00`)\n"
        "• `/schedule stop` — 자동 실행 중지\n"
        "• 텍스트/링크 직접 입력 → 콘텐츠 자동 생성\n\n"
        "🔧 *파이프라인:*\n"
        "Reddit 소재 → Claude 대본 → TTS → 배경 영상 → 영상/카드뉴스 합성 → 인스타 업로드\n\n"
        "시작하려면 `/trending` 을 입력하거나 소재를 직접 붙여넣으세요!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats 명령어: 업로드 통계 + 최근 이력"""
    stats = get_stats()
    recents = get_recent_uploads(limit=5)

    lines = [
        "📊 *업로드 통계*\n",
        f"• 전체 업로드: {stats['total_uploads']}회",
        f"• 성공: {stats['success']}회 | 실패: {stats['failed']}회",
        f"• 수집 소재 수: {stats['sources']}개\n",
    ]

    scheduler = get_scheduler()
    if scheduler.is_running:
        next_run = scheduler.get_next_run()
        lines.append(f"⏰ 다음 자동 실행: {next_run}")
    else:
        lines.append("⏰ 자동 실행: 비활성화")

    if recents:
        lines.append("\n📋 *최근 업로드 5건*")
        for r in recents:
            date = r["uploaded_at"][:16]
            title = (r.get("title") or "")[:30]
            status_icon = "✅" if r["status"] == "success" else "❌"
            lines.append(f"{status_icon} `{date}` {title}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/schedule HH:MM | stop — 자동 실행 스케줄 설정"""
    args = context.args
    scheduler = get_scheduler()

    if not args:
        status = "실행 중" if scheduler.is_running else "중지됨"
        next_run = scheduler.get_next_run() or "없음"
        await update.message.reply_text(
            f"⏰ *스케줄러 상태*: {status}\n다음 실행: {next_run}\n\n"
            "사용법: `/schedule 09:00` 또는 `/schedule stop`",
            parse_mode="Markdown",
        )
        return

    cmd = args[0].lower()

    if cmd == "stop":
        scheduler.stop()
        await update.message.reply_text("⏹️ 자동 실행 스케줄러가 중지되었습니다.")
        return

    # HH:MM 파싱
    try:
        h, m = map(int, cmd.split(":"))
        assert 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        await update.message.reply_text("❌ 형식 오류. 예: `/schedule 09:00`", parse_mode="Markdown")
        return

    if scheduler.is_running:
        scheduler.update_schedule(h, m)
        await update.message.reply_text(f"✅ 스케줄 변경: 매일 {h:02d}:{m:02d} 자동 실행")
    else:
        scheduler.start(hour=h, minute=m)
        await update.message.reply_text(f"✅ 스케줄러 시작: 매일 {h:02d}:{m:02d} 자동 실행")


async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/trending 명령어: Reddit 상위 소재 수집 후 선택지 제시"""
    await update.message.reply_text("🔍 Reddit 트렌딩 소재 수집 중...")

    try:
        posts = get_trending_posts()
        if not posts:
            await update.message.reply_text("❌ 소재를 가져오지 못했습니다. 다시 시도해주세요.")
            return

        # context에 posts 저장 (callback에서 사용)
        context.user_data["trending_posts"] = posts

        # InlineKeyboard 생성
        buttons = []
        text_lines = ["📋 *Reddit 트렌딩 소재 TOP 5*\n아래 항목을 선택하면 파이프라인이 실행됩니다:\n"]

        for i, post in enumerate(posts):
            title_short = post["title"][:50] + ("..." if len(post["title"]) > 50 else "")
            score_str = f"{post['score']:,}"
            text_lines.append(f"{i+1}. [{score_str}↑] {title_short}")
            buttons.append([
                InlineKeyboardButton(
                    f"{i+1}. {title_short}",
                    callback_data=f"trending_select_{i}",
                )
            ])

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "\n".join(text_lines),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"/trending 오류: {e}")
        await update.message.reply_text(f"❌ 오류: {e}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일반 텍스트/링크 입력 → 파이프라인 실행"""
    user_input = update.message.text.strip()

    if not user_input:
        return

    await update.message.reply_text("🚀 파이프라인 시작...")

    source_url = ""
    source_text = user_input

    # URL 감지
    if user_input.startswith("http://") or user_input.startswith("https://"):
        source_url = user_input
        source_text = f"URL 소재: {user_input}"

    result = await run_pipeline(update, context, source_text, source_url)
    if result:
        context.user_data["last_pipeline_result"] = result
        await send_results(update, context, result)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """InlineKeyboard 콜백 처리"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("trending_select_"):
        idx = int(data.split("_")[-1])
        posts = context.user_data.get("trending_posts", [])

        if idx >= len(posts):
            await query.edit_message_text("❌ 잘못된 선택입니다.")
            return

        post = posts[idx]
        source_text = f"{post['title']}\n\n{post['selftext']}"
        source_url = post["url"]

        await query.edit_message_text(
            f"✅ 선택됨: *{post['title'][:60]}*\n\n🚀 파이프라인 시작...",
            parse_mode="Markdown",
        )

        result = await run_pipeline(update, context, source_text, source_url, title=post.get("title", ""))
        if result:
            context.user_data["last_pipeline_result"] = result
            await send_results(update, context, result)

    elif data == "approve_upload":
        last_result = context.user_data.get("last_pipeline_result")
        if not last_result:
            await query.edit_message_text("❌ 업로드할 콘텐츠가 없습니다. 파이프라인을 먼저 실행해주세요.")
            return

        await query.edit_message_text("📤 *인스타그램 업로드 중...*", parse_mode="Markdown")

        content = last_result["content"]
        caption = f"{content['reels_header_title']}\n\n{content['instagram_caption']}"

        try:
            upload_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: upload_all(
                    reels_path=last_result["reels_path"],
                    cardnews_paths=last_result["cardnews_paths"],
                    caption=caption,
                ),
            )

            status = "failed" if upload_result["errors"] else "success"
            save_upload(
                source_hash=last_result.get("source_hash", ""),
                reels_url=upload_result.get("reels_url", ""),
                carousel_url=upload_result.get("carousel_url", ""),
                caption=caption,
                status=status,
            )

            if upload_result["errors"]:
                error_msg = "\n".join(upload_result["errors"])
                await query.edit_message_text(
                    f"⚠️ *일부 업로드 실패*\n\n{error_msg}",
                    parse_mode="Markdown",
                )
            else:
                lines = ["✅ *인스타그램 업로드 완료!*\n"]
                if upload_result["reels_url"]:
                    lines.append(f"🎬 Reels: {upload_result['reels_url']}")
                if upload_result["carousel_url"]:
                    lines.append(f"📰 카드뉴스: {upload_result['carousel_url']}")
                await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

        except Exception as e:
            logger.error(f"업로드 오류: {e}")
            await query.edit_message_text(f"❌ *업로드 실패*\n\n{e}", parse_mode="Markdown")

    elif data == "reject_content":
        await query.edit_message_text(
            "🗑️ *콘텐츠 폐기됨*\n\n"
            "새로운 소재로 다시 시작하려면 `/trending` 을 입력하세요.",
            parse_mode="Markdown",
        )


# ──────────────────────────────────────────────
# 앱 진입점
# ──────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        raise ValueError(".env 파일에 TELEGRAM_BOT_TOKEN을 설정해주세요.")

    logger.info("텔레그램 봇 시작...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("trending", cmd_trending))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # .env에 SCHEDULE_HOUR가 숫자로 설정되어 있으면 자동 시작
    auto_hour_raw = os.getenv("SCHEDULE_HOUR", "").strip()
    if auto_hour_raw.isdigit():
        scheduler = get_scheduler()
        scheduler.start()
        auto_min = os.getenv("SCHEDULE_MINUTE", "0").strip() or "0"
        logger.info(f"자동 스케줄러 활성화: {int(auto_hour_raw):02d}:{int(auto_min):02d}")

    logger.info("봇 폴링 시작 (Ctrl+C로 종료)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
