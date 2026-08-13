"""
환경 점검 스크립트 — .env API 키 연동 및 패키지 설치 상태를 한 번에 검증.

사용법:
    python check_env.py          # 전체 점검 (API 실제 호출)
    python check_env.py --quick  # 패키지/환경변수 존재 여부만 확인 (API 호출 X)
"""

import sys
import os
import importlib
import argparse
from pathlib import Path

# .env 로드
from dotenv import load_dotenv
load_dotenv()

# 색상 출력 헬퍼
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
BLUE  = "\033[94m"
RESET = "\033[0m"
BOLD  = "\033[1m"

PASS = f"{GREEN}✅ PASS{RESET}"
FAIL = f"{RED}❌ FAIL{RESET}"
WARN = f"{YELLOW}⚠️  WARN{RESET}"
SKIP = f"{YELLOW}⏭  SKIP{RESET}"

results: list[tuple[str, str, str]] = []  # (category, item, status_str)


def log(category: str, item: str, ok: bool | None, detail: str = ""):
    if ok is True:
        status = PASS
    elif ok is False:
        status = FAIL
    else:
        status = WARN
    detail_str = f"  → {detail}" if detail else ""
    print(f"  [{category}] {item:<40} {status}{detail_str}")
    results.append((category, item, "PASS" if ok else ("WARN" if ok is None else "FAIL")))


def section(title: str):
    print(f"\n{BOLD}{BLUE}{'─'*60}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*60}{RESET}")


# ── 1. Python 버전 ──────────────────────────────────────────────
def check_python():
    section("Python 버전")
    ver = sys.version_info
    ok = ver >= (3, 11)
    log("Python", f"Python {ver.major}.{ver.minor}.{ver.micro}", ok,
        "3.11 이상 필요" if not ok else "")


# ── 2. 패키지 설치 ──────────────────────────────────────────────
REQUIRED_PACKAGES = [
    ("anthropic",           "anthropic"),
    ("python-telegram-bot", "telegram"),
    ("pillow",              "PIL"),
    ("moviepy",             "moviepy"),
    ("gtts",                "gtts"),
    ("requests",            "requests"),
    ("python-dotenv",       "dotenv"),
    ("loguru",              "loguru"),
    ("PyQt6",               "PyQt6"),
    ("praw",                "praw"),
    ("yt-dlp",              "yt_dlp"),
    ("elevenlabs",          "elevenlabs"),
]

def check_packages():
    section("패키지 설치 상태")
    for pkg_name, import_name in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(import_name)
            ver = getattr(mod, "__version__", "?")
            log("Package", pkg_name, True, f"v{ver}")
        except ImportError:
            log("Package", pkg_name, False, "pip install -r requirements.txt 실행 필요")


# ── 3. .env 파일 및 환경변수 ────────────────────────────────────
ENV_VARS = [
    ("ANTHROPIC_API_KEY",      True,  "Claude AI 대본 생성 필수"),
    ("TELEGRAM_BOT_TOKEN",     True,  "텔레그램 봇 필수"),
    ("TELEGRAM_CHAT_ID",       True,  "텔레그램 봇 필수"),
    ("REDDIT_CLIENT_ID",       False, "Reddit 소재 수집 (없으면 JSON API fallback)"),
    ("REDDIT_CLIENT_SECRET",   False, "Reddit 소재 수집 (없으면 JSON API fallback)"),
    ("ELEVENLABS_API_KEY",     False, "ElevenLabs TTS (없으면 gTTS 사용)"),
    ("PEXELS_API_KEY",         False, "Pexels 배경 미디어 (없으면 yt-dlp fallback)"),
    ("TTS_PROVIDER",           False, "gtts 또는 elevenlabs (기본: gtts)"),
    ("DEMO_MODE",              False, "true 설정 시 API 호출 없이 테스트"),
]

def check_env_vars():
    section(".env 환경변수")
    env_path = Path(".env")
    if env_path.exists():
        log("ENV", ".env 파일 존재", True)
    else:
        log("ENV", ".env 파일 존재", False, ".env.example을 복사해 .env 생성 필요")

    for var, required, desc in ENV_VARS:
        val = os.getenv(var, "")
        if val and not val.startswith("your_") and not val.startswith("sk-ant-xxx"):
            log("ENV", var, True, f"설정됨 ({val[:8]}...)")
        elif required:
            log("ENV", var, False, f"필수 — {desc}")
        else:
            log("ENV", var, None, f"선택 — {desc}")


# ── 4. API 연동 테스트 (--quick 아닐 때만) ─────────────────────
def check_anthropic():
    section("Anthropic Claude API 연동 테스트")
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-xxx"):
        log("API", "Claude API 키 유효성", False, "ANTHROPIC_API_KEY 미설정")
        return

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": "안녕? 'OK'라고만 답해줘."}],
        )
        reply = msg.content[0].text.strip()
        log("API", "Claude API 호출", True, f"응답: {reply[:30]}")
    except Exception as e:
        log("API", "Claude API 호출", False, str(e)[:80])


def check_telegram():
    section("Telegram Bot API 연동 테스트")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or "xxx" in token:
        log("API", "Telegram Bot 토큰", False, "TELEGRAM_BOT_TOKEN 미설정")
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getMe"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("ok"):
            bot_name = data["result"].get("username", "?")
            log("API", "Telegram getMe", True, f"@{bot_name}")
        else:
            log("API", "Telegram getMe", False, data.get("description", "Unknown error"))
    except Exception as e:
        log("API", "Telegram getMe", False, str(e)[:80])


def check_reddit():
    section("Reddit API 연동 테스트")
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")

    if not client_id or not client_secret or "your_" in client_id:
        log("API", "Reddit PRAW", None, "미설정 — JSON API fallback 사용 예정")
        # JSON API fallback 테스트
        try:
            import requests
            headers = {"User-Agent": "insta-content-bot/1.0"}
            resp = requests.get(
                "https://www.reddit.com/r/UnsolvedMysteries/top.json?t=day&limit=1",
                headers=headers, timeout=10
            )
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            if posts:
                title = posts[0]["data"].get("title", "")[:40]
                log("API", "Reddit JSON API fallback", True, f"'{title}...'")
            else:
                log("API", "Reddit JSON API fallback", None, "게시물 없음")
        except Exception as e:
            log("API", "Reddit JSON API fallback", False, str(e)[:80])
        return

    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=os.getenv("REDDIT_USER_AGENT", "insta-content-bot/1.0"),
        )
        subreddit = reddit.subreddit("UnsolvedMysteries")
        post = next(subreddit.top(time_filter="day", limit=1))
        log("API", "Reddit PRAW 연결", True, f"'{post.title[:40]}...'")
    except Exception as e:
        log("API", "Reddit PRAW 연결", False, str(e)[:80])


def check_pexels():
    section("Pexels API 연동 테스트")
    key = os.getenv("PEXELS_API_KEY", "")
    if not key or "your_" in key:
        log("API", "Pexels API", None, "미설정 — yt-dlp fallback 사용 예정")
        return

    try:
        import requests
        headers = {"Authorization": key}
        resp = requests.get(
            "https://api.pexels.com/v1/search?query=mystery+dark&per_page=1",
            headers=headers, timeout=10
        )
        data = resp.json()
        if data.get("photos"):
            log("API", "Pexels 이미지 검색", True, f"총 {data.get('total_results', '?')}개 결과")
        else:
            log("API", "Pexels 이미지 검색", False, str(data)[:80])
    except Exception as e:
        log("API", "Pexels API", False, str(e)[:80])


def check_elevenlabs():
    section("ElevenLabs TTS 연동 테스트")
    key = os.getenv("ELEVENLABS_API_KEY", "")
    provider = os.getenv("TTS_PROVIDER", "gtts")

    if provider != "elevenlabs":
        log("TTS", "ElevenLabs", None, f"TTS_PROVIDER={provider} → ElevenLabs 미사용")
        # gTTS 자체 테스트
        try:
            from gtts import gTTS
            log("TTS", "gTTS 패키지", True, "정상")
        except Exception as e:
            log("TTS", "gTTS 패키지", False, str(e))
        return

    if not key or "your_" in key:
        log("API", "ElevenLabs API Key", False, "ELEVENLABS_API_KEY 미설정")
        return

    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=key)
        voices = client.voices.get_all()
        log("API", "ElevenLabs 음성 목록", True, f"{len(voices.voices)}개 음성 사용 가능")
    except Exception as e:
        log("API", "ElevenLabs 연결", False, str(e)[:80])


def check_ffmpeg():
    section("FFmpeg 설치 확인")
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            ver_line = result.stdout.split("\n")[0]
            log("System", "FFmpeg", True, ver_line[:60])
        else:
            log("System", "FFmpeg", False, "ffmpeg 명령어 실패")
    except FileNotFoundError:
        log("System", "FFmpeg", False,
            "FFmpeg 미설치 — https://ffmpeg.org/download.html 에서 설치 후 PATH 등록 필요")
    except Exception as e:
        log("System", "FFmpeg", False, str(e)[:80])


def check_output_dirs():
    section("디렉터리 구조 확인")
    dirs = ["output", "templates", "modules", "gui"]
    for d in dirs:
        p = Path(d)
        if p.exists():
            log("Dir", d + "/", True)
        else:
            log("Dir", d + "/", False, "디렉터리 없음")


# ── 최종 요약 ──────────────────────────────────────────────────
def print_summary():
    section("점검 결과 요약")
    total = len(results)
    passed = sum(1 for _, _, s in results if s == "PASS")
    warned = sum(1 for _, _, s in results if s == "WARN")
    failed = sum(1 for _, _, s in results if s == "FAIL")

    print(f"\n  총 {total}개 항목  |  "
          f"{GREEN}PASS {passed}{RESET}  |  "
          f"{YELLOW}WARN {warned}{RESET}  |  "
          f"{RED}FAIL {failed}{RESET}\n")

    if failed == 0:
        print(f"  {GREEN}{BOLD}🎉 모든 필수 항목 통과! 봇을 실행할 준비가 됐습니다.{RESET}")
        print(f"\n  실행 방법:")
        print(f"    텔레그램 봇  →  python main.py")
        print(f"    GUI 패널    →  python gui_main.py")
    else:
        print(f"  {RED}{BOLD}❌ {failed}개 항목 실패. 위 오류를 수정 후 다시 실행하세요.{RESET}")
        print(f"\n  빠른 테스트를 원하면 .env 에서 DEMO_MODE=true 설정 후 재시도")


# ── 메인 ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="insta-content-bot 환경 점검 스크립트")
    parser.add_argument("--quick", action="store_true",
                        help="패키지/환경변수만 확인 (API 실제 호출 X)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*60}")
    print("  insta-content-bot 환경 점검 스크립트")
    mode = "빠른 점검 (--quick)" if args.quick else "전체 점검 (API 실제 호출)"
    print(f"  모드: {mode}")
    print(f"{'='*60}{RESET}")

    check_python()
    check_packages()
    check_env_vars()
    check_output_dirs()
    check_ffmpeg()

    if not args.quick:
        check_anthropic()
        check_telegram()
        check_reddit()
        check_pexels()
        check_elevenlabs()

    print_summary()


if __name__ == "__main__":
    main()
