# 동네AI 설치·외부 접속

## Streamlit Community Cloud 무료 체험 배포

1. `https://share.streamlit.io/`에 로그인하고 Create app을 선택합니다.
2. Repository: `ssaminssamal/dongnae-ai-marketer`, Branch: `main`, Main file: `app.py`.
3. Advanced settings에서 Python **3.11**을 선택하고 Secrets에 아래 값을 입력합니다.

```toml
RUNWAYML_API_SECRET = "실제 Runway API 키"
DONGNAE_APP_PASSWORD = "교수님과 공유할 별도 체험 비밀번호"
DONGNAE_TTS_BACKEND = "gtts"
```

실제 키와 비밀번호는 Cloud Secrets에만 저장합니다. `.env`와 `.streamlit/secrets.toml`은 커밋하지 않습니다. 루트 Secrets는 환경 변수로 제공되므로 기존 `os.getenv` 방식으로 읽습니다. 체험 비밀번호를 설정하면 앱의 저장 자료와 영상 생성 기능을 로그인 뒤에 제공합니다. 로그인한 체험자는 같은 브랜드·캠페인·완성 영상 보관함을 공유합니다.

4. 앱 주소를 선택한 뒤 Deploy합니다. `requirements.txt`로 Python 패키지, `packages.txt`로 Linux 한글 폰트와 시스템 라이브러리를 설치합니다.
5. 앱에서 로그인 → 사진 업로드 → 기획안 → 음성 미리 듣기 → 영상 생성 → 자막·BGM 합성 → MP4 다운로드를 확인합니다. Runway 생성에는 설정한 계정의 크레딧이 사용됩니다.

Cloud에서는 미설치 로컬 음성 모델 대신 gTTS를 사용합니다. 문구가 Google 음성 서비스로 전송되며 인터넷 연결이 필요합니다. 기본 한국어 음성만 지원하고 속도·품질 선택은 비활성화됩니다. 기존 PC의 모델이 있으면 로컬 음성을 계속 사용하며 `DONGNAE_TTS_BACKEND=local`로 명시할 수도 있습니다.

Cloud 파일과 SQLite 자료는 재시작·재배포 때 사라질 수 있습니다. 완성 영상은 즉시 다운로드하세요. Community Cloud는 `app.py`만 실행하므로 별도 `launch_app.py`가 제공하는 PWA 설치와 `/c/...` 캠페인 랜딩·성과 수집 서버는 제공되지 않습니다. 해당 기능은 아래 Docker 배포가 필요합니다. 공유 PC 자료를 Cloud로 업로드하지 마세요.

교수님 체험은 짧은 5초 장면으로 먼저 확인하세요. 무료 서버의 메모리 한도로 긴 영상이나 여러 동시 합성은 실패할 수 있습니다.

## PC에서 앱처럼 사용

```powershell
conda activate local_ai_demo
python launch_app.py
```

http://localhost:8503 에서 **앱 설치**를 누르거나 Chrome·Edge 메뉴의 앱 설치를 선택하세요. 설치 버튼은 브라우저가 설치 조건을 확인한 뒤 표시되며, 지원하지 않는 내장 브라우저에서는 Chrome·Edge를 사용하세요. 아이콘을 설치해도 제작 기능을 쓰려면 서버가 실행 중이어야 합니다.

## 무료 외부 테스트

```powershell
python setup_public_preview.py
python public_preview.py
```

이 PC가 켜져 있고 위 명령이 실행 중인 동안, 출력된 HTTPS 주소에 휴대폰으로 접속할 수 있습니다. 접속 비밀번호는 `.runtime/connection.txt`에 있습니다. API 키나 비밀번호를 URL에 넣지 않습니다. 접속 정보 파일은 다른 사람과 공유하지 마세요.

Cloudflare Quick Tunnel은 테스트용이며 SLA가 없습니다. 주소는 다시 실행할 때 바뀔 수 있습니다. 현재 실행을 종료하면 접속도 종료됩니다. 고정 앱 주소가 필요하면 아래 서버 배포 또는 소유한 도메인의 Named Tunnel을 사용하세요. Quick Tunnel은 계정·도메인 구매 없이 사용할 수 있지만 지속 운영용은 아닙니다.

## 모바일 설치

- 안드로이드: HTTPS 주소를 Chrome으로 열기 → 앱 설치 또는 홈 화면에 추가
- 아이폰·아이패드: HTTPS 주소를 Safari로 열기 → 공유 → 홈 화면에 추가

임시 주소로 설치한 아이콘은 해당 주소가 살아 있는 동안의 테스트용입니다. 계속 사용할 설치 아이콘은 고정 HTTPS 주소에 배포한 뒤 만드세요. 휴대폰 자체에서 Python·AI 모델·영상 합성을 실행하는 구조가 아닙니다. 모바일 앱은 서버에 연결합니다.

## PC를 꺼도 쓰는 상시 배포

서버·도메인은 자동 구매하지 않습니다. 이 폴더에는 Dockerfile, compose.yml, Caddyfile이 준비되어 있습니다. Docker 빌드와 실제 외부 서버 배포는 별도 서버에서 확인해야 합니다.

1. Docker가 있는 Linux 서버 준비. 영상 인코딩과 로컬 TTS를 위해 메모리 2GB 이상에서 시험 후 용량을 조절하세요.
2. 도메인의 DNS가 해당 서버를 가리키도록 설정하고 80·443 포트 제공.
3. 소스와 아래 환경 변수 준비. `.env`, `.runtime`, 기존 생성물, API 키를 Git에 업로드하지 마세요.

```env
DONGNAE_DOMAIN=studio.example.com
DONGNAE_APP_PASSWORD=12자_이상의_본인_접속_비밀번호
RUNWAYML_API_SECRET=본인의_Runway_키
```

4. `docker compose up -d --build`. Caddy가 HTTPS를 제공하고 내부 앱은 비밀번호 로그인 뒤에 있습니다. 영상은 Docker named volume에 보관합니다.
5. 실제 HTTPS 주소에서 로그인·업로드·영상 다운로드·모바일 설치를 확인하세요.

호스팅 업체를 쓰면 해당 서비스의 도메인·환경 변수·지속 디스크 설정으로 같은 Docker 이미지를 실행할 수 있습니다. 로그인은 한 명의 소유자용 공유 비밀번호 방식이며 일반 고객 대상 다중 계정 서비스는 아닙니다. 모델과 영상 작업 때문에 완전 무료 상시 서버 제공 여부를 보장하지 않습니다.

## 포함된 무료 배경음악

따뜻한 로파이 / 산뜻한 팝 / 차분한 앰비언트. 외부 샘플을 사용하지 않고 합성한 기본 트랙입니다. 프로젝트의 `assets_music_LICENSE.txt`에 따라 광고에 무료로 사용할 수 있습니다. 음량·내레이션 중 자동 음량 낮추기·페이드가 최종 MP4에 적용됩니다.

TTS와 기본 BGM은 건당 과금이 없습니다. Runway로 새 장면을 만드는 비용과 별도 서버를 운영하는 비용은 분리됩니다.
