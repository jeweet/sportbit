#!/usr/bin/env python3

"""Flask-webapp voor automatische SportBit-inschrijvingen."""

import os
import secrets
import importlib
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from notify import send_test_ntfy

from dotenv import dotenv_values, load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    jsonify,
    url_for,
)

from sportbit_logging import schrijf_log


# ============================================================
# PADEN / OMGEVING
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

SECRET_KEY_FILE = BASE_DIR / ".flask_secret_key"

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "sportbit.log"

load_dotenv(ENV_FILE)


# ============================================================
# INSTELLINGEN / .ENV
# ============================================================

ENV_SETTINGS = (
    "SPORTBIT_USERNAME",
    "SPORTBIT_PASSWORD",
    "NOTIFY_ENABLED",
    "NOTIFY_EMAIL_TO",
    "NOTIFY_SUCCESS_ENABLED",
    "NTFY_ENABLED",
    "NTFY_URL",
    "NTFY_TOPIC",
    "NTFY_TOKEN",
    "NTFY_NOTIFY_SUCCESS",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_USE_TLS",
    "NOTIFY_FROM",
    "WEB_USERNAME",
    "WEB_PASSWORD",
    "SPORTBIT_SCHEDULER_ENABLED",
    "SPORTBIT_SCHEDULER_TIME",
    "SPORTBIT_SCHEDULER_TIMEZONE",
)


SENSITIVE_ENV_SETTINGS = {
    "SPORTBIT_PASSWORD",
    "SMTP_PASSWORD",
    "WEB_PASSWORD",
    "NTFY_TOKEN",
}


def get_of_maak_secret_key():
    """Geef een stabiele Flask secret key terug."""

    waarde = os.getenv(
        "FLASK_SECRET_KEY",
        "",
    ).strip()

    if waarde:
        return waarde

    if SECRET_KEY_FILE.exists():

        bestaande = SECRET_KEY_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if bestaande:
            return bestaande

    nieuwe_sleutel = secrets.token_hex(32)

    tijdelijke_file = SECRET_KEY_FILE.with_suffix(
        ".tmp"
    )

    tijdelijke_file.write_text(
        nieuwe_sleutel,
        encoding="utf-8",
    )

    tijdelijke_file.replace(
        SECRET_KEY_FILE
    )

    try:
        os.chmod(
            SECRET_KEY_FILE,
            0o600,
        )
    except OSError:
        pass

    schrijf_log(
        "Geen FLASK_SECRET_KEY ingesteld: "
        f"nieuwe sleutel opgeslagen in {SECRET_KEY_FILE.name}.",
        onderwerp="app",
        niveau="warning",
    )

    return nieuwe_sleutel


def lees_instellingen():

    waarden = dotenv_values(
        ENV_FILE
    )

    settings = {}

    for naam in ENV_SETTINGS:

        waarde = waarden.get(
            naam,
            "",
        )

        if waarde is None:
            waarde = ""

        if naam in SENSITIVE_ENV_SETTINGS:

            settings[naam] = ""

            settings[
                f"{naam}_PLACEHOLDER"
            ] = (
                "Ingesteld — leeg laten om te behouden"
                if waarde
                else
                "Niet ingesteld"
            )

        else:

            settings[naam] = str(
                waarde
            )

    return settings


def sla_instellingen_op():

    waarden = dotenv_values(
        ENV_FILE
    )

    for naam in ENV_SETTINGS:

        if naam not in request.form:
            continue

        waarde = request.form.get(
            naam,
            "",
        ).strip()

        # Bestaand wachtwoord behouden
        # wanneer het wachtwoordveld leeg blijft.
        if (
            naam in SENSITIVE_ENV_SETTINGS
            and not waarde
        ):
            continue

        if naam == "SPORTBIT_SCHEDULER_ENABLED":

            if waarde not in {
                "true",
                "false",
            }:

                raise ValueError(
                    "Scheduler moet Ingeschakeld of "
                    "Uitgeschakeld zijn."
                )

        if naam == "NTFY_ENABLED":

            if waarde not in {
                "true",
                "false",
            }:

                raise ValueError(
                    "ntfy moet Ingeschakeld of "
                    "Uitgeschakeld zijn."
                )

        if naam in {
            "NTFY_ENABLED",
            "NOTIFY_SUCCESS_ENABLED",
            "NTFY_NOTIFY_SUCCESS",
        }:

            if waarde not in {
                "true",
                "false",
            }:

                raise ValueError(
                    f"{naam} moet Ingeschakeld of "
                    "Uitgeschakeld zijn."
                )

        if naam == "SPORTBIT_SCHEDULER_TIME":

            try:

                parse_tijd(
                    waarde
                )

            except ValueError:

                raise ValueError(
                    "Scheduler-tijd moet in HH:MM-formaat zijn."
                )

        if naam == "SPORTBIT_SCHEDULER_TIMEZONE":

            toegestane_timezones = {
                "Europe/Amsterdam",
                "UTC",
            }

            if waarde not in toegestane_timezones:

                raise ValueError(
                    "Ongeldige scheduler-tijdzone."
                )

        waarden[naam] = waarde

    # Zorg dat alle bekende variabelen aanwezig blijven.
    for naam in ENV_SETTINGS:

        if naam not in waarden:
            waarden[naam] = ""

    regels = []

    for naam in ENV_SETTINGS:

        waarde = waarden.get(
            naam,
            "",
        )

        if waarde is None:
            waarde = ""

        regels.append(
            f"{naam}={waarde}"
        )

    tijdelijke_file = (
        ENV_FILE.with_suffix(
            ".tmp"
        )
    )

    tijdelijke_file.write_text(
        "\n".join(regels) + "\n",
        encoding="utf-8",
    )

    tijdelijke_file.replace(
        ENV_FILE
    )

    load_dotenv(
        ENV_FILE,
        override=True,
    )

    import sportbit_api
    import notify

    importlib.reload(
        sportbit_api
    )

    importlib.reload(
        notify
    )

    app.secret_key = (
        get_of_maak_secret_key()
    )


# ============================================================
# MODULES
# ============================================================

from sportbit_config import (
    CONFIG_FILE,
    lees_config,
    lees_config_parser,
    schrijf_config,
    volgende_nummer,
)

from sportbit_dates import (
    DAGEN,
    parse_tijd,
    volgende_datum,
)

from sportbit_events import (
    automatische_volgende_twee_controle,
    beschikbare_lessen_op_dag_en_tijd,
    beschikbare_lessen_op_dag,
)

import sportbit_api

from sportbit_registration import (
    voer_inschrijving_uit,
    uitschrijven_les,
)

from sportbit_automation_state import (
    is_afgehandeld,
    is_handmatig_overgeslagen,
    markeer_afgehandeld,
    markeer_handmatig_overgeslagen,
    verwijder_section,
)

from sportbit_state import (
    clear_section,
    get_last_output,
    get_status,
)


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.secret_key = (
    get_of_maak_secret_key()
)


# ------------------------------------------------------------
# Sessiecookie-beveiliging
# ------------------------------------------------------------

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "false",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    ),
)


# ============================================================
# WEBREQUEST-LOGGING
# ============================================================

@app.after_request
def log_webrequest_fout(
    response
):
    """Log alleen HTTP-fouten."""

    if response.status_code >= 400:

        schrijf_log(
            f"FOUT {request.method} "
            f"{request.path} "
            f"endpoint={request.endpoint or '-'} "
            f"status={response.status_code} "
            f"ip={request.remote_addr or '-'}",
            onderwerp="web",
            niveau="error",
        )

    return response


# ============================================================
# WEBAPP LOGIN
# ============================================================

def get_web_credentials():

    username = os.getenv(
        "WEB_USERNAME",
        "",
    ).strip()

    password = os.getenv(
        "WEB_PASSWORD",
        "",
    )

    return username, password


def login_ingesteld():

    username, password = (
        get_web_credentials()
    )

    return bool(
        username
        and password
    )


@app.context_processor
def inject_login_status():

    return {
        "login_ingesteld": (
            login_ingesteld()
        ),
    }


@app.before_request
def controleer_login():

    if request.endpoint in {
        "login",
        "static",
    }:

        return

    if not login_ingesteld():
        return

    if session.get(
        "web_logged_in"
    ):

        return

    return redirect(
        url_for("login")
    )


# ============================================================
# CSRF-BESCHERMING
# ============================================================

def csrf_token():

    token = session.get(
        "csrf_token"
    )

    if not token:

        token = secrets.token_hex(
            16
        )

        session[
            "csrf_token"
        ] = token

    return token


@app.context_processor
def inject_csrf_token():

    return {
        "csrf_token": csrf_token,
    }


@app.before_request
def controleer_csrf():

    if request.method not in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }:

        return

    if request.endpoint == "static":
        return

    verwachte_token = session.get(
        "csrf_token"
    )

    ontvangen_token = (
        request.form.get(
            "csrf_token",
            "",
        )
    )

    if (
        not verwachte_token
        or not ontvangen_token
        or not secrets.compare_digest(
            ontvangen_token,
            verwachte_token,
        )
    ):

        abort(
            400,
            description=(
                "Ongeldige of verlopen "
                "beveiligingstoken. "
                "Herlaad de pagina en "
                "probeer het opnieuw."
            ),
        )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=[
        "GET",
        "POST",
    ],
)
def login():

    if request.method == "POST":

        username = (
            request.form.get(
                "username",
                "",
            )
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        web_username, web_password = (
            get_web_credentials()
        )

        if (
            secrets.compare_digest(
                username,
                web_username,
            )
            and secrets.compare_digest(
                password,
                web_password,
            )
        ):

            session[
                "web_logged_in"
            ] = True

            schrijf_log(
                f"Login succesvol voor gebruiker "
                f"'{username}'.",
                onderwerp="login",
            )

            return redirect(
                url_for("index")
            )

        schrijf_log(
            f"Login mislukt voor "
            f"gebruikersnaam '{username}'.",
            onderwerp="login",
            niveau="warning",
        )

        flash(
            "Ongeldige gebruikersnaam "
            "of wachtwoord.",
            "error",
        )

    return render_template(
        "login.html",
        logo=url_for(
            "static",
            filename="images/logo.svg",
        ),
    )


@app.route(
    "/logout",
    methods=["POST"],
)
def logout():

    schrijf_log(
        "Logout uitgevoerd.",
        onderwerp="login",
    )

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    inschrijvingen = (
        lees_config()
    )

    for item in inschrijvingen:

        item["volgende"] = (
            volgende_datum(
                item["dag"],
                item["tijd"],
            )
        )

        item["lessen"] = (
            automatische_volgende_twee_controle(
                item["naam"]
            )
        )

        doel_tijd = parse_tijd(item["tijd"])
        doel_les = item["les"]

        for les in item["lessen"]:
            if is_handmatig_overgeslagen(
                item["naam"],
                les["datum"].date(),
                doel_les,
                doel_tijd,
            ):
                les["status"] = {
                    "code": "uitgeschreven",
                    "css": "uitgeschreven",
                    "text": "Handmatig uitgeschreven",
                }

        actuele_status = (
            get_status(
                item["naam"]
            )
        )

        if (
            actuele_status["code"]
            != "onbekend"
        ):

            item["status"] = (
                actuele_status
            )

        elif item["lessen"]:

            item["status"] = (
                item["lessen"][0][
                    "status"
                ]
            )

        else:

            item["status"] = (
                actuele_status
            )

    return render_template(
        "index.html",
        inschrijvingen=inschrijvingen,
        scheduler_status=lees_scheduler_status(),
    )


# ============================================================
# NU INSCHRIJVEN
# ============================================================

@app.post(
    "/inschrijving/<section>/uitvoeren"
)
def run_inschrijving(
    section
):

    schrijf_log(
        f"Handmatig inschrijven gestart: "
        f"{section}",
        onderwerp="inschrijving",
    )

    try:

        resultaat = (
            voer_inschrijving_uit(
                section
            )
        )

        if resultaat:

            schrijf_log(
                f"Handmatig inschrijven geslaagd: "
                f"{section}",
                onderwerp="inschrijving",
            )

            flash(
                "SportBit-actie succesvol uitgevoerd.",
                "success",
            )

        else:

            schrijf_log(
                f"Handmatig inschrijven niet uitgevoerd: "
                f"{section}",
                onderwerp="inschrijving",
                niveau="warning",
            )

            flash(
                "SportBit-actie mislukt.",
                "error",
            )

    except Exception as error:

        schrijf_log(
            f"Handmatig inschrijven fout "
            f"{section}: {error}",
            onderwerp="inschrijving",
            niveau="error",
        )

        flash(
            f"Inschrijving mislukt: {error}",
            "error",
        )

    return redirect(
        url_for("index")
    )


# ============================================================
# UITSCHRIJVEN
# ============================================================

@app.post(
    "/inschrijving/<section>/uitschrijven/<datum>"
)
def uitschrijven(
    section,
    datum,
):

    schrijf_log(
        f"Handmatig uitschrijven gestart: "
        f"{section} datum={datum}",
        onderwerp="uitschrijving",
    )

    from datetime import date

    try:

        les_datum = date.fromisoformat(
            datum
        )

        resultaat = (
            uitschrijven_les(
                section=section,
                datum=les_datum,
            )
        )

        if resultaat:

            config = (
                lees_config_parser()
            )

            if section in config:

                doel_tijd = parse_tijd(
                    config.get(
                        section,
                        "tijd",
                    ).strip()
                )

                les = config.get(
                    section,
                    "les",
                ).strip()

                markeer_handmatig_overgeslagen(
                    section,
                    les_datum,
                    les,
                    doel_tijd,
                )

            clear_section(
                section
            )

            schrijf_log(
                f"{section}: handmatig "
                f"uitgeschreven voor {les_datum}; "
                "automatische herinschrijving "
                "voor deze doel-les geblokkeerd.",
                onderwerp="uitschrijving",
            )

            flash(
                "Je bent uitgeschreven "
                "voor deze les.",
                "success",
            )

        else:

            schrijf_log(
                f"Handmatig uitschrijven niet "
                f"uitgevoerd: {section} "
                f"datum={datum}",
                onderwerp="uitschrijving",
                niveau="warning",
            )

            flash(
                "Uitschrijven mislukt.",
                "error",
            )

    except Exception as error:

        schrijf_log(
            f"Handmatig uitschrijven fout "
            f"{section} datum={datum}: {error}",
            onderwerp="uitschrijving",
            niveau="error",
        )

        flash(
            f"Uitschrijven mislukt: {error}",
            "error",
        )

    return redirect(
        url_for("index")
    )


# ============================================================
# NIEUWE INSCHRIJVING
# ============================================================

@app.route(
    "/inschrijving/nieuw",
    methods=[
        "GET",
        "POST",
    ],
)
def nieuwe_inschrijving():

    if request.method == "POST":

        dag = (
            request.form.get(
                "dag",
                "",
            )
            .strip()
            .lower()
        )

        tijd = (
            request.form.get(
                "tijd",
                "",
            )
            .strip()
        )

        les = (
            request.form.get(
                "les",
                "",
            )
            .strip()
        )

        fouten = []

        if dag not in DAGEN:

            fouten.append(
                "Selecteer een geldige dag."
            )

        try:

            parse_tijd(tijd)

        except ValueError:

            fouten.append(
                "Gebruik een geldige tijd "
                "in HH:MM-formaat."
            )

        if not les:

            fouten.append(
                "Selecteer een les."
            )

        if fouten:

            for fout in fouten:

                flash(
                    fout,
                    "error",
                )

            return render_template(
                "edit.html",
                nieuw=True,
                item={
                    "dag": dag,
                    "tijd": tijd,
                    "les": les,
                },
                dagen=DAGEN,
            )

        config = (
            lees_config_parser()
        )

        nummer = volgende_nummer(
            config
        )

        section = (
            f"inschrijving_{nummer}"
        )

        schrijf_log(
            f"Nieuwe inschrijving: "
            f"{section} dag={dag} "
            f"tijd={tijd} les={les}",
            onderwerp="instellingen",
        )

        config[section] = {
            "dag": dag,
            "tijd": tijd,
            "les": les,
        }

        schrijf_config(
            config
        )

        try:

            resultaat = (
                voer_inschrijving_uit(
                    section
                )
            )

            if resultaat:

                flash(
                    "Les toegevoegd en "
                    "direct ingeschreven.",
                    "success",
                )

            else:

                flash(
                    "Les toegevoegd. "
                    "Inschrijven is momenteel "
                    "nog niet mogelijk; de "
                    "automatische inschrijving "
                    "blijft actief.",
                    "success",
                )

        except Exception as error:

            schrijf_log(
                f"Direct inschrijven na "
                f"toevoegen mislukt: {error}",
                onderwerp="inschrijving",
                niveau="error",
            )

            flash(
                "Les toegevoegd, maar direct "
                f"inschrijven mislukte: {error}",
                "error",
            )

        return redirect(
            url_for("index")
        )

    return render_template(
        "edit.html",
        nieuw=True,
        item={
            "dag": "maandag",
            "tijd": "07:00",
            "les": "",
        },
        dagen=DAGEN,
    )


# ============================================================
# BEWERKEN
# ============================================================

@app.route(
    "/inschrijving/<section>/bewerken",
    methods=[
        "GET",
        "POST",
    ],
)
def bewerk_inschrijving(
    section
):

    config = (
        lees_config_parser()
    )

    if section not in config:

        flash(
            "Inschrijving bestaat niet.",
            "error",
        )

        return redirect(
            url_for("index")
        )

    if request.method == "POST":

        dag = (
            request.form.get(
                "dag",
                "",
            )
            .strip()
            .lower()
        )

        tijd = (
            request.form.get(
                "tijd",
                "",
            )
            .strip()
        )

        les = (
            request.form.get(
                "les",
                "",
            )
            .strip()
        )

        fouten = []

        if dag not in DAGEN:

            fouten.append(
                "Selecteer een geldige dag."
            )

        try:

            parse_tijd(tijd)

        except ValueError:

            fouten.append(
                "Gebruik een geldige tijd "
                "in HH:MM-formaat."
            )

        if not les:

            fouten.append(
                "Vul een lesnaam in."
            )

        if fouten:

            for fout in fouten:

                flash(
                    fout,
                    "error",
                )

            return render_template(
                "edit.html",
                nieuw=False,
                item={
                    "dag": dag,
                    "tijd": tijd,
                    "les": les,
                },
                section=section,
                dagen=DAGEN,
            )

        oude_waarden = dict(
            config[section]
        )

        config[section]["dag"] = dag
        config[section]["tijd"] = tijd
        config[section]["les"] = les

        schrijf_log(
            f"Inschrijving gewijzigd: "
            f"{section} "
            f"van={dict(oude_waarden)} "
            f"naar={{'dag': dag, "
            f"'tijd': tijd, "
            f"'les': les}}",
            onderwerp="instellingen",
        )

        schrijf_config(
            config
        )

        clear_section(
            section
        )

        flash(
            "Inschrijving gewijzigd.",
            "success",
        )

        return redirect(
            url_for("index")
        )

    item = {
        "dag": config.get(
            section,
            "dag",
        ),
        "tijd": config.get(
            section,
            "tijd",
        ),
        "les": config.get(
            section,
            "les",
        ),
    }

    return render_template(
        "edit.html",
        nieuw=False,
        item=item,
        section=section,
        dagen=DAGEN,
    )


# ============================================================
# BESCHIKBARE LESSEN
# ============================================================

@app.get(
    "/api/lessen"
)
def api_lessen():

    dag = (
        request.args.get(
            "dag",
            "",
        )
        .strip()
        .lower()
    )

    if dag not in DAGEN:

        return jsonify({
            "lessen": [],
            "error": "Ongeldige dag.",
        }), 400

    try:

        datum = (
            volgende_datum(
                dag,
                "00:00",
            )
            .date()
        )

        sportbit_session = (
            sportbit_api.create_session()
        )

        sportbit_api.login(
            sportbit_session
        )

        lessen = (
            beschikbare_lessen_op_dag(
                session=sportbit_session,
                datum=datum,
            )
        )

    except Exception as error:

        schrijf_log(
            f"Lessen ophalen mislukt: "
            f"dag={dag} fout={error}",
            onderwerp="sportbit",
            niveau="error",
        )

        return jsonify({
            "lessen": [],
            "error": (
                "Lessen konden niet "
                "worden opgehaald."
            ),
        }), 500

    return jsonify({
        "datum": datum.isoformat(),
        "lessen": lessen,
    })


# ============================================================
# VERWIJDEREN
# ============================================================

@app.post(
    "/inschrijving/<section>/verwijderen"
)
def delete_inschrijving(
    section
):

    config = (
        lees_config_parser()
    )

    if section not in config:

        flash(
            "Inschrijving bestaat niet.",
            "error",
        )

    else:

        schrijf_log(
            f"Inschrijving verwijderd: "
            f"{section}",
            onderwerp="instellingen",
        )

        config.remove_section(
            section
        )

        schrijf_config(
            config
        )

        clear_section(
            section
        )

        verwijder_section(
            section
        )

        flash(
            "Inschrijving verwijderd.",
            "success",
        )

    return redirect(
        url_for("index")
    )


# ============================================================
# INSTELLINGEN
# ============================================================

@app.route(
    "/instellingen",
    methods=[
        "GET",
        "POST",
    ],
)
def instellingen():

    if request.method == "POST":

        try:

            sla_instellingen_op()

            schrijf_log(
                "Instellingen opgeslagen "
                "en runtime opnieuw geladen.",
                onderwerp="instellingen",
            )

            flash(
                "Instellingen opgeslagen.",
                "success",
            )

        except Exception as error:

            schrijf_log(
                f"Instellingen opslaan mislukt: "
                f"{error}",
                onderwerp="instellingen",
                niveau="error",
            )

            flash(
                f"Instellingen opslaan mislukt: "
                f"{error}",
                "error",
            )

        return redirect(
            url_for("instellingen")
        )

    return render_template(
        "settings.html",
        settings=lees_instellingen(),
    )

@app.post("/scheduler/nu-uitvoeren")
def scheduler_nu_uitvoeren():

    schrijf_log("HANDMATIGE SCHEDULERCONTROLE gestart.")

    try:
        try:
            timezone_naam = scheduler_instellingen()[2]
            timezone = ZoneInfo(timezone_naam)
        except Exception:
            timezone = None

        with _scheduler_status_lock:
            _scheduler_status["laatste_run"] = (
                datetime.now(timezone) if timezone else datetime.now()
            )
            _scheduler_status["laatste_resultaat"] = "Bezig..."
            _scheduler_status["fout"] = None

        voer_automatische_inschrijvingen_uit()

        with _scheduler_status_lock:
            _scheduler_status["laatste_resultaat"] = "Controle afgerond"

        schrijf_log("HANDMATIGE SCHEDULERCONTROLE succesvol afgerond.")
        flash("Schedulercontrole uitgevoerd.", "success")

    except Exception as error:
        with _scheduler_status_lock:
            _scheduler_status["laatste_resultaat"] = "Mislukt"
            _scheduler_status["fout"] = str(error)

        schrijf_log(
            f"HANDMATIGE SCHEDULERCONTROLE mislukt: {error}",
            "exception",
        )
        flash(f"Schedulercontrole mislukt: {error}", "error")

    return redirect(url_for("index"))


# ============================================================
# DOCUMENTATIE
# ============================================================

@app.route(
    "/documentatie"
)
def documentatie():

    return render_template(
        "documentation.html"
    )


# ============================================================
# TESTMAIL
# ============================================================

@app.post(
    "/testmail"
)
def testmail():

    schrijf_log(
        "Testmail gestart.",
        onderwerp="notificatie",
    )

    import notify

    try:

        notify.send_test_mail()

        schrijf_log(
            "Testmail succesvol verstuurd.",
            onderwerp="notificatie",
        )

        flash(
            "Testmail is verstuurd.",
            "success",
        )

    except Exception as error:

        schrijf_log(
            f"Testmail mislukt: {error}",
            onderwerp="notificatie",
            niveau="error",
        )

        flash(
            f"Testmail mislukt: {error}",
            "error",
        )

    return redirect(
        url_for("instellingen")
    )


@app.route("/testntfy", methods=["POST"])
def testntfy():

    schrijf_log(
        "Test ntfy gestart.",
        onderwerp="notificatie",
    )

    try:

        send_test_ntfy()

        schrijf_log(
            "Test ntfy succesvol verstuurd.",
            onderwerp="notificatie",
        )

        flash(
            "Test ntfy-notificatie is verstuurd.",
            "success",
        )

    except Exception as error:

        schrijf_log(
            f"Test ntfy mislukt: {error}",
            onderwerp="notificatie",
            niveau="error",
        )

        flash(
            f"Test ntfy mislukt: {error}",
            "error",
        )

    return redirect(
        url_for("instellingen")
    )

# ============================================================
# INGEBOUWDE SCHEDULER
# ============================================================

_scheduler_lock = (
    threading.Lock()
)

_scheduler_last_run = None

_scheduler_started = False

_scheduler_status = {
    "actief": False,
    "laatste_run": None,
    "volgende_run": None,
    "laatste_resultaat": None,
    "fout": None,
}

_scheduler_status_lock = threading.Lock()

def scheduler_instellingen():
    """Lees schedulerinstellingen rechtstreeks uit de actuele .env."""

    waarden = dotenv_values(
        ENV_FILE
    )

    enabled = (
        str(
            waarden.get(
                "SPORTBIT_SCHEDULER_ENABLED",
                "true",
            )
        )
        .strip()
        .lower()
        == "true"
    )

    tijd = str(
        waarden.get(
            "SPORTBIT_SCHEDULER_TIME",
            "00:01",
        )
        or "00:01"
    ).strip()

    timezone_naam = str(
        waarden.get(
            "SPORTBIT_SCHEDULER_TIMEZONE",
            "Europe/Amsterdam",
        )
        or "Europe/Amsterdam"
    ).strip()

    return (
        enabled,
        tijd,
        timezone_naam,
    )


def lees_scheduler_status():
    """Geef de actuele schedulerstatus voor de homepage."""

    enabled, ingestelde_tijd, timezone_naam = (
        scheduler_instellingen()
    )

    try:
        timezone = ZoneInfo(timezone_naam)
        tijd = parse_tijd(ingestelde_tijd)
        nu = datetime.now(timezone)

        volgende = nu.replace(
            hour=tijd.hour,
            minute=tijd.minute,
            second=0,
            microsecond=0,
        )

        if volgende <= nu:
            volgende += timedelta(days=1)

    except Exception:
        volgende = None

    with _scheduler_status_lock:
        status = dict(_scheduler_status)

    status["actief"] = bool(enabled)
    status["volgende_run"] = (
        volgende if enabled else None
    )

    return status


def lees_scheduler_status():
    """Geef een veilige kopie van de actuele schedulerstatus."""

    with _scheduler_status_lock:
        status = dict(_scheduler_status)

    enabled, ingestelde_tijd, timezone_naam = (
        scheduler_instellingen()
    )

    status["actief"] = bool(enabled)

    try:
        timezone = ZoneInfo(timezone_naam)
        nu = datetime.now(timezone)

        if status["volgende_run"] is None:
            volgende = nu.replace(
                hour=ingestelde_tijd.hour,
                minute=ingestelde_tijd.minute,
                second=0,
                microsecond=0,
            )

            if volgende <= nu:
                volgende += timedelta(days=1)

            status["volgende_run"] = volgende

    except Exception:
        pass

    return status


def voer_automatische_inschrijvingen_uit(testmodus=False):
    """Behandel iedere concrete doel-les maximaal één keer automatisch.

    In testmodus worden controles uitgevoerd en wordt gelogd
    wat de scheduler zou doen, zonder echt in te schrijven.
    """

    config = (
        lees_config_parser()
    )

    secties = [
        section
        for section in config.sections()
        if section.startswith(
            "inschrijving_"
        )
    ]

    schrijf_log(
        "Automatische SportBit-scheduler gestart.",
        onderwerp="scheduler",
    )

    schrijf_log(
        f"Modus: {'TESTMODUS' if testmodus else 'ECHT'}",
        onderwerp="scheduler",
    )

    if not secties:
        schrijf_log(
            "Geen inschrijvingen geconfigureerd.",
            onderwerp="scheduler",
        )
        return

    for section in secties:
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

            doel = volgende_datum(
                dag,
                tijd,
            )

            if doel is None:
                schrijf_log(
                    f"{section}: geen doelmoment gevonden.",
                    onderwerp="scheduler",
                    niveau="warning",
                )
                continue

            datum = doel.date()

            schrijf_log(
                f"{section}: doel-les "
                f"{datum} "
                f"{tijd.strftime('%H:%M')} "
                f"({les})",
                onderwerp="scheduler",
            )

            if is_handmatig_overgeslagen(
                section,
                datum,
                les,
                tijd,
            ):
                schrijf_log(
                    f"{section}: "
                    f"{datum} "
                    f"{tijd.strftime('%H:%M')} "
                    "overgeslagen omdat deze "
                    "doel-les handmatig is geannuleerd.",
                    onderwerp="scheduler",
                )
                continue

            if is_afgehandeld(
                section,
                datum,
                les,
                tijd,
            ):
                schrijf_log(
                    f"{section}: "
                    f"{datum} "
                    f"{tijd.strftime('%H:%M')} "
                    "al automatisch afgehandeld.",
                    onderwerp="scheduler",
                )
                continue

            # Testmodus: geen echte inschrijving uitvoeren.
            if testmodus:
                schrijf_log(
                    f"{section}: TESTMODUS — zou inschrijven "
                    f"voor {datum} "
                    f"{tijd.strftime('%H:%M')} "
                    f"({les}), indien registratie open is.",
                    onderwerp="scheduler",
                )
                continue

            schrijf_log(
                f"Automatisch uitvoeren: "
                f"{section} -> "
                f"{datum} "
                f"{tijd.strftime('%H:%M')} "
                f"({les})",
                onderwerp="scheduler",
            )

            resultaat = (
                voer_inschrijving_uit(
                    section
                )
            )

            if resultaat:
                markeer_afgehandeld(
                    section,
                    datum,
                    les,
                    tijd,
                )

                schrijf_log(
                    f"{section}: succesvol uitgevoerd "
                    "en gemarkeerd als afgehandeld.",
                    onderwerp="scheduler",
                )
            else:
                schrijf_log(
                    f"{section}: niet uitgevoerd "
                    "(momenteel niet open); "
                    "wordt later opnieuw gecontroleerd.",
                    onderwerp="scheduler",
                )

        except Exception as error:
            schrijf_log(
                f"{section}: fout tijdens "
                f"automatische inschrijving: "
                f"{error}",
                onderwerp="scheduler",
                niveau="error",
            )


def scheduler_loop():
    """Achtergrondlus voor de dagelijkse automatische controle."""

    global _scheduler_last_run

    vorige_instellingen = None

    while True:
        try:
            (
                enabled,
                ingestelde_tijd,
                timezone_naam,
            ) = scheduler_instellingen()

            actuele_instellingen = (
                enabled,
                ingestelde_tijd,
                timezone_naam,
            )

            if actuele_instellingen != vorige_instellingen:
                schrijf_log(
                    "Scheduler-instellingen: "
                    f"enabled={enabled}, "
                    f"tijd={ingestelde_tijd}, "
                    f"timezone={timezone_naam}",
                    onderwerp="scheduler",
                )
                vorige_instellingen = actuele_instellingen

            try:
                timezone = ZoneInfo(timezone_naam)
                tijd = parse_tijd(ingestelde_tijd)
            except Exception as error:
                with _scheduler_status_lock:
                    _scheduler_status["actief"] = False
                    _scheduler_status["fout"] = str(error)
                    _scheduler_status["volgende_run"] = None

                schrijf_log(
                    f"Ongeldige scheduler-instellingen: {error}",
                    onderwerp="scheduler",
                    niveau="error",
                )
                time.sleep(30)
                continue

            nu = datetime.now(timezone)

            volgende = nu.replace(
                hour=tijd.hour,
                minute=tijd.minute,
                second=0,
                microsecond=0,
            )

            if volgende <= nu:
                volgende += timedelta(days=1)

            with _scheduler_status_lock:
                _scheduler_status["actief"] = bool(enabled)
                _scheduler_status["volgende_run"] = (
                    volgende if enabled else None
                )
                _scheduler_status["fout"] = None

            if not enabled:
                time.sleep(10)
                continue

            huidige_datum = nu.date()
            huidige_tijd = nu.strftime("%H:%M")

            if (
                huidige_tijd == ingestelde_tijd
                and _scheduler_last_run != huidige_datum
            ):
                with _scheduler_lock:
                    if _scheduler_last_run != huidige_datum:
                        starttijd = datetime.now(timezone)

                        with _scheduler_status_lock:
                            _scheduler_status["laatste_run"] = starttijd
                            _scheduler_status["volgende_run"] = (
                                starttijd.replace(
                                    hour=tijd.hour,
                                    minute=tijd.minute,
                                    second=0,
                                    microsecond=0,
                                ) + timedelta(days=1)
                            )

                        schrijf_log(
                            "Scheduler gestart om "
                            f"{starttijd.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                            onderwerp="scheduler",
                        )

                        with _scheduler_status_lock:
                            _scheduler_status["laatste_run"] = starttijd
                            _scheduler_status["laatste_resultaat"] = "Bezig..."
                            _scheduler_status["fout"] = None

                        try:
                            voer_automatische_inschrijvingen_uit()

                            with _scheduler_status_lock:
                                _scheduler_status["laatste_resultaat"] = "Controle afgerond"

                        except Exception as error:
                            with _scheduler_status_lock:
                                _scheduler_status["laatste_resultaat"] = "Mislukt"
                                _scheduler_status["fout"] = str(error)

                            schrijf_log(
                                f"Schedulercontrole mislukt: {error}",
                                "exception",
                            )

                        finally:
                            _scheduler_last_run = huidige_datum

            time.sleep(10)

        except Exception as error:
            with _scheduler_status_lock:
                _scheduler_status["fout"] = str(error)

            schrijf_log(
                f"Fout in scheduler: {error}",
                onderwerp="scheduler",
                niveau="error",
            )
            time.sleep(30)


def start_ingebouwde_scheduler():
    """Start de scheduler éénmalig binnen het Flask-process."""

    global _scheduler_started

    if _scheduler_started:
        return

    with _scheduler_lock:

        if _scheduler_started:
            return

        _scheduler_started = True

        thread = threading.Thread(
            target=scheduler_loop,
            name="sportbit-scheduler",
            daemon=True,
        )

        thread.start()

        (
            enabled,
            ingestelde_tijd,
            timezone_naam,
        ) = scheduler_instellingen()

        schrijf_log(
            "Ingebouwde scheduler gestart: "
            f"enabled={enabled}, "
            f"tijd={ingestelde_tijd}, "
            f"timezone={timezone_naam}",
            onderwerp="scheduler",
        )


# Start wanneer Flask/Gunicorn importeert.
start_ingebouwde_scheduler()


if not login_ingesteld():

    schrijf_log(
        "WAARSCHUWING: "
        "WEB_USERNAME/WEB_PASSWORD zijn "
        "niet ingesteld. De volledige "
        "webinterface is hierdoor bereikbaar "
        "voor iedereen die deze server kan "
        "benaderen.",
        onderwerp="login",
        niveau="warning",
    )


# ============================================================
# LOG
# ============================================================

def lees_logbestand(
    max_regels=500
):
    """Lees de laatste logregels uit het permanente logbestand."""

    if not LOG_FILE.exists():

        return (
            "Nog geen logbestand beschikbaar."
        )

    try:

        with LOG_FILE.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as bestand:

            regels = (
                bestand.readlines()
            )

        if not regels:

            return (
                "Logbestand is nog leeg."
            )

        return "".join(
            regels[-max_regels:]
        )

    except OSError as error:

        return (
            "Logbestand kon niet worden "
            f"gelezen: {error}"
        )


@app.route(
    "/log"
)
def log():

    return render_template(
        "log.html",
        output=lees_logbestand(),
    )


@app.get(
    "/api/log"
)
def api_log():
    """Geef de actuele logregels terug voor live verversen."""

    return jsonify({
        "output": lees_logbestand(),
        "updated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    })


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    schrijf_log(
        "Go Personal · SportBit webapp gestart.",
        onderwerp="app",
    )

    if not login_ingesteld():

        schrijf_log(
            "WEB_USERNAME/WEB_PASSWORD zijn niet "
            "ingesteld. De volledige webinterface "
            "is hierdoor bereikbaar voor iedereen "
            "die deze server kan benaderen.",
            onderwerp="login",
            niveau="warning",
        )

    schrijf_log(
        "Luistert op 0.0.0.0:5000.",
        onderwerp="app",
    )

    schrijf_log(
        "Gebruik Gunicorn voor productie.",
        onderwerp="app",
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
