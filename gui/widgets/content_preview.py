"""ContentPreview - 생성된 결과물 미리보기 위젯"""

import os
import subprocess
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


class CardnewsStrip(QWidget):
    """카드뉴스 썸네일 가로 스크롤 스트립"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch()

    def update_images(self, image_paths: list[str]):
        """이미지 경로 리스트로 썸네일 갱신"""
        # 기존 위젯 제거
        while self._layout.count() > 1:  # 마지막 stretch 유지
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, path in enumerate(image_paths):
            p = Path(path)
            frame = QFrame()
            frame.setFixedSize(QSize(120, 120))
            frame.setFrameShape(QFrame.Shape.Box)

            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(2, 2, 2, 2)
            frame_layout.setSpacing(2)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setFixedSize(QSize(110, 90))

            if p.exists() and p.stat().st_size > 0:
                pixmap = QPixmap(str(p))
                if not pixmap.isNull():
                    img_label.setPixmap(
                        pixmap.scaled(
                            110, 90,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                else:
                    img_label.setText("미리보기\n없음")
            else:
                img_label.setText("파일\n없음")

            num_label = QLabel(f"슬라이드 {i+1}")
            num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_label.setObjectName("subtitle")
            num_label.setFont(QFont("Segoe UI", 9))

            frame_layout.addWidget(img_label)
            frame_layout.addWidget(num_label)

            self._layout.insertWidget(self._layout.count() - 1, frame)


class ContentPreview(QWidget):
    """
    생성된 결과물 미리보기 위젯.
    - 캡션 텍스트 표시
    - 카드뉴스 썸네일 미리보기
    - 인스타그램 업로드 버튼
    - 업로드 이력 탭

    Signals:
        upload_requested(str, list, str, str): (reels_path, cardnews_paths, caption, source_hash)
        history_refresh_requested(): 이력 새로고침 요청
    """

    upload_requested = pyqtSignal(str, list, str, str)
    history_refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result: dict | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── 제목 ──
        header = QHBoxLayout()
        title = QLabel("결과물 미리보기")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setObjectName("subtitle")
        header.addWidget(title)
        header.addStretch()

        open_btn = QPushButton("📂 output 폴더 열기")
        open_btn.setFixedWidth(150)
        open_btn.clicked.connect(self._open_output_folder)
        header.addWidget(open_btn)

        layout.addLayout(header)

        # ── 탭 ──
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # 탭 1: 캡션
        caption_tab = QWidget()
        caption_layout = QVBoxLayout(caption_tab)
        caption_layout.setContentsMargins(8, 8, 8, 8)

        caption_layout.addWidget(QLabel("헤드라인:"))
        self._headline_label = QLabel("—")
        self._headline_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._headline_label.setStyleSheet("color: #e1306c;")
        self._headline_label.setWordWrap(True)
        caption_layout.addWidget(self._headline_label)

        caption_layout.addWidget(QLabel("인스타그램 캡션:"))
        self._caption_edit = QTextEdit()
        self._caption_edit.setReadOnly(True)
        self._caption_edit.setPlaceholderText("파이프라인 실행 후 캡션이 여기에 표시됩니다.")
        caption_layout.addWidget(self._caption_edit)

        caption_layout.addWidget(QLabel("TTS 대본:"))
        self._tts_edit = QTextEdit()
        self._tts_edit.setReadOnly(True)
        self._tts_edit.setFixedHeight(80)
        self._tts_edit.setPlaceholderText("TTS 대본이 여기에 표시됩니다.")
        caption_layout.addWidget(self._tts_edit)

        tabs.addTab(caption_tab, "캡션")

        # 탭 2: 카드뉴스 미리보기
        cardnews_tab = QWidget()
        cardnews_layout = QVBoxLayout(cardnews_tab)
        cardnews_layout.setContentsMargins(8, 8, 8, 8)

        cardnews_layout.addWidget(QLabel("카드뉴스 썸네일:"))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(160)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cardnews_strip = CardnewsStrip()
        scroll_area.setWidget(self._cardnews_strip)
        cardnews_layout.addWidget(scroll_area)

        cardnews_layout.addWidget(QLabel("슬라이드 텍스트:"))
        self._slides_edit = QTextEdit()
        self._slides_edit.setReadOnly(True)
        self._slides_edit.setPlaceholderText("슬라이드 텍스트가 여기에 표시됩니다.")
        cardnews_layout.addWidget(self._slides_edit)

        tabs.addTab(cardnews_tab, "카드뉴스")

        # 탭 3: 영상 정보 + 업로드
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)
        video_layout.setContentsMargins(8, 8, 8, 8)
        video_layout.setSpacing(10)

        self._video_info = QLabel("파이프라인 실행 후 영상 정보가 표시됩니다.")
        self._video_info.setWordWrap(True)
        self._video_info.setObjectName("subtitle")
        self._video_info.setAlignment(Qt.AlignmentFlag.AlignTop)
        video_layout.addWidget(self._video_info)

        btn_row = QHBoxLayout()
        self._open_video_btn = QPushButton("▶ 영상 재생")
        self._open_video_btn.setEnabled(False)
        self._open_video_btn.clicked.connect(self._open_video)
        btn_row.addWidget(self._open_video_btn)

        self._upload_btn = QPushButton("인스타그램 업로드")
        self._upload_btn.setObjectName("primary")
        self._upload_btn.setEnabled(False)
        self._upload_btn.clicked.connect(self._on_upload_clicked)
        btn_row.addWidget(self._upload_btn)
        video_layout.addLayout(btn_row)

        # 업로드 상태 라벨
        self._upload_status = QLabel("")
        self._upload_status.setObjectName("subtitle")
        self._upload_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._upload_status.setWordWrap(True)
        video_layout.addWidget(self._upload_status)

        video_layout.addStretch()
        tabs.addTab(video_tab, "Reels 영상")

        # 탭 4: 업로드 이력
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(8, 8, 8, 8)
        history_layout.setSpacing(8)

        # 통계 라벨
        self._stats_label = QLabel("통계: —")
        self._stats_label.setObjectName("subtitle")
        history_layout.addWidget(self._stats_label)

        # 새로고침 버튼
        refresh_btn = QPushButton("이력 새로고침")
        refresh_btn.setFixedWidth(130)
        refresh_btn.clicked.connect(self.history_refresh_requested.emit)
        history_layout.addWidget(refresh_btn)

        # 이력 테이블
        self._history_table = QTableWidget(0, 5)
        self._history_table.setHorizontalHeaderLabels(["업로드 시각", "제목", "상태", "Reels URL", "Carousel URL"])
        self._history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setAlternatingRowColors(True)
        history_layout.addWidget(self._history_table)

        tabs.addTab(history_tab, "업로드 이력")

    # ──────────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────────

    def update_content(self, result: dict):
        """
        파이프라인 결과로 미리보기 갱신.

        Args:
            result: {
                "content": dict (generator 출력),
                "reels_path": str,
                "cardnews_paths": list[str],
                "tts_path": str,
            }
        """
        self._current_result = result
        content = result.get("content", {})

        # 캡션 탭 갱신
        self._headline_label.setText(content.get("reels_header_title", "—"))
        self._caption_edit.setPlainText(content.get("instagram_caption", ""))
        self._tts_edit.setPlainText(content.get("tts_script", ""))

        # 카드뉴스 탭 갱신
        cardnews_paths = result.get("cardnews_paths", [])
        self._cardnews_strip.update_images(cardnews_paths)

        slides_text = "\n\n".join(
            [f"[슬라이드 {i+1}]\n{s}" for i, s in enumerate(content.get("cardnews_slides", []))]
        )
        self._slides_edit.setPlainText(slides_text)

        # 영상 탭 갱신
        reels_path = result.get("reels_path", "")
        p = Path(reels_path)
        if p.exists() and p.stat().st_size > 0:
            size_mb = p.stat().st_size / (1024 * 1024)
            self._video_info.setText(
                f"파일: {p.name}\n"
                f"크기: {size_mb:.1f} MB\n"
                f"경로: {p}"
            )
            self._open_video_btn.setEnabled(True)
            self._upload_btn.setEnabled(True)
            self._upload_status.setText("업로드 버튼을 눌러 인스타그램에 게시하세요.")
        else:
            self._video_info.setText("영상 파일이 생성되지 않았거나 데모 모드입니다.")
            self._open_video_btn.setEnabled(False)
            self._upload_btn.setEnabled(False)

    def clear_preview(self):
        """미리보기 초기화"""
        self._headline_label.setText("—")
        self._caption_edit.clear()
        self._tts_edit.clear()
        self._slides_edit.clear()
        self._video_info.setText("파이프라인 실행 후 영상 정보가 표시됩니다.")
        self._open_video_btn.setEnabled(False)
        self._upload_btn.setEnabled(False)
        self._upload_status.setText("")
        self._current_result = None

    def set_upload_status(self, msg: str, success: bool = False):
        """업로드 상태 메시지 갱신 (MainWindow에서 호출)"""
        self._upload_status.setText(msg)
        if success:
            self._upload_btn.setEnabled(False)
            self._upload_btn.setText("업로드 완료")

    def update_history(self, uploads: list, stats: dict):
        """업로드 이력 및 통계 갱신 (HistoryWorker 결과 수신)"""
        total = stats.get("total_uploads", 0)
        success = stats.get("success", 0)
        sources = stats.get("sources", 0)
        self._stats_label.setText(
            f"총 업로드: {total}건 | 성공: {success}건 | 소재: {sources}건"
        )

        self._history_table.setRowCount(0)
        for row_idx, item in enumerate(uploads):
            self._history_table.insertRow(row_idx)

            uploaded_at = item.get("uploaded_at", "")[:19].replace("T", " ")
            title = item.get("title") or item.get("source_url") or "—"
            status = item.get("status", "—")
            reels_url = item.get("reels_url") or "—"
            carousel_url = item.get("carousel_url") or "—"

            self._history_table.setItem(row_idx, 0, QTableWidgetItem(uploaded_at))
            self._history_table.setItem(row_idx, 1, QTableWidgetItem(title[:60]))
            status_cell = QTableWidgetItem(status)
            if status == "success":
                status_cell.setForeground(QColor("#26a69a"))
            else:
                status_cell.setForeground(QColor("#e1306c"))
            self._history_table.setItem(row_idx, 2, status_cell)
            self._history_table.setItem(row_idx, 3, QTableWidgetItem(reels_url))
            self._history_table.setItem(row_idx, 4, QTableWidgetItem(carousel_url))

    def _open_output_folder(self):
        """output 폴더를 탐색기로 열기"""
        path = OUTPUT_DIR
        path.mkdir(exist_ok=True)
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(path))
            elif system == "Darwin":
                subprocess.run(["open", str(path)], check=True)
            else:
                subprocess.run(["xdg-open", str(path)], check=True)
        except Exception as e:
            pass

    def _on_upload_clicked(self):
        """업로드 버튼 클릭 → 시그널 발송"""
        if self._current_result is None:
            return
        content = self._current_result.get("content", {})
        caption = (
            f"{content.get('reels_header_title', '')}\n\n"
            f"{content.get('instagram_caption', '')}"
        ).strip()
        reels_path = self._current_result.get("reels_path", "")
        cardnews_paths = self._current_result.get("cardnews_paths", [])
        source_hash = self._current_result.get("source_hash", "")

        self._upload_btn.setEnabled(False)
        self._upload_btn.setText("업로드 중...")
        self._upload_status.setText("인스타그램에 업로드 중입니다...")
        self.upload_requested.emit(reels_path, cardnews_paths, caption, source_hash)

    def _open_video(self):
        """생성된 Reels 영상 재생"""
        if self._current_result is None:
            return
        reels_path = self._current_result.get("reels_path", "")
        p = Path(reels_path)
        if p.exists():
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(str(p))
                elif system == "Darwin":
                    subprocess.run(["open", str(p)], check=True)
                else:
                    subprocess.run(["xdg-open", str(p)], check=True)
            except Exception:
                pass
