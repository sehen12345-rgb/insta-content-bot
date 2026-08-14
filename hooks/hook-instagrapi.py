"""PyInstaller hook: instagrapi 패키지 전체 수집"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('instagrapi')
