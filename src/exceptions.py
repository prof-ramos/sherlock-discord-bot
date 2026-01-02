class SherlockBotError(Exception):
    """Base exception for SherlockBot."""

    pass


class ConfigError(SherlockBotError):
    """Raised when there is a configuration error."""

    pass


class OpenRouterError(SherlockBotError):
    """Raised when there is an error with the OpenRouter API."""

    pass


class ModerationError(SherlockBotError):
    """Raised when a message is blocked by moderation."""

    pass
