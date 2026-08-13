"""Reddit 소재 자동 수집 모듈"""

import os
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

SUBREDDITS = ["UnsolvedMysteries", "Damnthatsinteresting"]
LIMIT = 5

DUMMY_POSTS = [
    {
        "title": "[DEMO] The Disappearance of Frederick Valentich",
        "selftext": (
            "In 1978, pilot Frederick Valentich disappeared over Bass Strait, Australia. "
            "His last radio transmission described a large metallic craft hovering above him. "
            "Neither he nor his plane were ever found. The case remains officially unsolved."
        ),
        "url": "https://www.reddit.com/r/UnsolvedMysteries/comments/demo1",
        "score": 12500,
        "subreddit": "UnsolvedMysteries",
    },
    {
        "title": "[DEMO] The Dyatlov Pass Incident - New Evidence",
        "selftext": (
            "Nine experienced hikers died under mysterious circumstances in the Ural Mountains in 1959. "
            "Their tent was ripped from the inside and bodies found scattered in extreme cold. "
            "Recent studies suggest an avalanche, but many details remain unexplained."
        ),
        "url": "https://www.reddit.com/r/UnsolvedMysteries/comments/demo2",
        "score": 9800,
        "subreddit": "UnsolvedMysteries",
    },
    {
        "title": "[DEMO] Scientist discovers bioluminescent deep-sea creature never seen before",
        "selftext": (
            "A marine biologist captured footage of a never-before-documented creature at 4,000 meters depth. "
            "The organism appears to communicate using patterns of light. "
            "It does not match any known species classification."
        ),
        "url": "https://www.reddit.com/r/Damnthatsinteresting/comments/demo3",
        "score": 7600,
        "subreddit": "Damnthatsinteresting",
    },
    {
        "title": "[DEMO] Ancient Roman concrete found to be self-healing after 2000 years",
        "selftext": (
            "Researchers discovered that Roman seawater concrete actually grows stronger over time. "
            "Seawater filters through the concrete creating new minerals that seal cracks automatically. "
            "Modern concrete deteriorates in decades; Roman structures survive millennia."
        ),
        "url": "https://www.reddit.com/r/Damnthatsinteresting/comments/demo4",
        "score": 5400,
        "subreddit": "Damnthatsinteresting",
    },
    {
        "title": "[DEMO] The Voynich Manuscript - 600 year old book no one can read",
        "selftext": (
            "The Voynich Manuscript is a 240-page illustrated codex written in an unknown script. "
            "Carbon-dated to the early 15th century, the text has resisted every attempt at decryption. "
            "It contains detailed botanical, astronomical, and biological illustrations of unknown subjects."
        ),
        "url": "https://www.reddit.com/r/UnsolvedMysteries/comments/demo5",
        "score": 4200,
        "subreddit": "UnsolvedMysteries",
    },
]


def _fetch_via_praw() -> list[dict]:
    """PRAW 라이브러리를 사용해 Reddit에서 게시물 수집"""
    import praw

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "insta-content-bot/1.0")

    if not client_id or not client_secret:
        raise ValueError("REDDIT_CLIENT_ID 또는 REDDIT_CLIENT_SECRET 환경변수가 없습니다.")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    posts = []
    for sub_name in SUBREDDITS:
        subreddit = reddit.subreddit(sub_name)
        for submission in subreddit.top(time_filter="day", limit=LIMIT):
            posts.append(
                {
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "url": submission.url,
                    "score": submission.score,
                    "subreddit": sub_name,
                }
            )
    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts[:LIMIT]


def _fetch_via_json_api() -> list[dict]:
    """Reddit JSON API를 직접 호출하는 fallback 방식"""
    headers = {"User-Agent": os.getenv("REDDIT_USER_AGENT", "insta-content-bot/1.0")}
    posts = []

    for sub_name in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub_name}/top.json?t=day&limit={LIMIT}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                item = child.get("data", {})
                posts.append(
                    {
                        "title": item.get("title", ""),
                        "selftext": item.get("selftext", ""),
                        "url": item.get("url", ""),
                        "score": item.get("score", 0),
                        "subreddit": sub_name,
                    }
                )
        except Exception as e:
            logger.warning(f"Reddit JSON API 호출 실패 ({sub_name}): {e}")

    posts.sort(key=lambda x: x["score"], reverse=True)
    return posts[:LIMIT]


def get_trending_posts() -> list[dict]:
    """
    Reddit에서 24시간 내 상위 게시물 수집.

    Returns:
        list[dict]: 각 항목은 title, selftext, url, score, subreddit 포함.
    """
    if DEMO_MODE:
        logger.info("[DEMO MODE] 더미 Reddit 게시물 반환")
        return DUMMY_POSTS

    logger.info("Reddit 트렌딩 게시물 수집 시작...")

    # 1차: PRAW 시도
    try:
        posts = _fetch_via_praw()
        logger.success(f"PRAW로 {len(posts)}개 게시물 수집 완료")
        return posts
    except Exception as e:
        logger.warning(f"PRAW 수집 실패, JSON API로 fallback: {e}")

    # 2차: JSON API fallback
    try:
        posts = _fetch_via_json_api()
        logger.success(f"JSON API로 {len(posts)}개 게시물 수집 완료")
        return posts
    except Exception as e:
        logger.error(f"Reddit 수집 완전 실패: {e}")
        return []
