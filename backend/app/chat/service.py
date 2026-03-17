import os
from openai import OpenAI
from openai import OpenAIError


DEFAULT_SYSTEM_PROMPT = """You are Visory, a helpful AI assistant that helps users plan their day.
Help users organize their tasks, set priorities, and create realistic schedules.
Be concise and friendly."""


class ChatService:
    """Central service for all OpenAI interactions.

    This is the base module that all other submodules (categorize, constraints, etc.)
    will use to interact with the LLM.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        default_system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.default_system_prompt = default_system_prompt

    def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_default_system_prompt: bool = True,
    ) -> str:
        """Send a chat completion request to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: Optional system prompt to prepend (overrides default).
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens in response.
            use_default_system_prompt: If True and no system_prompt provided, use default.

        Returns:
            The assistant's response content.
        """
        full_messages = []

        # Use provided system prompt, or default if enabled
        prompt = system_prompt
        if prompt is None and use_default_system_prompt:
            prompt = self.default_system_prompt

        if prompt:
            full_messages.append({"role": "system", "content": prompt})

        full_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    def simple_chat(self, user_message: str, system_prompt: str | None = None) -> str:
        """Simplified interface for single-turn conversations."""
        messages = [{"role": "user", "content": user_message}]
        return self.chat(messages, system_prompt=system_prompt)

    def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_default_system_prompt: bool = True,
    ):
        """Stream a chat completion response from OpenAI.

        Yields:
            String chunks as they arrive from the API.
        """
        full_messages = []

        prompt = system_prompt
        if prompt is None and use_default_system_prompt:
            prompt = self.default_system_prompt

        if prompt:
            full_messages.append({"role": "system", "content": prompt})

        full_messages.extend(messages)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def check_connectivity(self) -> bool:
        """Verify that we can reach the OpenAI API.

        Returns:
            True if connection successful, raises exception otherwise.
        """
        try:
            self.client.models.list()
            return True
        except OpenAIError:
            raise


# Singleton instance for use across the application
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create the singleton ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
