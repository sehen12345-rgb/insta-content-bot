"""PipelinePanel - 파이프라인 수동 실행 컨트롤 위젯"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFrame,
    QSizePolicy,
    QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class StepIndicator(QLabel):
    """단계 표시 라벨 (대기/진행/완료)"""

    STATES = {
        "pending": ("step_pending", "○"),
        "active":  ("step_active", "◉"),
        "done":    ("step_done", "●"),
    }

    def __init__(self, step_num: int, label: str, parent=None):
        super().__init__(parent)
        self._step_num = step_num
        self._label = label
        self._state = "pending"
        self._update_display()

    def _update_display(self):
        obj_name, symbol = self.STATES[self._state]
        self.setObjectName(obj_name)
        self.setText(f"  {symbol}  {self._step_num}. {self._label}")
        self.setFont(QFont("Segoe UI", 12))
        # 스타일 재적용
        self.style().unpolish(self)
        self.style().polish(self)

    def set_state(self, state: str):
        """state: 'pending' | 'active' | 'done'"""
        self._state = state
        self._update_display()


class PipelinePanel(QWidget):
    """
    파이프라인 수동 실행 컨트롤 패널.

    Signals:
        run_requested(str): 파이프라인 실행 요청 (입력 텍스트)
        trending_requested(): Reddit 트렌딩 수집 요청
    """

    run_requested = pyqtSignal(str)
    trending_requested = pyqtSignal()
    scheduler_start_requested = pyqtSignal(int, int)   # (hour, minute)
    scheduler_stop_requested = pyqtSignal()
    scheduler_run_now_requested = pyqtSignal()

    STEPS = [
        "Reddit 스크래핑",
        "Claude 대본 생성",
        "TTS & 미디어 다운로드",
        "영상/카드뉴스 합성",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._step_labels: list[StepIndicator] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ── 제목 ──
        title = QLabel("파이프라인 제어")
        title.setObjectName("subtitle")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)

        self._add_separator(layout)

        # ── 입력 필드 ──
        input_label = QLabel("소재 텍스트 또는 URL 입력:")
        input_label.setObjectName("subtitle")
        layout.addWidget(input_label)

        self._input_field = QTextEdit()
        self._input_field.setPlaceholderText(
            "Reddit 링크, 뉴스 기사 URL, 또는 소재 텍스트를 직접 붙여넣으세요.\n\n"
            "예시:\n"
            "https://www.reddit.com/r/UnsolvedMysteries/...\n"
            "또는 텍스트 직접 입력"
        )
        self._input_field.setFixedHeight(120)
        layout.addWidget(self._input_field)

        # ── 버튼 영역 ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._trending_btn = QPushButton("Reddit 트렌딩 가져오기")
        self._trending_btn.setObjectName("success")
        self._trending_btn.clicked.connect(self._on_trending_clicked)
        btn_layout.addWidget(self._trending_btn)

        self._run_btn = QPushButton("파이프라인 실행")
        self._run_btn.setObjectName("primary")
        self._run_btn.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self._run_btn)

        layout.addLayout(btn_layout)

        self._add_separator(layout)

        # ── 진행 단계 표시 ──
        steps_label = QLabel("진행 단계")
        steps_label.setObjectName("subtitle")
        steps_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(steps_label)

        for i, step_name in enumerate(self.STEPS, start=1):
            indicator = StepIndicator(i, step_name)
            self._step_labels.append(indicator)
            layout.addWidget(indicator)

        # ── 상태 텍스트 ──
        self._add_separator(layout)
        self._status_label = QLabel("대기 중")
        self._status_label.setObjectName("subtitle")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._add_separator(layout)

        # ── 스케줄러 섹션 ──
        sched_title = QLabel("자동 스케줄러")
        sched_title.setObjectName("subtitle")
        sched_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(sched_title)

        # 시각 설정
        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_row.addWidget(QLabel("실행 시각:"))

        self._hour_spin = QSpinBox()
        self._hour_spin.setRange(0, 23)
        self._hour_spin.setValue(9)
        self._hour_spin.setSuffix("시")
        self._hour_spin.setFixedWidth(65)
        time_row.addWidget(self._hour_spin)

        self._minute_spin = QSpinBox()
        self._minute_spin.setRange(0, 59)
        self._minute_spin.setValue(0)
        self._minute_spin.setSuffix("분")
        self._minute_spin.setFixedWidth(65)
        time_row.addWidget(self._minute_spin)
        time_row.addStretch()
        layout.addLayout(time_row)

        # 스케줄러 버튼 행
        sched_btn_row = QHBoxLayout()
        sched_btn_row.setSpacing(6)

        self._sched_toggle_btn = QPushButton("스케줄러 시작")
        self._sched_toggle_btn.setObjectName("success")
        self._sched_toggle_btn.clicked.connect(self._on_sched_toggle)
        sched_btn_row.addWidget(self._sched_toggle_btn)

        self._sched_now_btn = QPushButton("지금 실행")
        self._sched_now_btn.clicked.connect(self.scheduler_run_now_requested.emit)
        sched_btn_row.addWidget(self._sched_now_btn)
        layout.addLayout(sched_btn_row)

        # 다음 실행 예정 라벨
        self._next_run_label = QLabel("다음 실행: —")
        self._next_run_label.setObjectName("subtitle")
        self._next_run_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._next_run_label)

        self._scheduler_running = False

        layout.addStretch()

    def _add_separator(self, layout: QVBoxLayout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        layout.addWidget(line)

    def _on_trending_clicked(self):
        self.set_status("Reddit 트렌딩 소재 수집 중...")
        self.trending_requested.emit()

    def _on_sched_toggle(self):
        if not self._scheduler_running:
            h = self._hour_spin.value()
            m = self._minute_spin.value()
            self.scheduler_start_requested.emit(h, m)
        else:
            self.scheduler_stop_requested.emit()

    def _on_run_clicked(self):
        text = self._input_field.toPlainText().strip()
        if not text:
            self.set_status("소재를 입력해주세요.")
            return
        self.run_requested.emit(text)

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────

    def set_step_state(self, step_index: int, state: str):
        """
        특정 단계 상태 변경.
        step_index: 0-based (0=스크래핑, 1=대본, 2=미디어, 3=합성)
        state: 'pending' | 'active' | 'done'
        """
        if 0 <= step_index < len(self._step_labels):
            self._step_labels[step_index].set_state(state)

    def reset_steps(self):
        """모든 단계를 pending으로 초기화"""
        for label in self._step_labels:
            label.set_state("pending")

    def set_status(self, text: str):
        """하단 상태 텍스트 갱신"""
        self._status_label.setText(text)

    def set_running(self, running: bool):
        """실행 중 버튼 비활성화"""
        self._run_btn.setEnabled(not running)
        self._trending_btn.setEnabled(not running)
        if running:
            self._run_btn.setText("실행 중...")
        else:
            self._run_btn.setText("파이프라인 실행")

    def set_trending_posts(self, posts: list[dict]):
        """트렌딩 게시물을 입력 필드에 채워넣기 (첫 번째 항목)"""
        if posts:
            post = posts[0]
            text = f"{post.get('title', '')}\n\n{post.get('selftext', '')}"
            self._input_field.setPlainText(text.strip())
            self.set_status(f"트렌딩 소재 {len(posts)}개 수집 완료. 원하는 소재로 수정 후 실행하세요.")

    def set_scheduler_running(self, running: bool, next_run: str = ""):
        """스케줄러 상태 반영"""
        self._scheduler_running = running
        if running:
            self._sched_toggle_btn.setText("스케줄러 중지")
            self._sched_toggle_btn.setObjectName("danger")
            self._next_run_label.setText(f"다음 실행: {next_run}" if next_run else "다음 실행: 계산 중...")
        else:
            self._sched_toggle_btn.setText("스케줄러 시작")
            self._sched_toggle_btn.setObjectName("success")
            self._next_run_label.setText("다음 실행: —")
        self._sched_toggle_btn.style().unpolish(self._sched_toggle_btn)
        self._sched_toggle_btn.style().polish(self._sched_toggle_btn)
