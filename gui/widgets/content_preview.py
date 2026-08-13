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
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont

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
    - [파일 열기] 버튼 (output 폴더 탐색기)
    """

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

        # 탭 3: 영상 정보
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)
        video_layout.setContentsMargins(8, 8, 8, 8)

        self._video_info = QLabel("파이프라인 실행 후 영상 정보가 표시됩니다.")
        self._video_info.setWordWrap(True)
        self._video_info.setObjectName("subtitle")
        self._video_info.setAlignment(Qt.AlignmentFlag.AlignTop)
        video_layout.addWidget(self._video_info)

        self._open_video_btn = QPushButton("▶ 영상 재생")
        self._open_video_btn.setEnabled(False)
        self._open_video_btn.clicked.connect(self._open_video)
        video_layout.addWidget(self._open_video_btn)
        video_layout.addStretch()

        tabs.addTab(video_tab, "Reels 영상")

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
        else:
            self._video_info.setText("영상 파일이 생성되지 않았거나 데모 모드입니다.")
            self._open_video_btn.setEnabled(False)

    def clear_preview(self):
        """미리보기 초기화"""
        self._headline_label.setText("—")
        self._caption_edit.clear()
        self._tts_edit.clear()
        self._slides_edit.clear()
        self._video_info.setText("파이프라인 실행 후 영상 정보가 표시됩니다.")
        self._open_video_btn.setEnabled(False)
        self._current_result = None

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
