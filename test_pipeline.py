"""
전체 파이프라인 통합 테스트 스크립트.

텔레그램 봇 없이 직접 파이프라인을 실행하여 각 단계를 검증합니다.

사용법:
    python test_pipeline.py                      # 기본 테스트 ("버뮤다 삼각지대")
    python test_pipeline.py "다른 주제 텍스트"   # 커스텀 주제
    python test_pipeline.py --demo               # DEMO_MODE 강제 적용

단계별 출력 결과:
    output/tts_audio.mp3
    output/bg_video.mp4 또는 bg_image.jpg
    output/header_overlay.png
    output/reels_final.mp4
    output/cardnews_1~5.png
"""

import sys
import os
import time
import argparse
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 테스트용 기본 소재
DEFAULT_SOURCE_TEXT = """
주제: 버뮤다 삼각지대

버뮤다 삼각지대는 미국 플로리다, 버뮤다 제도, 푸에르토리코를 잇는 삼각형 해역으로,
수십 년간 수백 척의 선박과 항공기가 흔적도 없이 사라진 것으로 알려진 미스터리 지역이다.
1945년에는 미군 어뢰 폭격기 5대(플라이트 19)가 훈련 비행 중 교신이 끊기며 실종됐고,
구조를 위해 출동한 수상 비행기마저 사라졌다. 과학자들은 메탄 하이드레이트 분출,
나침반 이상, 갑작스러운 기후 변화를 원인으로 제시하지만 공식적으로 해결된 사례는 없다.
"""


def step(name: str):
    print(f"\n{BOLD}{BLUE}▶ {name}{RESET}")


def ok(msg: str, elapsed: float = 0):
    t = f"  ({elapsed:.1f}s)" if elapsed > 0 else ""
    print(f"  {GREEN}✅ {msg}{RESET}{t}")


def fail(msg: str, err: Exception = None):
    print(f"  {RED}❌ {msg}{RESET}")
    if err:
        print(f"     {RED}{err}{RESET}")


def warn(msg: str):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def check_file(path: str, min_bytes: int = 100) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    return p.stat().st_size >= min_bytes


def run_pipeline(source_text: str) -> dict:
    """실제 파이프라인 순차 실행"""

    results = {}
    total_start = time.time()

    # ── Step 1: 대본 생성 ──────────────────────────────────────
    step("Step 1 / 5  |  Claude AI 대본 생성")
    try:
        from modules.generator import generate_content
        t = time.time()
        content = generate_content(source_text)
        elapsed = time.time() - t

        ok(f"대본 생성 완료", elapsed)
        print(f"    헤드라인  : {content.get('reels_header_title', '')}")
        print(f"    인용구    : {content.get('reels_header_quote', '')}")
        print(f"    TTS 대본  : {content.get('tts_script', '')[:60]}...")
        print(f"    키워드    : {content.get('media_keywords', [])}")

        results["content"] = content
    except Exception as e:
        fail("대본 생성 실패", e)
        return results

    # ── Step 2: TTS 생성 ──────────────────────────────────────
    step("Step 2 / 5  |  TTS 음성 생성")
    try:
        from modules.media import generate_tts
        tts_path = str(OUTPUT_DIR / "tts_audio.mp3")
        t = time.time()
        generate_tts(content["tts_script"], tts_path)
        elapsed = time.time() - t

        if check_file(tts_path, min_bytes=100):
            size_kb = Path(tts_path).stat().st_size // 1024
            ok(f"TTS 파일 생성 완료: {tts_path} ({size_kb}KB)", elapsed)
        else:
            warn("TTS 파일이 비어있음 (DEMO_MODE 또는 오류)")

        results["tts_path"] = tts_path
    except Exception as e:
        fail("TTS 생성 실패", e)
        results["tts_path"] = str(OUTPUT_DIR / "tts_audio.mp3")

    # ── Step 3: 배경 미디어 다운로드 ──────────────────────────
    step("Step 3 / 5  |  배경 미디어 다운로드")
    try:
        from modules.media import download_background
        keywords = content.get("media_keywords", ["mystery ocean dark"])
        t = time.time()
        bg_path = download_background(keywords, str(OUTPUT_DIR))
        elapsed = time.time() - t

        if check_file(bg_path, min_bytes=100):
            size_mb = Path(bg_path).stat().st_size / 1024 / 1024
            ok(f"배경 미디어 다운로드: {Path(bg_path).name} ({size_mb:.1f}MB)", elapsed)
        else:
            warn("배경 파일이 비어있음 (DEMO_MODE 또는 fallback)")

        results["bg_path"] = bg_path
    except Exception as e:
        fail("배경 미디어 다운로드 실패", e)
        results["bg_path"] = ""

    # ── Step 4: 헤더 오버레이 + 영상 합성 ─────────────────────
    step("Step 4 / 5  |  영상 합성 (헤더 오버레이 + Reels MP4)")
    try:
        from modules.editor import create_header_overlay, create_reels_video

        overlay_path = str(OUTPUT_DIR / "header_overlay.png")
        t = time.time()
        create_header_overlay(
            quote=content.get("reels_header_quote", "'미스터리가 시작된다'"),
            title=content.get("reels_header_title", "알 수 없는 실종"),
            output_path=overlay_path,
        )
        elapsed_overlay = time.time() - t
        ok(f"헤더 오버레이 생성: {overlay_path}", elapsed_overlay)

        reels_path = str(OUTPUT_DIR / "reels_final.mp4")
        t = time.time()
        create_reels_video(
            bg_video=results.get("bg_path", overlay_path),
            overlay_img=overlay_path,
            audio=results.get("tts_path", ""),
            output_path=reels_path,
        )
        elapsed_reels = time.time() - t

        if check_file(reels_path, min_bytes=100):
            size_mb = Path(reels_path).stat().st_size / 1024 / 1024
            ok(f"Reels 영상 합성 완료: {reels_path} ({size_mb:.1f}MB)", elapsed_reels)
        else:
            warn("Reels 파일이 비어있음 (DEMO_MODE 또는 오류)")

        results["reels_path"] = reels_path
        results["overlay_path"] = overlay_path
    except Exception as e:
        fail("영상 합성 실패", e)

    # ── Step 5: 카드뉴스 생성 ─────────────────────────────────
    step("Step 5 / 5  |  카드뉴스 PNG 5장 생성")
    try:
        from modules.editor import create_cardnews
        slides = content.get("cardnews_slides", ["슬라이드"] * 5)
        t = time.time()
        cardnews_paths = create_cardnews(slides, str(OUTPUT_DIR))
        elapsed = time.time() - t

        real_files = [p for p in cardnews_paths if check_file(p, min_bytes=100)]
        ok(f"카드뉴스 {len(real_files)}/5장 생성 완료", elapsed)
        for p in cardnews_paths:
            size_kb = Path(p).stat().st_size // 1024 if Path(p).exists() else 0
            status = "✅" if check_file(p, 100) else "⚠️ "
            print(f"    {status} {Path(p).name} ({size_kb}KB)")

        results["cardnews_paths"] = cardnews_paths
    except Exception as e:
        fail("카드뉴스 생성 실패", e)

    total_elapsed = time.time() - total_start
    return results, total_elapsed


def print_summary(results: dict, total_elapsed: float):
    print(f"\n{BOLD}{'='*60}")
    print(f"  파이프라인 테스트 결과 요약")
    print(f"{'='*60}{RESET}")

    checks = [
        ("Claude 대본",    "content" in results),
        ("TTS 음성",       check_file(results.get("tts_path", ""), 100)),
        ("배경 미디어",    check_file(results.get("bg_path", ""), 100)),
        ("헤더 오버레이",  check_file(results.get("overlay_path", ""), 100)),
        ("Reels 영상",     check_file(results.get("reels_path", ""), 100)),
        ("카드뉴스 5장",   len([p for p in results.get("cardnews_paths", [])
                                if check_file(p, 100)]) == 5),
    ]

    passed = 0
    for name, ok_flag in checks:
        icon = f"{GREEN}✅{RESET}" if ok_flag else f"{YELLOW}⚠️ {RESET}"
        print(f"  {icon}  {name}")
        if ok_flag:
            passed += 1

    is_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    demo_note = f"  {YELLOW}[DEMO_MODE — 실제 파일은 빈 더미]{RESET}" if is_demo else ""

    print(f"\n  총 소요 시간: {total_elapsed:.1f}초")
    print(f"  결과: {passed}/{len(checks)} 단계 완료")
    if demo_note:
        print(demo_note)
    print(f"\n  output/ 폴더에서 결과물을 확인하세요.")
    if passed >= 4:
        print(f"  {GREEN}{BOLD}🎉 파이프라인 정상 동작!{RESET}")
    else:
        print(f"  {YELLOW}⚠️  일부 단계 실패 또는 DEMO_MODE 실행됨{RESET}")


def main():
    parser = argparse.ArgumentParser(description="파이프라인 통합 테스트")
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE_TEXT,
                        help="테스트할 소재 텍스트 (기본: 버뮤다 삼각지대)")
    parser.add_argument("--demo", action="store_true",
                        help="DEMO_MODE 강제 적용 (API 호출 없이 테스트)")
    args = parser.parse_args()

    if args.demo:
        os.environ["DEMO_MODE"] = "true"

    is_demo = os.getenv("DEMO_MODE", "false").lower() == "true"

    print(f"\n{BOLD}{'='*60}")
    print(f"  insta-content-bot 파이프라인 통합 테스트")
    print(f"  모드: {'DEMO (API 호출 없음)' if is_demo else '실제 API 연동'}")
    print(f"{'='*60}{RESET}")
    print(f"\n소재 (앞 80자): {args.source.strip()[:80]}...")

    results, elapsed = run_pipeline(args.source.strip())
    print_summary(results, elapsed)


if __name__ == "__main__":
    main()
