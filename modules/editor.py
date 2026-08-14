"""Pillow + MoviePy 영상 및 카드뉴스 합성 모듈"""

import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from modules.paths import OUTPUT_DIR, TEMPLATES_DIR

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# 색상 팔레트
COLOR_BG_DARK = (15, 15, 26)        # #0f0f1a
COLOR_PANEL = (26, 26, 46)          # #1a1a2e
COLOR_ACCENT = (225, 48, 108)       # #e1306c 인스타 레드
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (160, 160, 184)        # #a0a0b8
COLOR_OVERLAY = (0, 0, 0, 180)      # 반투명 검정

CARD_SIZE = (1080, 1080)
REELS_SIZE = (1080, 1920)
HEADER_SIZE = (1080, 400)


def _get_font(size: int, bold: bool = False):
    """폰트 로드 (NanumGothicBold 우선, 없으면 PIL default)"""
    from PIL import ImageFont

    font_name = "NanumGothicBold.ttf" if bold else "NanumGothic.ttf"
    font_path = TEMPLATES_DIR / font_name

    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception as e:
            logger.warning(f"폰트 로드 실패 ({font_path}): {e}")

    # fallback: PIL default
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_multiline_centered(draw, text: str, y_center: int, width: int,
                              font, color, line_spacing: int = 8):
    """텍스트를 가로 중앙 정렬로 그리기"""
    from PIL import ImageDraw

    lines = text.split("\n")
    line_height = font.size if hasattr(font, "size") else 20
    total_height = len(lines) * (line_height + line_spacing) - line_spacing
    y = y_center - total_height // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_height + line_spacing


def create_header_overlay(quote: str, title: str, output_path: str = None) -> str:
    """
    1080x400 PNG 헤더 오버레이 생성.
    - 상단 반투명 다크 박스
    - quote: 흰색 이탤릭 (상단)
    - title: 빨간 굵은 글씨 (하단)

    Args:
        quote: 강조 문구 (작은따옴표 포함)
        title: 메인 헤드라인
        output_path: 저장 경로 (None이면 output/header_overlay.png)

    Returns:
        str: 저장된 파일 경로
    """
    from PIL import Image, ImageDraw

    if output_path is None:
        output_path = str(OUTPUT_DIR / "header_overlay.png")

    if DEMO_MODE:
        logger.info("[DEMO MODE] 헤더 오버레이 생성 건너뜀")
        img = Image.new("RGBA", HEADER_SIZE, (0, 0, 0, 0))
        img.save(output_path)
        return output_path

    logger.info("헤더 오버레이 생성 중...")

    img = Image.new("RGBA", HEADER_SIZE, (0, 0, 0, 0))
    overlay = Image.new("RGBA", HEADER_SIZE, COLOR_OVERLAY)
    img.paste(overlay, (0, 0))

    draw = ImageDraw.Draw(img)

    # quote 텍스트 (흰색, 소형)
    font_quote = _get_font(36, bold=False)
    _draw_multiline_centered(draw, quote, y_center=130, width=HEADER_SIZE[0],
                              font=font_quote, color=COLOR_WHITE)

    # 구분선
    draw.line([(80, 210), (1000, 210)], fill=COLOR_ACCENT, width=2)

    # title 텍스트 (빨간색, 굵고 크게)
    font_title = _get_font(54, bold=True)
    _draw_multiline_centered(draw, title, y_center=300, width=HEADER_SIZE[0],
                              font=font_title, color=COLOR_ACCENT)

    img.save(output_path, "PNG")
    logger.success(f"헤더 오버레이 저장: {output_path}")
    return output_path


def _check_ffmpeg():
    """FFmpeg 설치 확인 — 없으면 명확한 오류 메시지"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.debug(f"FFmpeg 확인: {exe}")
        return exe
    except Exception:
        pass
    import shutil
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    raise RuntimeError(
        "FFmpeg를 찾을 수 없습니다.\n"
        "해결: pip install imageio-ffmpeg  또는  https://ffmpeg.org 에서 설치 후 PATH 추가"
    )


def _image_to_video(image_path: str, duration: float, output_path: str) -> str:
    """이미지를 정지 영상으로 변환"""
    _check_ffmpeg()
    from moviepy.editor import ImageClip

    clip = ImageClip(image_path, duration=duration)
    clip.write_videofile(output_path, fps=24, codec="libx264",
                         audio=False, logger=None)
    clip.close()
    return output_path


def create_reels_video(
    bg_video: str,
    overlay_img: str,
    audio: str,
    output_path: str = None,
) -> str:
    """
    Instagram Reels용 1080x1920 영상 합성.
    - 배경 영상을 1080x1920으로 crop/resize
    - 상단에 헤더 오버레이 합성
    - TTS 오디오 합성
    - bg_video가 이미지(.jpg/.jpeg/.png)면 5초 정지 영상으로 변환 후 처리

    Args:
        bg_video: 배경 영상 또는 이미지 경로
        overlay_img: 헤더 오버레이 PNG 경로
        audio: TTS mp3 파일 경로
        output_path: 출력 경로 (None이면 output/reels_final.mp4)

    Returns:
        str: 생성된 mp4 파일 경로
    """
    from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip

    if output_path is None:
        output_path = str(OUTPUT_DIR / "reels_final.mp4")

    if DEMO_MODE:
        logger.info("[DEMO MODE] 영상 합성 건너뜀")
        Path(output_path).touch()
        return output_path

    logger.info("Reels 영상 합성 시작...")
    _check_ffmpeg()

    bg_path = Path(bg_video)
    tmp_video_path = str(OUTPUT_DIR / "_tmp_bg.mp4")

    # 이미지 → 정지 영상 변환
    if bg_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        logger.info("배경이 이미지. 5초 정지 영상으로 변환...")
        _image_to_video(str(bg_path), duration=5, output_path=tmp_video_path)
        bg_video = tmp_video_path

    # 배경 영상 로드 및 리사이즈
    try:
        bg_clip = VideoFileClip(bg_video)
    except Exception as e:
        logger.error(f"배경 영상 로드 실패: {e}")
        # 검정 영상으로 대체
        from moviepy.editor import ColorClip
        bg_clip = ColorClip(size=REELS_SIZE, color=COLOR_BG_DARK, duration=30)

    # 오디오 길이에 맞추기
    try:
        audio_clip = AudioFileClip(audio)
        audio_duration = audio_clip.duration
    except Exception:
        audio_clip = None
        audio_duration = bg_clip.duration or 30

    # 배경 영상을 1080x1920으로 crop/resize
    target_w, target_h = REELS_SIZE
    bg_aspect = bg_clip.w / bg_clip.h
    target_aspect = target_w / target_h

    if bg_aspect > target_aspect:
        # 영상이 더 넓음 → 높이 기준 resize 후 좌우 crop
        new_h = target_h
        new_w = int(new_h * bg_aspect)
    else:
        # 영상이 더 좁음 → 너비 기준 resize 후 상하 crop
        new_w = target_w
        new_h = int(new_w / bg_aspect)

    bg_clip = bg_clip.resize((new_w, new_h))
    x_crop = (new_w - target_w) // 2
    y_crop = (new_h - target_h) // 2
    bg_clip = bg_clip.crop(x1=x_crop, y1=y_crop,
                           x2=x_crop + target_w, y2=y_crop + target_h)

    # 오디오 길이에 맞게 루프/트리밍
    if bg_clip.duration < audio_duration:
        from moviepy.editor import vfx
        loops_needed = int(audio_duration / bg_clip.duration) + 1
        from moviepy.editor import concatenate_videoclips
        bg_clip = concatenate_videoclips([bg_clip] * loops_needed)
    bg_clip = bg_clip.subclip(0, audio_duration)

    # 오버레이 합성
    clips = [bg_clip]
    if Path(overlay_img).exists() and Path(overlay_img).stat().st_size > 0:
        overlay_clip = ImageClip(overlay_img, duration=audio_duration).set_position(("center", 0))
        clips.append(overlay_clip)

    final = CompositeVideoClip(clips, size=REELS_SIZE)

    # 오디오 합성
    if audio_clip is not None:
        final = final.set_audio(audio_clip)

    try:
        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
    except Exception as e:
        raise RuntimeError(
            f"FFmpeg 영상 합성 실패: {e}\n"
            "확인사항:\n"
            "  1. pip install imageio-ffmpeg 설치 여부\n"
            "  2. 배경 영상/이미지 파일이 유효한지\n"
            "  3. output/ 폴더 쓰기 권한"
        ) from e
    finally:
        final.close()
        bg_clip.close()
        if audio_clip:
            audio_clip.close()

    logger.success(f"Reels 영상 저장: {output_path}")
    return output_path


def create_cardnews(slides: list[str], output_dir: str = None) -> list[str]:
    """
    카드뉴스 1080x1080 PNG 5장 생성.
    - 배경: 다크 그라디언트 (#1a1a2e → #16213e)
    - 슬라이드 번호, 본문 텍스트 중앙 배치
    - 인스타그램 레드 강조 포인트

    Args:
        slides: 슬라이드 텍스트 리스트 (5개 권장)
        output_dir: 저장 디렉토리 (None이면 output/)

    Returns:
        list[str]: 생성된 png 파일 경로 리스트
    """
    from PIL import Image, ImageDraw

    if output_dir is None:
        output_dir = str(OUTPUT_DIR)

    Path(output_dir).mkdir(exist_ok=True)
    output_paths = []

    if DEMO_MODE:
        logger.info("[DEMO MODE] 카드뉴스 생성 건너뜀")
        for i in range(1, 6):
            path = str(Path(output_dir) / f"cardnews_{i}.png")
            img = Image.new("RGB", CARD_SIZE, COLOR_PANEL)
            img.save(path)
            output_paths.append(path)
        return output_paths

    logger.info(f"카드뉴스 {len(slides)}장 생성 중...")

    for idx, slide_text in enumerate(slides[:5], start=1):
        img = Image.new("RGB", CARD_SIZE, COLOR_BG_DARK)
        draw = ImageDraw.Draw(img)

        # 다크 그라디언트 효과 (상단 #1a1a2e → 하단 #16213e)
        for y in range(CARD_SIZE[1]):
            ratio = y / CARD_SIZE[1]
            r = int(26 + (22 - 26) * ratio)
            g = int(26 + (33 - 26) * ratio)
            b = int(46 + (62 - 46) * ratio)
            draw.line([(0, y), (CARD_SIZE[0], y)], fill=(r, g, b))

        # 상단 강조 라인
        draw.rectangle([(0, 0), (CARD_SIZE[0], 8)], fill=COLOR_ACCENT)

        # 슬라이드 번호 (우상단)
        font_num = _get_font(40, bold=True)
        num_text = f"{idx} / 5"
        bbox = draw.textbbox((0, 0), num_text, font=font_num)
        draw.text(
            (CARD_SIZE[0] - (bbox[2] - bbox[0]) - 50, 40),
            num_text,
            font=font_num,
            fill=COLOR_ACCENT,
        )

        # 가운데 구분선
        draw.line([(80, CARD_SIZE[1] // 2 - 80), (CARD_SIZE[0] - 80, CARD_SIZE[1] // 2 - 80)],
                  fill=COLOR_ACCENT, width=2)

        # 본문 텍스트
        font_body = _get_font(52, bold=True)
        _draw_multiline_centered(
            draw,
            slide_text,
            y_center=CARD_SIZE[1] // 2 + 40,
            width=CARD_SIZE[0],
            font=font_body,
            color=COLOR_WHITE,
            line_spacing=16,
        )

        # 하단 브랜드 텍스트
        font_brand = _get_font(28, bold=False)
        brand_bbox = draw.textbbox((0, 0), "@mystery.daily", font=font_brand)
        draw.text(
            (CARD_SIZE[0] - (brand_bbox[2] - brand_bbox[0]) - 50, CARD_SIZE[1] - 70),
            "@mystery.daily",
            font=font_brand,
            fill=COLOR_GRAY,
        )

        output_path = str(Path(output_dir) / f"cardnews_{idx}.png")
        img.save(output_path, "PNG")
        output_paths.append(output_path)
        logger.debug(f"카드뉴스 {idx}장 저장: {output_path}")

    logger.success(f"카드뉴스 {len(output_paths)}장 생성 완료")
    return output_paths
