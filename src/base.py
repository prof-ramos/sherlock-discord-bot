from dataclasses import dataclass
from typing import Any, Optional

SEPARATOR_TOKEN = "<|endoftext|>"


@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None

    def render(self):
        result = self.user + ":"
        if self.text is not None:
            result += " " + self.text
        return result


@dataclass
class Conversation:
    messages: list[Message]

    def prepend(self, message: Message):
        self.messages.insert(0, message)
        return self

    def render(self):
        return f"\n{SEPARATOR_TOKEN}".join([message.render() for message in self.messages])


@dataclass(frozen=True)
class Config:
    name: str
    instructions: str
    example_conversations: list[Conversation]


@dataclass(frozen=True)
class ThreadConfig:
    model: str
    max_tokens: int
    temperature: float


def get_model_provider(model: Optional[str]) -> str:
    """Normalize model provider from string."""
    if not model or not isinstance(model, str):
        return "other"

    model_lower = model.lower()
    if "anthropic" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "google" in model_lower:
        return "gemini"
    if "openai" in model_lower:
        return "openai"
    return "other"


@dataclass(frozen=True)
class Prompt:
    header: Message
    examples: list[Conversation]
    convo: Conversation

    def full_render(
        self, bot_name: str, model: str, extra_context: str = ""
    ) -> list[dict[str, Any]]:
        """Render the full prompt for the model, handling provider-specific caching."""
        if not model or not model.strip():
            raise ValueError("Model must be a non-empty string.")

        # 1. Build Static Part (Instructions + Examples)
        # Separated to allow prompt caching of invariant parts.
        static_parts = (
            [self.header.render()]
            + [Message("system", "Example conversations:").render()]
            + [conversation.render() for conversation in self.examples]
        )

        static_text = f"\n{SEPARATOR_TOKEN}".join(static_parts)

        # 2. Build Dynamic Part (RAG Context + Transition)
        dynamic_parts = []
        if extra_context and extra_context.strip():
            # Trim and validate extra_context before using it
            cleaned_context = extra_context.strip()
            dynamic_parts.append(cleaned_context)
            dynamic_parts.append(
                Message(
                    "system", "Now, you will work with the actual current conversation."
                ).render()
            )

        dynamic_text = f"\n{SEPARATOR_TOKEN}".join(dynamic_parts)

        # 3. Construct System Content based on Model
        provider = get_model_provider(model)

        # Anthropic supports explicit caching via cache_control
        if provider == "anthropic":
            content = [
                {"type": "text", "text": static_text, "cache_control": {"type": "ephemeral"}}
            ]
            if dynamic_text:
                content.append({"type": "text", "text": dynamic_text})
        elif provider == "gemini":
            # Gemini: Use structured content but without cache_control keys
            content = [{"type": "text", "text": static_text}]
            if dynamic_text:
                content.append({"type": "text", "text": dynamic_text})
        else:
            # Legacy/OpenAI format
            if dynamic_text:
                content = static_text + f"\n{SEPARATOR_TOKEN}" + dynamic_text
            else:
                content = static_text

        messages = [
            {
                "role": "system",
                "content": content,
            }
        ]

        for message in self.render_messages(bot_name):
            messages.append(message)
        return messages

    def render_messages(self, bot_name: str):
        """Render the coversation messages as model history."""
        for message in self.convo.messages:
            if bot_name not in message.user:
                yield {
                    "role": "user",
                    "name": message.user,
                    "content": message.text,
                }
            else:
                yield {
                    "role": "assistant",
                    "name": bot_name,
                    "content": message.text,
                }
