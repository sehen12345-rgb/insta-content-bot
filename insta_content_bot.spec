# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec 파일 - insta-content-bot GUI
빌드: pyinstaller insta_content_bot.spec
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'gui_main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # 폰트 / 템플릿
        (str(ROOT / 'templates'), 'templates'),
        # .env (기본값 포함)
        (str(ROOT / '.env'), '.'),
        # GUI 스타일
        (str(ROOT / 'gui' / 'styles'), 'gui/styles'),
    ],
    hiddenimports=[
        # ── 표준 라이브러리 ──
        'sqlite3',
        'hashlib',
        'asyncio',
        'concurrent.futures',
        # ── Anthropic ──
        'anthropic',
        'anthropic._streaming',
        'anthropic._models',
        # ── PyQt6 ──
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        # ── Telegram ──
        'telegram',
        'telegram.ext',
        'telegram._bot',
        'telegram.ext._application',
        # ── Instagrapi ──
        'instagrapi',
        'instagrapi.mixins',
        'instagrapi.mixins.auth',
        'instagrapi.mixins.clip',
        'instagrapi.mixins.album',
        'instagrapi.mixins.photo',
        'instagrapi.mixins.video',
        'instagrapi.exceptions',
        # ── APScheduler ──
        'apscheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.cron',
        'apscheduler.executors.pool',
        'apscheduler.jobstores.memory',
        # ── MoviePy / ImageIO ──
        'moviepy',
        'moviepy.editor',
        'imageio',
        'imageio.plugins.ffmpeg',
        'imageio_ffmpeg',
        # ── Pillow ──
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # ── PRAW ──
        'praw',
        'praw.models',
        'prawcore',
        # ── TTS ──
        'gtts',
        'elevenlabs',
        # ── 기타 ──
        'loguru',
        'dotenv',
        'requests',
        'urllib3',
        'certifi',
        'yt_dlp',
        'httpx',
        'httpcore',
        'h11',
        'anyio',
        'sniffio',
    ],
    hookspath=[str(ROOT / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'distutils',
        'setuptools',
        'pip',
        'notebook',
        'jupyter',
        'matplotlib',
        'scipy',
        'numpy.testing',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='insta-content-bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # GUI 모드 (콘솔창 없음)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 아이콘 있으면 'templates/icon.ico' 로 변경
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='insta-content-bot',
)
