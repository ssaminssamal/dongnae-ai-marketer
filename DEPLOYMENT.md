# 배포

## Streamlit Community Cloud

- 저장소의 `app.py`를 시작 파일로 선택합니다. Python 3.11을 권장합니다.
- `requirements.txt`를 설치하고 `packages.txt`의 Linux 한글 폰트 패키지를 사용합니다.
- 앱 설정의 Secrets에 아래 키를 입력합니다. 실제 값은 저장소에 올리지 마세요.

```toml
OPENAI_API_KEY = "your-key"
RUNWAYML_API_SECRET = "your-key"
OPENAI_COPY_MODEL = "gpt-4o-mini"
DONGNAE_TTS_BACKEND = "gtts"
```

선택적으로 `DONGNAE_APP_PASSWORD`를 설정할 수 있습니다. 기본 음성은 온라인 gTTS여서 대용량 모델이 필요 없습니다. 영상·문구 생성 비용은 서비스 계정에 부과됩니다. 세션 기록은 종료 전에 내려받으세요.

## Windows

`python -m streamlit run app.py` 또는 `python launch_app.py`를 실행합니다. 경로는 프로젝트 파일 기준으로 계산하며 한글 폰트는 Windows 맑은 고딕을 사용합니다. 로컬 TTS는 README의 선택 설치 절차를 따르세요.

## 선택 Docker / 외부 미리보기

Docker는 기본 gTTS 구성입니다. `compose.yml` 사용 시 `.env`에 API 키와 도메인, 12자 이상의 접속 비밀번호를 설정합니다. 외부 미리보기는 `python setup_public_preview.py` 후 `python public_preview.py`로 실행하며 PC가 켜져 있어야 합니다. 임시 주소는 바뀔 수 있습니다.
