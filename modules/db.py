"""SQLite 기반 소재 중복 방지 및 콘텐츠 이력 관리 DB"""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from loguru import logger

DB_PATH = Path(__file__).parent.parent / "output" / "content_history.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """DB 초기화 — 테이블 없으면 생성"""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS source_hashes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                hash        TEXT    NOT NULL UNIQUE,
                source_url  TEXT,
                title       TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS upload_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash     TEXT,
                reels_url       TEXT,
                carousel_url    TEXT,
                caption         TEXT,
                uploaded_at     TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'success'
            );

            CREATE INDEX IF NOT EXISTS idx_source_hashes_hash ON source_hashes(hash);
            CREATE INDEX IF NOT EXISTS idx_upload_history_date ON upload_history(uploaded_at);
        """)
    logger.debug(f"DB 초기화 완료: {DB_PATH}")


def _make_hash(source_text: str) -> str:
    """소재 텍스트의 SHA256 해시 (앞 16자리)"""
    return hashlib.sha256(source_text.strip().encode("utf-8")).hexdigest()[:16]


def is_duplicate(source_text: str) -> bool:
    """소재가 이미 처리된 중복인지 확인"""
    h = _make_hash(source_text)
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM source_hashes WHERE hash = ?", (h,)
        ).fetchone()
    return row is not None


def mark_processed(source_text: str, source_url: str = "", title: str = "") -> str:
    """소재를 처리 완료로 등록하고 해시 반환"""
    h = _make_hash(source_text)
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO source_hashes (hash, source_url, title, created_at) VALUES (?,?,?,?)",
            (h, source_url, title[:200] if title else "", now),
        )
    logger.debug(f"소재 등록: {h} | {title[:40] if title else source_url}")
    return h


def save_upload(
    source_hash: str,
    reels_url: str = "",
    carousel_url: str = "",
    caption: str = "",
    status: str = "success",
):
    """업로드 이력 저장"""
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO upload_history
               (source_hash, reels_url, carousel_url, caption, uploaded_at, status)
               VALUES (?,?,?,?,?,?)""",
            (source_hash, reels_url, carousel_url, caption[:1000], now, status),
        )
    logger.debug(f"업로드 이력 저장: {source_hash} [{status}]")


def get_recent_uploads(limit: int = 20) -> list[dict]:
    """최근 업로드 이력 조회"""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT u.*, s.title, s.source_url
               FROM upload_history u
               LEFT JOIN source_hashes s ON u.source_hash = s.hash
               ORDER BY u.uploaded_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """전체 통계 조회"""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM upload_history").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM upload_history WHERE status='success'"
        ).fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM source_hashes").fetchone()[0]
    return {"total_uploads": total, "success": success, "failed": total - success, "sources": sources}


# 모듈 임포트 시 자동 초기화
init_db()
