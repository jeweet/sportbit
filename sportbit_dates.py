"""Datum- en tijdlogica voor SportBit."""

from datetime import datetime, timedelta


import sportbit_api


DAGEN = {
    "maandag": 0,
    "dinsdag": 1,
    "woensdag": 2,
    "donderdag": 3,
    "vrijdag": 4,
    "zaterdag": 5,
    "zondag": 6,
}


def parse_tijd(tijd):
    """
    Zet een tijd om naar datetime.time.

    Accepteert:
        "07:00"
        datetime.time(...)
    """

    if isinstance(tijd, str):

        try:
            return datetime.strptime(
                tijd.strip(),
                "%H:%M",
            ).time()

        except ValueError:
            raise ValueError(
                f"Ongeldige tijd: {tijd}. "
                f"Gebruik HH:MM."
            )

    # datetime.time is al een geldige tijd.
    if hasattr(tijd, "hour") and hasattr(
        tijd,
        "minute",
    ):
        return tijd

    raise ValueError(
        f"Ongeldig tijdstype: "
        f"{type(tijd).__name__}"
    )


def volgende_datum(dag, tijd):
    """
    Bepaal de eerstvolgende datum/tijd
    voor de opgegeven weekdag.

    'tijd' mag een string of datetime.time zijn.
    """

    dag = str(dag).strip().lower()

    if dag not in DAGEN:
        return None

    tijd_obj = parse_tijd(tijd)

    nu = datetime.now(
        sportbit_api.TIMEZONE
    )

    dagen_tot = (
        DAGEN[dag]
        - nu.weekday()
    ) % 7

    doel_datum = (
        nu.date()
        + timedelta(days=dagen_tot)
    )

    doel = datetime.combine(
        doel_datum,
        tijd_obj,
        tzinfo=sportbit_api.TIMEZONE,
    )

    # Als het tijdstip vandaag al voorbij is,
    # pak de volgende week.
    if doel <= nu:
        doel += timedelta(days=7)

    return doel


def inschrijving_open(datum):
    """
    Een les kan worden geboekt vanaf 00:00 op de dag
    die precies zeven dagen vóór de lesdatum ligt.
    """

    nu = datetime.now(
        sportbit_api.TIMEZONE
    )

    openingsdatum = datum - timedelta(days=7)

    openingsmoment = datetime.combine(
        openingsdatum,
        datetime.min.time(),
        tzinfo=sportbit_api.TIMEZONE,
    )

    return nu >= openingsmoment


def volgende_twee_datums(dag, tijd):
    """Geef de twee eerstvolgende lessen terug."""

    eerste = volgende_datum(
        dag,
        tijd,
    )

    if eerste is None:
        return []

    return [
        eerste,
        eerste + timedelta(days=7),
    ]
