# 동네AI 마케터 V3

사진과 간단한 설명을 입력하면 **상권 특성 → 타깃 고객 → 광고 카피 → Runway 영상 프롬프트 → AI 광고영상** 순서로 만드는 공모전 데모입니다.

## VSCode 실행

```bat
conda activate local_ai_demo
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 `http://localhost:8501`

## 결제 전
`.env`의 API 키를 비워둬도 앱이 실행됩니다. 업종/상권 입력, 사진 업로드, 데모 상권 분석, 광고 카피, Runway 영상 프롬프트, 예상 비용, JSON 저장까지 테스트할 수 있습니다.

## Runway API 키
`.env`에 다음처럼 넣습니다.

```env
RUNWAYML_API_SECRET=key_여기에_본인키
```

키를 바꿨으면 Streamlit을 `Ctrl+C`로 종료하고 다시 실행하세요.

## 결제 후
1. Runway Dev Billing에 크레딧 추가
2. 사진 업로드
3. 상권 분석 + 광고 기획
4. 프롬프트 확인/수정
5. 실제 Runway 영상 생성

## 모델
- `gen4_turbo`: 개발/테스트 추천
- `gen4.5`: 최종 공모전 영상 추천

현재 상권 분석은 **공모전 데모용 샘플 프로필**이며 실제 지역 매출·유동인구 수치를 꾸며내지 않습니다. 추후 `market_engine.py`를 공공데이터 API에 연결하도록 분리되어 있습니다.
