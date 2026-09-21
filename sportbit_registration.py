"""SportBit-inschrijving."""

import io
from contextlib import redirect_stdout

import sportbit_api
import notify

from sportbit_config import lees_config_parser
from sportbit_dates import (
    inschrijving_open,
    parse_tijd,
    volgende_datum,
)
from sportbit_events import (
    bepaal_event_status,
    zoek_event,
)
from sportbit_automation_state import markeer_handmatig_overgeslagen

from sportbit_state import (
    run_lock,
    set_last_output,
    next_lessons_cache,
    statuses,
)


def vernieuw_status(
    session,
    section,
    datum,
    les,
    tijd,
):
    """
    Haal de actuele status opnieuw op bij SportBit
    en werk de bestaande status-cache bij.

    Geeft de nieuwe status terug, of None wanneer
    het event niet gevonden kan worden.
    """

    print()
    print("Status opnieuw ophalen...")

    event = zoek_event(
        session=session,
        datum=datum,
        les=les,
        tijd=tijd,
    )

    if event is None:
        print(
            "Event niet gevonden bij statuscontrole."
        )
        return None

    status = bepaal_event_status(
        event,
        datum,
    )

    statuses[section] = status

    # Oude lessen-cache wissen zodat de homepage
    # direct de actuele status gebruikt.
    next_lessons_cache.pop(
        section,
        None,
    )

    print(
        "Status bijgewerkt: "
        f"{status}"
    )

    return status


def voer_inschrijving_uit(section):
    """
    Voer de SportBit-inschrijving uit.

    Geeft True terug bij succes.
    """

    config = lees_config_parser()

    if section not in config:
        raise RuntimeError(
            f"Onbekende inschrijving: {section}"
        )

    dag = config.get(
        section,
        "dag",
    ).strip().lower()

    tijd_string = config.get(
        section,
        "tijd",
    ).strip()

    les = config.get(
        section,
        "les",
    ).strip()

    tijd = parse_tijd(
        tijd_string
    )

    doel = volgende_datum(
        dag,
        tijd,
    )

    if doel is None:
        raise RuntimeError(
            "Kon doelmoment niet bepalen."
        )

    # Bescherm directe/automatische aanroepen.
    if not inschrijving_open(
        doel.date()
    ):
        return False

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                print("=" * 50)
                print(
                    f"Inschrijven: {section}"
                )
                print(f"Les   : {les}")
                print(
                    f"Datum : {doel.date()}"
                )
                print(
                    f"Tijd  : {tijd.strftime('%H:%M')}"
                )
                print()

                session = sportbit_api.create_session()

                sportbit_api.login(session)

                event = zoek_event(
                    session=session,
                    datum=doel.date(),
                    les=les,
                    tijd=tijd,
                )

                if event is None:

                    raise RuntimeError(
                        f"Geen '{les}' gevonden om "
                        f"{tijd.strftime('%H:%M')} "
                        f"op {doel.date()}. "
                        "Mogelijk is de les gewijzigd, "
                        "geannuleerd of vervangen "
                        "(bijvoorbeeld feestdag/kerstWOD)."
                    )

                print("Event gevonden:")

                print(
                    f"  ID         : {event.get('id')}"
                )

                print(
                    f"  Titel      : {event.get('titel')}"
                )

                print(
                    f"  Start      : {event.get('start')}"
                )

                print(
                    "  Deelnemers : "
                    f"{event.get('aantalDeelnemers')}"
                )

                print(
                    "  Maximum    : "
                    f"{event.get('maxDeelnemers')}"
                )

                if event.get("aangemeld"):

                    print(
                        "\nJe bent al aangemeld."
                    )

                    resultaat = True

                elif event.get("opWachtlijst"):

                    print(
                        "\nJe staat al op de wachtlijst."
                    )

                    resultaat = True

                else:

                    resultaat = (
                        sportbit_api.inschrijven(
                            session,
                            event,
                        )
                    )

                if not resultaat:

                    raise RuntimeError(
                        "SportBit heeft de "
                        "inschrijving niet bevestigd."
                    )

                print(
                    "\nInschrijving succesvol."
                )

                # Direct na de actie de actuele status
                # opnieuw bij SportBit ophalen.
                try:

                    vernieuw_status(
                        session=session,
                        section=section,
                        datum=doel.date(),
                        les=les,
                        tijd=tijd,
                    )

                except Exception as status_error:

                    print(
                        "Status opnieuw ophalen mislukt: "
                        f"{status_error}"
                    )

    except Exception as error:

        print(
            f"\nFout: {error}"
        )

        log = output.getvalue()

        set_last_output(log)

        try:

            notify.notify_inschrijving_mislukt(
                section=section,
                les=les,
                datum=doel.date(),
                tijd=tijd,
                reden=str(error),
                log=log,
            )

        except Exception as notify_error:

            print(
                "\nNotificatie mislukt: "
                f"{notify_error}"
            )

        raise

    log = output.getvalue()

    set_last_output(log)

    return resultaat


def uitschrijven_les(
    section,
    datum,
):
    """
    Schrijf de gebruiker uit voor een specifieke les.

    `datum` moet een datetime.date zijn.

    Geeft True terug bij succes.
    """

    config = lees_config_parser()

    if section not in config:
        raise RuntimeError(
            f"Onbekende inschrijving: {section}"
        )

    tijd_string = config.get(
        section,
        "tijd",
    ).strip()

    les = config.get(
        section,
        "les",
    ).strip()

    tijd = parse_tijd(
        tijd_string
    )

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                print("=" * 50)
                print(
                    f"Uitschrijven: {section}"
                )
                print(f"Les   : {les}")
                print(
                    f"Datum : {datum}"
                )
                print(
                    f"Tijd  : {tijd.strftime('%H:%M')}"
                )
                print()

                session = sportbit_api.create_session()

                sportbit_api.login(session)

                event = zoek_event(
                    session=session,
                    datum=datum,
                    les=les,
                    tijd=tijd,
                )

                if event is None:

                    raise RuntimeError(
                        f"Geen '{les}' gevonden om "
                        f"{tijd.strftime('%H:%M')} "
                        f"op {datum}."
                    )

                print("Event gevonden:")

                print(
                    f"  ID         : {event.get('id')}"
                )

                print(
                    f"  Titel      : {event.get('titel')}"
                )

                print(
                    f"  Start      : {event.get('start')}"
                )

                print(
                    "  Aangemeld  : "
                    f"{event.get('aangemeld')}"
                )

                print(
                    "  Wachtlijst : "
                    f"{event.get('opWachtlijst')}"
                )

                if (
                    not event.get("aangemeld")
                    and not event.get("opWachtlijst")
                ):

                    print(
                        "\nJe bent niet ingeschreven "
                        "voor deze les."
                    )

                    resultaat = True

                else:

                    resultaat = (
                        sportbit_api.uitschrijven(
                            session,
                            event,
                        )
                    )

                if not resultaat:

                    raise RuntimeError(
                        "SportBit heeft de "
                        "uitschrijving niet bevestigd."
                    )

                print(
                    "\nUitschrijving succesvol."
                )

                # Een handmatige uitschrijving geldt alleen voor deze
                # concrete doel-les. De scheduler mag deze les dus niet
                # later opnieuw automatisch inschrijven.
                markeer_handmatig_overgeslagen(
                    section=section,
                    datum=datum,
                    les=les,
                    tijd=tijd,
                )

                # Direct na de DELETE de actuele status
                # opnieuw bij SportBit ophalen.
                try:

                    vernieuw_status(
                        session=session,
                        section=section,
                        datum=datum,
                        les=les,
                        tijd=tijd,
                    )

                except Exception as status_error:

                    print(
                        "Status opnieuw ophalen mislukt: "
                        f"{status_error}"
                    )

    except Exception as error:

        print(
            f"\nFout: {error}"
        )

        log = output.getvalue()

        set_last_output(log)

        try:

            notify.notify_inschrijving_mislukt(
                section=section,
                les=les,
                datum=datum,
                tijd=tijd,
                reden=str(error),
                log=log,
            )

        except Exception as notify_error:

            print(
                "\nNotificatie mislukt: "
                f"{notify_error}"
            )

        raise

    log = output.getvalue()

    set_last_output(log)

    return resultaat
