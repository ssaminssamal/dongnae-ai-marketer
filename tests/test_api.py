import unittest
from unittest.mock import patch
from types import SimpleNamespace
import requests
from runway_service import generate_image_to_video
from copy_service import generate_copy, validate_copy

class ApiReliability(unittest.TestCase):
    def test_task_resume_after_download_failure_without_paid_recreation(self):
        state={}
        with patch('runway_service.api_key_configured',return_value=True), patch('runway_service.get_api_key',return_value='private'), patch('runway_service.normalize_to_portrait',return_value=b'image'), patch('runway_service.RunwayML') as sdk, patch('runway_service._download_video',side_effect=[requests.Timeout('private'),b'video']):
            client=sdk.return_value
            client.image_to_video.create.return_value.id='task-1'
            client.tasks.retrieve.return_value=SimpleNamespace(status='SUCCEEDED',output=['https://example.com/ad.mp4'])
            self.assertFalse(generate_image_to_video(b'image','prompt',task_state=state).ok)
            self.assertTrue(generate_image_to_video(b'image','prompt',task_state=state).ok)
            self.assertEqual(client.image_to_video.create.call_count,1)
            self.assertEqual(client.tasks.retrieve.call_count,1)
            self.assertEqual(client.close.call_count,2)
            self.assertEqual(sdk.call_args.kwargs['max_retries'],0)

    def test_poll_timeout_keeps_task_and_cancellation_stops(self):
        state={'task_id':'existing'}
        with patch('runway_service.api_key_configured',return_value=True),patch('runway_service.get_api_key',return_value='private'),patch('runway_service.RunwayML') as sdk:
            client=sdk.return_value
            client.tasks.retrieve.return_value=SimpleNamespace(status='RUNNING')
            self.assertEqual(generate_image_to_video(b'image','prompt',task_state=state,poll_timeout=0).error_code,'TIMEOUT')
            self.assertEqual(state['task_id'],'existing')
            client.tasks.retrieve.return_value=SimpleNamespace(status='CANCELLED')
            self.assertEqual(generate_image_to_video(b'image','prompt',task_state=state).error_code,'TASK_FAILED')
            self.assertEqual(state,{})
            client.image_to_video.create.assert_not_called()

    def test_invalid_json_shape_and_incomplete_copy_fail_closed(self):
        with patch('copy_service.setting',side_effect=lambda name, default='': 'gemini-3.5-flash-lite' if name == 'GEMINI_COPY_MODEL' else 'private'), patch('copy_service.requests.post') as post:
            for message in ('[]','null','"text"'):
                post.return_value.json.return_value={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':message}]}}]}
                with self.assertRaises(RuntimeError): generate_copy({})
            post.return_value.json.return_value={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{}'}]}}]}
            with self.assertRaises(RuntimeError): generate_copy({})

    def test_auth_and_timeout_errors_are_safe(self):
        with patch('copy_service.setting',side_effect=lambda name, default='': 'gemini-3.5-flash-lite' if name == 'GEMINI_COPY_MODEL' else 'private'),patch('copy_service.requests.post') as post:
            response=requests.Response(); response.status_code=401
            post.side_effect=requests.HTTPError('private',response=response)
            with self.assertRaisesRegex(RuntimeError,'인증') as error: generate_copy({})
            self.assertNotIn('private',str(error.exception))
            post.side_effect=requests.Timeout('private')
            with self.assertRaisesRegex(RuntimeError,'초과'): generate_copy({})

    def test_partial_price_or_negated_claim_is_not_approved(self):
        self.assertFalse(validate_copy({'detail':'500원'}, {'price':'1500원'})['passed'])
        self.assertFalse(validate_copy({'detail':'무료'}, {'discount':'무료 아님'})['passed'])
        self.assertFalse(validate_copy({'detail':'0% 할인'}, {'discount':'10% 할인'})['passed'])
        self.assertTrue(validate_copy({'detail':'아메리카노 3,000원'}, {'description':'고소한 커피. 아메리카노 3,000원.'})['passed'])

    def test_local_key_update_is_visible_without_process_restart(self):
        import os
        import tempfile
        from pathlib import Path
        import secrets_config
        with tempfile.TemporaryDirectory() as folder:
            env_file = Path(folder)/'.env'
            with patch('secrets_config.ENV_PATH', env_file), patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
                env_file.write_text('GEMINI_API_KEY=first-test-value', encoding='utf-8')
                self.assertEqual(secrets_config.setting('GEMINI_API_KEY'), 'first-test-value')
                env_file.write_text('GEMINI_API_KEY=second-test-value', encoding='utf-8')
                self.assertEqual(secrets_config.setting('GEMINI_API_KEY'), 'second-test-value')
                self.assertEqual(os.environ['GEMINI_API_KEY'], '')
