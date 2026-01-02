from dotenv import load_dotenv
import os
import dacite
import yaml
from typing import Dict, List, Literal

from src.base import Config
from src.utils import logger

load_dotenv()


# load config.yaml
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG: Config = dacite.from_dict(
    Config, yaml.safe_load(open(os.path.join(SCRIPT_DIR, "config.yaml"), "r"))
)

BOT_NAME = CONFIG.name
BOT_INSTRUCTIONS = CONFIG.instructions
EXAMPLE_CONVOS = CONFIG.example_conversations

# OpenRouter API base URL - Default points to OpenRouter
# Can be changed to https://api.openai.com/v1 for direct OpenAI API usage
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
DEFAULT_MODEL = os.environ["DEFAULT_MODEL"]

ALLOWED_SERVER_IDS: List[int] = []
server_ids = os.environ["ALLOWED_SERVER_IDS"].split(",")
for s in server_ids:
    ALLOWED_SERVER_IDS.append(int(s))

SERVER_TO_MODERATION_CHANNEL: Dict[int, int] = {}
server_channels = os.environ.get("SERVER_TO_MODERATION_CHANNEL", "").split(",")
for s in server_channels:
    if not s.strip():  # Skip empty strings
        continue
    if ":" not in s:  # Validate format
        logger.warning(f"Invalid SERVER_TO_MODERATION_CHANNEL format: {s}. Expected format: server_id:channel_id")
        continue
    try:
        values = s.split(":")
        if len(values) == 2:
            server_id = int(values[0])
            channel_id = int(values[1])

            # Warn about duplicate server IDs
            if server_id in SERVER_TO_MODERATION_CHANNEL:
                logger.warning(f"Duplicate server ID {server_id} in SERVER_TO_MODERATION_CHANNEL. Overwriting previous value.")

            SERVER_TO_MODERATION_CHANNEL[server_id] = channel_id
        else:
            logger.warning(f"Invalid SERVER_TO_MODERATION_CHANNEL entry: {s}")
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse SERVER_TO_MODERATION_CHANNEL entry '{s}': {e}")

# Send Messages, Create Public Threads, Send Messages in Threads, Manage Messages, Manage Threads, Read Message History, Use Slash Command
BOT_INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=328565073920&scope=bot"

SECONDS_DELAY_RECEIVING_MSG = (
    3  # give a delay for the bot to respond so it can catch multiple messages
)
MAX_THREAD_MESSAGES = 200
ACTIVATE_THREAD_PREFX = "💬✅"
INACTIVATE_THREAD_PREFIX = "💬❌"
MAX_CHARS_PER_REPLY_MSG = (
    1500  # discord has a 2k limit, we just break message into 1.5k
)

AVAILABLE_MODELS = Literal[
    "openai/gpt-3.5-turbo",
    "openai/gpt-4o",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "google/gemini-2.0-flash-exp",
    "meta-llama/llama-3-70b-instruct"
]
