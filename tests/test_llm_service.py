import unittest
from unittest.mock import patch, MagicMock
import os
from llm_service import LLMService

class TestLLMService(unittest.TestCase):
    def setUp(self):
        # Ensure environment variable is set for tests
        os.environ["OPENAI_API_KEY"] = "test_key"

    def tearDown(self):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    @patch("llm_service.openai.OpenAI")
    def test_init_success(self, mock_openai):
        """Test that LLMService initializes correctly with an API key."""
        service = LLMService()
        self.assertEqual(service.api_key, "test_key")
        mock_openai.assert_called_once_with(api_key="test_key")

    @patch("llm_service.openai.OpenAI")
    def test_init_failure(self, mock_openai):
        """Test initialization without an API key."""
        del os.environ["OPENAI_API_KEY"]
        service = LLMService()
        self.assertIsNone(service.api_key)
        self.assertIsNone(service.client)

    @patch("llm_service.openai.OpenAI")
    def test_query_api_success(self, mock_openai):
        """Test a successful API query."""
        # Setup mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService()
        response = service.query_api("Test prompt", "gpt-4o-mini")
        
        self.assertEqual(response, "Test response")
        mock_client.chat.completions.create.assert_called_once()

    @patch("llm_service.openai.OpenAI")
    def test_query_api_no_client(self, mock_openai):
        """Test query failure when client is not initialized."""
        del os.environ["OPENAI_API_KEY"]
        service = LLMService()
        response = service.query_api("Test prompt")
        self.assertIn("Error: OpenAI Client not initialized", response)

if __name__ == "__main__":
    unittest.main()
