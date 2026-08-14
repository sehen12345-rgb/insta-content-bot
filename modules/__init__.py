# modules package
from modules.scraper import get_trending_posts
from modules.generator import generate_content
from modules.media import generate_tts, download_background
from modules.editor import create_header_overlay, create_reels_video, create_cardnews
from modules.uploader import upload_all, upload_reels, upload_carousel, verify_credentials
from modules.db import is_duplicate, mark_processed, save_upload, get_recent_uploads, get_stats
from modules.scheduler import get_scheduler

__all__ = [
    "get_trending_posts",
    "generate_content",
    "generate_tts",
    "download_background",
    "create_header_overlay",
    "create_reels_video",
    "create_cardnews",
    "upload_all",
    "upload_reels",
    "upload_carousel",
    "verify_credentials",
    "is_duplicate",
    "mark_processed",
    "save_upload",
    "get_recent_uploads",
    "get_stats",
    "get_scheduler",
]
