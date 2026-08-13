"""PyQt6 메인 윈도우 - 파이프라인 모니터링 패널"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStatusBar,
    QProgressBar,
    QFrame,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from gui.widgets.pipeline_panel import PipelinePanel
from gui.widgets.content_preview import ContentPreview
from gui.widgets.log_widget import LogWidget
from gui.workers import BotWorker, PipelineWorker, TrendingWorker
from loguru import logger


class MainWindow(QMainWindow):
    """
    인스타그램 콘텐츠 봇 모니터링 메인 윈도우.

    레이아웃:
    ┌─────────────────────────────────────────────────┐
    │ 헤더: 타이틀 + 봇 시작/중지 버튼                  │
    ├───────────────────┬─────────────────────────────┤
    │  PipelinePanel    │     ContentPreview           │
    │  (좌측 300px)      │     (중앙, flex)             │
    ├───────────────────┴─────────────────────────────┤
    │  LogWidget (하단 200px)                          │
    ├─────────────────────────────────────────────────┤
    │  상태바                                          │
    └─────────────────────────────────────────────────┘
    """

    APP_TITLE = "insta-content-bot | 인스타그램 자동 콘텐츠 생성"
    MIN_WIDTH = 1100
    MIN_HEIGHT = 750

    def __init__(self):
        super().__init__()
        self._bot_worker: BotWorker | None = None
        self._pipeline_worker: PipelineWorker | None = None
        self._trending_worker: TrendingWorker | None = None
        self._bot_running = False

        self._setup_window()
        self._setup_ui()
        self._connect_signals()

        logger.info("MainWindow 초기화 완료")

    def _setup_window(self):
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(QSize(self.MIN_WIDTH, self.MIN_HEIGHT))
        self.resize(1280, 820)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 헤더 ──
        header = self._build_header()
        main_layout.addWidget(header)

        # 진행바
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        main_layout.addWidget(self._progress_bar)

        # ── 콘텐츠 영역 ──
        # 수직 스플리터 (상단 패널 / 하단 로그)
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setChildrenCollapsible(False)

        # 수평 스플리터 (파이프라인 패널 / 미리보기)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setChildrenCollapsible(False)

        # 좌측: PipelinePanel
        self._pipeline_panel = PipelinePanel()
        self._pipeline_panel.setMinimumWidth(280)
        self._pipeline_panel.setMaximumWidth(400)
        h_splitter.addWidget(self._pipeline_panel)

        # 중앙: ContentPreview
        self._content_preview = ContentPreview()
        h_splitter.addWidget(self._content_preview)
        h_splitter.setSizes([300, 900])

        v_splitter.addWidget(h_splitter)

        # 하단: LogWidget
        self._log_widget = LogWidget()
        self._log_widget.setMinimumHeight(160)
        v_splitter.addWidget(self._log_widget)
        v_splitter.setSizes([520, 200])

        main_layout.addWidget(v_splitter)

        # ── 상태바 ──
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("준비됨")

    def _build_header(self) -> QWidget:
        """상단 헤더 위젯 생성"""
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(60)
        header.setStyleSheet(
            "QWidget#header { background-color: #1a1a2e; border-bottom: 2px solid #e1306c; }"
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)

        # 타이틀
        title = QLabel("insta-content-bot")
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Instagram 자동 콘텐츠 생성 파이프라인")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Segoe UI", 11))
        layout.addWidget(subtitle)

        layout.addStretch()

        # 봇 상태 표시
        self._bot_status_label = QLabel("봇: 중지됨")
        self._bot_status_label.setObjectName("subtitle")
        self._bot_status_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self._bot_status_label)

        # 봇 시작/중지 버튼
        self._bot_btn = QPushButton("텔레그램 봇 시작")
        self._bot_btn.setObjectName("success")
        self._bot_btn.setFixedWidth(150)
        self._bot_btn.clicked.connect(self._toggle_bot)
        layout.addWidget(self._bot_btn)

        return header

    def _connect_signals(self):
        """PipelinePanel 시그널 연결"""
        self._pipeline_panel.run_requested.connect(self._on_run_requested)
        self._pipeline_panel.trending_requested.connect(self._on_trending_requested)

    # ──────────────────────────────────────────────
    # 텔레그램 봇 제어
    # ──────────────────────────────────────────────

    def _toggle_bot(self):
        if self._bot_running:
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        if self._bot_worker and self._bot_worker.isRunning():
            return

        self._bot_worker = BotWorker()
        self._bot_worker.status_changed.connect(self._on_bot_status)
        self._bot_worker.error_occurred.connect(self._on_bot_error)
        self._bot_worker.start()

        self._bot_running = True
        self._bot_btn.setText("텔레그램 봇 중지")
        self._bot_btn.setObjectName("danger")
        self._bot_btn.style().unpolish(self._bot_btn)
        self._bot_btn.style().polish(self._bot_btn)
        logger.info("텔레그램 봇 시작 요청")

    def _stop_bot(self):
        if self._bot_worker:
            self._bot_worker.stop()
            self._bot_worker.wait(3000)

        self._bot_running = False
        self._bot_btn.setText("텔레그램 봇 시작")
        self._bot_btn.setObjectName("success")
        self._bot_btn.style().unpolish(self._bot_btn)
        self._bot_btn.style().polish(self._bot_btn)
        self._bot_status_label.setText("봇: 중지됨")
        logger.info("텔레그램 봇 중지 요청")

    def _on_bot_status(self, msg: str):
        self._bot_status_label.setText(f"봇: {msg}")
        self._status_bar.showMessage(f"[봇] {msg}")
        logger.info(f"봇 상태: {msg}")

    def _on_bot_error(self, msg: str):
        self._bot_status_label.setText("봇: 오류")
        self._status_bar.showMessage(f"[봇 오류] {msg}")
        self._bot_running = False
        logger.error(f"봇 오류: {msg}")

    # ──────────────────────────────────────────────
    # 파이프라인 실행
    # ──────────────────────────────────────────────

    def _on_run_requested(self, text: str):
        """PipelinePanel에서 실행 요청"""
        if self._pipeline_worker and self._pipeline_worker.isRunning():
            logger.warning("파이프라인이 이미 실행 중입니다.")
            return

        source_url = ""
        if text.startswith("http://") or text.startswith("https://"):
            source_url = text

        self._pipeline_panel.set_running(True)
        self._pipeline_panel.reset_steps()
        self._content_preview.clear_preview()
        self._progress_bar.setValue(0)
        self._progress_bar.show()

        self._pipeline_worker = PipelineWorker(source_text=text, source_url=source_url)
        self._pipeline_worker.status_changed.connect(self._on_pipeline_status)
        self._pipeline_worker.progress_updated.connect(self._progress_bar.setValue)
        self._pipeline_worker.pipeline_completed.connect(self._on_pipeline_completed)
        self._pipeline_worker.error_occurred.connect(self._on_pipeline_error)
        self._pipeline_worker.step_changed.connect(self._pipeline_panel.set_step_state)
        self._pipeline_worker.start()

        logger.info(f"파이프라인 시작: {text[:60]}")

    def _on_trending_requested(self):
        """Reddit 트렌딩 수집"""
        if self._trending_worker and self._trending_worker.isRunning():
            return

        self._trending_worker = TrendingWorker()
        self._trending_worker.posts_fetched.connect(self._on_trending_fetched)
        self._trending_worker.error_occurred.connect(self._on_pipeline_error)
        self._trending_worker.start()
        self._pipeline_panel.set_status("Reddit 수집 중...")

    def _on_trending_fetched(self, posts: list):
        self._pipeline_panel.set_trending_posts(posts)
        logger.success(f"Reddit 트렌딩 {len(posts)}개 수집 완료")

    def _on_pipeline_status(self, msg: str):
        self._pipeline_panel.set_status(msg)
        self._status_bar.showMessage(f"[파이프라인] {msg}")

    def _on_pipeline_completed(self, result: dict):
        self._content_preview.update_content(result)
        self._pipeline_panel.set_running(False)
        self._pipeline_panel.set_status("완료!")
        self._progress_bar.hide()
        self._status_bar.showMessage("파이프라인 완료 — output/ 폴더에서 결과물을 확인하세요.")
        logger.success("파이프라인 완료")

    def _on_pipeline_error(self, msg: str):
        self._pipeline_panel.set_running(False)
        self._pipeline_panel.set_status(f"오류: {msg}")
        self._progress_bar.hide()
        self._status_bar.showMessage(f"[오류] {msg}")
        logger.error(f"파이프라인 오류: {msg}")

    # ──────────────────────────────────────────────
    # 종료 처리
    # ──────────────────────────────────────────────

    def closeEvent(self, event):
        """앱 종료 시 워커 정리"""
        logger.info("앱 종료 처리 중...")

        if self._bot_worker and self._bot_worker.isRunning():
            self._bot_worker.stop()
            self._bot_worker.wait(3000)

        if self._pipeline_worker and self._pipeline_worker.isRunning():
            self._pipeline_worker.terminate()
            self._pipeline_worker.wait(2000)

        if self._trending_worker and self._trending_worker.isRunning():
            self._trending_worker.terminate()
            self._trending_worker.wait(1000)

        event.accept()
