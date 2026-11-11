"""Ad copy written by Claude, checked against what the owner actually entered.

Flow: generate -> check every field with claim_guard -> if anything was invented,
regenerate once with the problems listed -> drop sentences that are still flagged ->
fill an emptied field from the template copy. Every run is appended to
<data dir>/copy_log.jsonl so before/after numbers can go into the report.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from claim_guard import CATEGORY_LABELS, find_unsupported, strip_sentences
from market_engine import make_ad_copy

load_dotenv(Path(__file__).parent / '.env')
MODEL = os.getenv('DONGNAE_COPY_MODEL', 'claude-opus-5-5')
FIELDS = ('headline', 'detail', 'cta', 'narration')
FIELD_LABELS = {'headline': '첫 문장', 'detail': '핵심 장점', 'cta': '방문·예약 문구', 'narration': '내레이션'}

SYSTEM = """당신은 동네 소상공인의 9:16 세로 숏폼 광고 문구를 쓰는 카피라이터입니다.

반드시 지킬 규칙:
- 사장님이 입력한 정보만 사용합니다. 입력에 없는 가격, 숫자, 할인, 무료, 증정, 이벤트, 기간, 경력 연수, 수상, 순위를 만들지 않습니다.
- 건강·다이어트·피부·치료 같은 효능이나 효과를 주장하지 않습니다.
- '최고', '최초', '1위', '유일', '100%', '보장' 같은 과장 표현을 쓰지 않습니다.
- 모르는 내용은 지어내지 말고 맛, 분위기, 정성, 접근성처럼 입력에서 확인되는 장점으로 표현합니다.
- 화면 자막이므로 짧고 자연스러운 한국어로 씁니다.

필드:
- headline: 시선을 붙잡는 첫 자막, 공백 포함 22자 이내
- detail: 가게만의 장점 한 문장, 30자 이내
- cta: 방문·예약·문의를 부르는 한 문장, 25자 이내
- narration: 성우가 읽을 내레이션 2~4문장, 120자 이내"""

SCHEMA = {
    'type': 'object',
    'properties': {name: {'type': 'string'} for name in FIELDS},
    'required': list(FIELDS),
    'additionalProperties': False,
}


def api_key_configured() -> bool:
    return bool(os.getenv('ANTHROPIC_API_KEY', '').strip())


def owner_facts(form: dict) -> str:
    """Everything the owner typed. Only these facts may appear in the copy."""
    rows = [
        ('가게 이름', form.get('store_name')), ('상품·서비스', form.get('subject_name')),
        ('소개', form.get('description')), ('가장 자신 있는 점', form.get('unique_point')),
        ('업종', form.get('business_type')), ('지역', form.get('location_name')),
        ('메뉴·상품 목록', form.get('menu')),
        ('가격', f"{form['price']:,}원" if form.get('price') else ''),
        ('실제로 제공할 혜택', form.get('offer')), ('혜택 조건', form.get('terms')),
    ]
    return '\n'.join(f'- {k}: {str(v).strip()}' for k, v in rows if v and str(v).strip())


def _request(form: dict, analysis: dict, style: str, goal: str, feedback: str = '') -> dict:
    import anthropic
    client = anthropic.Anthropic()
    prompt = f"""[사장님 입력 정보 — 이 안의 사실만 사용]
{owner_facts(form)}

[광고 방향 — 사실이 아니라 말투와 강조점 참고용]
- 광고 분위기: {style}
- 광고 목표: {goal}
- 주요 고객: {analysis.get('target', '')}
- 상권: {analysis.get('area_type', '')}"""
    if feedback:
        prompt += f'\n\n[이전 결과에서 입력에 없는 내용이 나왔습니다. 아래 표현을 빼고 다시 써 주세요]\n{feedback}'
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=8000,
        betas=['server-side-fallback-2026-07-01'],
        fallbacks='default',
        output_config={'effort': 'medium', 'format': {'type': 'json_schema', 'schema': SCHEMA}},
        system=SYSTEM,
        messages=[{'role': 'user', 'content': prompt}],
    )
    if response.stop_reason == 'refusal':
        raise RuntimeError('AI가 이 요청에 대한 문구 작성을 거절했습니다. 입력 내용을 바꿔 다시 시도해 주세요.')
    if response.stop_reason == 'max_tokens':
        raise RuntimeError('AI 응답이 중간에 끊겼습니다. 다시 시도해 주세요.')
    text = next(block.text for block in response.content if block.type == 'text')
    data = json.loads(text)
    return {name: str(data.get(name, '')).strip() for name in FIELDS}


def _check(copy: dict, facts: str):
    return [f for name in FIELDS for f in find_unsupported(copy[name], facts, name)]


def _log(entry: dict) -> None:
    folder = Path(os.getenv('DONGNAE_DATA_DIR', str(Path(__file__).parent / '.data')))
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / 'copy_log.jsonl', 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')


def generate_copy(form: dict, analysis: dict, style: str, goal: str) -> dict:
    """Return checked AI copy plus what was filtered. Raises RuntimeError with a Korean message."""
    import anthropic
    facts = owner_facts(form)
    try:
        first = _request(form, analysis, style, goal)
        first_findings = _check(first, facts)
        final, retried = first, False
        if first_findings:
            feedback = '\n'.join(sorted({f"- {FIELD_LABELS[f.field]}: '{f.term}' ({CATEGORY_LABELS[f.category]})" for f in first_findings}))
            final, retried = _request(form, analysis, style, goal, feedback), True
    except anthropic.AuthenticationError as error:
        raise RuntimeError('Claude API 키가 올바르지 않습니다. .env의 ANTHROPIC_API_KEY를 확인해 주세요.') from error
    except anthropic.RateLimitError as error:
        raise RuntimeError('요청이 많아 잠시 제한되었습니다. 1분 뒤 다시 시도해 주세요.') from error
    except anthropic.APIConnectionError as error:
        raise RuntimeError('Claude API에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.') from error
    except anthropic.APIStatusError as error:
        raise RuntimeError(f'Claude API 오류({error.status_code})가 발생했습니다. 잠시 후 다시 시도해 주세요.') from error

    final_findings = _check(final, facts)
    template = make_ad_copy(subject_name=form.get('subject_name', ''), description=form.get('description', ''),
                            analysis=analysis, style=style, goal=goal, store_name=form.get('store_name', ''))
    fallback = {'headline': template['headline'], 'detail': form.get('unique_point') or form.get('description', ''),
                'cta': template['cta'], 'narration': ''}
    cleaned, used_fallback = {}, []
    for name in FIELDS:
        own = [f for f in final_findings if f.field == name]
        value = strip_sentences(final[name], own) if own else final[name]
        if not value and fallback[name]:
            value, _ = fallback[name], used_fallback.append(name)
        cleaned[name] = value
    if not cleaned['narration']:
        cleaned['narration'] = ' '.join(cleaned[k] for k in ('headline', 'detail', 'cta') if cleaned[k])

    result = {
        'copy': cleaned,
        'model': MODEL,
        'retried': retried,
        'first_findings': [f.as_dict() for f in first_findings],
        'final_findings': [f.as_dict() for f in final_findings],
        'used_template_for': used_fallback,
    }
    _log({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'facts': facts, 'style': style, 'goal': goal,
          'first_output': first, 'final_output': final, **result})
    return result
