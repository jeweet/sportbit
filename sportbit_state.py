"""Runtime-status, logging en synchronisatie."""

import threading


run_lock = threading.Lock()


last_output = ""


statuses = {}


next_lessons_cache = {}


STATUS_CACHE_SECONDS = 5 * 60


def set_last_output(output):
    global last_output
    last_output = output


def get_last_output():
    return last_output


def get_status(section):
    status = statuses.get(section)

    if status:
        return status

    return {
        "code": "onbekend",
        "css": "onbekend",
        "text": "NIET GECONTROLEERD",
        "event": None,
        "checked_at": None,
        "checked_at_ts": None,
    }


def clear_section(section):
    statuses.pop(section, None)
    next_lessons_cache.pop(section, None)
