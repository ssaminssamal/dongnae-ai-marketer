"""Find claims in generated ad copy that the owner never entered.

AI copy may invent prices, discounts, health effects or "No.1" claims. Each finding
names the sentence, the matched words and a category, so the app can drop the
sentence and the report can count how often it happened.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict

CATEGORY_LABELS = {
    'number': '숫자·가격',
    'promo': '할인·혜택',
    'efficacy': '효능·건강',
    'absolute': '과장·최상급',
}

# Words that are only allowed when the owner wrote them (or their stem) in the input.
PROMO_WORDS = ['할인', '세일', '특가', '반값', '무료', '공짜', '증정', '사은품', '쿠폰', '이벤트',
               '적립', '덤', '1+1', '2+1', '오픈 기념', '오픈기념', '한정 수량', '선착순', '프로모션']
EFFICACY_WORDS = ['다이어트', '살 빠', '살빠', '체중', '면역', '피부 개선', '피부개선', '미백', '주름',
                  '탈모', '치료', '효능', '혈압', '혈당', '해독', '디톡스', '노화 방지', '항산화',
                  '질병', '예방', '완치', '숙취 해소', '숙취해소', '피로 회복', '피로회복', '건강에 좋',
                  '몸에 좋', '부작용 없']
ABSOLUTE_WORDS = ['최고', '최초', '1위', '1등', '넘버원', 'No.1', '유일', '100%', '완벽', '국내 최',
                  '업계 최', '지역 최', '동네 최', '보장', '무조건', '절대', '최저가', '최대 규모']

NUMBER = re.compile(r'\d[\d,.]*\s*(?:만\s*원|천\s*원|원|%|퍼센트|개월|년|분|시간|일|명|개|잔|인분|kg|g)?')
SENTENCE = re.compile(r'[^.!?…\n]+[.!?…]*')


@dataclass
class Finding:
    field: str
    sentence: str
    term: str
    category: str

    def as_dict(self):
        data = asdict(self)
        data['category_label'] = CATEGORY_LABELS[self.category]
        return data


def _plain(text: str) -> str:
    return re.sub(r'\s+', '', text or '').lower()


def _digits(text: str) -> set[str]:
    return {m.replace(',', '') for m in re.findall(r'\d[\d,]*', text or '')}


def find_unsupported(text: str, facts: str, field: str = '') -> list[Finding]:
    """Return every claim in ``text`` that is not backed by the owner's ``facts``."""
    plain_facts = _plain(facts)
    fact_digits = _digits(facts)
    findings: list[Finding] = []
    for sentence in (s.strip() for s in SENTENCE.findall(text or '')):
        if not sentence:
            continue
        plain = _plain(sentence)
        for category, words in (('promo', PROMO_WORDS), ('efficacy', EFFICACY_WORDS), ('absolute', ABSOLUTE_WORDS)):
            for word in words:
                key = _plain(word)
                if key in plain and key not in plain_facts:
                    findings.append(Finding(field, sentence, word, category))
        for match in NUMBER.finditer(sentence):
            number = match.group().strip()
            digits = _digits(number)
            if digits and not digits <= fact_digits:
                findings.append(Finding(field, sentence, number, 'number'))
    return findings


def strip_sentences(text: str, findings: list[Finding]) -> str:
    """Remove the flagged sentences and keep the rest of the text."""
    bad = {f.sentence for f in findings}
    kept = [s.strip() for s in SENTENCE.findall(text or '') if s.strip() and s.strip() not in bad]
    return ' '.join(kept).strip()
