from __future__ import annotations
from typing import Dict

AREA_PROFILE = {
    "대학가": {
        "target": "20대 대학생과 젊은 소비자",
        "peak": "점심, 하교 이후, 저녁",
        "traits": ["가격 민감도 높음", "SNS·숏폼 반응 높음", "친구·연인 단위 방문"],
        "keywords": ["가성비", "재미", "트렌드", "빠른 이해"],
    },
    "오피스 상권": {
        "target": "20~40대 직장인",
        "peak": "출근 전, 점심, 퇴근 직후",
        "traits": ["시간 효율 중시", "품질과 편의성 중시", "예약·포장·빠른 서비스 선호"],
        "keywords": ["효율", "보상", "편의", "신뢰"],
    },
    "주거 상권": {
        "target": "지역 주민, 가족 고객, 생활권 소비자",
        "peak": "오후, 저녁, 주말",
        "traits": ["거리와 접근성 중요", "재방문 가능성 높음", "후기와 신뢰 중시"],
        "keywords": ["동네", "신뢰", "가족", "재방문"],
    },
    "역세권": {
        "target": "출퇴근 고객과 유동인구",
        "peak": "출퇴근 시간과 저녁",
        "traits": ["짧은 체류시간", "즉시 이해되는 메시지 중요", "접근성과 편의성 중시"],
        "keywords": ["빠름", "접근성", "한눈에", "즉시성"],
    },
    "관광 상권": {
        "target": "방문객, 관광객, 데이트 고객",
        "peak": "오후, 저녁, 주말",
        "traits": ["비주얼과 경험 중시", "사진·SNS 공유 성향", "지역 특색에 반응"],
        "keywords": ["경험", "비주얼", "지역성", "기억"],
    },
    "혼합 상권": {
        "target": "주변 직장인·주민·유동인구가 혼합된 고객층",
        "peak": "점심과 저녁",
        "traits": ["고객층이 다양함", "명확한 가치 제안 필요", "후기·접근성 중요"],
        "keywords": ["명확함", "범용성", "후기", "접근성"],
    },
}

BUSINESS_DIRECTION = {
    "음식점 / 카페": ["맛과 신선함", "대표 메뉴", "방문 욕구"],
    "식품 / 베이커리": ["재료와 식감", "신선함", "선물·간식 수요"],
    "미용 / 뷰티": ["전후 변화", "스타일", "예약 유도"],
    "의류 / 패션 / 잡화": ["디자인", "착용·사용 장면", "개성"],
    "헬스 / 운동": ["공간과 프로그램", "전문성", "상담·등록"],
    "학원 / 교육": ["수업 특징", "학습 경험", "상담 유도"],
    "공방 / 제작 / 수리": ["기술력", "과정", "완성도"],
    "반려동물": ["안심", "친근함", "서비스 경험"],
    "숙박 / 여행 / 체험": ["공간", "분위기", "경험"],
    "부동산 / 공간": ["공간 장점", "동선", "문의 유도"],
    "자동차 / 모빌리티": ["상태", "전문성", "신뢰"],
    "사진 / 스튜디오": ["결과물", "분위기", "예약"],
    "생활서비스": ["문제 해결", "신속함", "신뢰"],
    "전문서비스": ["전문성", "신뢰", "상담"],
    "온라인 / 프리랜서": ["포트폴리오", "차별점", "문의"],
    "기타": ["핵심 장점", "고객 가치", "행동 유도"],
}

GOAL_CTA = {
    "신규 고객 유입": "처음이라면 지금 한 번 경험해보세요.",
    "매장 방문": "가까운 매장에서 직접 만나보세요.",
    "예약 / 문의": "지금 예약하거나 편하게 문의해보세요.",
    "제품 판매": "마음에 든다면 지금 만나보세요.",
    "브랜드 인지도": "우리 동네에서 기억할 새로운 선택입니다.",
    "재방문 유도": "다시 찾고 싶은 이유를 만나보세요.",
    "이벤트 홍보": "기간이 끝나기 전에 이번 혜택을 확인해보세요.",
}

STYLE_TONE = {
    "감성적": "따뜻하고 짧은 문장", "유머러스": "가볍고 재치 있는 문장",
    "트렌디": "짧고 강한 SNS형 문장", "고급스러운": "절제되고 세련된 문장",
    "친근한": "동네 사람에게 말하듯 편안한 문장", "정보 전달형": "핵심 장점을 빠르게 이해시키는 문장",
}

def analyze_market(area_type: str, business_type: str, goal: str, location_name: str = "") -> Dict:
    area = AREA_PROFILE[area_type]
    directions = BUSINESS_DIRECTION.get(business_type, BUSINESS_DIRECTION["기타"])
    place = location_name.strip() or area_type
    return {
        "location": place, "area_type": area_type, "target": area["target"], "peak": area["peak"],
        "traits": area["traits"], "keywords": area["keywords"], "business_points": directions, "goal": goal,
        "disclaimer": "현재 데모의 상권 분석은 상권 유형별 샘플 프로필을 기반으로 합니다. 실서비스에서는 공공 상권·인구·유동인구 데이터로 교체할 수 있도록 분리 설계했습니다.",
    }

def make_ad_copy(subject_name: str, description: str, analysis: Dict, style: str, goal: str, store_name: str = "") -> Dict:
    name = subject_name.strip() or "우리 서비스"
    store = store_name.strip()
    if style == "유머러스": headline = f"{name}, 그냥 지나치기엔 아깝잖아요?"
    elif style == "감성적": headline = f"오늘의 일상에, {name} 한 가지를 더해보세요."
    elif style == "고급스러운": headline = f"{name}, 차이를 만드는 선택."
    elif style == "정보 전달형": headline = f"{name}의 핵심 장점을 한눈에."
    elif style == "친근한": headline = f"우리 동네에서 만나는 {name}."
    else: headline = f"지금 주목할 {name}."
    body = f"{analysis['location']}의 {analysis['target']}에게 {analysis['business_points'][0]}을 중심으로 알립니다."
    cta = GOAL_CTA.get(goal, "지금 확인해보세요.")
    if store: cta = f"{store}에서 {cta}"
    return {"headline": headline, "body": body, "cta": cta, "tone": STYLE_TONE[style], "description": description.strip()}
