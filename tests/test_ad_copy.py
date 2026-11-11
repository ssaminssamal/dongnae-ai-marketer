"""Offline checks for AI copy filtering; no Claude API calls are made."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ad_copy_ai
from claim_guard import find_unsupported, strip_sentences

FACTS = '- 가게 이름: 안서동 빵집\n- 상품·서비스: 소금빵\n- 소개: 매일 아침 직접 굽는 소금빵\n- 가격: 3,500원'
FORM = dict(store_name='안서동 빵집', subject_name='소금빵', description='매일 아침 직접 굽는 소금빵',
            unique_point='버터 향이 진한 겉바속촉', location_name='천안 안서동', price=3500)
ANALYSIS = {'target': '20대 대학생', 'area_type': '대학가', 'location': '천안 안서동',
            'business_points': ['재료와 식감']}


def fake_response(payload):
    return SimpleNamespace(stop_reason='end_turn', content=[
        SimpleNamespace(type='thinking', thinking=''),
        SimpleNamespace(type='text', text=json.dumps(payload, ensure_ascii=False))])


class ClaimGuard(unittest.TestCase):
    def test_flags_invented_claims(self):
        cases = {
            '오늘만 30% 할인해 드려요.': {'number', 'promo'},
            '1+1 행사 중입니다.': {'promo', 'number'},
            '다이어트에도 좋은 빵이에요.': {'efficacy'},
            '천안 최고의 소금빵!': {'absolute'},
            '20년 경력 제빵사가 만듭니다.': {'number'},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertTrue(expected <= {f.category for f in find_unsupported(text, FACTS)})

    def test_allows_owner_facts(self):
        for text in ['소금빵 한 개 3,500원.', '매일 아침 직접 굽는 소금빵.', '안서동 빵집에서 만나요!']:
            with self.subTest(text=text):
                self.assertEqual(find_unsupported(text, FACTS), [])

    def test_owner_entered_discount_is_allowed(self):
        facts = FACTS + '\n- 실제로 제공할 혜택: 첫 방문 10% 할인'
        self.assertEqual(find_unsupported('첫 방문 10% 할인!', facts), [])

    def test_strip_keeps_clean_sentences(self):
        text = '갓 구운 소금빵. 오늘만 반값! 지금 들르세요.'
        self.assertEqual(strip_sentences(text, find_unsupported(text, FACTS)), '갓 구운 소금빵. 지금 들르세요.')


class GenerateCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DONGNAE_DATA_DIR': self.tmp.name, 'ANTHROPIC_API_KEY': 'test'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_with(self, *payloads):
        with patch('anthropic.Anthropic') as client:
            client.return_value.beta.messages.create.side_effect = [fake_response(p) for p in payloads]
            result = ad_copy_ai.generate_copy(FORM, ANALYSIS, '친근한', '매장 방문')
            return result, client.return_value.beta.messages.create.call_args_list

    def test_clean_copy_passes_without_retry(self):
        clean = dict(headline='겉바속촉 소금빵 나왔어요', detail='버터 향 진한 아침 소금빵', cta='안서동 빵집으로 오세요',
                     narration='매일 아침 직접 굽는 소금빵. 안서동 빵집에서 만나요.')
        result, calls = self.run_with(clean)
        self.assertEqual(len(calls), 1)
        self.assertFalse(result['retried'])
        self.assertEqual(result['copy'], clean)
        request = calls[0].kwargs
        self.assertEqual(request['model'], 'claude-opus-5-5')
        self.assertIn('3,500원', request['messages'][0]['content'])

    def test_invented_claims_trigger_retry_then_strip(self):
        bad = dict(headline='오늘만 50% 할인!', detail='천안 최고의 소금빵', cta='지금 오세요',
                   narration='다이어트에도 좋아요. 버터 향 가득한 소금빵.')
        still_bad = dict(headline='무료 시식 진행 중', detail='버터 향 진한 소금빵', cta='지금 오세요',
                         narration='버터 향 가득한 소금빵. 1+1로 만나요.')
        result, calls = self.run_with(bad, still_bad)
        self.assertEqual(len(calls), 2)
        self.assertTrue(result['retried'])
        self.assertIn('50%', calls[1].kwargs['messages'][0]['content'])
        copy = result['copy']
        self.assertNotIn('무료', copy['headline'])
        self.assertIn('headline', result['used_template_for'])
        self.assertEqual(copy['narration'], '버터 향 가득한 소금빵.')
        with open(os.path.join(self.tmp.name, 'copy_log.jsonl'), encoding='utf-8') as fh:
            log = json.loads(fh.readline())
        self.assertEqual(len(log['first_findings']), len(result['first_findings']))


if __name__ == '__main__':
    unittest.main()
