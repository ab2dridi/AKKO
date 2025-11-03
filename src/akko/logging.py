"""Log settings and configuration for mcp-websearch."""

import os
import sys
import threading
import traceback
from datetime import datetime
from functools import lru_cache
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    NOTSET,
    WARNING,
    FileHandler,
    Formatter,
    Logger,
    LogRecord,
    StreamHandler,
    getLevelName,
    getLogger,
)
from pathlib import Path
from typing import Any, TextIO

import structlog
from orjson import JSONDecodeError, loads
from structlog.typing import EventDict, Processor

LOG_LEVELS = {
    "CRITICAL": CRITICAL,
    "ERROR": ERROR,
    "WARNING": WARNING,
    "INFO": INFO,
    "DEBUG": DEBUG,
    "NOTSET": NOTSET,
}


def _get_caller_info() -> EventDict:
    """Inspect the call stack and return metadata for the first non-internal frame.

    This function walks the Python traceback to skip over frames belonging to logging
    or internal structlog modules, then returns a dictionary with keys:
    - module: module name
    - lineno: line number in the source file
    - funcName: name of the function containing the call

    Returns:
        EventDict: Mapping of caller metadata with keys 'module', 'lineno',
            and 'funcName'.

    """
    tb = traceback.extract_stack()

    skip_modules = {"structlog", "logger", __name__.split(".")[-1]}

    for frame in reversed(tb[:-1]):
        module_name = frame.filename.split("/")[-1].replace(".py", "")
        if not any(skip in frame.filename for skip in skip_modules):
            return {
                "module": module_name,
                "lineno": frame.lineno,
                "funcName": frame.name,
            }

    return {
        "module": "unknown",
        "lineno": 0,
        "funcName": "unknown",
    }


def _get_system_info() -> EventDict:
    """Gather current thread and process identifiers.

    Returns:
        EventDict: A dictionary containing:
            - thread: current thread identifier (int)
            - threadName: name of the current thread (str)
            - processName: name of the current process (usually 'MainProcess')
            - process: process ID (int)

    """
    current_thread = threading.current_thread()
    return {
        "thread": current_thread.ident,
        "threadName": current_thread.name,
        "processName": "MainProcess",
        "process": os.getpid(),
    }


def _format_exception(event_dict: EventDict) -> str:
    """Format exception information from the event dictionary.

    If 'exc_info' is set, returns the full traceback. Otherwise, if 'exception'
    is provided, returns its string representation. If neither is present, returns
    the most recent formatted stack trace.

    Args:
        event_dict (EventDict): Dictionary potentially containing 'exc_info'
            or 'exception'.

    Returns:
        str: The formatted exception stack trace or message.

    """
    if event_dict.get("exc_info"):
        return traceback.format_exc()
    if "exception" in event_dict:
        return str(event_dict.get("exception", ""))
    return traceback.format_exc()


def add_package_fields(
    logger: Logger,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: EventDict,
) -> EventDict:
    """Process log event and add custom fields for akko package.

    This function adds caller information, system information, timestamps,
    package name, and handles exceptions and call stacks.

    Args:
        logger (Logger): The logger instance.
        method_name (str): The name of the method being logged.
        event_dict (EventDict): The event dictionary containing log data.

    Returns:
        EventDict: The updated event dictionary with additional fields.

    """
    # Get caller information
    caller_info = _get_caller_info()
    event_dict.update(caller_info)

    # Add system information
    event_dict.update(_get_system_info())

    # Add timestamps
    now = datetime.now()
    event_dict["created"] = now.timestamp()
    event_dict["time"] = now.isoformat()

    # Add package name and args
    event_dict["name"] = "akko"
    event_dict["args"] = event_dict.get("args", [])

    # Handle level naming
    if "level" in event_dict:
        event_dict["levelname"] = event_dict.pop("level").upper()

    # Rename 'event' to 'message'
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")

    # Handle exceptions and call stacks
    if any(key in event_dict for key in ["exception", "exc_info", "exc_type"]):
        event_dict["call_stack"] = _format_exception(event_dict)

    # Clean up None values
    return {k: v for k, v in event_dict.items() if v is not None}


def human_readable_renderer(
    logger: Logger | None,  # noqa: ARG001
    method_name: str | None,  # noqa: ARG001
    event_dict: EventDict,
) -> str:
    """Render log entries in a human-readable format.

    Format: [TIME] [LEVEL] [MODULE:FUNC:LINE] MESSAGE {EXTRA_FIELDS}

    Args:
        logger (Optional[Logger]): the logger instance, not used in this renderer.
        method_name (Optional[str]): the method name, not used in this renderer.
        event_dict (EventDict): a dictionnary of event data, typically containing
            log information.

    Returns:
        str: A formatted string representing the log entry, including timestamp,

    """
    timestamp = datetime.fromisoformat(
        event_dict.get("time", datetime.now().isoformat()),
    )
    # Milliseconds precision
    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    level = event_dict.get("levelname", "INFO")
    module = event_dict.get("module", "unknown")
    func = event_dict.get("funcName", "unknown")
    line = event_dict.get("lineno", 0)
    message = str(event_dict.get("message", ""))

    parts = [f"[{time_str}]", f"[{level:>8}]", f"[{module}:{func}:{line}]", message]

    exclude_keys = {
        "name",
        "args",
        "levelname",
        "module",
        "lineno",
        "funcName",
        "created",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "time",
        "timestamp",
        "level",
        "logger",
        "exc_info",
        "exc_type",
        "exc_value",
        "exc_traceback",
        "exception",
        "stack_info",
    }

    extra_fields = {k: v for k, v in event_dict.items() if k not in exclude_keys}

    if extra_fields:
        extra_str = " ".join(f"{k}={v}" for k, v in extra_fields.items())
        parts.append(f"{{{extra_str}}}")

    if "call_stack" in event_dict:
        parts.append(f"\n{event_dict['call_stack']}")

    return " ".join(parts)


def _create_human_formatter() -> Formatter:
    """Create a formatter that applies human-readable rendering to structlog output.

    This formatter will parse JSON messages and render them in a human-readable format.

    Returns:
        logging.Formatter: A custom formatter that renders log messages in a
            human-readable format.

    """

    class HumanReadableFormatter(Formatter):
        """Formatter for stdout readable by humans."""

        def format(self, record: LogRecord) -> str:
            try:
                data = loads(record.getMessage())
                logger: Logger | None = None
                method_name: str | None = None
                return human_readable_renderer(logger, method_name, data)
            except (JSONDecodeError, TypeError):
                return record.getMessage()

    return HumanReadableFormatter()


def _create_json_formatter() -> Formatter:
    """Create a formatter that ensures JSON output."""

    class JSONFormatter(Formatter):
        """Serialize the log records into json."""

        def format(self, record: LogRecord) -> str:
            return record.getMessage()

    return JSONFormatter()


@lru_cache(maxsize=1)
def configure_logger(
    log_level: int | str = INFO,
    output_stream: TextIO = sys.stdout,
    log_file: str | Path | None = None,
    *,
    human_readable: bool = True,
) -> None:
    """Configure structlog for the akko package.

    This function should be called once at package initialization.

    Args:
        log_level (int|str): The logging level to set for the logger.
            (default to logging.INFO).
        output_stream (Any): The stream to which logs will be written
            (default is sys.stdout).
        log_file (Optional[str|Path]): Optional path to a log file if logs should
            also be written to a file.
        human_readable (bool): If True, use a human-readable renderer instead of JSON.

    """
    if isinstance(log_level, str):
        log_level = LOG_LEVELS.get(log_level.upper(), INFO)

    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_package_fields,
        human_readable_renderer
        if human_readable
        else structlog.processors.JSONRenderer(indent=None, sort_keys=False),
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = getLogger()
    root_logger.handlers.clear()

    console_handler = StreamHandler(output_stream)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        _create_human_formatter() if human_readable else _create_json_formatter(),
    )

    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(_create_json_formatter())
        root_logger.addHandler(file_handler)

    root_logger.setLevel(log_level)


def get_logger(
    name: str | None = None, **kwargs: dict[str, Any]
) -> structlog.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (optional)
        **kwargs: Additional context to bind to the logger

    Returns:
        A configured structlog BoundLogger instance

    """
    logger = structlog.get_logger(name or "akko")
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


def get_module_logger(
    module_name: str, **kwargs: dict[str, Any]
) -> structlog.BoundLogger:
    """Get a logger for a specific module.

    Args:
        module_name: Usually _name_ from the calling module
        **kwargs: Additional context to bind to the logger

    Returns:
        A configured structlog BoundLogger instance

    """
    return get_logger(name=module_name, **kwargs)


def add_file_handler(
    log_file: str | Path,
    log_level: int | str | None = None,
    *,
    human_readable: bool = False,
) -> FileHandler:
    """Add a file handler to the existing logger configuration.

    Args:
        log_file (str | Path): The path to the log file.
        log_level (Optional[int | str]): The logging level for the file handler.
            If None, uses the root logger's level.
        human_readable (bool): If True, use a human-readable formatter.

    Returns:
        logging.FileHandler: The configured file handler.

    """
    root_logger = getLogger()

    if log_level is None:
        log_level = root_logger.level
    elif isinstance(log_level, str):
        log_level = LOG_LEVELS.get(log_level.upper(), INFO)
    else:
        log_level = INFO

    file_handler = FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)

    current_processors = structlog.get_config().get("processors", [])
    human_readable = (human_readable_renderer in current_processors) or human_readable

    if human_readable:
        file_handler.setFormatter(_create_human_formatter())
    else:
        file_handler.setFormatter(_create_json_formatter())

    root_logger.addHandler(file_handler)

    return file_handler


def remove_file_handler(handler_or_path: FileHandler | str | Path) -> bool:
    """Remove a file handler from the logger.

    Args:
        handler_or_path (logging.FileHandler | str | Path): Either a direct
            reference to the FileHandler or a string/path to the log file.

    Returns:
        bool: True if handler was found and removed, False otherwise

    """
    root_logger = getLogger()

    if isinstance(handler_or_path, FileHandler):
        if handler_or_path in root_logger.handlers:
            root_logger.removeHandler(handler_or_path)
            handler_or_path.close()
            return True
    else:
        target_path = Path(handler_or_path).resolve()
        for handler in root_logger.handlers:
            if isinstance(handler, FileHandler):
                handler_path = Path(handler.baseFilename).resolve()
                if handler_path == target_path:
                    root_logger.removeHandler(handler)
                    handler.close()
                    return True

    return False


def get_current_handlers() -> EventDict:
    """Get information about current logging handlers.

    Returns:
        EventDict: A dictionary containing information about console,
            file, and other handlers.

    """
    root_logger = getLogger()
    handlers_info: EventDict = {"console": [], "file": [], "other": []}

    for handler in root_logger.handlers:
        handler_info = {
            "type": type(handler).__name__,
            "level": getLevelName(handler.level),
        }

        if isinstance(handler, FileHandler):
            handler_info["filename"] = handler.baseFilename
            handlers_info["file"].append(handler_info)

        elif isinstance(handler, StreamHandler):
            stream = getattr(handler, "stream", None)  # pyright: ignore[reportUnknownArgumentType]
            stream_name = getattr(stream, "name", repr(stream))
            handler_info["stream"] = stream_name
            handlers_info["console"].append(handler_info)

        else:
            handlers_info["other"].append(handler_info)

    return handlers_info


def apply_structlog_to_other_packages(
    name: str,
    log_level: int | str | None = None,
) -> None:
    """Apply the main mcp-websearch logger configuration to other packages.

    Args:
        name (str): The name of the package or module to configure.
        log_level (Optional[int  |  str], optional): The logging level to set for
            the package logger. If None, it will get the mcp-websearch logger's level.
            Defaults to None.

    """
    base_package_logger = getLogger()

    if log_level is None:
        log_level = base_package_logger.level

    package_logger = getLogger(name)
    package_logger.handlers.clear()
    for handler in base_package_logger.handlers:
        package_logger.addHandler(handler)
    package_logger.setLevel(log_level)
    package_logger.propagate = True
