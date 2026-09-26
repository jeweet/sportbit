#!/usr/bin/env python3

"""Laagdrempelige SportBit API-laag.

Dit bestand bevat uitsluitend de ruwe HTTP-communicatie met SportBit:
een sessie opzetten, inloggen, en in-/uitschrijven voor een event.

Bewust NIET hier:
    - configuratie lezen/schrijven        -> sportbit_config.py
    - datum-/tijdlogica                   -> sportbit_dates.py
    - events zoeken en status bepalen     -> sportbit_events.py
    - een inschrijving orkestreren/loggen -> sportbit_registration.py

Zo blijft dit bestand een dunne, herbruikbare API-laag zonder
duplicatie van logica die elders al bestaat.
"""

import os
from zoneinfo import ZoneInfo

import requests

from sportbit_logging import schrijf_log


BASE_URL = "https://cfgp.sportbitapp.nl"

LOGIN_PAGE = f"{BASE_URL}/web/nl/login"
HEARTBEAT_URL = f"{BASE_URL}/cbm/api/data/heartbeat/"
LOGIN_URL = f"{BASE_URL}/cbm/api/data/inloggen/"
EVENTS_URL = f"{BASE_URL}/cbm/api/data/events/"

TIMEZONE = ZoneInfo("Europe/Amsterdam")


def create_session():
    """Maak een HTTP-sessie aan."""

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:156.0) "
            "Gecko/20100101 Firefox/156.0"
        ),
        "Accept": "application/json, text/plain, */*",
    })

    return session


def login(session):
    """Start de SportBit-sessie en log in."""

    username = os.getenv("SPORTBIT_USERNAME")
    password = os.getenv("SPORTBIT_PASSWORD")

    if not username:
        raise RuntimeError(
            "SPORTBIT_USERNAME ontbreekt in .env"
        )

    if not password:
        raise RuntimeError(
            "SPORTBIT_PASSWORD ontbreekt in .env"
        )

    # ---------------------------------------------------------
    # 1. Loginpagina openen
    # ---------------------------------------------------------

    schrijf_log(
        "Loginpagina ophalen...",
        onderwerp="sportbit",
    )

    response = session.get(
        LOGIN_PAGE,
        timeout=15,
    )

    response.raise_for_status()

    # ---------------------------------------------------------
    # 2. Heartbeat
    # ---------------------------------------------------------

    schrijf_log(
        "Heartbeat uitvoeren...",
        onderwerp="sportbit",
    )

    response = session.get(
        HEARTBEAT_URL,
        params={
            "taalIso": "nl",
        },
        headers={
            "Origin": BASE_URL,
            "Referer": LOGIN_PAGE,
        },
        timeout=15,
    )

    response.raise_for_status()

    xsrf = session.cookies.get("XSRF-TOKEN")

    if not xsrf:
        raise RuntimeError(
            "Heartbeat heeft geen XSRF-TOKEN opgeleverd."
        )

    schrijf_log(
        "XSRF-token ontvangen.",
        onderwerp="sportbit",
    )

    # ---------------------------------------------------------
    # 3. Inloggen
    # ---------------------------------------------------------

    schrijf_log(
        "Inloggen...",
        onderwerp="sportbit",
    )

    response = session.post(
        LOGIN_URL,
        json={
            "username": username,
            "password": password,
            "remember": False,
        },
        headers={
            "X-XSRF-TOKEN": xsrf,
            "Origin": BASE_URL,
            "Referer": LOGIN_PAGE,
        },
        timeout=15,
    )

    if response.status_code != 200:
        schrijf_log(
            f"Login mislukt: HTTP {response.status_code}",
            niveau="error",
            onderwerp="sportbit",
        )
        response.raise_for_status()

    schrijf_log(
        "Login geslaagd.",
        onderwerp="sportbit",
    )


def inschrijven(session, event):
    """Schrijf de gebruiker in voor het event."""

    event_id = event.get("id")

    if not event_id:
        raise RuntimeError("Event heeft geen ID.")

    url = f"{EVENTS_URL}{event_id}/deelname/"

    # Gebruik altijd de meest recente XSRF-token uit de cookies.
    xsrf = session.cookies.get("XSRF-TOKEN")

    if not xsrf:
        raise RuntimeError(
            "Geen XSRF-TOKEN aanwezig vóór deelname-POST."
        )

    schrijf_log(
        f"Inschrijven voor '{event.get('titel')}' "
        f"(ID {event_id})...",
        onderwerp="sportbit",
    )

    response = session.post(
        url,
        json={},
        headers={
            "X-XSRF-TOKEN": xsrf,
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/web/nl/",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=15,
    )

    if response.status_code == 204:
        schrijf_log(
            "Succesvol ingeschreven!",
            onderwerp="sportbit",
        )
        return True

    if response.status_code == 200:
        schrijf_log(
            "Inschrijving geaccepteerd (HTTP 200).",
            onderwerp="sportbit",
        )
        return True

    schrijf_log(
        f"Inschrijving mislukt: HTTP {response.status_code}",
        niveau="error",
        onderwerp="sportbit",
    )

    return False


def uitschrijven(session, event):
    """Schrijf de gebruiker uit voor het event."""

    event_id = event.get("id")

    if not event_id:
        raise RuntimeError("Event heeft geen ID.")

    url = f"{EVENTS_URL}{event_id}/deelname/"

    # Gebruik altijd de meest recente XSRF-token uit de cookies.
    xsrf = session.cookies.get("XSRF-TOKEN")

    if not xsrf:
        raise RuntimeError(
            "Geen XSRF-TOKEN aanwezig vóór uitschrijf-DELETE."
        )

    schrijf_log(
        f"Uitschrijven voor '{event.get('titel')}' "
        f"(ID {event_id})...",
        onderwerp="sportbit",
    )

    response = session.delete(
        url,
        headers={
            "X-XSRF-TOKEN": xsrf,
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/web/nl/",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=15,
    )

    if response.status_code == 204:
        schrijf_log(
            "Succesvol uitgeschreven!",
            onderwerp="sportbit",
        )
        return True

    if response.status_code == 200:
        schrijf_log(
            "Uitschrijving geaccepteerd (HTTP 200).",
            onderwerp="sportbit",
        )
        return True

    schrijf_log(
        f"Uitschrijven mislukt: HTTP {response.status_code}",
        niveau="error",
        onderwerp="sportbit",
    )

    return False
