"""
PyInstaller 빌드 자동화 스크립트.
실행: python build.py
결과: dist/insta-content-bot/ 폴더 (실행파일 포함)
"""

import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "insta_content_bot.spec"
OUTPUT_DIR = ROOT / "output"


def clean():
    """이전 빌드 결과 삭제"""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"삭제: {d}")


def ensure_output_dir():
    """output/ 디렉토리 생성 (빌드 후 복사용)"""
    OUTPUT_DIR.mkdir(exist_ok=True)


def build():
    """PyInstaller 빌드 실행"""
    print("=" * 50)
    print("insta-content-bot 빌드 시작")
    print("=" * 50)

    clean()
    ensure_output_dir()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]

    print(f"\n실행: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode != 0:
        print("\n빌드 실패. 위 오류를 확인하세요.")
        sys.exit(1)

    _post_build()


def _post_build():
    """빌드 후처리: output 디렉토리 복사 + 안내 메시지"""
    app_dir = DIST_DIR / "insta-content-bot"
    if not app_dir.exists():
        print("경고: 빌드 결과물을 찾을 수 없습니다.")
        return

    # output/ 디렉토리를 실행파일 옆에 생성
    (app_dir / "output").mkdir(exist_ok=True)

    # .env 파일이 있으면 복사 (없으면 빈 파일 생성)
    env_src = ROOT / ".env"
    env_dst = app_dir / ".env"
    if env_src.exists() and not env_dst.exists():
        shutil.copy2(env_src, env_dst)
        print(f".env 복사: {env_dst}")

    exe_path = app_dir / "insta-content-bot.exe"
    print("\n" + "=" * 50)
    print("빌드 완료!")
    print(f"실행파일: {exe_path}")
    print(f"배포 폴더: {app_dir}")
    print("\n배포 시 포함할 항목:")
    print("  dist/insta-content-bot/ 폴더 전체")
    print("  (폴더 째로 압축해서 배포하세요)")
    print("\n실행 전 .env 파일에 API 키를 입력하세요.")
    print("=" * 50)


if __name__ == "__main__":
    build()
