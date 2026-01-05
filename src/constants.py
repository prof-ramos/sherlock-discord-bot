import os
from pathlib import Path
from typing import Any, Final, Literal

import dacite
import yaml
from dotenv import load_dotenv

from src.base import Config
from src.exceptions import ConfigError
from src.utils import logger

load_dotenv()


def get_env(key: str, default: Any = None, required: bool = True) -> Any:
    """Retrieve environment variable or raise ConfigError if required and missing."""
    if key not in os.environ and required:
        raise ConfigError(f"Missing required environment variable: {key}")
    return os.environ.get(key, default)


def _get_int_env(key: str, default: int) -> int:
    try:
        val = os.environ.get(key)
        if val is None or not val.strip():
            return default
        return int(val)
    except (ValueError, TypeError):
        logger.warning("Invalid value for environment variable %s, defaulting to %s", key, default)
        return default


# Configuration Loading
SCRIPT_DIR: Final[Path] = Path(__file__).parent.resolve()
CONFIG_PATH: Final[Path] = SCRIPT_DIR / "config.yaml"

try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    CONFIG: Final[Config] = dacite.from_dict(Config, config_data)
except Exception as e:
    raise ConfigError(f"Failed to load config.yaml: {e}") from e

BOT_NAME: Final[str] = CONFIG.name
BOT_INSTRUCTIONS: Final[str] = CONFIG.instructions
EXAMPLE_CONVOS: Final[list] = CONFIG.example_conversations


def _get_float_env(key: str, default: float) -> float:
    try:
        val = os.environ.get(key)
        if val is None or not val.strip():
            return default
        return float(val)
    except (ValueError, TypeError):
        logger.warning("Invalid value for environment variable %s, defaulting to %s", key, default)
        return default


# API Configuration
OPENROUTER_API_KEY: Final[str] = get_env("OPENROUTER_API_KEY")
OPENAI_API_KEY: Final[str | None] = get_env(
    "OPENAI_API_KEY", required=False
)  # Optional, strictly for embeddings if needed
OPENROUTER_BASE_URL: Final[str] = get_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MAX_RETRIES: Final[int] = _get_int_env("OPENROUTER_MAX_RETRIES", 3)
OPENROUTER_TIMEOUT: Final[float] = _get_float_env("OPENROUTER_TIMEOUT", 60.0)
DEFAULT_MODEL: Final[str] = get_env("DEFAULT_MODEL")

# Discord Configuration
DISCORD_BOT_TOKEN: Final[str] = get_env("DISCORD_BOT_TOKEN")
DISCORD_CLIENT_ID: Final[str] = get_env("DISCORD_CLIENT_ID")


# Allowed Server IDs
def _parse_allowed_servers() -> list[int]:
    raw = os.environ.get("ALLOWED_SERVER_IDS", "")
    if not raw:
        return []
    servers: list[int] = []
    for s in raw.split(","):
        try:
            val = s.strip()
            if val:
                servers.append(int(val))
        except ValueError:
            logger.warning("Invalid server ID in ALLOWED_SERVER_IDS: %s", s)
    return servers


ALLOWED_SERVER_IDS: Final[list[int]] = _parse_allowed_servers()


# Moderation Channel Mapping
def _parse_moderation_channels() -> dict[int, int]:
    mapping: dict[int, int] = {}
    raw = os.environ.get("SERVER_TO_MODERATION_CHANNEL", "")
    if not raw:
        return mapping

    for entry in raw.split(","):
        if not entry.strip() or ":" not in entry:
            continue
        try:
            guild_id_str, channel_id_str = entry.split(":", 1)
            mapping[int(guild_id_str)] = int(channel_id_str)
        except ValueError as e:
            logger.warning("Invalid moderation channel entry '%s': %s", entry, e)
    return mapping


SERVER_TO_MODERATION_CHANNEL: Final[dict[int, int]] = _parse_moderation_channels()

# Derived Constants
# Discord permissions integer (admin, manage channels, send messages, etc.)
DISCORD_BOT_PERMISSIONS: Final[int] = 328565073920
BOT_INVITE_URL: Final[str] = (
    f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions={DISCORD_BOT_PERMISSIONS}&scope=bot%20applications.commands"
)

# Operational Constants
SECONDS_DELAY_RECEIVING_MSG: Final[int] = 3
MAX_THREAD_MESSAGES: Final[int] = 200
OPTIMIZED_HISTORY_LIMIT: Final[int] = 50  # Optimized limit for history search
ACTIVATE_THREAD_PREFIX: Final[str] = "💬✅"
INACTIVATE_THREAD_PREFIX: Final[str] = "💬❌"
MAX_CHARS_PER_REPLY_MSG: Final[int] = 1500
# Defaults for direct mentions
DEFAULT_MENTION_MAX_TOKENS: Final[int] = 1024
DEFAULT_MENTION_TEMPERATURE: Final[float] = 0.7

# Cache Configuration
CACHE_MAX_SIZE: Final[int] = _get_int_env("CACHE_MAX_SIZE", 100)
CACHE_TTL_SECONDS: Final[int] = _get_int_env("CACHE_TTL_SECONDS", 3600)

# Available Models for runtime iteration and type hints
MODELS_LIST: Final[tuple[str, ...]] = (
    # OpenAI Models
    "openai/gpt-3.5-turbo",
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    # Anthropic Claude Models
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-haiku",
    # Google Models
    "google/gemini-pro-1.5",
    "google/gemini-2.0-flash-exp",
    # Meta Llama Models
    "meta-llama/llama-3-70b-instruct",
    # Free Models
    "xiaomi/mimo-v2-flash:free",
    "deepseek/deepseek-chat-v3-0324:free",
)

AVAILABLE_MODELS = Literal[
    "openai/gpt-3.5-turbo",
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-pro-1.5",
    "google/gemini-2.0-flash-exp",
    "meta-llama/llama-3-70b-instruct",
    "xiaomi/mimo-v2-flash:free",
    "deepseek/deepseek-chat-v3-0324:free",
]

# Thread Defaults
DEFAULT_THREAD_MAX_TOKENS: Final[int] = 512
DEFAULT_THREAD_TEMPERATURE: Final[float] = 1.0
