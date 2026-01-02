"""Tests for utility functions."""

from src.utils import split_into_shorter_messages


class TestSplitIntoShorterMessages:
    """Tests for split_into_shorter_messages function."""

    def test_short_message_not_split(self):
        """Short messages should not be split."""
        message = "Hello, world!"
        result = list(split_into_shorter_messages(message))
        assert len(result) == 1
        assert result[0] == message

    def test_long_message_split(self):
        """Long messages should be split into chunks."""
        # Create a message longer than MAX_CHARS_PER_REPLY_MSG (1500)
        message = "A" * 3000
        result = list(split_into_shorter_messages(message))
        assert len(result) == 2
        assert len(result[0]) == 1500
        assert len(result[1]) == 1500

    def test_empty_message(self):
        """Empty messages should return empty list."""
        result = list(split_into_shorter_messages(""))
        assert len(result) == 0


class TestIsLastMessageStale:
    """Tests for is_last_message_stale function."""

    def test_placeholder(self):
        """Placeholder test - requires Discord mocks."""
        # TODO: Add proper tests with Discord message mocks
        assert True
