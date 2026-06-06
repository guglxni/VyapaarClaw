"""Tests for application logging configuration."""

from __future__ import annotations

import json
import logging

from vyapaar_mcp.logging_config import JSONFormatter, configure_logging, get_structured_logger


class TestJSONFormatter:
    """JSON formatter should preserve structured context."""

    def test_format_includes_extra_fields(self) -> None:
        record = logging.LogRecord(
            name="vyapaar.test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=10,
            msg="policy %s",
            args=("held",),
            exc_info=None,
        )
        record.extra_fields = {"agent_id": "agent-1", "decision": "HELD"}

        payload = json.loads(JSONFormatter().format(record))

        assert payload["level"] == "WARNING"
        assert payload["logger"] == "vyapaar.test"
        assert payload["message"] == "policy held"
        assert payload["agent_id"] == "agent-1"
        assert payload["decision"] == "HELD"


class TestConfigureLogging:
    """Logging configuration should respect explicit caller choices."""

    def test_explicit_non_json_overrides_environment(self, monkeypatch) -> None:
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        old_level = root.level
        monkeypatch.setenv("VYAPAAR_LOG_FORMAT", "json")

        try:
            configure_logging(level="INFO", json_format=False)

            assert len(root.handlers) == 1
            formatter = root.handlers[0].formatter
            assert formatter is not None
            assert not isinstance(formatter, JSONFormatter)
        finally:
            for handler in root.handlers[:]:
                root.removeHandler(handler)
            for handler in old_handlers:
                root.addHandler(handler)
            root.setLevel(old_level)


class TestStructuredLogger:
    """Structured logger helper should bind context for JSONFormatter."""

    def test_extra_is_bound_under_extra_fields(self) -> None:
        logger = get_structured_logger("vyapaar.test.bound", {"agent_id": "agent-1"})

        assert isinstance(logger, logging.LoggerAdapter)
        _, kwargs = logger.process("message", {})
        assert kwargs["extra"] == {"extra_fields": {"agent_id": "agent-1"}}
