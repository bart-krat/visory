"""Tests to verify OpenAI API connectivity.

These tests ensure that the application can always reach OpenAI.
Run with: pytest tests/test_openai_connectivity.py -v
"""

import pytest
from openai import AuthenticationError, OpenAIError


class TestOpenAIConnectivity:
    """Test suite for OpenAI API connectivity."""

    def test_can_connect_to_openai(self, chat_service):
        """Verify that we can successfully connect to OpenAI API."""
        assert chat_service.check_connectivity() is True

    def test_can_list_models(self, chat_service):
        """Verify that we can list available models."""
        models = chat_service.client.models.list()
        model_ids = [m.id for m in models.data]
        # Verify at least one GPT model is available
        assert any("gpt" in model_id for model_id in model_ids)

    def test_simple_chat_completion(self, chat_service):
        """Verify that we can make a simple chat completion request."""
        response = chat_service.simple_chat(
            user_message="Respond with exactly: PONG",
            system_prompt="You are a simple echo bot. Follow instructions exactly.",
        )
        assert response is not None
        assert len(response) > 0
        assert "PONG" in response.upper()

    def test_chat_with_conversation_history(self, chat_service):
        """Verify that conversation history is handled correctly."""
        messages = [
            {"role": "user", "content": "My name is TestUser."},
            {"role": "assistant", "content": "Hello TestUser!"},
            {"role": "user", "content": "What is my name?"},
        ]
        response = chat_service.chat(messages=messages)
        assert response is not None
        assert "TestUser" in response


class TestChatEndpoint:
    """Test the /api/chat endpoint."""

    def test_chat_endpoint_returns_response(self, client):
        """Verify the chat endpoint returns a valid response."""
        response = client.post(
            "/api/chat",
            json={"content": "Say hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "done" in data
        assert data["done"] is True

    def test_chat_endpoint_with_system_prompt(self, client):
        """Verify system prompt is passed correctly."""
        response = client.post(
            "/api/chat",
            json={
                "content": "What are you?",
                "system_prompt": "You are a helpful assistant named Visory.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_chat_endpoint_with_conversation_history(self, client):
        """Verify conversation history is handled correctly."""
        response = client.post(
            "/api/chat",
            json={
                "content": "What did I just tell you?",
                "conversation_history": [
                    {"role": "user", "content": "Remember the code word: ALPHA"},
                    {"role": "assistant", "content": "I'll remember ALPHA."},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "ALPHA" in data["message"]


class TestHealthEndpoint:
    """Test the health endpoint."""

    def test_health_endpoint(self, client):
        """Verify health endpoint is working."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
