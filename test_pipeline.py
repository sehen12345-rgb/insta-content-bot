"""
전체 파이프라인 실전 테스트 스크립트.
텔레그램 봇 없이 직접 각 단계를 순차 검증한다.

실행: python test_pipeline.py
DEMO_MODE=true 로 실행하면 실제 API 호출 없이 구조만 테스트한다.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 테스트 소재
TEST_SOURCE = "주제: 버뮤다 삼각지대"

PASS = "[OK]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def check(label: str, ok: bool, detail: str = ""):
    icon = PASS if ok else FAIL
    detail_str = f"  {detail}" if detail else ""
    print(f"  {icon}  {label}{detail_str}")
    return ok


# ── Step 0: 환경 변수 점검 ──────────────────────

def test_env():
    section("Step 0: 환경 변수 점검")
    demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    if demo:
        print("  [DEMO MODE] 실제 API 호출 없이 구조 테스트")

    keys = {
        "ANTHROPIC_API_KEY": "Claude 대본 생성",
        "TELEGRAM_BOT_TOKEN": "텔레그램 봇",
        "TELEGRAM_CHAT_ID": "텔레그램 채팅 ID",
        "INSTAGRAM_USERNAME": "인스타그램 아이디",
        "INSTAGRAM_PASSWORD": "인스타그램 비밀번호",
    }
    optional = {
        "ELEVENLABS_API_KEY": "ElevenLabs TTS (없으면 gTTS 사용)",
        "PEXELS_API_KEY": "Pexels 배경 영상 (없으면 yt-dlp 사용)",
    }

    all_ok = True
    for key, desc in keys.items():
        val = os.getenv(key, "")
        ok = bool(val) or demo
        if not check(f"{key} ({desc})", ok, "(미설정)" if not ok else ""):
            all_ok = False

    for key, desc in optional.items():
        val = os.getenv(key, "")
        icon = PASS if val else SKIP
        print(f"  {icon}  {key} ({desc})")

    return all_ok or demo


# ── Step 1: 중복 체크 ───────────────────────────

def test_db():
    section("Step 1: 소재 중복 체크 (DB)")
    from modules.db import is_duplicate, get_stats

    try:
        dup = is_duplicate(TEST_SOURCE)
        stats = get_stats()
        check("DB 연결", True)
        check(f"소재 상태: {'중복 (이미 처리됨)' if dup else '신규 소재'}", True)
        print(f"  현재 DB: 총 {stats['total_uploads']}건 업로드, 소재 {stats['sources']}개")
        return True
    except Exception as e:
        check("DB 연결", False, str(e))
        return False


# ── Step 2: 대본 생성 ───────────────────────────

def test_generator():
    section("Step 2: Claude 대본 생성")
    from modules.generator import generate_content

    try:
        content = generate_content(TEST_SOURCE)
        required = ["reels_header_quote", "reels_header_title", "instagram_caption",
                    "cardnews_slides", "tts_script", "media_keywords"]
        ok = all(k in content for k in required)
        check("JSON 키 완전성", ok)
        check(f"슬라이드 수", len(content["cardnews_slides"]) == 5,
              f"{len(content['cardnews_slides'])}장")
        print(f"\n  제목: {content.get('reels_header_title', '')}")
        print(f"  TTS 길이: {len(content.get('tts_script', ''))}자")
        print(f"  미디어 키워드: {content.get('media_keywords', [])}")
        return content
    except Exception as e:
        check("대본 생성", False, str(e))
        return None


# ── Step 3: TTS 생성 ────────────────────────────

def test_tts(content: dict):
    section("Step 3: TTS 음성 생성")
    from modules.media import generate_tts
    from modules.paths import OUTPUT_DIR

    try:
        path = generate_tts(
            script=content["tts_script"],
            output_path=str(OUTPUT_DIR / "test_tts.mp3"),
        )
        p = Path(path)
        size = p.stat().st_size if p.exists() else 0
        ok = p.exists() and size > 0
        check("mp3 파일 생성", ok, f"({size:,}B)")
        return path if ok else None
    except Exception as e:
        check("TTS 생성", False, str(e))
        return None


# ── Step 4: 배경 미디어 다운로드 ────────────────

def test_media(content: dict):
    section("Step 4: 배경 미디어 다운로드")
    from modules.media import download_background
    from modules.paths import OUTPUT_DIR

    try:
        path = download_background(
            keywords=content["media_keywords"],
            output_dir=str(OUTPUT_DIR),
        )
        p = Path(path)
        size = p.stat().st_size if p.exists() else 0
        ok = p.exists() and size > 0
        check("배경 파일 다운로드", ok, f"({size:,}B) {p.suffix}")
        return path if ok else None
    except Exception as e:
        check("배경 다운로드", False, str(e))
        return None


# ── Step 5: 영상 & 카드뉴스 합성 ────────────────

def test_editor(content: dict, tts_path: str, bg_path: str):
    section("Step 5: 영상 & 카드뉴스 합성 (FFmpeg)")
    from modules.editor import create_header_overlay, create_reels_video, create_cardnews
    from modules.paths import OUTPUT_DIR

    results = {}

    try:
        overlay = create_header_overlay(
            quote=content["reels_header_quote"],
            title=content["reels_header_title"],
            output_path=str(OUTPUT_DIR / "test_overlay.png"),
        )
        p = Path(overlay)
        check("헤더 오버레이 PNG", p.exists() and p.stat().st_size > 0)
        results["overlay"] = overlay
    except Exception as e:
        check("헤더 오버레이", False, str(e))
        results["overlay"] = ""

    try:
        reels = create_reels_video(
            bg_video=bg_path,
            overlay_img=results.get("overlay", ""),
            audio=tts_path,
            output_path=str(OUTPUT_DIR / "test_reels.mp4"),
        )
        p = Path(reels)
        size_kb = p.stat().st_size // 1024 if p.exists() else 0
        check("Reels mp4 합성", p.exists() and size_kb > 1, f"({size_kb}KB)")
        results["reels"] = reels
    except Exception as e:
        check("Reels 합성", False, str(e))
        results["reels"] = None

    try:
        cards = create_cardnews(
            slides=content["cardnews_slides"],
            output_dir=str(OUTPUT_DIR),
        )
        ok = len(cards) == 5 and all(Path(p).exists() for p in cards)
        check(f"카드뉴스 {len(cards)}장 생성", ok)
        results["cardnews"] = cards
    except Exception as e:
        check("카드뉴스 생성", False, str(e))
        results["cardnews"] = []

    return results


# ── Step 6: 인스타그램 업로드 ───────────────────

def test_upload(content: dict, reels_path: str, cardnews_paths: list):
    section("Step 6: 인스타그램 업로드")
    from modules.uploader import upload_all

    caption = f"{content['reels_header_title']}\n\n{content['instagram_caption']}"

    try:
        result = upload_all(
            reels_path=reels_path,
            cardnews_paths=cardnews_paths,
            caption=caption,
        )
        check("Reels 업로드", bool(result.get("reels_url")),
              result.get("reels_url") or "실패")
        check("카드뉴스 업로드", bool(result.get("carousel_url")),
              result.get("carousel_url") or "실패")
        if result["errors"]:
            print(f"\n  오류 목록:")
            for err in result["errors"]:
                print(f"    - {err}")
        return result
    except Exception as e:
        check("업로드", False, str(e))
        return None


# ── Step 7: DB 이력 저장 ────────────────────────

def test_db_save(content: dict, upload_result: dict):
    section("Step 7: DB 이력 저장 & 중복 등록")
    from modules.db import mark_processed, save_upload, is_duplicate, get_stats

    try:
        source_hash = mark_processed(TEST_SOURCE, "", content.get("reels_header_title", ""))
        check("소재 해시 등록", bool(source_hash), source_hash)

        if upload_result:
            save_upload(
                source_hash=source_hash,
                reels_url=upload_result.get("reels_url", ""),
                carousel_url=upload_result.get("carousel_url", ""),
                caption=content.get("instagram_caption", ""),
                status="success" if not upload_result.get("errors") else "failed",
            )
            check("업로드 이력 저장", True)

        dup = is_duplicate(TEST_SOURCE)
        check("재실행 시 중복 감지", dup, "(같은 소재 재입력 시 차단됨)")
        stats = get_stats()
        print(f"\n  최종 DB: 총 {stats['total_uploads']}건 | 성공 {stats['success']} | 실패 {stats['failed']}")
        return True
    except Exception as e:
        check("DB 저장", False, str(e))
        return False


# ── 메인 ────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print("  insta-content-bot 전체 파이프라인 테스트")
    print(f"  소재: {TEST_SOURCE}")
    print("="*55)

    env_ok = test_env()
    if not env_ok:
        print("\n필수 환경 변수가 없습니다.")
        print("  옵션 1: .env 파일에 실제 API 키 입력")
        print("  옵션 2: DEMO_MODE=true python test_pipeline.py")
        sys.exit(1)

    test_db()

    content = test_generator()
    if not content:
        print("\n대본 생성 실패. 테스트 중단.")
        sys.exit(1)

    tts_path = test_tts(content)
    if not tts_path:
        print("\nTTS 생성 실패. 테스트 중단.")
        sys.exit(1)

    bg_path = test_media(content)
    if not bg_path:
        print("\n배경 미디어 다운로드 실패. 테스트 중단.")
        sys.exit(1)

    editor_results = test_editor(content, tts_path, bg_path)
    reels_path = editor_results.get("reels")
    cardnews_paths = editor_results.get("cardnews", [])

    upload_result = None
    if reels_path and cardnews_paths:
        upload_result = test_upload(content, reels_path, cardnews_paths)
    else:
        print("\n[SKIP] 영상/카드뉴스 없어 업로드 건너뜀")

    test_db_save(content, upload_result)

    section("테스트 완료")
    print("  output/ 폴더에서 생성된 파일을 확인하세요.")
    print()


if __name__ == "__main__":
    main()
