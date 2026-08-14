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
    """Instagrapi 클라이언트 로드 (세션 재사용 → 실패 시 재로그인 → 실패 시 세션 삭제 후 재시도)"""
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

    def _fresh_login(cl: Client) -> Client:
        """세션 없이 신규 로그인"""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()  # 오염된 세션 삭제
        cl2 = Client()
        cl2.delay_range = [1, 3]
        cl2.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        SESSION_FILE.parent.mkdir(exist_ok=True)
        cl2.dump_settings(SESSION_FILE)
        logger.info("인스타그램 신규 로그인 성공 (세션 저장)")
        return cl2

    cl = Client()
    cl.delay_range = [1, 3]

    # 1차: 세션 파일이 있으면 재사용 시도
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info("인스타그램 세션 재사용 성공")
            return cl
        except LoginRequired:
            logger.warning("세션 만료 → 재로그인 시도")
        except ChallengeRequired:
            logger.error(
                "인스타그램 보안 인증 요구 (ChallengeRequired).\n"
                "인스타그램 앱/웹에서 로그인 후 보안 알림을 승인하세요."
            )
            raise
        except TwoFactorRequired:
            logger.error("2단계 인증 필요. 인스타그램 앱에서 2FA를 비활성화하거나 앱 비밀번호를 사용하세요.")
            raise
        except Exception as e:
            logger.warning(f"세션 로드 실패 ({type(e).__name__}: {e}) → 재로그인 시도")

    # 2차: 신규 로그인
    try:
        return _fresh_login(cl)
    except ChallengeRequired:
        logger.error(
            "인스타그램 보안 인증 요구 (ChallengeRequired).\n"
            "인스타그램 앱에서 로그인 요청 알림을 승인한 후 다시 시도하세요."
        )
        raise
    except TwoFactorRequired:
        logger.error("2단계 인증 필요. 인스타그램 2FA를 비활성화하거나 앱 비밀번호를 사용하세요.")
        raise
    except Exception as e:
        logger.error(f"인스타그램 로그인 최종 실패: {type(e).__name__}: {e}")
        raise


def upload_reels(video_path: str, caption: str, thumbnail_path: str = None) -> str | None:
    """
    인스타그램 Reels 업로드.

    Returns:
        str: 업로드된 게시물 URL
    """
    if DEMO_MODE:
        logger.info(f"[DEMO MODE] Reels 업로드 건너뜀: {video_path}")
        return "https://www.instagram.com/p/DEMO_REELS/"

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise ValueError(".env에 INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD를 설정해주세요.")

    video_path = Path(video_path)
    if not video_path.exists() or video_path.stat().st_size == 0:
        raise FileNotFoundError(f"영상 파일이 없거나 비어있습니다: {video_path}")

    # 영상 최소 크기 체크 (1KB 미만은 더미 파일)
    if video_path.stat().st_size < 1024:
        raise ValueError(f"영상 파일이 너무 작습니다 ({video_path.stat().st_size}B). 합성이 제대로 됐는지 확인하세요.")

    logger.info(f"Reels 업로드 시작: {video_path.name} ({video_path.stat().st_size // 1024}KB)")

    cl = _get_client()

    extra_data = {}
    if thumbnail_path and Path(thumbnail_path).exists():
        extra_data["thumbnail"] = thumbnail_path

    try:
        media = cl.clip_upload(
            path=video_path,
            caption=caption,
            extra_data=extra_data,
        )
    except Exception as e:
        logger.error(f"clip_upload 실패: {type(e).__name__}: {e}")
        raise

    post_url = f"https://www.instagram.com/p/{media.code}/"
    logger.success(f"Reels 업로드 완료: {post_url}")
    return post_url


def upload_carousel(image_paths: list[str], caption: str) -> str | None:
    """
    인스타그램 카드뉴스 (Carousel/Album) 업로드.

    Returns:
        str: 업로드된 게시물 URL
    """
    if DEMO_MODE:
        logger.info(f"[DEMO MODE] 카드뉴스 업로드 건너뜀: {len(image_paths)}장")
        return "https://www.instagram.com/p/DEMO_CAROUSEL/"

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        raise ValueError(".env에 INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD를 설정해주세요.")

    valid_paths = [
        Path(p) for p in image_paths
        if Path(p).exists() and Path(p).stat().st_size > 1024  # 1KB 이상만 유효
    ]
    if not valid_paths:
        raise FileNotFoundError("업로드할 유효한 이미지가 없습니다 (파일이 없거나 비어있음).")

    logger.info(f"카드뉴스 업로드 시작: {len(valid_paths)}장")

    cl = _get_client()

    try:
        media = cl.album_upload(
            paths=valid_paths,
            caption=caption,
        )
    except Exception as e:
        logger.error(f"album_upload 실패: {type(e).__name__}: {e}")
        raise

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
                logger.info("연속 업로드 차단 방지 딜레이 (5초)...")
                time.sleep(5)
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
