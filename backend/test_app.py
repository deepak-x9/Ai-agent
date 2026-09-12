import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend import app


class AssistantApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.chat_sessions.clear()
        self.client = TestClient(app.app)

    def test_detect_language(self) -> None:
        self.assertEqual(app.detect_language("How does a Python list work?"), "python")
        self.assertEqual(app.detect_language("What is a SQL join?"), "sql")
        self.assertEqual(app.detect_language("Explain this concept"), "unknown")

    @patch("backend.app.request_completion", return_value="```python\nprint('hi')\n```")
    def test_chat_stores_only_completed_turns(self, request_completion: Mock) -> None:
        response = self.client.post("/chat", json={"message": "Write Python code"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["detected_language"], "python")
        self.assertEqual(len(app.chat_sessions[payload["session_id"]]), 2)
        messages = request_completion.call_args.args[0]
        self.assertEqual(messages[-2], {"role": "user", "content": "Write Python code"})

    @patch("backend.app.request_completion", side_effect=app.HTTPException(502, "Provider failed"))
    def test_failed_completion_does_not_store_unanswered_message(self, _: Mock) -> None:
        response = self.client.post("/chat", json={"message": "Write Python code"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(app.chat_sessions, {})

    def test_missing_api_key_returns_configuration_error(self) -> None:
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            response = self.client.post("/chat", json={"message": "Explain Python"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "GROQ_API_KEY is not configured. Add it to backend/.env and restart the server.")

    def test_whitespace_only_message_is_rejected(self) -> None:
        response = self.client.post("/chat", json={"message": "  "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Message cannot be empty.")

    @patch("backend.app.httpx.post")
    def test_completion_uses_server_side_authorization(self, post: Mock) -> None:
        provider_response = Mock()
        provider_response.json.return_value = {
            "choices": [{"message": {"content": "A helpful answer"}}]
        }
        post.return_value = provider_response

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "test-model"}, clear=False):
            answer = app.request_completion([{"role": "user", "content": "Hello"}])

        self.assertEqual(answer, "A helpful answer")
        _, request_kwargs = post.call_args
        self.assertEqual(request_kwargs["headers"], {"Authorization": "Bearer test-key"})
        self.assertEqual(request_kwargs["json"]["model"], "test-model")


if __name__ == "__main__":
    unittest.main()
