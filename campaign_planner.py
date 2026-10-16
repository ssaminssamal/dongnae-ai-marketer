"""Explainable situation-based drafts. No invented sales, offers, or population."""
import csv
import io
import math
from datetime import date,datetime,timedelta,timezone
from studio_store import safe_url

SITUATIONS=['가게 소개','빈 예약 시간 채우기','오늘 남은 상품 알리기','신메뉴·신상품 소개','재방문 유도','행사·혜택 안내']


def plan_campaign(form,situation,availability,offer,terms):
    name=form.get('subject_name','').strip()
    if not name: raise ValueError('홍보할 제품·서비스를 입력해 주세요.')
    if situation in SITUATIONS[1:3] and not availability.strip():
        raise ValueError('실제로 가능한 시간이나 남은 수량을 입력해 주세요.')
    store=form.get('store_name','').strip()
    area=form.get('location_name','').strip()
    advantage=form.get('unique_point','').strip() or form.get('description','').strip()
    lead={
        '가게 소개':f'{area+"에서 " if area else ""}만나는 {name}',
        '빈 예약 시간 채우기':f'{availability.strip()}, {name} 예약 가능해요',
        '오늘 남은 상품 알리기':f'{name}, {availability.strip()}',
        '신메뉴·신상품 소개':f'새롭게 선보이는 {name}',
        '재방문 유도':f'다시 생각나는 {name}',
        '행사·혜택 안내':f'{name}, 이번 혜택을 확인하세요',
    }[situation]
    benefit=offer.strip() or advantage or f'{name}을 직접 만나보세요.'
    cta='예약 가능 시간 확인하기' if situation=='빈 예약 시간 채우기' else '가게 소식 확인하기'
    variants=[]
    for label,headline,detail in [('A',lead,benefit),('B',f'{name}, {advantage}' if advantage else f'{store or "우리 가게"}의 {name}',offer.strip() or availability.strip() or benefit)]:
        price=form.get('price',0)
        if label=='A' and isinstance(price,(int,float)) and price>0:
            detail=f'{name} {price:,.0f}원. '+detail
        pieces=[headline,detail,cta]
        variants.append(dict(label=label,headline=headline,detail=detail,cta=cta,
            brand=' · '.join(x for x in [store,area] if x),narration='. '.join(p.rstrip('. ') for p in pieces if p)+'.'))
    rationale=[f'입력한 상황: {situation}', 'A는 현재 상황·방문 계기, B는 제품·서비스의 장점을 첫 문장에 배치했습니다.',
               '할인·수량·예약 가능 시간은 사장님이 입력한 내용만 사용했습니다.']
    evidence=form.get('local_evidence',[])
    if evidence:
        rationale += [f"지역 근거: {r['metric']} {r['value']:g}{r['unit']} · 기준일 {r['as_of']} · 출처 {r['source_url']}" for r in evidence[:5]]
        rationale.append('지역 수치는 사용자 제공 자료이며, 서로 다른 단위·기간을 섞거나 매출 효과로 해석하지 않았습니다.')
    else:
        rationale.append('실제 지역 지표가 없어 상권 유형별 샘플 제안만 사용했습니다.')
    return {'variants':variants,'rationale':rationale,'terms':terms.strip()}


def parse_market_csv(raw):
    if len(raw)>2*1024*1024: raise ValueError('지역 데이터는 2MB 이하 CSV로 올려 주세요.')
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError: text=raw.decode('cp949')
    reader=csv.DictReader(io.StringIO(text))
    required={'region','metric','value','unit','source_url','as_of'}
    if not required.issubset(reader.fieldnames or []): raise ValueError('필수 열: region, metric, value, unit, source_url, as_of')
    rows=[]; today=datetime.now(timezone(timedelta(hours=9))).date()
    for number,row in enumerate(reader,start=2):
        if number>1001: raise ValueError('최대 1,000행까지 가져올 수 있습니다.')
        try:
            value=float(str(row['value']).replace(',',''))
            if not math.isfinite(value) or value<0: raise ValueError()
            measured=date.fromisoformat(row['as_of'])
            if measured>today: raise ValueError()
            source=safe_url(row['source_url'])
            if not source or not row['region'].strip() or not row['metric'].strip() or not row['unit'].strip(): raise ValueError()
        except (ValueError,TypeError): raise ValueError(f'{number}행의 수치·기준일·출처 주소·필수 값을 확인해 주세요.') from None
        rows.append(dict(region=row['region'].strip(),metric=row['metric'].strip(),value=value,
                         unit=row['unit'].strip(),source_url=source,as_of=measured.isoformat()))
    if not rows: raise ValueError('가져올 데이터 행이 없습니다.')
    return rows
