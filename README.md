# insta-content-bot

인스타그램 미스터리/이슈 계정용 콘텐츠 완전 자동 생성 Python 파이프라인.

Reddit에서 소재를 수집하고, Claude AI로 대본을 재가공한 뒤, TTS 음성과 배경 영상을 합성하여
Reels 영상 + 카드뉴스를 자동 생성합니다. 텔레그램 봇 또는 PyQt6 GUI로 운영할 수 있습니다.

---

## 🔄 Status Tracker

> 마지막 업데이트: 2026-08-16

| 단계 | 모듈 | 상태 | 비고 |
|------|------|------|------|
| 소재 수집 | `modules/scraper.py` | ✅ 완료 | PRAW + JSON API fallback |
| 대본 생성 | `modules/generator.py` | ✅ 완료 | Claude Sonnet 4.6, Strict JSON |
| TTS + 미디어 | `modules/media.py` | ✅ 완료 | gTTS/ElevenLabs + Pexels/yt-dlp |
| 영상 합성 | `modules/editor.py` | ✅ 완료 | Pillow + MoviePy 1.x |
| 텔레그램 봇 | `main.py` | ✅ 완료 | python-telegram-bot v21 async |
| PyQt6 GUI | `gui_main.py` | ✅ 완료 | 모니터링 패널 |
| 환경 점검 | `check_env.py` | ✅ 완료 | API 키 연동 검증 스크립트 |
| 파이프라인 테스트 | `test_pipeline.py` | ✅ 완료 | 버뮤다 삼각지대 테스트 포함 |
| 인스타 자동 업로드 | `modules/uploader.py` | ✅ 완료 | instagrapi, GUI 업로드 버튼 |
| 스케줄링 | `modules/scheduler.py` | ✅ 완료 | APScheduler, GUI 제어 패널 |
| 중복 방지 DB | `modules/db.py` | ✅ 완료 | SQLite, PipelineWorker 연동 |
| 업로드 이력 뷰 | `gui/widgets/content_preview.py` | ✅ 완료 | GUI 이력 탭 + 통계 |

### 최근 변경사항 (2026-08-13)

| 파일 | 변경 내용 |
|------|-----------|
| `requirements.txt` | moviepy 버전을 `<2.0.0`으로 핀 (v2.x는 API 완전 변경), imageio-ffmpeg 추가 |
| `modules/generator.py` | Claude 모델 `claude-sonnet-4-5` → `claude-sonnet-4-6` 업데이트 |
| `check_env.py` | **신규** — API 키 연동 및 패키지 설치 상태 전체 점검 스크립트 |
| `test_pipeline.py` | **신규** — 전체 파이프라인 통합 테스트 (버뮤다 삼각지대 시나리오) |

---

## 🛠 개발환경

| 항목 | 버전/설명 |
|------|-----------|
| Python | 3.11 이상 |
| PyQt6 | 6.7+ (GUI 패널) |
| anthropic | 0.40+ (Claude Sonnet 4.6 대본 생성) |
| praw | 7.7+ (Reddit 소재 수집) |
| python-telegram-bot | 21.0+ (async 텔레그램 봇) |
| moviepy | 1.0.3 이상 2.0.0 미만 (영상 합성) |
| Pillow | 10.0+ (카드뉴스 이미지 생성) |
| gTTS / ElevenLabs | TTS 음성 생성 |
| yt-dlp | 배경 영상 다운로드 fallback |
| FFmpeg | 영상 합성 필수 (시스템 설치) |
| OS | Windows 10/11, macOS, Linux |

---

## 🏗 아키텍처

```
입력 소스
┌────────────────┐    ┌──────────────────────┐
│  Reddit 자동   │    │  텍스트/URL 직접 입력  │
│  트렌딩 수집   │    │  (텔레그램 or GUI)    │
└───────┬────────┘    └──────────┬───────────┘
        │                        │
        └──────────┬─────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 1: 소재 수집           │
    │   modules/scraper.py         │
    │   PRAW → Reddit JSON API     │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 2: Claude 대본 생성   │
    │   modules/generator.py       │
    │   claude-sonnet-4-6          │
    │   원문 유사도 80% 이하 재가공  │
    │   출력: JSON (캡션/슬라이드/  │
    │          TTS/미디어 키워드)   │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 3: TTS + 배경 미디어  │
    │   modules/media.py           │
    │   ElevenLabs → gTTS fallback │
    │   Pexels → yt-dlp fallback   │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 4: 영상/카드뉴스 합성  │
    │   modules/editor.py          │
    │   Pillow + MoviePy 1.x       │
    └──────────────┬───────────────┘
                   ▼
    출력 (output/ 폴더)
    ┌──────────────────────────────┐
    │  reels_final.mp4  (1080x1920)│
    │  cardnews_1~5.png (1080x1080)│
    │  tts_audio.mp3               │
    │  → 텔레그램으로 전송         │
    │  → [승인] → 인스타 업로드    │
    └──────────────────────────────┘
```

### 파일 구조

```
insta-content-bot/
├── .env.example          # 환경 변수 예시
├── .gitignore
├── requirements.txt
├── README.md
├── check_env.py          # ★ 환경 점검 스크립트 (API 키 연동 검증)
├── test_pipeline.py      # ★ 파이프라인 통합 테스트 스크립트
├── main.py               # 텔레그램 봇 + 파이프라인 (asyncio)
├── gui_main.py           # PyQt6 GUI 런처
├── modules/
│   ├── scraper.py        # Reddit 소재 수집
│   ├── generator.py      # Claude AI 대본 생성 (claude-sonnet-4-6)
│   ├── media.py          # TTS + 배경 미디어 다운로드
│   └── editor.py         # Pillow/MoviePy 영상·카드뉴스 합성
├── gui/
│   ├── main_window.py    # 메인 윈도우
│   ├── workers.py        # QThread 워커 (BotWorker, PipelineWorker)
│   ├── styles/
│   │   └── theme.py      # 다크 QSS 테마
│   └── widgets/
│       ├── pipeline_panel.py   # 파이프라인 제어 패널
│       ├── content_preview.py  # 결과물 미리보기
│       └── log_widget.py       # loguru 로그 스트림
├── templates/            # 폰트 파일 (NanumGothicBold.ttf 등)
└── output/               # 생성된 미디어 저장
```

---

## 🎨 디자인 가이드

### PyQt6 GUI 색상 팔레트

| 역할 | 색상 코드 | 설명 |
|------|-----------|------|
| 배경 | `#0f0f1a` | 메인 배경 (가장 어두운 톤) |
| 패널 | `#1a1a2e` | 카드/그룹박스 배경 |
| 강조 | `#e1306c` | 인스타그램 레드/핑크 |
| 성공 | `#26a69a` | 완료/성공 상태 |
| 텍스트 | `#ffffff` | 기본 텍스트 |
| 보조 텍스트 | `#a0a0b8` | 라벨/캡션 |
| 테두리 | `#2a2a4e` | 패널 테두리 |

### 폰트
- GUI: Segoe UI (Windows), Nanum Gothic (한국어)
- 카드뉴스: `templates/NanumGothicBold.ttf` (없으면 PIL 기본 폰트)

### 레이아웃
- 메인 윈도우: 최소 1100x750
- 좌측 PipelinePanel: 280~400px 고정
- 하단 LogWidget: 160px 고정
- Reels 영상: 1080x1920 (세로형)
- 카드뉴스: 1080x1080 (정사각형)

---

## 🚀 실행 방법

### 1. 설치

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# FFmpeg 설치 (영상 합성 필수)
# Windows:  winget install ffmpeg
# macOS:    brew install ffmpeg
# Ubuntu:   sudo apt install ffmpeg
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집기로 열어 API 키 입력
```

### 3. 환경 점검 ← 여기서 시작

```bash
# 패키지/환경변수만 확인 (API 호출 X)
python check_env.py --quick

# 전체 점검 (실제 API 연동 테스트)
python check_env.py
```

### 4. 파이프라인 통합 테스트

```bash
# DEMO_MODE (API 없이 파이프라인 흐름만 테스트)
python test_pipeline.py --demo

# 실제 API로 "버뮤다 삼각지대" 테스트
python test_pipeline.py

# 커스텀 소재로 테스트
python test_pipeline.py "주제: 딕쉰 사건..."
```

### 5. 텔레그램 봇 실행

```bash
python main.py
```

봇 시작 후 텔레그램에서:
- `/start` — 봇 소개
- `/trending` — Reddit 트렌딩 소재 선택
- 텍스트/URL 직접 입력 → 파이프라인 자동 실행

### 6. GUI 패널 실행

```bash
python gui_main.py
```

- 좌측: 소재 입력 + 파이프라인 단계 모니터링
- 중앙: 생성된 캡션/카드뉴스 미리보기
- 하단: 실시간 로그 스트림

### 7. 카드뉴스 폰트 설정 (선택)

`templates/` 폴더에 아래 파일을 저장하면 한글 폰트가 적용됩니다:
- `NanumGothicBold.ttf`
- `NanumGothic.ttf`

없을 경우 PIL 기본 폰트로 자동 대체됩니다.

---

## 🚀 배포환경

| 항목 | 설명 |
|------|------|
| 실행 환경 | 로컬 Windows/macOS/Linux PC |
| 봇 24시간 운영 | AWS EC2 t3.small 또는 Railway 권장 |
| 출력 저장 | 로컬 `output/` 폴더 (향후 S3/GCS 연동 가능) |
| 패키징 | PyInstaller로 단일 실행 파일 생성 가능 (TODO) |

---

## 📋 TODO 리스트

### ✅ 완료

- [x] 프로젝트 초기화 및 전체 파일 구조 (2026-08-13)
- [x] `modules/scraper.py` — Reddit PRAW + JSON API fallback
- [x] `modules/generator.py` — Claude Sonnet 4.6 대본 생성 (Strict JSON)
- [x] `modules/media.py` — ElevenLabs/gTTS TTS + Pexels/yt-dlp 배경 다운로드
- [x] `modules/editor.py` — Pillow 카드뉴스 + MoviePy Reels 영상 합성
- [x] `main.py` — 텔레그램 봇 (python-telegram-bot v21 async)
- [x] `gui_main.py` + PyQt6 GUI 전체 구현
- [x] DEMO_MODE 지원 (API 없이 전체 파이프라인 테스트)
- [x] `check_env.py` — API 키 연동 및 패키지 환경 점검 스크립트 (2026-08-13)
- [x] `test_pipeline.py` — 전체 파이프라인 통합 테스트 (버뮤다 삼각지대) (2026-08-13)
- [x] moviepy 버전 핀 (`<2.0.0`) 및 imageio-ffmpeg 추가 (2026-08-13)
- [x] Claude 모델 `claude-sonnet-4-6`으로 업데이트 (2026-08-13)
- [x] `modules/uploader.py` — instagrapi 기반 Reels + 카드뉴스 업로드 (2026-08-16)
- [x] `modules/db.py` — SQLite 소재 중복 방지 + 업로드 이력 DB (2026-08-16)
- [x] `modules/scheduler.py` — APScheduler 매일 자동 실행 (2026-08-16)
- [x] GUI 인스타그램 업로드 버튼 (파이프라인 완료 후 즉시 게시 가능) (2026-08-16)
- [x] GUI 스케줄러 제어 패널 (시각 설정, 시작/중지, 즉시 실행) (2026-08-16)
- [x] GUI 업로드 이력 탭 (최근 30건 이력 + 통계) (2026-08-16)
- [x] PipelineWorker DB 중복 체크 연동 (2026-08-16)

### 📌 추가 예정

- [ ] **성과 분석 대시보드** (좋아요/팔로워 추이 그래프)
- [ ] **PyInstaller 단일 실행 파일** 패키징 (.exe)
- [ ] 다국어 지원 (영어 버전 콘텐츠 생성)
- [ ] 커스텀 워터마크/브랜딩 설정 UI

---

## 🔑 필요한 API 키

| API | 발급 주소 | 필수 여부 |
|-----|-----------|-----------|
| Anthropic (Claude) | https://console.anthropic.com | **필수** |
| Telegram Bot | BotFather (@BotFather) | **필수** |
| Reddit | https://www.reddit.com/prefs/apps | 선택 (JSON API fallback) |
| Pexels | https://www.pexels.com/api | 선택 (yt-dlp fallback) |
| ElevenLabs | https://elevenlabs.io | 선택 (gTTS fallback) |

---

## ⚠️ 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요 (API 키 유출 위험)
- `output/` 폴더의 영상/이미지는 `.gitignore`로 제외됨
- `DEMO_MODE=true` 설정 시 실제 API 호출 없이 더미 데이터로 파이프라인 테스트 가능
- **MoviePy v2.x 사용 불가** — `requirements.txt`에서 `moviepy<2.0.0`으로 고정됨 (API 완전 변경)
- FFmpeg 미설치 시 영상 합성 실패 → `check_env.py` 로 사전 확인
- Reddit JSON API는 rate limit 있음 — 과도한 요청 주의
- ElevenLabs 무료 티어는 월 10,000자 제한 → 초과 시 gTTS로 자동 fallback

---

## 📅 개발 이력

| 날짜 | 내용 |
|------|------|
| 2026-08-13 | 프로젝트 초기화, 전체 파일 구조, 모든 모듈 + GUI 구현 |
| 2026-08-13 | `check_env.py`, `test_pipeline.py` 추가; moviepy 버전 핀; Claude 모델 업데이트 |
| 2026-08-16 | GUI 인스타 업로드 버튼 + 이력 탭; 스케줄러 제어 패널; PipelineWorker DB 연동 |
