"""SportBit event-ophaling, zoeken en statusbepaling."""

from datetime import datetime

import sportbit2

from sportbit_dates import (
    inschrijving_open,
    parse_tijd,
    volgende_twee_datums,
)
from sportbit_state import (
    STATUS_CACHE_SECONDS,
    next_lessons_cache,
    run_lock,
    statuses,
)


def extract_events(data):
    """Haal een lijst met event-dictionaries uit een SportBit-response."""

    if isinstance(data, list):

        if all(
            isinstance(x, dict)
            for x in data
        ):
            return data

    if isinstance(data, dict):

        mogelijke_keys = (
            "events",
            "data",
            "items",
            "result",
            "results",
            "ochtend",
            "middag",
            "avond",
        )

        for key in mogelijke_keys:

            value = data.get(key)

            if isinstance(value, list):

                if all(
                    isinstance(x, dict)
                    for x in value
                ):
                    return value

        # Eén niveau dieper zoeken.
        for value in data.values():

            if isinstance(value, dict):

                nested = extract_events(value)

                if nested is not None:
                    return nested

    return None


def zoek_event(
    session,
    datum,
    les,
    tijd,
):
    """Zoek een specifiek SportBit-event op datum, lesnaam en tijd."""

    tijd_obj = parse_tijd(tijd)

    print(
        f"Events ophalen voor {datum} "
        f"({les} om "
        f"{tijd_obj.strftime('%H:%M')})..."
    )

    response = session.get(
        sportbit2.EVENTS_URL,
        params={
            "datum": datum.isoformat()
        },
        headers={
            "Origin": sportbit2.BASE_URL,
            "Referer": f"{sportbit2.BASE_URL}/web/nl/",
        },
        timeout=15,
    )

    response.raise_for_status()

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "SportBit gaf geen geldige JSON terug."
        )

    events = extract_events(data)

    if events is None:
        raise RuntimeError(
            "Onverwachte events-response. "
            f"Type: {type(data).__name__}"
        )

    print(
        f"{len(events)} events ontvangen."
    )

    gewenste_les = (
        str(les)
        .strip()
        .casefold()
    )

    for event in events:

        titel = str(
            event.get(
                "titel",
                "",
            )
        ).strip()

        start_string = event.get("start")

        if not start_string:
            continue

        try:
            start = datetime.fromisoformat(
                start_string
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        if (
            titel.casefold() == gewenste_les
            and start.hour == tijd_obj.hour
            and start.minute == tijd_obj.minute
        ):
            return event

    return None


def maak_status(
    code,
    text,
    event=None,
):
    """Maak een uniform statusobject."""

    checked_at = datetime.now(
        sportbit2.TIMEZONE
    )

    return {
        "code": code,
        "css": code,
        "text": text,
        "event": event,
        "checked_at": checked_at.strftime(
            "%d-%m-%Y %H:%M:%S"
        ),
        "checked_at_ts": checked_at.timestamp(),
    }


def bepaal_event_status(event, datum):
    """Bepaal de zichtbare status van één event."""

    if event is None:
        return maak_status(
            "geen-event",
            "GEEN EVENT",
        )

    if event.get("aangemeld"):
        return maak_status(
            "ingeschreven",
            "INGESCHREVEN",
            event,
        )

    if event.get("opWachtlijst"):
        return maak_status(
            "wachtlijst",
            "WACHTLIJST",
            event,
        )

    if not inschrijving_open(datum):
        return maak_status(
            "gesloten",
            "INSCHRIJVING GESLOTEN",
            event,
        )

    return maak_status(
        "niet-ingeschreven",
        "NIET INGESCHREVEN",
        event,
    )


def automatische_volgende_twee_controle(section):
    """
    Controleer de twee eerstvolgende lessen.

    Resultaten worden maximaal vijf minuten gecachet.
    """

    bestaande = next_lessons_cache.get(section)

    if bestaande:

        checked_at_ts = bestaande.get(
            "checked_at_ts"
        )

        if checked_at_ts:

            leeftijd = (
                datetime.now(
                    sportbit2.TIMEZONE
                ).timestamp()
                - checked_at_ts
            )

            if leeftijd < STATUS_CACHE_SECONDS:
                return bestaande.get(
                    "lessen",
                    [],
                )

    from sportbit_config import lees_config_parser

    config = lees_config_parser()

    if section not in config:
        return []

    dag = config.get(
        section,
        "dag",
    ).strip().lower()

    tijd = parse_tijd(
        config.get(
            section,
            "tijd",
        ).strip()
    )

    les = config.get(
        section,
        "les",
    ).strip()

    datums = volgende_twee_datums(
        dag,
        tijd,
    )

    if not datums:
        return []

    resultaten = []

    try:

        with run_lock:

            session = sportbit2.create_session()

            sportbit2.login(session)

            for doel in datums:

                event = zoek_event(
                    session=session,
                    datum=doel.date(),
                    les=les,
                    tijd=tijd,
                )

                status = bepaal_event_status(
                    event,
                    doel.date(),
                )

                resultaten.append({
                    "datum": doel,
                    "status": status,
                    "event": event,
                })

    except Exception:

        if bestaande and bestaande.get("lessen"):
            return bestaande["lessen"]

        onbekend = {
            "code": "onbekend",
            "css": "onbekend",
            "text": "STATUS ONBEKEND",
            "event": None,
            "checked_at": None,
            "checked_at_ts": None,
        }

        # Bug uit de originele versie opgelost:
        # hier werd 'datum' gebruikt terwijl die variabele
        # niet bestond. We gebruiken nu 'doel'.

        return [
            {
                "datum": doel,
                "status": onbekend,
                "event": None,
            }
            for doel in datums
        ]

    now_ts = datetime.now(
        sportbit2.TIMEZONE
    ).timestamp()

    next_lessons_cache[section] = {
        "lessen": resultaten,
        "checked_at_ts": now_ts,
    }

    if resultaten:
        statuses[section] = resultaten[0]["status"]

    return resultaten
