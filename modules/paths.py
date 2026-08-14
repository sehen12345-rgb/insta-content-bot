"""
PyInstaller 패키징 시 경로 해결 유틸리티.
개발 환경과 .exe 실행 환경 모두에서 올바른 경로를 반환한다.
"""

import sys
from pathlib import Path


def get_root() -> Path:
    """프로젝트 루트 경로 반환 (개발 환경 / 패키징 환경 모두 지원)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 패키징 후: _MEIPASS는 압축 해제 임시 폴더,
        # 실제 실행파일(과 .env, output/)은 exe 옆에 있다.
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_bundle_dir() -> Path:
    """번들 내부 리소스 경로 (templates 등) 반환"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


ROOT_DIR = get_root()
BUNDLE_DIR = get_bundle_dir()
OUTPUT_DIR = ROOT_DIR / "output"
TEMPLATES_DIR = BUNDLE_DIR / "templates"

OUTPUT_DIR.mkdir(exist_ok=True)
