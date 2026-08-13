"""LogWidget - loguru 로그 스트림 실시간 표시 위젯"""

import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
from loguru import logger


# ──────────────────────────────────────────────
# loguru → Qt Signal 브릿지
# ──────────────────────────────────────────────

class _LogSignalEmitter(QObject):
    """loguru sink를 Qt Signal로 연결하는 브릿지"""
    log_received = pyqtSignal(str, str)  # (level, message)

    def write(self, message):
        """loguru sink 콜백"""
        try:
            record = message.record
            level = record["level"].name
            time_str = record["time"].strftime("%H:%M:%S")
            name = record["name"]
            text = record["message"]
            formatted = f"[{time_str}] [{level}] {name} | {text}"
            self.log_received.emit(level, formatted)
        except Exception:
            pass

    def flush(self):
        pass


# 전역 싱크 인스턴스 (앱 전체 공유)
_log_emitter = _LogSignalEmitter()
_sink_id = None


def install_log_sink():
    """loguru에 Qt 싱크를 등록. 앱 시작 시 1회 호출."""
    global _sink_id
    if _sink_id is None:
        _sink_id = logger.add(
            _log_emitter,
            format="{message}",
            level="DEBUG",
            colorize=False,
        )
    return _log_emitter


# ──────────────────────────────────────────────
# 로그 색상 매핑
# ──────────────────────────────────────────────

LEVEL_COLORS = {
    "TRACE":    "#a0a0b8",
    "DEBUG":    "#a0a0b8",
    "INFO":     "#ffffff",
    "SUCCESS":  "#26a69a",
    "WARNING":  "#f9a825",
    "ERROR":    "#e1306c",
    "CRITICAL": "#ff1744",
}

LEVEL_PREFIXES = {
    "TRACE":    "  ",
    "DEBUG":    "  ",
    "INFO":     "  ",
    "SUCCESS":  "✓ ",
    "WARNING":  "⚠ ",
    "ERROR":    "✗ ",
    "CRITICAL": "!! ",
}


class LogWidget(QWidget):
    """
    loguru 로그를 실시간으로 표시하는 PyQt6 위젯.
    - 레벨별 색상 구분
    - 자동 스크롤 (하단 고정)
    - 필터링 (레벨 드롭다운)
    - 로그 초기화 버튼
    - 최대 2000줄 유지 (자동 오래된 로그 제거)
    """

    MAX_LINES = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level_filter = "DEBUG"
        self._auto_scroll = True
        self._log_buffer: list[tuple[str, str]] = []  # (level, text)

        self._setup_ui()
        self._connect_sink()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── 툴바 ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl = QLabel("로그")
        lbl.setObjectName("subtitle")
        toolbar.addWidget(lbl)

        toolbar.addStretch()

        # 레벨 필터
        self._level_combo = QComboBox()
        self._level_combo.addItems(["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"])
        self._level_combo.setCurrentText("DEBUG")
        self._level_combo.setFixedWidth(100)
        self._level_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(QLabel("필터:"))
        toolbar.addWidget(self._level_combo)

        # 자동 스크롤 토글
        self._scroll_btn = QPushButton("자동 스크롤 ON")
        self._scroll_btn.setFixedWidth(120)
        self._scroll_btn.setCheckable(True)
        self._scroll_btn.setChecked(True)
        self._scroll_btn.clicked.connect(self._toggle_auto_scroll)
        toolbar.addWidget(self._scroll_btn)

        # 초기화 버튼
        clear_btn = QPushButton("초기화")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self.clear_logs)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # ── 로그 텍스트 영역 ──
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMaximumBlockCount(self.MAX_LINES)
        self._text_edit.setFont(QFont("Consolas", 11))
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text_edit)

        # 하단 상태
        self._status_label = QLabel("로그 대기 중...")
        self._status_label.setObjectName("subtitle")
        layout.addWidget(self._status_label)

    def _connect_sink(self):
        """loguru 싱크 연결"""
        emitter = install_log_sink()
        emitter.log_received.connect(self._on_log_received)

    def _get_level_priority(self, level: str) -> int:
        priorities = {
            "TRACE": 0, "DEBUG": 1, "INFO": 2,
            "SUCCESS": 3, "WARNING": 4, "ERROR": 5, "CRITICAL": 6,
        }
        return priorities.get(level, 0)

    def _on_log_received(self, level: str, text: str):
        """새 로그 수신 시 호출"""
        self._log_buffer.append((level, text))
        if len(self._log_buffer) > self.MAX_LINES * 2:
            self._log_buffer = self._log_buffer[-self.MAX_LINES:]

        # 필터 적용
        if self._get_level_priority(level) >= self._get_level_priority(self._level_filter):
            self._append_colored_text(level, text)

        self._status_label.setText(f"마지막 로그: {datetime.now().strftime('%H:%M:%S')} — {text[:60]}")

    def _append_colored_text(self, level: str, text: str):
        """색상이 있는 텍스트를 QPlainTextEdit에 추가"""
        color_hex = LEVEL_COLORS.get(level, "#ffffff")
        prefix = LEVEL_PREFIXES.get(level, "")

        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        cursor.insertText(prefix + text + "\n", fmt)

        if self._auto_scroll:
            self._text_edit.setTextCursor(cursor)
            self._text_edit.ensureCursorVisible()

    def _on_filter_changed(self, level: str):
        """레벨 필터 변경 시 전체 재렌더링"""
        self._level_filter = level
        self._text_edit.clear()
        min_priority = self._get_level_priority(level)
        for log_level, log_text in self._log_buffer:
            if self._get_level_priority(log_level) >= min_priority:
                self._append_colored_text(log_level, log_text)

    def _toggle_auto_scroll(self, checked: bool):
        self._auto_scroll = checked
        self._scroll_btn.setText("자동 스크롤 ON" if checked else "자동 스크롤 OFF")

    def clear_logs(self):
        """로그 초기화"""
        self._text_edit.clear()
        self._log_buffer.clear()
        self._status_label.setText("로그 초기화됨")

    def append_message(self, level: str, text: str):
        """외부에서 직접 로그를 추가할 때 사용"""
        self._on_log_received(level.upper(), text)
