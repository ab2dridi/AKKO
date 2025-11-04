from __future__ import annotations

import io
import logging
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import akko.logging as akko_logging


def test_human_readable_renderer_formats_message() -> None:
    event: dict[str, object] = {
        "time": "2024-01-01T00:00:00",
        "levelname": "INFO",
        "module": "tests",
        "funcName": "test_func",
        "lineno": 12,
        "message": "hello",
        "user": "alice",
    }

    rendered = akko_logging.human_readable_renderer(None, None, event)

    assert "[2024-01-01 00:00:00.000]" in rendered
    assert "[    INFO]" in rendered
    assert "[tests:test_func:12]" in rendered
    assert "hello" in rendered
    assert "{user=alice}" in rendered


def test_add_package_fields_merges_metadata(mocker: MockerFixture) -> None:
    mocker.patch(
        "akko.logging._get_caller_info",
        return_value={"module": "mod", "lineno": 3, "funcName": "fn"},
    )
    mocker.patch(
        "akko.logging._get_system_info",
        return_value={
            "thread": 1,
            "threadName": "MainThread",
            "processName": "MainProcess",
            "process": 100,
        },
    )

    enriched = akko_logging.add_package_fields(
        logger=logging.getLogger("test"),
        method_name="info",
        event_dict={"event": "ping", "level": "info"},
    )

    assert enriched["module"] == "mod"
    assert enriched["lineno"] == 3
    assert enriched["funcName"] == "fn"
    assert enriched["levelname"] == "INFO"
    assert enriched["message"] == "ping"
    assert enriched["args"] == []
    assert enriched["name"] == "akko"
    assert enriched["thread"] == 1


@pytest.mark.usefixtures("reset_logger_state")
def test_configure_logger_human_readable_sets_formatter() -> None:
    stream = io.StringIO()

    akko_logging.configure_logger(
        log_level="DEBUG",
        output_stream=stream,
        human_readable=True,
    )

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert handler.formatter.__class__.__name__ == "HumanReadableFormatter"


@pytest.mark.usefixtures("reset_logger_state")
def test_configure_logger_json_mode_sets_formatter() -> None:
    stream = io.StringIO()

    akko_logging.configure_logger(
        log_level="INFO",
        output_stream=stream,
        human_readable=False,
    )

    root = logging.getLogger()
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert handler.formatter.__class__.__name__ == "JSONFormatter"


@pytest.mark.usefixtures("reset_logger_state")
def test_add_and_remove_file_handler(tmp_path: Path) -> None:
    stream = io.StringIO()
    akko_logging.configure_logger(output_stream=stream, human_readable=False)

    log_file = tmp_path / "akko.log"
    handler = akko_logging.add_file_handler(
        log_file,
        log_level="WARNING",
        human_readable=True,
    )

    root = logging.getLogger()
    assert handler in root.handlers
    assert handler.level == logging.WARNING
    assert Path(handler.baseFilename) == log_file
    assert handler.formatter.__class__.__name__ == "HumanReadableFormatter"

    assert akko_logging.remove_file_handler(handler)

    handler = akko_logging.add_file_handler(log_file)
    assert akko_logging.remove_file_handler(log_file)
    assert handler not in root.handlers


@pytest.mark.usefixtures("reset_logger_state")
def test_get_current_handlers_reports_console_and_file(tmp_path: Path) -> None:
    stream = io.StringIO()
    akko_logging.configure_logger(output_stream=stream, human_readable=True)

    log_file = tmp_path / "akko.log"
    akko_logging.add_file_handler(log_file, human_readable=False)

    info = akko_logging.get_current_handlers()

    assert any(handler["type"] == "StreamHandler" for handler in info["console"])
    assert any(Path(handler["filename"]) == log_file for handler in info["file"])


@pytest.mark.usefixtures("reset_logger_state")
def test_apply_structlog_to_other_packages() -> None:
    stream = io.StringIO()
    akko_logging.configure_logger(output_stream=stream, human_readable=True)

    root = logging.getLogger()
    akko_logging.apply_structlog_to_other_packages("external.module")

    external = logging.getLogger("external.module")
    assert external.level == root.level
    assert len(external.handlers) == len(root.handlers)
