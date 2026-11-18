# 최종 정리 및 검증 결과

검증일: 2026-11-18

## 제거한 기능

위치 CSV·지역 근거·샘플 상권 분석, 지도·위치 링크, 캠페인·쿠폰·QR·클릭 집계, 브랜드 보관함과 A/B 제작, 부가 음악 UI 및 관련 미사용 모듈·음악 파일을 제거했습니다. 기존 개인 자료 디렉터리는 건드리지 않았습니다.

## 유지·정리한 흐름

가게 정보 → 사진 1~3장 → 실제 AI 광고 문구 → 민감한 주장 검사·차단 → 장면 프롬프트 → 기존 Runway 영상 생성 → 장면 합치기·한글 자막·TTS → MP4 다운로드의 6단계 화면으로 정리했습니다.

입력 변경 시 문구 재생성을 요구하며 편집한 자막과 내레이션도 검사합니다. 음성을 먼저 생성하고 완성된 장면은 세션에서 재사용합니다. 개선 전후 프롬프트 조건, 사진 해시, 생성 원문·최종 문구·검증 결과, 장면별 왜곡과 사장님 의견을 JSON으로 내려받을 수 있습니다.

## 주요 파일

- `app.py`: 단계형 제작·미리보기·평가 화면
- `copy_service.py`, `secrets_config.py`, `scene_prompts.py`: 실제 문구 API, 보수적 주장 검사, 비밀 설정 읽기, 전후 연출
- `runway_service.py`: 기존 생성 방식 유지, Secrets 지원, 원시 API 오류 노출 축소
- `video_merge.py`: 핵심 자막·음성·합성만 유지
- `tts_service.py`, `local_tts.py`: 기본 온라인/선택 로컬 음성과 설정 처리
- `launch_app.py`, `config.py`: 제거 기능의 경로·설정 정리
- `requirements.txt`, `requirements-local-tts.txt`, `Dockerfile`, `compose.yml`: 실제 의존성 정리와 로컬 음성 선택 분리
- `.env.example`, `.gitignore`, `.dockerignore`: 예제 설정·비밀 파일 및 출력 제외 유지
- `README.md`, `FINAL_FEATURES.md`, `DEPLOYMENT.md`: 최종 기능에 맞게 안내 갱신
- `tests/test_final.py`, `tests/test_server.py`: 안전 차단·제작 흐름·실제 서버 점검 추가

## 테스트 결과

Windows / Python 3.11에서 `python -m unittest discover -s tests -v`: **12개 통과**.

- 앱 로딩·비밀번호, 사진 개수 제한, 실제 AI 연동을 모의한 문구 생성·편집·차단
- 가격·할인·효능·전각 숫자·가격 구분자 회귀 검사
- 입력 변경 시 차단, 완료 장면 재사용, 제작·평가 저장
- 실제 짧은 MP4 합성, 두 장면 연결, 한글 자막, 오디오 트랙, 긴 음성에 맞춘 화면 연장
- TTS 오류 정리, Linux 폰트 선택 모의 검사
- 실제 실행기·Streamlit 서버 기동 및 HTTP 정상 응답, 제거된 지도 경로 404
- 소스 구문 검사, 삭제 모듈 참조 없음, `git diff --check` 통과
- 추적 소스의 하드코딩 키 패턴 없음, `.env`·Streamlit Secrets·개인 데이터 Git 제외 확인
- requirements 설치 완료, 기존 Gen-4.5를 지원하는 SDK 시그니처 확인

현재 설치된 MoviePy에서 리소스 경고, Streamlit에서 기존 이미지 폭 인자의 폐기 예정 경고가 출력되지만 테스트는 모두 통과했습니다.

## 직접 검증하지 않은 범위

유료 AI 문구·영상 API의 실제 생성 요청, 온라인 TTS 실통신, 선택 로컬 모델의 실음성, Linux 서버·Streamlit Cloud 실배포는 수행하지 않았습니다. Linux 폰트 경로와 패키지 설정은 검토하고 선택 동작을 모의 검사했습니다.

민감한 주장 검사는 모든 허위 문장의 사실성을 입증하지 않습니다. 상품 원본 영역 합성은 구현하지 않았으며 개선 수치는 실제 영상으로 평가해야 합니다. 실제 가게 3곳·사진 조건 5개 이상의 전후 제작과 사장님 2명 이상의 답변은 실제 자료로 채워야 합니다. 세션 기록은 종료 전에 내려받아야 합니다.


후속 API 안정성 보강과 실제 생성 검증 결과는 [API_REVIEW.md](API_REVIEW.md)를 확인하세요. 앞의 미검증 범위 중 Runway 실생성·온라인 TTS·최종 합성은 후속 검증을 완료했으며, OpenAI 정상 생성은 API 크레딧 소진으로 대기 중입니다.


Gemini 전환 후 실제 문구 생성·검증·온라인 TTS·최종 MP4 합성까지 후속 검증을 완료했습니다. OpenAI는 사용하지 않으며, Gemini 연결 검증 내역은 API_REVIEW.md의 마지막 절을 기준으로 확인하세요.
