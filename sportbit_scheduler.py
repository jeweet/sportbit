import configparser
import threading
import time as time_module
from datetime import datetime, timedelta

import notify
import sportbit2

from sportbit_config import CONFIG_FILE
from sportbit_dates import (
    DAGEN,
    parse_tijd,
    volgende_datum,
)
from sportbit_events import zoek_event
from sportbit_state import run_lock


def controleer_verwachte_lessen_en_mail():
    """
    Controleer rond 00:01 de lessen waarvoor
    vandaag boeken opent.
    """

    config = configparser.ConfigParser()

    config.read(
        CONFIG_FILE,
        encoding="utf-8",
    )

    vandaag = datetime.now(
        sportbit2.TIMEZONE
    ).date()

    for section in config.sections():

        if not section.startswith(
            "inschrijving_"
        ):
            continue

        try:

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

            if dag not in DAGEN or not les:
                continue

            doel = volgende_datum(
                dag,
                tijd,
            )

            if (
                doel is None
                or (
                    doel.date()
                    - timedelta(days=7)
                    != vandaag
                )
            ):
                continue

            with run_lock:

                session = (
                    sportbit2.create_session()
                )

                sportbit2.login(session)

                event = zoek_event(
                    session=session,
                    datum=doel.date(),
                    les=les,
                    tijd=tijd,
                )

            if event is None:

                notify.notify_les_ontbreekt(
                    section=section,
                    les=les,
                    datum=doel.date(),
                    tijd=tijd,
                )

        except Exception as error:

            # Een technische fout is geen bewijs
            # dat de les ontbreekt.
            print(
                f"Dagelijkse lescontrole "
                f"mislukt voor {section}: {error}"
            )


def start_dagelijkse_controle():
    """
    Start één achtergrondthread die dagelijks
    rond 00:01 controleert.
    """

    def worker():

        laatste_controle_datum = None

        while True:

            try:

                nu = datetime.now(
                    sportbit2.TIMEZONE
                )

                vandaag = nu.date()

                if (
                    nu.hour == 0
                    and nu.minute >= 1
                    and laatste_controle_datum
                    != vandaag
                ):

                    controleer_verwachte_lessen_en_mail()

                    laatste_controle_datum = (
                        vandaag
                    )

                time_module.sleep(20)

            except Exception as error:

                print(
                    f"Dagelijkse scheduler-fout: "
                    f"{error}"
                )

                time_module.sleep(20)

    thread = threading.Thread(
        target=worker,
        name="sportbit-dagelijkse-controle",
        daemon=True,
    )

    thread.start()

    return thread
