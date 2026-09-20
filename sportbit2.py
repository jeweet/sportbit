#!/usr/bin/env python3

import configparser
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


BASE_URL = "https://cfgp.sportbitapp.nl"

LOGIN_PAGE = f"{BASE_URL}/web/nl/login"
HEARTBEAT_URL = f"{BASE_URL}/cbm/api/data/heartbeat/"
LOGIN_URL = f"{BASE_URL}/cbm/api/data/inloggen/"
EVENTS_URL = f"{BASE_URL}/cbm/api/data/events/"

TIMEZONE = ZoneInfo("Europe/Amsterdam")

CONFIG_FILE = "sportbit.conf"

DAGEN = {
    "maandag": 0,
    "dinsdag": 1,
    "woensdag": 2,
    "donderdag": 3,
    "vrijdag": 4,
    "zaterdag": 5,
    "zondag": 6,
}


def laad_config():
    """Lees de inschrijvingen uit sportbit.conf."""

    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_FILE):
        raise RuntimeError(
            f"Configuratiebestand '{CONFIG_FILE}' bestaat niet."
        )

    config.read(CONFIG_FILE, encoding="utf-8")

    inschrijvingen = []

    for section in config.sections():

        if not section.startswith("inschrijving_"):
            continue

        if not config.has_option(section, "dag"):
            raise RuntimeError(
                f"{section}: optie 'dag' ontbreekt."
            )

        if not config.has_option(section, "tijd"):
            raise RuntimeError(
                f"{section}: optie 'tijd' ontbreekt."
            )

        if not config.has_option(section, "les"):
            raise RuntimeError(
                f"{section}: optie 'les' ontbreekt."
            )

        dag_naam = config.get(section, "dag").strip().lower()
        tijd_string = config.get(section, "tijd").strip()
        les = config.get(section, "les").strip()

        if dag_naam not in DAGEN:
            raise RuntimeError(
                f"{section}: onbekende dag '{dag_naam}'."
            )

        try:
            tijd = datetime.strptime(
                tijd_string,
                "%H:%M",
            ).time()
        except ValueError:
            raise RuntimeError(
                f"{section}: ongeldige tijd '{tijd_string}'. "
                "Gebruik bijvoorbeeld 07:00 of 10:00."
            )

        if not les:
            raise RuntimeError(
                f"{section}: 'les' mag niet leeg zijn."
            )

        inschrijvingen.append({
            "naam": section,
            "dag": dag_naam,
            "dag_nummer": DAGEN[dag_naam],
            "tijd": tijd,
            "les": les,
        })

    if not inschrijvingen:
        raise RuntimeError(
            "Geen inschrijvingen gevonden in "
            f"'{CONFIG_FILE}'."
        )

    return inschrijvingen


def eerstvolgende_dag(dag_nummer):
    """
    Geef de eerstvolgende datum terug voor de opgegeven weekdag.

    Als de gewenste dag vandaag is, wordt vandaag gebruikt wanneer
    het tijdstip nog niet verstreken is. Als het tijdstip al voorbij
    is, wordt de dag van de volgende week gebruikt.
    """

    nu = datetime.now(TIMEZONE)

    dagen_tot_dag = (
        dag_nummer - nu.weekday()
    ) % 7

    doel_datum = nu.date() + timedelta(
        days=dagen_tot_dag
    )

    return doel_datum


def doel_datum_en_tijd(inschrijving):
    """
    Bepaal de eerstvolgende datum/tijd voor een inschrijving.
    """

    nu = datetime.now(TIMEZONE)

    dag_nummer = inschrijving["dag_nummer"]
    tijd = inschrijving["tijd"]

    dagen_tot_dag = (
        dag_nummer - nu.weekday()
    ) % 7

    doel_datum = nu.date() + timedelta(
        days=dagen_tot_dag
    )

    doel_datetime = datetime.combine(
        doel_datum,
        tijd,
        tzinfo=TIMEZONE,
    )

    # Als de les vandaag al voorbij is, neem volgende week.
    if doel_datetime <= nu:
        doel_datetime += timedelta(days=7)

    return doel_datetime


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

    print("Loginpagina ophalen...")

    response = session.get(
        LOGIN_PAGE,
        timeout=15,
    )

    response.raise_for_status()

    # ---------------------------------------------------------
    # 2. Heartbeat
    # ---------------------------------------------------------

    print("Heartbeat uitvoeren...")

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

    print("XSRF-token ontvangen.")

    # ---------------------------------------------------------
    # 3. Inloggen
    # ---------------------------------------------------------

    print("Inloggen...")

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
        print(
            f"Login mislukt: HTTP {response.status_code}"
        )
        print(response.text[:1000])
        response.raise_for_status()

    print("Login geslaagd.")


def extract_events(data):
    """
    Haal de lijst met events uit de API-response.

    SportBit kan afhankelijk van de response een lijst
    rechtstreeks teruggeven of een lijst in een dictionary
    plaatsen. Omdat de exacte API-response kan verschillen,
    zoeken we recursief naar een lijst met dictionaries.
    """

    # Response is direct een lijst.
    if isinstance(data, list):
        return data

    # Response is een dictionary.
    if isinstance(data, dict):

        # Eerst bekende keys proberen.
        mogelijke_keys = (
            "events",
            "data",
            "items",
            "result",
            "results",
        )

        for key in mogelijke_keys:

            value = data.get(key)

            if isinstance(value, list):
                return value

        # Daarna automatisch zoeken naar een lijst met
        # dictionary-objecten.
        for key, value in data.items():

            if isinstance(value, list):

                if value and all(
                    isinstance(item, dict)
                    for item in value
                ):
                    print(
                        f"Events gevonden onder key: {key!r}"
                    )
                    return value

        # Soms zit de response nog dieper genest.
        for value in data.values():

            if isinstance(value, dict):

                try:
                    events = extract_events(value)

                    if events:
                        return events

                except RuntimeError:
                    pass

    raise RuntimeError(
        "Onverwachte events-response. "
        f"Type: {type(data).__name__}"
    )


def zoek_event(
    session,
    datum,
    les,
    doel_tijd,
):
    """
    Zoek een specifiek event op datum, naam en tijd.
    """

    print(
        f"Events ophalen voor {datum} "
        f"({les} om {doel_tijd.strftime('%H:%M')})..."
    )

    response = session.get(
        EVENTS_URL,
        params={
            "datum": datum.isoformat(),
        },
        headers={
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/web/nl/",
        },
        timeout=15,
    )

    if response.status_code != 200:
        print(
            f"Events ophalen mislukt: "
            f"HTTP {response.status_code}"
        )
        print(response.text[:1000])
        response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "SportBit gaf geen geldige JSON terug."
        )

    events = extract_events(data)

    print(f"{len(events)} events ontvangen.")

    for event in events:

        titel = event.get("titel", "")
        start_string = event.get("start")

        if not start_string:
            continue

        try:
            start = datetime.fromisoformat(start_string)
        except (ValueError, TypeError):
            continue

        print(
            f"  gevonden: {start.strftime('%H:%M')} - "
            f"{titel!r}"
        )

        if (
            titel.strip().casefold() == les.strip().casefold()
            and start.hour == doel_tijd.hour
            and start.minute == doel_tijd.minute
        ):

            return event

    return None


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

    print()
    print(
        f"Inschrijven voor '{event.get('titel')}' "
        f"(ID {event_id})..."
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
        print("Succesvol ingeschreven!")
        return True

    if response.status_code == 200:
        print("Inschrijving geaccepteerd (HTTP 200).")
        return True

    print(
        f"Inschrijving mislukt: HTTP {response.status_code}"
    )

    if response.text:
        print(response.text[:1000])

    return False


def verwerk_inschrijving(session, inschrijving):
    """Verwerk één inschrijving uit de configuratie."""

    doel = doel_datum_en_tijd(inschrijving)

    les = inschrijving["les"]

    print()
    print("=" * 50)
    print(
        f"{inschrijving['naam']}: "
        f"{les}"
    )
    print(
        f"Doeldatum : {doel.strftime('%Y-%m-%d')}"
    )
    print(
        f"Tijd      : {doel.strftime('%H:%M')}"
    )
    print("=" * 50)

    event = zoek_event(
        session=session,
        datum=doel.date(),
        les=les,
        doel_tijd=doel.time(),
    )

    if event is None:

        print()
        print(
            f"Geen '{les}' gevonden om "
            f"{doel.strftime('%H:%M')} "
            f"op {doel.strftime('%Y-%m-%d')}."
        )

        return False

    # ---------------------------------------------------------
    # Eventinformatie tonen
    # ---------------------------------------------------------

    print()
    print("Event gevonden:")
    print(
        f"  ID         : "
        f"{event.get('id')}"
    )
    print(
        f"  Titel      : "
        f"{event.get('titel')}"
    )
    print(
        f"  Start      : "
        f"{event.get('start')}"
    )
    print(
        f"  Deelnemers : "
        f"{event.get('aantalDeelnemers')}"
    )
    print(
        f"  Maximum    : "
        f"{event.get('maxDeelnemers')}"
    )
    print(
        f"  Aangemeld  : "
        f"{event.get('aangemeld')}"
    )
    print(
        f"  Wachtlijst : "
        f"{event.get('opWachtlijst')}"
    )

    # ---------------------------------------------------------
    # Al ingeschreven?
    # ---------------------------------------------------------

    if event.get("aangemeld"):

        print()
        print("Je bent al aangemeld.")

        return True

    # ---------------------------------------------------------
    # Al op wachtlijst?
    # ---------------------------------------------------------

    if event.get("opWachtlijst"):

        print()
        print("Je staat al op de wachtlijst.")

        return True

    # ---------------------------------------------------------
    # Inschrijven
    # ---------------------------------------------------------

    return inschrijven(
        session,
        event,
    )


def main():
    load_dotenv(
        Path(__file__).resolve().parent / ".env"
    )

    try:
        inschrijvingen = laad_config()
    except Exception as error:
        print(f"Configuratiefout: {error}")
        sys.exit(1)

    print("=" * 50)
    print("SportBit automatische inschrijving")
    print("=" * 50)

    print()
    print("Geconfigureerde inschrijvingen:")

    for inschrijving in inschrijvingen:

        doel = doel_datum_en_tijd(inschrijving)

        print(
            f"  {inschrijving['naam']}: "
            f"{inschrijving['les']} - "
            f"{doel.strftime('%A %Y-%m-%d %H:%M')}"
        )

    print()

    session = create_session()

    try:

        # -----------------------------------------------------
        # Eén keer inloggen; daarna alle inschrijvingen verwerken.
        # -----------------------------------------------------

        login(session)

        fouten = 0

        for inschrijving in inschrijvingen:

            try:

                resultaat = verwerk_inschrijving(
                    session,
                    inschrijving,
                )

                if not resultaat:
                    fouten += 1

            except requests.RequestException as error:

                fouten += 1

                print()
                print(
                    f"HTTP-fout bij "
                    f"{inschrijving['naam']}: {error}"
                )

            except Exception as error:

                fouten += 1

                print()
                print(
                    f"Fout bij "
                    f"{inschrijving['naam']}: {error}"
                )

        print()
        print("=" * 50)

        if fouten:
            print(
                f"Klaar met {fouten} fout(en)."
            )
            sys.exit(1)

        print("Alle inschrijvingen verwerkt.")

    except requests.RequestException as error:

        print()
        print(f"HTTP-fout: {error}")
        sys.exit(1)

    except Exception as error:

        print()
        print(f"Fout: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
