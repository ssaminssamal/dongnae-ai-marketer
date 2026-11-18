import unittest
from unittest.mock import patch
from types import SimpleNamespace
import requests
from runway_service import generate_image_to_video
from copy_service import generate_copy

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
        with patch('copy_service.setting',return_value='private'), patch('copy_service.requests.post') as post:
            for message in ('[]','null','"text"'):
                post.return_value.json.return_value={'choices':[{'message':{'content':message}}]}
                with self.assertRaises(RuntimeError): generate_copy({})
            post.return_value.json.return_value={'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}
            with self.assertRaises(RuntimeError): generate_copy({})

    def test_auth_and_timeout_errors_are_safe(self):
        with patch('copy_service.setting',return_value='private'),patch('copy_service.requests.post') as post:
            response=requests.Response(); response.status_code=401
            post.side_effect=requests.HTTPError('private',response=response)
            with self.assertRaisesRegex(RuntimeError,'인증') as error: generate_copy({})
            self.assertNotIn('private',str(error.exception))
            post.side_effect=requests.Timeout('private')
            with self.assertRaisesRegex(RuntimeError,'초과'): generate_copy({})
