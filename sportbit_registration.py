"""SportBit-inschrijving."""

import io
from contextlib import redirect_stdout

import notify
import sportbit_api

from sportbit_automation_state import (
    markeer_handmatig_overgeslagen,
)
from sportbit_config import (
    lees_config_parser,
)
from sportbit_dates import (
    inschrijving_open,
    parse_tijd,
    volgende_datum,
)
from sportbit_events import (
    bepaal_event_status,
    zoek_event,
)
from sportbit_logging import (
    schrijf_log,
)
from sportbit_state import (
    next_lessons_cache,
    run_lock,
    set_last_output,
    statuses,
)


def _log(
    output,
    bericht,
    onderwerp,
    niveau="info",
):
    """Schrijf naar het permanente log en optioneel naar de laatste output."""

    schrijf_log(
        bericht,
        niveau=niveau,
        onderwerp=onderwerp,
    )

    if output is not None:
        print(
            f"[{onderwerp}] {bericht}",
            file=output,
        )


def vernieuw_status(
    session,
    section,
    datum,
    les,
    tijd,
    output=None,
):
    """
    Haal de actuele status opnieuw op bij SportBit
    en werk de bestaande status-cache bij.

    Geeft de nieuwe status terug, of None wanneer
    het event niet gevonden kan worden.
    """

    tijd_weergave = tijd.strftime(
        "%H:%M"
    )

    _log(
        output,
        f"{les} {datum} {tijd_weergave} "
        "→ actuele status ophalen",
        "status",
    )

    event = zoek_event(
        session=session,
        datum=datum,
        les=les,
        tijd=tijd,
    )

    if event is None:

        _log(
            output,
            f"{les} {datum} {tijd_weergave} "
            "→ event niet gevonden",
            "status",
            niveau="warning",
        )

        return None

    status = bepaal_event_status(
        event,
        datum,
    )

    statuses[
        section
    ] = status

    # Oude lessen-cache wissen zodat de homepage
    # direct de actuele status gebruikt.
    next_lessons_cache.pop(
        section,
        None,
    )

    _log(
        output,
        f"{les} {datum} {tijd_weergave} "
        f"→ {status.get('text', status)}",
        "status",
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

    tijd_weergave = tijd.strftime(
        "%H:%M"
    )

    # ---------------------------------------------------------
    # Bescherming tegen directe/automatische aanroepen
    # ---------------------------------------------------------

    if not inschrijving_open(
        datum
    ):

        schrijf_log(
            f"{les} {datum} {tijd_weergave} "
            "→ registratie nog niet open",
            onderwerp="inschrijving",
        )

        return False

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    "→ gestart",
                    "inschrijving",
                )

                session = (
                    sportbit_api.create_session()
                )

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

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    f"→ event gevonden "
                    f"({deelnemers}/{maximum})",
                    "inschrijving",
                )

                if event.get(
                    "aangemeld"
                ):

                    _log(
                        output,
                        f"{les} {datum} {tijd_weergave} "
                        "→ al ingeschreven",
                        "inschrijving",
                    )

                    resultaat = True

                elif event.get(
                    "opWachtlijst"
                ):

                    _log(
                        output,
                        f"{les} {datum} {tijd_weergave} "
                        "→ al op wachtlijst",
                        "inschrijving",
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

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    "→ succesvol",
                    "inschrijving",
                )


                try:

                    notify.notify_inschrijving_gelukt(
                        section=section,
                        datum=datum,
                        les=les,
                        tijd=tijd,
                )

                except Exception as notify_error:

                    _log(
                        output,
                        f"Succesnotificatie mislukt: "
                        f"{notify_error}",
                        "notificatie",
                        niveau="error",
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
                        output=output,
                    )

                except Exception as status_error:

                    _log(
                        output,
                        f"{les} {datum} {tijd_weergave} "
                        f"→ status ophalen mislukt: "
                        f"{status_error}",
                        "status",
                        niveau="warning",
                    )

    except Exception as error:

        _log(
            output,
            f"{les} {datum} {tijd_weergave} "
            f"→ fout: {error}",
            "inschrijving",
            niveau="error",
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

            _log(
                output,
                f"Inschrijving mislukt: "
                f"{notify_error}",
                "notificatie",
                niveau="error",
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

    tijd_weergave = tijd.strftime(
        "%H:%M"
    )

    output = io.StringIO()

    resultaat = False

    try:

        with run_lock:

            with redirect_stdout(output):

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    "→ gestart",
                    "uitschrijving",
                )

                session = (
                    sportbit_api.create_session()
                )

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

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    f"→ event gevonden "
                    f"(aangemeld="
                    f"{event.get('aangemeld')}, "
                    f"wachtlijst="
                    f"{event.get('opWachtlijst')})",
                    "uitschrijving",
                )

                if (
                    not event.get(
                        "aangemeld"
                    )
                    and not event.get(
                        "opWachtlijst"
                    )
                ):

                    _log(
                        output,
                        f"{les} {datum} {tijd_weergave} "
                        "→ al niet ingeschreven",
                        "uitschrijving",
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

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    "→ succesvol",
                    "uitschrijving",
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

                _log(
                    output,
                    f"{les} {datum} {tijd_weergave} "
                    "→ automatische herinschrijving "
                    "geblokkeerd",
                    "scheduler",
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
                        output=output,
                    )

                except Exception as status_error:

                    _log(
                        output,
                        f"{les} {datum} {tijd_weergave} "
                        f"→ status ophalen mislukt: "
                        f"{status_error}",
                        "status",
                        niveau="warning",
                    )

    except Exception as error:

        _log(
            output,
            f"{les} {datum} {tijd_weergave} "
            f"→ fout: {error}",
            "uitschrijving",
            niveau="error",
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

            _log(
                output,
                f"Uitschrijving mislukt: "
                f"{notify_error}",
                "notificatie",
                niveau="error",
            )

        raise

    log = output.getvalue()

    set_last_output(
        log
    )

    return resultaat
