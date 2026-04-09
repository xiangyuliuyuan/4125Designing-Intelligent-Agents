import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_NAMESPACE = "sim"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "simulation.log"
DEFAULT_FILE_LEVEL = "INFO"
DEFAULT_CONSOLE_LEVEL = "WARNING"
DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_BACKUP_COUNT = 3
FILE_HANDLER_NAME = f"{LOG_NAMESPACE}.file"
CONSOLE_HANDLER_NAME = f"{LOG_NAMESPACE}.console"
LOG_LEVEL_NAMES = ("DEBUG", "INFO", "WARNING", "ERROR")


def _normalize_level(value, default):
    candidate = (value or default or DEFAULT_FILE_LEVEL).upper()
    if hasattr(logging, candidate):
        return getattr(logging, candidate)
    return getattr(logging, default.upper())


def _level_name(level):
    return logging.getLevelName(level)


def _find_handler(handler_name):
    logger = logging.getLogger(LOG_NAMESPACE)
    for handler in logger.handlers:
        if getattr(handler, "name", None) == handler_name:
            return handler
    return None


def _base_logger():
    logger = logging.getLogger(LOG_NAMESPACE)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def _current_tick():
    try:
        from simulation import runtime

        return getattr(runtime, "simulation_tick", 0)
    except Exception:
        return 0


def _format_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    if isinstance(value, float):
        return f"{value:.2f}"

    text = str(value)
    if any(ch.isspace() for ch in text) or any(ch in text for ch in ['"', "="]):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _coerce_logger(logger_or_name):
    if isinstance(logger_or_name, logging.Logger):
        return logger_or_name
    if not logger_or_name:
        return logging.getLogger(LOG_NAMESPACE)
    if isinstance(logger_or_name, str):
        if logger_or_name.startswith(f"{LOG_NAMESPACE}.") or logger_or_name == LOG_NAMESPACE:
            return logging.getLogger(logger_or_name)
        return logging.getLogger(f"{LOG_NAMESPACE}.{logger_or_name}")
    return logging.getLogger(LOG_NAMESPACE)


def reset_logging():
    logger = logging.getLogger(LOG_NAMESPACE)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    logger.addHandler(logging.NullHandler())
    return logger


def get_logger(name=None):
    _base_logger()
    if not name:
        return logging.getLogger(LOG_NAMESPACE)
    if name.startswith(f"{LOG_NAMESPACE}."):
        return logging.getLogger(name)
    if name == "__main__":
        return logging.getLogger(f"{LOG_NAMESPACE}.main")
    return logging.getLogger(f"{LOG_NAMESPACE}.{name}")


def log_event(level, logger_or_name, event, **fields):
    logger = _coerce_logger(logger_or_name)
    normalized_level = _normalize_level(level, DEFAULT_FILE_LEVEL)

    ordered_fields = {"tick": _current_tick(), "event": event}
    ordered_fields.update(fields)

    parts = []
    for key, value in ordered_fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")

    logger.log(normalized_level, " ".join(parts))


def configure_logging(
    log_dir=None,
    log_filename=DEFAULT_LOG_FILE,
    file_level=None,
    console_level=None,
    console_stream=None,
    max_bytes=DEFAULT_MAX_BYTES,
    backup_count=DEFAULT_BACKUP_COUNT,
    reset=False,
):
    resolved_log_dir = Path(log_dir or os.getenv("SIM_LOG_DIR", DEFAULT_LOG_DIR))
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = resolved_log_dir / log_filename

    resolved_file_level = _normalize_level(file_level or os.getenv("SIM_LOG_LEVEL"), DEFAULT_FILE_LEVEL)
    resolved_console_level = _normalize_level(
        console_level or os.getenv("SIM_CONSOLE_LOG_LEVEL"),
        DEFAULT_CONSOLE_LEVEL,
    )

    logger = logging.getLogger(LOG_NAMESPACE)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if reset or logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.name = FILE_HANDLER_NAME
    file_handler.setLevel(resolved_file_level)
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    console_handler = logging.StreamHandler(console_stream)
    console_handler.name = CONSOLE_HANDLER_NAME
    console_handler.setLevel(resolved_console_level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    log_event(
        "INFO",
        logger,
        event="logging.configured",
        file_level=_level_name(resolved_file_level),
        console_level=_level_name(resolved_console_level),
        path=log_path,
    )
    return str(log_path)


def get_logging_levels():
    file_handler = _find_handler(FILE_HANDLER_NAME)
    console_handler = _find_handler(CONSOLE_HANDLER_NAME)
    return {
        "file": _level_name(file_handler.level) if file_handler else None,
        "console": _level_name(console_handler.level) if console_handler else None,
    }


def set_file_log_level(level):
    normalized = _normalize_level(level, DEFAULT_FILE_LEVEL)
    file_handler = _find_handler(FILE_HANDLER_NAME)
    if file_handler is None:
        configure_logging(reset=True)
        file_handler = _find_handler(FILE_HANDLER_NAME)
    file_handler.setLevel(normalized)
    log_event(
        "INFO",
        get_logger(__name__),
        event="logging.file_level_changed",
        new_level=_level_name(normalized),
    )
    return _level_name(normalized)


def set_console_log_level(level):
    normalized = _normalize_level(level, DEFAULT_CONSOLE_LEVEL)
    console_handler = _find_handler(CONSOLE_HANDLER_NAME)
    if console_handler is None:
        configure_logging(reset=True)
        console_handler = _find_handler(CONSOLE_HANDLER_NAME)
    console_handler.setLevel(normalized)
    log_event(
        "INFO",
        get_logger(__name__),
        event="logging.console_level_changed",
        new_level=_level_name(normalized),
    )
    return _level_name(normalized)


_base_logger()
