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

    print(
        f"[STATUS] {les} {datum} {tijd.strftime('%H:%M')} "
        "→ actuele status ophalen"
    )

    event = zoek_event(
        session=session,
        datum=datum,
        les=les,
        tijd=tijd,
    )

    if event is None:

        print(
            f"[STATUS] {les} {datum} {tijd.strftime('%H:%M')} "
            "→ event niet gevonden"
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
        f"[STATUS] {les} {datum} {tijd.strftime('%H:%M')} "
        f"→ {status}"
    )

    return status


def voer_inschrijving_uit(
    section,
    doel=None,
):
    """
    Voer de SportBit-inschrijving uit.

    `doel` is optioneel en mag een concrete datetime zijn.
    Wanneer `doel` niet wordt meegegeven, wordt zoals voorheen
    de eerstvolgende les volgens de configuratie gebruikt.

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

    # ---------------------------------------------------------
    # Concrete doel-les bepalen
    # ---------------------------------------------------------

    if doel is None:

        doel = volgende_datum(
            dag,
            tijd,
        )

        if doel is None:
            raise RuntimeError(
                "Kon doelmoment niet bepalen."
            )

    datum = doel.date()
    tijd_weergave = tijd.strftime("%H:%M")

    # ---------------------------------------------------------
    # Bescherming tegen directe/automatische aanroepen
    # ---------------------------------------------------------

    if not inschrijving_open(datum):

        print(
            f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
            "→ registratie nog niet open"
        )

        return False

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                print(
                    f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
                    "→ gestart"
                )

                session = sportbit_api.create_session()

                sportbit_api.login(
                    session
                )

                event = zoek_event(
                    session=session,
                    datum=datum,
                    les=les,
                    tijd=tijd,
                )

                if event is None:

                    raise RuntimeError(
                        f"Geen '{les}' gevonden om "
                        f"{tijd_weergave} op {datum}. "
                        "Mogelijk is de les gewijzigd, "
                        "geannuleerd of vervangen "
                        "(bijvoorbeeld feestdag/kerstWOD)."
                    )

                deelnemers = event.get(
                    "aantalDeelnemers",
                    "-",
                )

                maximum = event.get(
                    "maxDeelnemers",
                    "-",
                )

                print(
                    f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
                    f"→ event gevonden ({deelnemers}/{maximum})"
                )

                if event.get("aangemeld"):

                    print(
                        f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
                        "→ al ingeschreven"
                    )

                    resultaat = True

                elif event.get("opWachtlijst"):

                    print(
                        f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
                        "→ al op wachtlijst"
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
                    f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
                    "→ succesvol"
                )

                # -------------------------------------------------
                # Direct na de actie actuele status ophalen
                # -------------------------------------------------

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
                        f"[STATUS] {les} {datum} {tijd_weergave} "
                        f"→ status ophalen mislukt: {status_error}"
                    )

    except Exception as error:

        print(
            f"[INSCHRIJVING] {les} {datum} {tijd_weergave} "
            f"→ fout: {error}"
        )

        log = output.getvalue()

        set_last_output(
            log
        )

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
                f"[NOTIFICATIE] Inschrijving mislukt: "
                f"{notify_error}"
            )

        raise

    log = output.getvalue()

    set_last_output(
        log
    )

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

    tijd_weergave = tijd.strftime("%H:%M")

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                print(
                    f"[UITSCHRIJVING] {les} {datum} {tijd_weergave} "
                    "→ gestart"
                )

                session = sportbit_api.create_session()

                sportbit_api.login(
                    session
                )

                event = zoek_event(
                    session=session,
                    datum=datum,
                    les=les,
                    tijd=tijd,
                )

                if event is None:

                    raise RuntimeError(
                        f"Geen '{les}' gevonden om "
                        f"{tijd_weergave} op {datum}."
                    )

                print(
                    f"[UITSCHRIJVING] {les} {datum} {tijd_weergave} "
                    f"→ event gevonden "
                    f"(aangemeld={event.get('aangemeld')}, "
                    f"wachtlijst={event.get('opWachtlijst')})"
                )

                if (
                    not event.get("aangemeld")
                    and not event.get("opWachtlijst")
                ):

                    print(
                        f"[UITSCHRIJVING] {les} {datum} {tijd_weergave} "
                        "→ al niet ingeschreven"
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
                    f"[UITSCHRIJVING] {les} {datum} {tijd_weergave} "
                    "→ succesvol"
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

                print(
                    f"[SKIP] {les} {datum} {tijd_weergave} "
                    "→ automatische herinschrijving geblokkeerd"
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
                        f"[STATUS] {les} {datum} {tijd_weergave} "
                        f"→ status ophalen mislukt: {status_error}"
                    )

    except Exception as error:

        print(
            f"[UITSCHRIJVING] {les} {datum} {tijd_weergave} "
            f"→ fout: {error}"
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
                f"[NOTIFICATIE] Uitschrijving mislukt: "
                f"{notify_error}"
            )

        raise

    log = output.getvalue()

    set_last_output(
        log
    )

    return resultaat
