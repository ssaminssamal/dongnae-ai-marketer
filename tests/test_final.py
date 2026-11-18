"""Safety and complete UI flow without paid API calls."""
import io
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ['DONGNAE_TTS_BACKEND'] = 'gtts'
from PIL import Image
from streamlit.testing.v1 import AppTest
from moviepy import ColorClip, VideoFileClip
from copy_service import FIELDS, generate_copy, validate_copy
from scene_prompts import build_scene_prompt
from video_merge import merge_video_bytes

ROOT = Path(__file__).resolve().parents[1]
FACTS = dict(store='테스트가게', product='커피', business='음식점 / 카페', description='고소한 커피', price='아메리카노 3,000원', discount='학생증 제시 시 10% 할인', effect='')
COPY = dict(headline='커피 한 잔의 여유', detail='고소한 커피', cta='방문해 주세요', brand='테스트가게', narration='고소한 커피를 만나보세요')


class CopySafety(unittest.TestCase):
    def test_unsupported_claims_all_fields(self):
        for field in FIELDS:
            for claim in ('단돈 100원', '누구나 10% 할인', '무료 증정', '피부 미백 효과', '질병을 예방해요', '십만 원', '１００원'):
                with self.subTest(field=field, claim=claim):
                    self.assertFalse(validate_copy(dict(COPY, **{field: claim}), FACTS)['passed'])

    def test_owner_exact_claims_and_changed_terms(self):
        self.assertTrue(validate_copy(dict(COPY, detail=FACTS['price'], cta=FACTS['discount']), FACTS)['passed'])
        self.assertFalse(validate_copy(dict(COPY, cta='누구나 10% 할인'), FACTS)['passed'])
        self.assertFalse(validate_copy(dict(COPY, detail='아메리카노 3,000원'), dict(FACTS, price=''))['passed'])
        self.assertFalse(validate_copy(dict(COPY, detail='5.000원'), dict(FACTS, price='15,000원'))['passed'])

    def test_no_api_fallback_and_safe_errors(self):
        with patch('copy_service.setting', return_value=''):
            with self.assertRaises(RuntimeError):
                generate_copy(FACTS)
        with patch('copy_service.setting', side_effect=lambda name, default='': 'gemini-3.5-flash-lite' if name == 'GEMINI_COPY_MODEL' else 'secret-test-value'), patch('copy_service.requests.post') as post:
            post.return_value.json.return_value = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(COPY)}]}}]}
            self.assertEqual(generate_copy(FACTS), COPY)
            self.assertIn('x-goog-api-key', post.call_args.kwargs['headers'])
            post.return_value.json.return_value = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{}'}]}}]}
            with self.assertRaises(RuntimeError) as error:
                generate_copy(FACTS)
            self.assertNotIn('secret-test-value', str(error.exception))

    def test_prompt_constraints_survive_long_input(self):
        result = build_scene_prompt(dict(FACTS, description='설명'*2000), True)
        self.assertLessEqual(len(result), 950)
        self.assertIn('Preserve the exact', result)
        self.assertIn('Fixed camera', result)
        self.assertNotEqual(result, build_scene_prompt(FACTS, False))


class MainFlow(unittest.TestCase):
    def widget(self, app, kind, label):
        return next(w for w in getattr(app, kind) if w.label == label)

    def test_generate_edit_block_render_and_evaluate(self):
        buffer = io.BytesIO()
        Image.new('RGB', (40, 60), 'red').save(buffer, format='PNG')
        class Photo(io.BytesIO):
            name = 'product.png'
            size = len(buffer.getvalue())
        photo = Photo(buffer.getvalue())
        with patch.dict(os.environ, {'DONGNAE_APP_PASSWORD': '', 'DONGNAE_REVIEW_MODE': '1'}), \
             patch('streamlit.file_uploader', return_value=[photo]), \
             patch('copy_service.generate_copy', return_value=COPY), \
             patch('runway_service.api_key_configured', return_value=True), \
             patch('runway_service.generate_image_to_video', return_value=SimpleNamespace(ok=True, video_bytes=b'scene')) as generate, \
             patch('video_merge.merge_video_bytes', return_value=(b'mp4-result', 'final_ad_test.mp4')) as merge:
            app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            self.widget(app, 'text_input', '가게명').set_value(FACTS['store'])
            self.widget(app, 'text_input', '홍보할 상품·서비스').set_value(FACTS['product'])
            self.widget(app, 'text_area', '특징과 홍보 정보').set_value(FACTS['description'])
            app.run()
            self.widget(app, 'button', 'AI 광고 문구 생성').click().run()
            self.assertFalse(app.exception)
            self.widget(app, 'text_area', '내레이션').set_value('오늘 90% 할인').run()
            render = self.widget(app, 'button', '광고 영상 만들기')
            self.assertTrue(render.disabled)
            self.assertTrue(self.widget(app, 'button', '내레이션 미리 듣기').disabled)
            generate.assert_not_called()
            self.widget(app, 'text_area', '내레이션').set_value(COPY['narration'])
            self.widget(app, 'checkbox', '내레이션 넣기').uncheck().run()
            self.widget(app, 'button', '광고 영상 만들기').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(generate.call_count, 1)
            merge.assert_called_once()
            self.assertEqual(len(app.session_state['runs']), 1)
            self.widget(app, 'button', '평가 저장').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state['evaluations']), 1)
            self.widget(app, 'button', '광고 영상 만들기').click().run()
            self.assertEqual(generate.call_count, 1)  # editing does not spend scene credits again
            self.widget(app, 'text_input', '가게명').set_value('다른가게').run()
            self.assertTrue(self.widget(app, 'button', '광고 영상 만들기').disabled)

    def test_production_editor_has_no_experiment_controls(self):
        with patch.dict(os.environ, {'DONGNAE_APP_PASSWORD': '', 'DONGNAE_REVIEW_MODE': ''}):
            app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertFalse(app.radio)
            text = '\n'.join(str(element.value) for element in app.markdown)
            for phrase in ('개선 전', '개선 후', '실험 조건', '평가 기록'):
                self.assertNotIn(phrase, text)
            self.assertEqual(len(app.get('file_uploader')), 1)
            self.assertTrue(self.widget(app, 'button', '광고 영상 만들기').disabled)

    def test_too_many_photos_blocked(self):
        with patch.dict(os.environ, {'DONGNAE_APP_PASSWORD': ''}), patch('streamlit.file_uploader', return_value=[SimpleNamespace(size=21*1024*1024)]*4):
            app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertTrue(self.widget(app, 'button', '광고 영상 만들기').disabled)


class VideoFlow(unittest.TestCase):
    def test_multiple_scenes_korean_captions_and_long_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.mp4'
            with ColorClip((180, 320), color=(120, 60, 30), duration=.5) as source:
                source.write_videofile(str(path), fps=24, codec='libx264', logger=None)
            sound = io.BytesIO()
            with wave.open(sound, 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b'\x00\x00' * 24000)
            data, result = merge_video_bytes([path.read_bytes()]*2, output_dir=folder,
                final_captions=['우리 가게', '고소한 커피'], narration_audio=sound.getvalue())
            self.assertGreater(len(data), 100)
            with VideoFileClip(result) as clip:
                self.assertEqual(clip.size, [180, 320])
                self.assertGreaterEqual(clip.duration, 1.5)
                self.assertIsNotNone(clip.audio)


if __name__ == '__main__':
    unittest.main()
