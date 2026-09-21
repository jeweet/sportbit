"""Persistente state voor automatische SportBit-acties per specifieke doel-les."""

import json
import threading
from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / ".sportbit_automation_state.json"
STATE_LOCK = threading.Lock()


def _lees_state():
    if not STATE_FILE.exists():
        return {"handled": [], "suppressed": []}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"handled": [], "suppressed": []}

    if not isinstance(data, dict):
        return {"handled": [], "suppressed": []}

    return {
        "handled": list(data.get("handled", [])),
        "suppressed": list(data.get("suppressed", [])),
    }


def _schrijf_state(data):
    tijdelijke_file = STATE_FILE.with_suffix(".tmp")
    tijdelijke_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tijdelijke_file.replace(STATE_FILE)


def doel_sleutel(section, datum, les, tijd):
    """Maak een stabiele sleutel voor één concrete doel-les."""
    if isinstance(datum, date):
        datum = datum.isoformat()
    else:
        datum = str(datum)

    return f"{section}|{datum}|{les.strip().casefold()}|{tijd.strftime('%H:%M')}"


def is_afgehandeld(section, datum, les, tijd):
    sleutel = doel_sleutel(section, datum, les, tijd)
    with STATE_LOCK:
        return sleutel in _lees_state()["handled"]


def markeer_afgehandeld(section, datum, les, tijd):
    sleutel = doel_sleutel(section, datum, les, tijd)
    with STATE_LOCK:
        data = _lees_state()
        if sleutel not in data["handled"]:
            data["handled"].append(sleutel)
        _schrijf_state(data)


def is_handmatig_overgeslagen(section, datum, les, tijd):
    sleutel = doel_sleutel(section, datum, les, tijd)
    with STATE_LOCK:
        return sleutel in _lees_state()["suppressed"]


def markeer_handmatig_overgeslagen(section, datum, les, tijd):
    """Blokkeer automatische herinschrijving voor precies deze doel-les."""
    sleutel = doel_sleutel(section, datum, les, tijd)
    with STATE_LOCK:
        data = _lees_state()
        if sleutel not in data["suppressed"]:
            data["suppressed"].append(sleutel)
        _schrijf_state(data)


def verwijder_section(section):
    """Verwijder state voor een verwijderde configuratiesectie."""
    prefix = f"{section}|"
    with STATE_LOCK:
        data = _lees_state()
        data["handled"] = [x for x in data["handled"] if not x.startswith(prefix)]
        data["suppressed"] = [x for x in data["suppressed"] if not x.startswith(prefix)]
        _schrijf_state(data)
