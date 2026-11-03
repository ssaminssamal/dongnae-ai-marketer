"""Offline cloud compatibility checks; no Runway credits or speech requests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['DONGNAE_TTS_BACKEND'] = 'gtts'

from streamlit.testing.v1 import AppTest
from moviepy import ColorClip, VideoFileClip
import tts_service
import video_merge

APP_PATH = str(Path(__file__).resolve().parents[1] / 'app.py')

class CloudCompatibility(unittest.TestCase):
    def test_app_loads_and_password_gate(self):
        with patch.dict(os.environ, {'DONGNAE_APP_PASSWORD': ''}):
            app = AppTest.from_file(APP_PATH).run(timeout=45)
            self.assertFalse(app.exception)
        with patch.dict(os.environ, {'DONGNAE_APP_PASSWORD': '교수님-test-password'}):
            app = AppTest.from_file(APP_PATH).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.file_uploader) if hasattr(app, 'file_uploader') else len(app.get('file_uploader')), 0)
            app.text_input[0].set_value('wrong')
            app.button[0].click().run()
            self.assertTrue(app.error)
            app.text_input[0].set_value('교수님-test-password')
            app.button[0].click().run()
            self.assertTrue(app.session_state['_demo_authenticated'])
            self.assertFalse(app.exception)

    def test_linux_font_selection(self):
        linux_font = '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf'
        with patch('video_merge.os.path.exists', side_effect=lambda p: p == linux_font), patch('video_merge.ImageFont.truetype') as load:
            video_merge._get_font(32)
            load.assert_called_once_with(linux_font, 32)

    def test_gtts_and_failure_cleanup(self):
        def save_audio(path):
            Path(path).write_bytes(b'test-speech')
        with patch('gtts.gTTS') as speech:
            speech.return_value.save.side_effect = save_audio
            path = tts_service.generate_tts('교수님 체험')
            try:
                self.assertEqual(Path(path).read_bytes(), b'test-speech')
                self.assertEqual(Path(path).suffix, '.mp3')
            finally:
                tts_service.remove_tts_file(path)
            paths = []
            def fail(path):
                paths.append(path)
                raise OSError('offline')
            speech.return_value.save.side_effect = fail
            with self.assertRaises(RuntimeError):
                tts_service.generate_tts('실패 시 정리')
            self.assertFalse(Path(paths[0]).exists())

    def test_captioned_video_export(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            with ColorClip((180, 320), color=(30, 70, 40), duration=.5) as clip:
                clip.write_videofile(str(source), fps=24, codec='libx264', logger=None)
            data, path = video_merge.merge_video_bytes([source.read_bytes()], output_dir=folder, final_captions=['우리 동네 가게'])
            self.assertGreater(len(data), 100)
            with VideoFileClip(path) as result:
                self.assertEqual(result.size, [180, 320])
                self.assertAlmostEqual(result.duration, .5, delta=.1)


if __name__ == '__main__':
    unittest.main()
