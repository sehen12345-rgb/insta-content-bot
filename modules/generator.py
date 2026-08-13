"""Claude AI 대본 생성 및 재가공 모듈"""

import os
import json
import re
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

DUMMY_CONTENT = {
    "reels_header_quote": "'진실은 항상 낯선 곳에 숨어있다'",
    "reels_header_title": "역사상 가장 미스터리한 실종 사건",
    "instagram_caption": (
        "1978년, 한 파일럿이 하늘에서 사라졌다.\n\n"
        "마지막 교신에서 그는 이렇게 말했다:\n"
        "'거대한 금속 물체가 내 위를 맴돌고 있습니다...'\n\n"
        "그 후로 그는 흔적조차 찾을 수 없었다.\n\n"
        "#미스터리 #미해결사건 #UFO #실종 #오컬트"
    ),
    "cardnews_slides": [
        "1978년 10월 21일\n파일럿 프레데릭 발렌티치\n호주 배스 해협 상공에서 실종",
        "마지막 교신 내용\n'비행기보다 4배 큰 물체가\n나를 따라오고 있습니다'",
        "교신 후 17초간\n정체불명의 금속음이 들렸고\n그 뒤로는 완전한 침묵",
        "호주 정부의 대규모 수색에도\n비행기도, 파일럿도\n단 한 조각도 발견되지 않았다",
        "47년이 지난 지금도\n이 사건은 공식적으로\n미해결 상태로 남아있다",
    ],
    "tts_script": (
        "1978년 10월, 호주의 젊은 파일럿 프레데릭 발렌티치가 배스 해협 상공에서 사라졌습니다. "
        "그의 마지막 교신에는 믿기 어려운 내용이 담겨 있었습니다. "
        "거대한 금속 물체가 자신의 비행기를 따라다닌다는 것이었죠. "
        "17초간 이어진 금속음과 함께 교신은 끊겼고, "
        "이후 어떤 수색에도 그의 흔적은 발견되지 않았습니다. "
        "47년이 지난 지금도, 이 사건의 진실은 아무도 모릅니다."
    ),
    "media_keywords": ["mystery aircraft disappearance", "dark stormy sky", "ocean horizon fog"],
}

SYSTEM_PROMPT = """당신은 한국 인스타그램 미스터리/이슈 계정의 전문 콘텐츠 크리에이터입니다.
주어진 원문 소재를 바탕으로 완전히 새로운 콘텐츠를 생성해야 합니다.

반드시 아래 규칙을 지키세요:
1. 원문과의 유사도가 80% 이하가 되도록 완전히 재구성하세요.
2. 출력은 반드시 유효한 JSON만 반환하세요. 다른 텍스트는 절대 포함하지 마세요.
3. 모든 텍스트는 한국어로 작성하세요. (media_keywords만 영어)
4. 독자의 호기심과 감정을 자극하는 스토리텔링을 사용하세요.
5. 해시태그는 반드시 5개 이상 포함하세요."""

USER_PROMPT_TEMPLATE = """아래 Reddit 소재를 바탕으로 인스타그램 콘텐츠를 생성해주세요.

[원문 소재]
{source_text}

[출처 URL]
{source_url}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "reels_header_quote": "분위기 있는 작은따옴표 강조 문구 (20자 이내)",
  "reels_header_title": "빨간색 두꺼운 강조 헤드라인 (30자 이내, 클릭을 유도하는 강렬한 제목)",
  "instagram_caption": "피드용 본문 (2~3줄 단위로 줄바꿈, 감성적 스토리텔링, 마지막에 해시태그 5개 이상)",
  "cardnews_slides": [
    "슬라이드1: 도입부 (사건/이슈 소개, 2~3줄)",
    "슬라이드2: 핵심 사실 1 (충격적인 세부 내용)",
    "슬라이드3: 핵심 사실 2 (미스터리 심화)",
    "슬라이드4: 미해결/반전 포인트",
    "슬라이드5: 결말 및 현재 상황"
  ],
  "tts_script": "30초 내외 내레이션 대본 (자연스러운 한국어 구어체, 150~200자)",
  "media_keywords": ["영어 키워드1", "영어 키워드2", "영어 키워드3"]
}}"""


def _extract_json(text: str) -> dict:
    """응답 텍스트에서 JSON 추출"""
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()

    # JSON 파싱 시도
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON 블록만 추출 시도
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def generate_content(source_text: str, source_url: str = "") -> dict:
    """
    Claude AI를 사용하여 Reddit 소재를 인스타그램 콘텐츠로 재가공.

    Args:
        source_text: Reddit 게시물 원문 (title + selftext 조합 권장)
        source_url: 원문 출처 URL (선택)

    Returns:
        dict: reels_header_quote, reels_header_title, instagram_caption,
              cardnews_slides, tts_script, media_keywords 포함
    """
    if DEMO_MODE:
        logger.info("[DEMO MODE] 더미 콘텐츠 반환")
        return DUMMY_CONTENT

    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        raise ValueError("ANTHROPIC_API_KEY 환경변수를 설정해주세요.")

    import anthropic

    logger.info("Claude AI 대본 생성 시작...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_text=source_text[:3000],  # 토큰 제한
        source_url=source_url,
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text
        logger.debug(f"Claude 응답 원문:\n{response_text[:500]}...")

        result = _extract_json(response_text)

        # 필수 키 검증
        required_keys = [
            "reels_header_quote",
            "reels_header_title",
            "instagram_caption",
            "cardnews_slides",
            "tts_script",
            "media_keywords",
        ]
        for key in required_keys:
            if key not in result:
                logger.warning(f"응답에 '{key}' 키가 없습니다. 기본값 사용.")
                result[key] = DUMMY_CONTENT.get(key, "")

        # cardnews_slides는 5개로 맞추기
        slides = result.get("cardnews_slides", [])
        while len(slides) < 5:
            slides.append(f"슬라이드 {len(slides)+1}")
        result["cardnews_slides"] = slides[:5]

        logger.success("대본 생성 완료")
        return result

    except Exception as e:
        logger.error(f"대본 생성 실패: {e}")
        raise
