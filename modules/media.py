"""TTS 생성 + 배경 영상/이미지 다운로드 모듈"""

import os
import requests
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "gtts").lower()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# TTS 생성
# ──────────────────────────────────────────────

def _generate_tts_elevenlabs(script: str, output_path: str) -> str:
    """ElevenLabs API로 TTS 생성"""
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save

    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY 환경변수가 없습니다.")

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio = client.generate(
        text=script,
        voice=ELEVENLABS_VOICE_ID,
        model="eleven_multilingual_v2",
    )
    save(audio, output_path)
    return output_path


def _generate_tts_gtts(script: str, output_path: str) -> str:
    """gTTS로 TTS 생성 (무료, 품질 낮음)"""
    from gtts import gTTS

    tts = gTTS(text=script, lang="ko", slow=False)
    tts.save(output_path)
    return output_path


def generate_tts(script: str, output_path: str = None) -> str:
    """
    텍스트를 음성으로 변환하여 mp3 파일 저장.

    Args:
        script: TTS로 변환할 텍스트 (한국어)
        output_path: 저장할 mp3 파일 경로 (None이면 output/tts_audio.mp3)

    Returns:
        str: 생성된 mp3 파일 경로
    """
    if output_path is None:
        output_path = str(OUTPUT_DIR / "tts_audio.mp3")

    if DEMO_MODE:
        logger.info("[DEMO MODE] TTS 생성 건너뜀, 더미 경로 반환")
        # 빈 파일 생성 (파이프라인 연속성 확보)
        Path(output_path).touch()
        return output_path

    logger.info(f"TTS 생성 시작 (provider: {TTS_PROVIDER})...")

    try:
        if TTS_PROVIDER == "elevenlabs":
            result = _generate_tts_elevenlabs(script, output_path)
        else:
            result = _generate_tts_gtts(script, output_path)

        logger.success(f"TTS 생성 완료: {result}")
        return result

    except Exception as e:
        logger.error(f"TTS 생성 실패: {e}")
        raise


# ──────────────────────────────────────────────
# 배경 영상/이미지 다운로드
# ──────────────────────────────────────────────

def _search_pexels_video(keyword: str) -> str | None:
    """Pexels에서 영상 검색 후 다운로드 URL 반환"""
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY 환경변수가 없습니다.")

    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=5&orientation=portrait"

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    videos = data.get("videos", [])
    if not videos:
        return None

    # HD 영상 우선 선택
    for video in videos:
        for file in video.get("video_files", []):
            if file.get("quality") in ("hd", "sd") and file.get("width", 0) >= 720:
                return file["link"]

    return None


def _search_pexels_photo(keyword: str) -> str | None:
    """Pexels에서 이미지 검색 후 다운로드 URL 반환"""
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY 환경변수가 없습니다.")

    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=5&orientation=portrait"

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    photos = data.get("photos", [])
    if not photos:
        return None

    return photos[0]["src"]["original"]


def _download_file(download_url: str, output_path: str) -> str:
    """URL에서 파일 다운로드"""
    logger.info(f"파일 다운로드 중: {download_url[:80]}...")
    response = requests.get(download_url, stream=True, timeout=60)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path


def _download_via_ytdlp(keyword: str, output_path: str) -> str:
    """yt-dlp fallback: YouTube Creative Commons 영상 다운로드"""
    import yt_dlp

    search_query = f"ytsearch1:{keyword} nature background no copyright"
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_query])

    return output_path


def download_background(keywords: list[str], output_dir: str = None) -> str:
    """
    미디어 키워드로 배경 영상/이미지 다운로드.
    우선순위: Pexels 영상 → Pexels 이미지 → yt-dlp fallback

    Args:
        keywords: 영어 검색 키워드 리스트 (generator.py의 media_keywords)
        output_dir: 저장 디렉토리 (None이면 output/)

    Returns:
        str: 다운로드된 파일 경로
    """
    if output_dir is None:
        output_dir = str(OUTPUT_DIR)

    Path(output_dir).mkdir(exist_ok=True)

    if DEMO_MODE:
        logger.info("[DEMO MODE] 배경 다운로드 건너뜀, 더미 경로 반환")
        dummy_path = str(Path(output_dir) / "bg_video.mp4")
        Path(dummy_path).touch()
        return dummy_path

    logger.info(f"배경 미디어 다운로드 시작 (키워드: {keywords})...")

    # 키워드별 순차 시도
    for keyword in keywords:
        # 1. Pexels 영상 시도
        try:
            video_url = _search_pexels_video(keyword)
            if video_url:
                output_path = str(Path(output_dir) / "bg_video.mp4")
                _download_file(video_url, output_path)
                logger.success(f"Pexels 영상 다운로드 완료: {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"Pexels 영상 실패 ({keyword}): {e}")

        # 2. Pexels 이미지 시도
        try:
            photo_url = _search_pexels_photo(keyword)
            if photo_url:
                output_path = str(Path(output_dir) / "bg_image.jpg")
                _download_file(photo_url, output_path)
                logger.success(f"Pexels 이미지 다운로드 완료: {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"Pexels 이미지 실패 ({keyword}): {e}")

    # 3. yt-dlp fallback
    try:
        keyword = keywords[0] if keywords else "mystery dark atmosphere"
        output_path = str(Path(output_dir) / "bg_video_yt.mp4")
        _download_via_ytdlp(keyword, output_path)
        logger.success(f"yt-dlp 다운로드 완료: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"yt-dlp fallback 실패: {e}")
        # 최종 fallback: 빈 파일
        output_path = str(Path(output_dir) / "bg_fallback.jpg")
        Path(output_path).touch()
        logger.warning(f"모든 다운로드 실패. 빈 파일 생성: {output_path}")
        return output_path
