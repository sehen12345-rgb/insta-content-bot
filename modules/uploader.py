"""Instagrapi 기반 인스타그램 자동 업로드 모듈"""

import os
import time
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from modules.paths import OUTPUT_DIR

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

SESSION_FILE = OUTPUT_DIR / "instagram_session.json"


def _get_client():
    """Instagrapi 클라이언트 로드 (세션 재사용)"""
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [1, 3]  # 요청 간 랜덤 딜레이 (차단 방지)

    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info("인스타그램 세션 로드 성공")
            return cl
        except Exception as e:
            logger.warning(f"세션 재사용 실패, 재로그인: {e}")

    # 신규 로그인
    cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
    SESSION_FILE.parent.mkdir(exist_ok=True)
    cl.dump_settings(SESSION_FILE)
    logger.info("인스타그램 로그인 성공 (세션 저장)")
    return cl


def upload_reels(video_path: str, caption: str, thumbnail_path: str = None) -> str | None:
    """
    인스타그램 Reels 업로드.

    Args:
        video_path: 업로드할 mp4 파일 경로
        caption: 캡션 (해시태그 포함)
        thumbnail_path: 썸네일 이미지 경로 (선택)

    Returns:
        str | None: 업로드된 게시물 URL, 실패 시 None
    """
    if DEMO_MODE:
        logger.info(f"[DEMO MODE] Reels 업로드 건너뜀: {video_path}")
        return "https://www.instagram.com/p/DEMO_REELS/"

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise ValueError("INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD 환경변수를 설정해주세요.")

    video_path = Path(video_path)
    if not video_path.exists() or video_path.stat().st_size == 0:
        raise FileNotFoundError(f"영상 파일이 없거나 비어있습니다: {video_path}")

    logger.info(f"Reels 업로드 시작: {video_path.name}")

    cl = _get_client()

    extra_data = {}
    if thumbnail_path and Path(thumbnail_path).exists():
        extra_data["thumbnail"] = thumbnail_path

    media = cl.clip_upload(
        path=video_path,
        caption=caption,
        extra_data=extra_data,
    )

    post_url = f"https://www.instagram.com/p/{media.code}/"
    logger.success(f"Reels 업로드 완료: {post_url}")
    return post_url


def upload_carousel(image_paths: list[str], caption: str) -> str | None:
    """
    인스타그램 카드뉴스 (Carousel/Album) 업로드.

    Args:
        image_paths: 이미지 파일 경로 리스트 (최대 10장)
        caption: 캡션 (해시태그 포함)

    Returns:
        str | None: 업로드된 게시물 URL, 실패 시 None
    """
    if DEMO_MODE:
        logger.info(f"[DEMO MODE] 카드뉴스 업로드 건너뜀: {len(image_paths)}장")
        return "https://www.instagram.com/p/DEMO_CAROUSEL/"

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise ValueError("INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD 환경변수를 설정해주세요.")

    valid_paths = [Path(p) for p in image_paths if Path(p).exists() and Path(p).stat().st_size > 0]
    if not valid_paths:
        raise FileNotFoundError("업로드할 유효한 이미지가 없습니다.")

    logger.info(f"카드뉴스 업로드 시작: {len(valid_paths)}장")

    cl = _get_client()

    media = cl.album_upload(
        paths=valid_paths,
        caption=caption,
    )

    post_url = f"https://www.instagram.com/p/{media.code}/"
    logger.success(f"카드뉴스 업로드 완료: {post_url}")
    return post_url


def upload_all(
    reels_path: str,
    cardnews_paths: list[str],
    caption: str,
    thumbnail_path: str = None,
    upload_reels_flag: bool = True,
    upload_carousel_flag: bool = True,
) -> dict:
    """
    Reels + 카드뉴스 순차 업로드 (요청 간 딜레이 포함).

    Returns:
        dict: {"reels_url": ..., "carousel_url": ..., "errors": [...]}
    """
    result = {"reels_url": None, "carousel_url": None, "errors": []}

    if upload_reels_flag:
        try:
            result["reels_url"] = upload_reels(reels_path, caption, thumbnail_path)
            if upload_carousel_flag:
                time.sleep(5)  # 연속 업로드 차단 방지
        except Exception as e:
            logger.error(f"Reels 업로드 실패: {e}")
            result["errors"].append(f"Reels: {e}")

    if upload_carousel_flag:
        try:
            result["carousel_url"] = upload_carousel(cardnews_paths, caption)
        except Exception as e:
            logger.error(f"카드뉴스 업로드 실패: {e}")
            result["errors"].append(f"Carousel: {e}")

    return result


def verify_credentials() -> bool:
    """인스타그램 로그인 자격증명 확인 (설정 검증용)"""
    if DEMO_MODE:
        return True
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        return False
    try:
        _get_client()
        return True
    except Exception as e:
        logger.error(f"자격증명 확인 실패: {e}")
        return False
