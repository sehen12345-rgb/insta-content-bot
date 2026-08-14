"""
gui_main.py - PyQt6 GUI 런처
인스타그램 콘텐츠 자동 생성 봇 데스크톱 모니터링 패널
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from loguru import logger

from modules.paths import OUTPUT_DIR
from gui.main_window import MainWindow
from gui.styles.theme import apply_theme


def main():
    # ── High DPI 지원 ──
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("insta-content-bot")
    app.setApplicationDisplayName("insta-content-bot")
    app.setOrganizationName("insta-content-bot")

    # ── 다크 테마 적용 ──
    apply_theme(app)

    # ── loguru 기본 설정 ──
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}",
        level="DEBUG",
        colorize=True,
    )
    logger.add(
        str(OUTPUT_DIR / "bot.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    logger.info("insta-content-bot GUI 시작")

    # ── 메인 윈도우 실행 ──
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
