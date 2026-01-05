import os
import sys

from src.base import Conversation, Message, Prompt


def verify_gemini_structure():
    """
    Verifies that the Google Gemini model prompt generation correctly uses
    a structured list for the system message, as required for potential caching integration,
    but does NOT yet include explicit Anthropic-style cache_control keys.
    """
    # Setup dummy data
    header = Message("system", "Test Instructions")
    examples = [Conversation([Message("user", "Hi"), Message("bot", "Hello")])]
    convo = Conversation([Message("user", "What is prompt caching?")])

    prompt = Prompt(header=header, examples=examples, convo=convo)

    # Test Gemini Model - Use configured environment variable or default
    model = os.environ.get("GEMINI_MODEL", "google/gemini-2.0-flash-exp")

    try:
        messages = prompt.full_render("TestBot", model)
    except Exception as e:
        print(f"❌ Failed to render prompt for model {model}: {e}")
        sys.exit(1)

    # Check system message content
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    if not system_msg:
        print("❌ System message not found in generated prompt!")
        sys.exit(1)

    content = system_msg["content"]

    print(f"Model: {model}")
    print("Content structure type:", type(content))

    if not isinstance(content, list):
        print(f"❌ Error: Expected content to be a list for Gemini, but got {type(content)}")
        sys.exit(1)

    # For Gemini, we expect NO cache_control keys for now (matching src/base.py logic)
    for block in content:
        if isinstance(block, dict) and "cache_control" in block:
            print(
                "⚠️ Warning: Found cache_control in Gemini block (unexpected for current implementation)"
            )

    print("✅ Structure verified (Gemini uses list content).")


if __name__ == "__main__":
    verify_gemini_structure()
