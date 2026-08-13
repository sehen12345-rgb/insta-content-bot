"""PyQt6 다크 테마 QSS - 인스타그램 감성"""

DARK_THEME_QSS = """
/* ============================================================
   insta-content-bot Dark Theme
   배경: #0f0f1a | 패널: #1a1a2e | 강조: #e1306c
   성공: #26a69a  | 텍스트: #ffffff, #a0a0b8
   ============================================================ */

QMainWindow, QDialog {
    background-color: #0f0f1a;
    color: #ffffff;
}

QWidget {
    background-color: #0f0f1a;
    color: #ffffff;
    font-family: 'Segoe UI', 'Nanum Gothic', 'Malgun Gothic', sans-serif;
    font-size: 13px;
}

/* ── 패널 / 그룹박스 ── */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px;
    font-weight: bold;
    font-size: 13px;
    color: #a0a0b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #e1306c;
    font-weight: bold;
    font-size: 13px;
    left: 12px;
}

QFrame {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 6px;
}

/* ── 버튼 ── */
QPushButton {
    background-color: #2a2a4e;
    color: #ffffff;
    border: 1px solid #3a3a6e;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #3a3a6e;
    border-color: #e1306c;
    color: #e1306c;
}

QPushButton:pressed {
    background-color: #e1306c;
    color: #ffffff;
    border-color: #e1306c;
}

QPushButton:disabled {
    background-color: #1a1a2e;
    color: #4a4a6a;
    border-color: #2a2a4e;
}

/* 강조 버튼 (primary) */
QPushButton#primary {
    background-color: #e1306c;
    color: #ffffff;
    border: none;
    font-weight: bold;
}

QPushButton#primary:hover {
    background-color: #ff4785;
    color: #ffffff;
}

QPushButton#primary:pressed {
    background-color: #c0245a;
}

/* 성공 버튼 */
QPushButton#success {
    background-color: #26a69a;
    color: #ffffff;
    border: none;
    font-weight: bold;
}

QPushButton#success:hover {
    background-color: #2ec4b6;
}

/* 위험 버튼 */
QPushButton#danger {
    background-color: #c62828;
    color: #ffffff;
    border: none;
}

QPushButton#danger:hover {
    background-color: #ef5350;
}

/* ── 입력 필드 ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #12122a;
    color: #ffffff;
    border: 1px solid #2a2a4e;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #e1306c;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #e1306c;
    outline: none;
}

QLineEdit::placeholder, QTextEdit::placeholder {
    color: #4a4a6a;
}

/* ── 라벨 ── */
QLabel {
    background-color: transparent;
    color: #ffffff;
    font-size: 13px;
}

QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #e1306c;
    letter-spacing: 1px;
}

QLabel#subtitle {
    font-size: 12px;
    color: #a0a0b8;
}

QLabel#step_active {
    color: #e1306c;
    font-weight: bold;
}

QLabel#step_done {
    color: #26a69a;
    font-weight: bold;
}

QLabel#step_pending {
    color: #4a4a6a;
}

/* ── 스크롤바 ── */
QScrollBar:vertical {
    background-color: #0f0f1a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2a2a4e;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #e1306c;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0f0f1a;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2a4e;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #e1306c;
}

/* ── 진행바 ── */
QProgressBar {
    background-color: #12122a;
    border: 1px solid #2a2a4e;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #e1306c;
    border-radius: 4px;
}

/* ── 리스트뷰 ── */
QListWidget, QListView {
    background-color: #12122a;
    border: 1px solid #2a2a4e;
    border-radius: 6px;
    color: #ffffff;
    outline: none;
}

QListWidget::item {
    padding: 6px 12px;
    border-bottom: 1px solid #1a1a2e;
}

QListWidget::item:selected {
    background-color: #e1306c;
    color: #ffffff;
    border-radius: 4px;
}

QListWidget::item:hover {
    background-color: #2a2a4e;
}

/* ── 탭 ── */
QTabWidget::pane {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #12122a;
    color: #a0a0b8;
    padding: 8px 20px;
    border: 1px solid #2a2a4e;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #e1306c;
    border-bottom: 2px solid #e1306c;
}

QTabBar::tab:hover {
    color: #ffffff;
}

/* ── 분리선 ── */
QFrame[frameShape="4"],  /* HLine */
QFrame[frameShape="5"] {  /* VLine */
    color: #2a2a4e;
    background-color: #2a2a4e;
}

/* ── 상태바 ── */
QStatusBar {
    background-color: #1a1a2e;
    color: #a0a0b8;
    border-top: 1px solid #2a2a4e;
    font-size: 12px;
}

/* ── 툴팁 ── */
QToolTip {
    background-color: #2a2a4e;
    color: #ffffff;
    border: 1px solid #e1306c;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ── 콤보박스 ── */
QComboBox {
    background-color: #12122a;
    color: #ffffff;
    border: 1px solid #2a2a4e;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 32px;
}

QComboBox:focus {
    border-color: #e1306c;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    color: #ffffff;
    selection-background-color: #e1306c;
    border: 1px solid #2a2a4e;
}

/* ── 체크박스 ── */
QCheckBox {
    color: #ffffff;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a2a4e;
    border-radius: 3px;
    background-color: #12122a;
}

QCheckBox::indicator:checked {
    background-color: #e1306c;
    border-color: #e1306c;
}
"""


def apply_theme(app):
    """QApplication에 다크 테마 적용"""
    app.setStyleSheet(DARK_THEME_QSS)
