# 동네AI 광고 스튜디오

사진으로 광고 장면을 만들고, 한글 자막과 무료 로컬 TTS를 더해 세로 MP4로 저장합니다.

## 실행

```bat
conda activate local_ai_demo
python -m pip install -r requirements.txt
python setup_free_tts.py
python launch_app.py
```

브라우저에서 http://localhost:8503 에 접속하세요. `setup_free_tts.py`는 최초 1회 약 400MB의 Supertonic 3 모델을 다운로드합니다. 모델은 프로젝트의 `models/supertonic3`에 보관하며, 설치 후 음성은 네트워크 없이 PC에서 생성합니다.

## 음성

- **무료 AI 음성:** 남성·여성 각 5개, 속도와 품질 선택. API 키·가입·건당 과금 없음
- **음성 파일 업로드:** 캡컷 등에서 생성한 MP3/WAV/M4A를 그대로 결합. 최대 20MB
- **미리 듣기:** 같은 문구·목소리·설정으로 만든 음성을 최종 영상에 재사용

기본 TTS는 캡컷 애덤과 다른 목소리입니다. ElevenLabs와 gTTS는 사용하지 않습니다. Runway 영상 생성 비용은 별도입니다. 기존 `.env`의 `RUNWAYML_API_SECRET`을 유지하세요.

## 편집

브랜드 정보를 입력하고, 사진 또는 저장된 장면을 선택합니다. 카피 · 음성에서 문구와 내레이션을 편집한 뒤 미리보기 아래 제작 버튼을 누릅니다. 기존 장면은 선택 순서대로 이어집니다. 내레이션이 길면 마지막 화면을 연장합니다. 자막은 전체 길이에 나누어 표시하며 단어별 음성 인식 자막은 아닙니다.

상권 제안은 샘플 프로필을 사용하며 실제 유동인구·매출 분석은 아닙니다.

## 라이선스

Supertonic 코드: MIT. 모델: BigScience Open RAIL-M. 모델 파일과 함께 제공되는 LICENSE·NOTICE를 유지하고 해당 이용 조건을 따르세요. 업로드 음성은 본인이 사용할 권한이 있는 파일을 사용하세요.


## 최종 기능과 사용 흐름

브랜드 보관함, 상황별 A/B 기획, 동일 장면을 활용한 두 광고 제작, QR·예약/지도 링크·쿠폰, 광고별 반응 집계와 CSV 저장, 출처·기준일이 있는 지역 CSV 가져오기를 제공합니다.

[전체 사용 안내](FINAL_FEATURES.md) · [외부 접속 및 배포](DEPLOYMENT.md)

외부 접속은 `python setup_public_preview.py` 최초 준비 후 `python public_preview.py`로 실행합니다. Quick Tunnel 주소는 임시이며 PC가 켜져 있어야 합니다. 클릭 집계는 실제 예약·매출이 아니며, 기본 상권 제안은 샘플입니다. 공공데이터 자동 수집과 고정 주소 호스팅은 별도 연결이 필요합니다.
