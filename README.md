# insta-content-bot

인스타그램 미스터리/이슈 계정용 콘텐츠 완전 자동 생성 Python 파이프라인.

Reddit에서 소재를 수집하고, Claude AI로 대본을 재가공한 뒤, TTS 음성과 배경 영상을 합성하여
Reels 영상 + 카드뉴스를 자동 생성합니다. 텔레그램 봇 또는 PyQt6 GUI로 운영할 수 있습니다.

---

## 개발환경

| 항목 | 버전/설명 |
|------|-----------|
| Python | 3.11 이상 |
| PyQt6 | 6.7+ (GUI 패널) |
| anthropic | 0.30+ (Claude AI 대본 생성) |
| praw | 7.7+ (Reddit 소재 수집) |
| python-telegram-bot | 21.0+ (async 텔레그램 봇) |
| moviepy | 1.0.3+ (영상 합성) |
| Pillow | 10.0+ (카드뉴스 이미지 생성) |
| gTTS / ElevenLabs | TTS 음성 생성 |
| yt-dlp | 배경 영상 다운로드 fallback |
| OS | Windows 10/11, macOS, Linux |

---

## 아키텍처

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
    │   원문 유사도 80% 이하 재가공  │
    │   출력: JSON (캡션/슬라이드/  │
    │          TTS/미디어 키워드)   │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 3: TTS + 배경 미디어  │
    │   modules/media.py           │
    │   ElevenLabs / gTTS          │
    │   Pexels → yt-dlp fallback   │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │   Step 4: 영상/카드뉴스 합성  │
    │   modules/editor.py          │
    │   Pillow + MoviePy           │
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

---

## 파일 구조

```
insta-content-bot/
├── .env.example          # 환경 변수 예시
├── .gitignore
├── requirements.txt
├── README.md
├── main.py               # 텔레그램 봇 + 파이프라인 (asyncio)
├── gui_main.py           # PyQt6 GUI 런처
├── modules/
│   ├── __init__.py
│   ├── scraper.py        # Reddit 소재 수집
│   ├── generator.py      # Claude AI 대본 생성
│   ├── media.py          # TTS + 배경 미디어 다운로드
│   └── editor.py         # Pillow/MoviePy 영상·카드뉴스 합성
├── gui/
│   ├── __init__.py
│   ├── main_window.py    # 메인 윈도우
│   ├── workers.py        # QThread 워커 (BotWorker, PipelineWorker)
│   ├── styles/
│   │   └── theme.py      # 다크 QSS 테마
│   └── widgets/
│       ├── pipeline_panel.py   # 파이프라인 제어 패널
│       ├── content_preview.py  # 결과물 미리보기
│       └── log_widget.py       # loguru 로그 스트림
├── templates/            # 폰트 파일 보관 (NanumGothicBold.ttf 등)
└── output/               # 생성된 미디어 저장
```

---

## 디자인 가이드

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
- 카드뉴스: templates/NanumGothicBold.ttf (없으면 PIL 기본 폰트)

### 레이아웃
- 메인 윈도우: 최소 1100x750
- 좌측 PipelinePanel: 280~400px 고정
- 하단 LogWidget: 160px 고정
- Reels 영상: 1080x1920 (세로형)
- 카드뉴스: 1080x1080 (정사각형)

---

## 실행 방법

### 1. 설치

```bash
cd /c/Users/com/insta-content-bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집기로 열어 API 키 입력
```

### 3. 데모 모드 테스트 (API 키 불필요)

```bash
# .env 에서 DEMO_MODE=true 설정 후
python main.py          # 텔레그램 봇
python gui_main.py      # GUI 패널
```

### 4. 텔레그램 봇 실행

```bash
python main.py
```

봇 시작 후 텔레그램에서:
- `/start` — 봇 소개
- `/trending` — Reddit 트렌딩 소재 선택
- 텍스트/URL 직접 입력 → 파이프라인 자동 실행

### 5. GUI 패널 실행

```bash
python gui_main.py
```

- 좌측: 소재 입력 + 파이프라인 단계 모니터링
- 중앙: 생성된 캡션/카드뉴스 미리보기
- 하단: 실시간 로그 스트림

### 6. 카드뉴스 폰트 (선택)

나눔고딕 폰트를 사용하려면 `templates/` 폴더에 아래 파일을 저장하세요:
- `NanumGothicBold.ttf`
- `NanumGothic.ttf`

없을 경우 PIL 기본 폰트로 자동 대체됩니다.

---

## 배포환경

| 항목 | 설명 |
|------|------|
| 실행 환경 | 로컬 Windows/macOS/Linux PC |
| 봇 운영 | 24시간 서버 필요 시 AWS EC2 t3.small 또는 Railway 권장 |
| 출력 저장 | 로컬 `output/` 폴더 (향후 S3/GCS 연동 가능) |
| 패키징 | PyInstaller로 단일 실행 파일 생성 가능 (TODO) |

---

## TODO 리스트

### 완료
- [x] 프로젝트 초기화 및 전체 파일 구조
- [x] `modules/scraper.py` — Reddit PRAW + JSON API fallback
- [x] `modules/generator.py` — Claude AI 대본 생성 (Strict JSON)
- [x] `modules/media.py` — ElevenLabs/gTTS TTS + Pexels/yt-dlp 배경 다운로드
- [x] `modules/editor.py` — Pillow 카드뉴스 + MoviePy Reels 영상 합성
- [x] `main.py` — 텔레그램 봇 (python-telegram-bot v21 async)
- [x] `gui_main.py` — PyQt6 GUI 런처
- [x] `gui/main_window.py` — 모니터링 메인 윈도우
- [x] `gui/workers.py` — BotWorker, PipelineWorker, TrendingWorker (QThread)
- [x] `gui/styles/theme.py` — 다크 QSS 테마
- [x] `gui/widgets/pipeline_panel.py` — 파이프라인 제어 패널
- [x] `gui/widgets/content_preview.py` — 결과물 미리보기
- [x] `gui/widgets/log_widget.py` — loguru 로그 스트림
- [x] README 문서화
- [x] DEMO_MODE 지원 (전체 파이프라인 API 없이 테스트 가능)

### 추가 예정
- [ ] 실제 인스타그램 Graph API 자동 업로드 연동
- [ ] 스케줄링: 매일 자동 실행 (APScheduler 또는 cron)
- [ ] 소재 중복 방지 DB (SQLite)
- [ ] 성과 분석 대시보드 (좋아요/팔로워 추이 그래프)
- [ ] PyInstaller 단일 실행 파일 패키징
- [ ] 다국어 지원 (영어 버전 콘텐츠 생성)

---

## 필요한 API 키

| API | 발급 주소 | 필수 여부 |
|-----|-----------|-----------|
| Anthropic (Claude) | https://console.anthropic.com | 필수 |
| Telegram Bot | BotFather (@BotFather) | 필수 |
| Reddit | https://www.reddit.com/prefs/apps | 선택 (JSON API fallback) |
| Pexels | https://www.pexels.com/api | 선택 (yt-dlp fallback) |
| ElevenLabs | https://elevenlabs.io | 선택 (gTTS fallback) |

---

## 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요. API 키가 유출될 수 있습니다.
- `output/` 폴더의 영상/이미지는 `.gitignore`로 제외되어 있습니다.
- `DEMO_MODE=true` 설정 시 실제 API 호출 없이 더미 데이터로 전체 파이프라인을 테스트할 수 있습니다.
- MoviePy는 FFmpeg에 의존합니다. 영상 합성 기능 사용 시 FFmpeg를 설치해야 합니다.
  - Windows: `winget install ffmpeg` 또는 https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
- Reddit JSON API는 rate limit이 있습니다. 과도한 요청을 피하세요.
- ElevenLabs 무료 티어는 월 10,000자 제한이 있습니다. 초과 시 gTTS로 자동 fallback.
- 생성된 콘텐츠의 저작권 및 Reddit 이용약관을 확인하세요.
