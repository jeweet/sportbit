"""SportBit-agenda: ICS-feed en logging."""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from sportbit_logging import schrijf_log


def _log(bericht, niveau=None):
    """Log een agendabericht via de centrale logger."""
    if niveau:
        schrijf_log(
            bericht,
            onderwerp="agenda",
            niveau=niveau,
        )
    else:
        schrijf_log(
            bericht,
            onderwerp="agenda",
        )


def is_calendar_event(event):
    """True voor inschrijving of wachtlijst; anders False."""
    return bool(
        event
        and (
            event.get("aangemeld")
            or event.get("opWachtlijst")
        )
    )


def escape_ics(value):
    """Escape tekst volgens het iCalendar-formaat."""
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def format_ics_datetime(value):
    """Zet een ISO-datum om naar een iCalendar-datum/tijd."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)

    if not isinstance(value, datetime):
        raise ValueError("Ongeldige event-starttijd")

    if value.tzinfo is None:
        return value.strftime("%Y%m%dT%H%M%S"), False

    return (
        value.astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        ),
        True,
    )



def maak_vevent(event):
    """Maak één VEVENT voor een SportBit-les."""
    startwaarde = event.get("start")
    eindwaarde = event.get("eind")

    if not startwaarde:
        _log(
            "Event overgeslagen: geen starttijd aanwezig.",
            "warning",
        )
        return None

    try:
        start, utc = format_ics_datetime(startwaarde)

    except (TypeError, ValueError) as error:
        _log(
            f"Event overgeslagen: ongeldige starttijd ({error}).",
            "warning",
        )
        return None

    eindregel = None

    if eindwaarde:
        try:
            eind, eind_utc = format_ics_datetime(
                eindwaarde
            )

            if eind_utc != utc:
                raise ValueError(
                    "Start- en eindtijd hebben verschillende tijdformaten."
                )

            eindregel = (
                f"DTEND:{eind}"
                if eind_utc
                else f"DTEND;TZID=Europe/Amsterdam:{eind}"
            )

        except (TypeError, ValueError) as error:
            _log(
                f"Ongeldige eindtijd; DTEND weggelaten ({error}).",
                "warning",
            )

    titel = str(
        event.get("titel") or "SportBit-les"
    ).strip()

    event_id = event.get("id")

    uid_basis = (
        f"sportbit:{event_id}"
        if event_id is not None
        else f"sportbit:{titel}:{start}"
    )

    uid = str(
        uuid5(
            NAMESPACE_URL,
            uid_basis,
        )
    )

    tentative = bool(
        event.get("_tentative")
    )

    wachtlijst = bool(
        event.get("opWachtlijst")
    )

    if tentative:
        status = "Voorlopig"
        ics_status = "TENTATIVE"
        samenvatting = f"{titel} (voorlopig)"
        beschrijving = "Nog niet ingeschreven"

    elif wachtlijst:
        status = "Wachtlijst"
        ics_status = "TENTATIVE"
        samenvatting = titel
        beschrijving = "SportBit-status: Wachtlijst"

    else:
        status = "Ingeschreven"
        ics_status = "CONFIRMED"
        samenvatting = titel
        beschrijving = "SportBit-status: Ingeschreven"

    dtstamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    tijdregel = (
        f"DTSTART:{start}"
        if utc
        else f"DTSTART;TZID=Europe/Amsterdam:{start}"
    )

    regels = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"STATUS:{ics_status}",
        tijdregel,
    ]

    if eindregel:
        regels.append(eindregel)

    regels.extend([
        f"SUMMARY:{escape_ics(samenvatting)}",
        f"DESCRIPTION:{escape_ics(beschrijving)}",
        "END:VEVENT",
    ])

    return regels


def maak_ics(events):
    """
    Maak een complete ICS-feed.

    Alleen aangemelde lessen en wachtlijstplekken worden opgenomen.
    """
    _log("ICS-feed genereren: gestart.")

    regels = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SportBit//Agenda//NL",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SportBit",
        "X-WR-TIMEZONE:Europe/Amsterdam",
    ]

    aantal_totaal = 0
    aantal_opgenomen = 0
    aantal_overgeslagen = 0

    try:
        for event in events:
            aantal_totaal += 1

            if not is_calendar_event(event) and not event.get("_tentative"):
                aantal_overgeslagen += 1
                continue

            vevent = maak_vevent(event)

            if vevent:
                regels.extend(vevent)
                aantal_opgenomen += 1
            else:
                aantal_overgeslagen += 1

        regels.append("END:VCALENDAR")

        resultaat = "\r\n".join(regels) + "\r\n"

        _log(
            "ICS-feed genereren: voltooid | "
            f"events ontvangen: {aantal_totaal} | "
            f"opgenomen: {aantal_opgenomen} | "
            f"overgeslagen: {aantal_overgeslagen}"
        )

        return resultaat

    except Exception as error:
        _log(
            f"ICS-feed genereren mislukt: {error}",
            "exception",
        )
        raise
