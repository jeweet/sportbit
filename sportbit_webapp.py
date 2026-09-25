#!/usr/bin/env python3

"""Flask-webapp voor automatische SportBit-inschrijvingen."""

import os
import secrets
import importlib
import logging
import threading
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
# LOGGING
# ============================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("sportbit")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    _file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s"
        )
    )
    _logger.addHandler(_file_handler)

    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s"
        )
    )
    _logger.addHandler(_console_handler)


def schrijf_log(bericht, niveau="info"):
    """Schrijf een bericht naar het permanente SportBit-logbestand."""
    logfunctie = getattr(_logger, niveau, _logger.info)
    logfunctie(str(bericht))



def get_of_maak_secret_key():
    """Geef een stabiele Flask secret key terug.

    Volgorde:
    1. FLASK_SECRET_KEY uit .env, indien ingesteld.
    2. Een eerder gegenereerde sleutel uit .flask_secret_key.
    3. Een nieuwe, willekeurige sleutel, die daarna wordt opgeslagen
       zodat bestaande sessies een herstart overleven.

    Er wordt bewust geen vaste/publieke fallbackstring meer gebruikt:
    zo'n vaste string zou sessies (en dus logins) vervalsbaar maken
    zodra de app buiten localhost bereikbaar is.
    """

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

    tijdelijke_file = SECRET_KEY_FILE.with_suffix(".tmp")

    tijdelijke_file.write_text(
        nieuwe_sleutel,
        encoding="utf-8",
    )

    tijdelijke_file.replace(SECRET_KEY_FILE)

    try:
        os.chmod(SECRET_KEY_FILE, 0o600)
    except OSError:
        pass

    print(
        "Geen FLASK_SECRET_KEY ingesteld in .env: nieuwe willekeurige "
        f"sleutel gegenereerd en opgeslagen in {SECRET_KEY_FILE.name}. "
        "Zet bij voorkeur zelf een vaste FLASK_SECRET_KEY in .env."
    )

    return nieuwe_sleutel


# ============================================================
# INSTELLINGEN / .ENV
# ============================================================

ENV_SETTINGS = (
    "SPORTBIT_USERNAME",
    "SPORTBIT_PASSWORD",
    "NOTIFY_ENABLED",
    "NOTIFY_EMAIL_TO",
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
}


def lees_instellingen():

    waarden = dotenv_values(ENV_FILE)

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

    waarden = dotenv_values(ENV_FILE)

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
            if waarde not in {"true", "false"}:
                raise ValueError(
                    "Scheduler moet Ingeschakeld of Uitgeschakeld zijn."
                )

        if naam == "SPORTBIT_SCHEDULER_TIME":
            try:
                parse_tijd(waarde)
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

    # Zorg dat alle bekende variabelen aanwezig
    # blijven in het .env-bestand.
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
        ENV_FILE.with_suffix(".tmp")
    )

    tijdelijke_file.write_text(
        "\n".join(regels) + "\n",
        encoding="utf-8",
    )

    tijdelijke_file.replace(
        ENV_FILE
    )

    # Nieuwe waarden direct beschikbaar maken voor het
    # huidige Flask-process. Alleen load_dotenv() is niet
    # voldoende wanneer een module instellingen tijdens import
    # in variabelen heeft gezet. Daarom laden we de modules die
    # de .env-instellingen gebruiken opnieuw.
    load_dotenv(
        ENV_FILE,
        override=True,
    )

    import sportbit_api
    import notify

    importlib.reload(sportbit_api)
    importlib.reload(notify)

    # Flask gebruikt de web-loginfuncties via os.getenv(), maar
    # houd ook de app-secret actueel wanneer die net in .env is gezet.
    app.secret_key = get_of_maak_secret_key()


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


app.secret_key = get_of_maak_secret_key()

# ------------------------------------------------------------
# Sessiecookie-beveiliging
# ------------------------------------------------------------
#
# HTTPONLY: cookie is niet leesbaar via JavaScript (voorkomt diefstal
#           via XSS).
# SAMESITE=Lax: cookie wordt niet meegestuurd bij cross-site POSTs
#           vanaf andere sites, wat ook CSRF bemoeilijkt.
# SECURE: cookie wordt alleen over HTTPS verstuurd. Dit staat standaard
#           uit omdat de app vaak direct over HTTP op een lokaal netwerk
#           draait; zet SESSION_COOKIE_SECURE=true in .env zodra de app
#           achter HTTPS (bijvoorbeeld een reverse proxy) bereikbaar is.
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
        in {"1", "true", "yes", "on"}
    ),
)


# ============================================================
# WEBREQUEST-LOGGING
# ============================================================

@app.after_request
def log_webrequest_fout(response):
    """Log alleen HTTP-fouten; normale requests blijven stil."""

    if response.status_code >= 400:
        schrijf_log(
            f"WEB FOUT {request.method} {request.path}"
            f" endpoint={request.endpoint or '-'}"
            f" status={response.status_code}"
            f" ip={request.remote_addr or '-'}",
            "error",
        )

    return response


class LogStdout:
    """Stuur bestaande print()-uitvoer van de app naar het logbestand."""

    def __init__(self, origineel):
        self.origineel = origineel

    def write(self, tekst):
        tekst = str(tekst)
        if tekst.strip():
            schrijf_log(f"STDOUT {tekst.rstrip()}")
        return len(tekst)

    def flush(self):
        try:
            self.origineel.flush()
        except Exception:
            pass


# Bestaande print()-meldingen uit de webapp en onderliggende modules
# worden hierdoor ook permanent opgeslagen. De logger schrijft zelf naar
# stderr voor de console, zodat deze omleiding geen log-recursie veroorzaakt.
import sys
sys.stdout = LogStdout(sys.stdout)


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

    username, password = get_web_credentials()

    return bool(
        username
        and password
    )


@app.context_processor
def inject_login_status():

    # Wordt gebruikt om in de webinterface zelf een duidelijke
    # waarschuwing te tonen zolang er geen WEB_USERNAME/WEB_PASSWORD
    # zijn ingesteld: zonder die instelling is de hele app (inclusief
    # Instellingen, met daarin gevoelige configuratie) bereikbaar voor
    # iedereen die de server kan benaderen.
    return {
        "login_ingesteld": login_ingesteld(),
    }


@app.before_request
def controleer_login():

    # Deze pagina's zijn zonder login bereikbaar.
    if request.endpoint in {
        "login",
        "static",
    }:
        return

    # Als er nog geen web-login is ingesteld,
    # blijft de applicatie gewoon bereikbaar.
    if not login_ingesteld():
        return

    # Gebruiker is al ingelogd.
    if session.get("web_logged_in"):
        return

    return redirect(
        url_for("login")
    )


# ============================================================
# CSRF-BESCHERMING
# ============================================================
#
# Lichtgewicht, afhankelijkheidsvrij CSRF-token: bij ieder GET-bezoek
# wordt een willekeurige token in de sessie gezet; ieder formulier
# stuurt deze token als verborgen veld mee. Bij een POST/PUT/PATCH/
# DELETE wordt de meegestuurde token vergeleken met de sessietoken.
# Zonder geldige (of ontbrekende) token wordt de aanvraag geweigerd,
# ook als de gebruiker wel is ingelogd.

def csrf_token():

    token = session.get("csrf_token")

    if not token:

        token = secrets.token_hex(
            16
        )

        session["csrf_token"] = token

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

    ontvangen_token = request.form.get(
        "csrf_token",
        "",
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
                "Ongeldige of verlopen beveiligingstoken. "
                "Herlaad de pagina en probeer het opnieuw."
            ),
        )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

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

            session["web_logged_in"] = True

            schrijf_log(
                f"LOGIN succesvol voor gebruiker '{username}'."
            )

            return redirect(
                url_for("index")
            )

        schrijf_log(
            f"LOGIN mislukt voor gebruikersnaam '{username}'.",
            "warning",
        )

        flash(
            "Ongeldige gebruikersnaam of wachtwoord.",
            "error",
        )

    return render_template(
        "login.html",
        logo=url_for(
            "static",
            filename="images/logo.svg",
        ),
    )


@app.route("/logout", methods=["POST"])
def logout():

    schrijf_log("LOGOUT uitgevoerd.")

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    schrijf_log("Overzicht geopend.")

    inschrijvingen = lees_config()

    for item in inschrijvingen:

        item["volgende"] = volgende_datum(
            item["dag"],
            item["tijd"],
        )

        item["lessen"] = (
            automatische_volgende_twee_controle(
                item["naam"]
            )
        )

        # Gebruik een direct na een actie opgehaalde
        # runtime-status wanneer die beschikbaar is.
        #
        # De bestaande cache blijft gewoon actief:
        # wanneer er geen actuele runtime-status is,
        # gebruiken we de status uit de gecontroleerde
        # lessen-cache.
        actuele_status = get_status(
            item["naam"]
        )

        if actuele_status["code"] != "onbekend":

            item["status"] = actuele_status

        elif item["lessen"]:

            item["status"] = (
                item["lessen"][0]["status"]
            )

        else:

            item["status"] = actuele_status

    return render_template(
        "index.html",
        inschrijvingen=inschrijvingen,
    )


# ============================================================
# NU INSCHRIJVEN
# ============================================================

@app.post(
    "/inschrijving/<section>/uitvoeren"
)
def run_inschrijving(section):

    schrijf_log(f"HANDMATIG inschrijven gestart: {section}")

    try:

        resultaat = voer_inschrijving_uit(
            section
        )

        if resultaat:

            schrijf_log(
                f"HANDMATIG inschrijven geslaagd: {section}"
            )

            flash(
                "SportBit-actie succesvol uitgevoerd.",
                "success",
            )

        else:

            schrijf_log(
                f"HANDMATIG inschrijven niet uitgevoerd: {section}",
                "warning",
            )

            flash(
                "SportBit-actie mislukt.",
                "error",
            )

    except Exception as error:

        schrijf_log(
            f"HANDMATIG inschrijven fout {section}: {error}",
            "exception",
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
def uitschrijven(section, datum):

    schrijf_log(
        f"HANDMATIG uitschrijven gestart: {section} datum={datum}"
    )

    from datetime import date

    try:

        les_datum = date.fromisoformat(
            datum
        )

        resultaat = uitschrijven_les(
            section=section,
            datum=les_datum,
        )


        if resultaat:

            config = lees_config_parser()
            if section in config:
                doel_tijd = parse_tijd(config.get(section, "tijd").strip())
                les = config.get(section, "les").strip()
                markeer_handmatig_overgeslagen(
                    section,
                    les_datum,
                    les,
                    doel_tijd,
                )

            # Verwijder de oude runtime-status en cache.
            # Bij de redirect naar de index wordt de actuele
            # SportBit-status daardoor opnieuw gecontroleerd.
            clear_section(section)

            schrijf_log(
                f"{section}: handmatig uitgeschreven voor {les_datum}; "
                "automatische herinschrijving voor deze doel-les geblokkeerd."
            )

            flash(
                "Je bent uitgeschreven voor deze les.",
                "success",
            )

        else:

            schrijf_log(
                f"HANDMATIG uitschrijven niet uitgevoerd: {section} datum={datum}",
                "warning",
            )

            flash(
                  "Uitschrijven mislukt.",
                  "error",
            )

    except Exception as error:

        schrijf_log(
            f"HANDMATIG uitschrijven fout {section} datum={datum}: {error}",
            "exception",
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
    methods=["GET", "POST"],
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

        config = lees_config_parser()

        nummer = volgende_nummer(
            config
        )

        section = (
            f"inschrijving_{nummer}"
        )

        schrijf_log(
            f"NIEUWE INSCHRIJVING: {section} dag={dag} tijd={tijd} les={les}"
        )

        config[section] = {
            "dag": dag,
            "tijd": tijd,
            "les": les,
        }

        schrijf_config(config)

        try:

            resultaat = voer_inschrijving_uit(
                section
            )

            if resultaat:

                flash(
                    "Les toegevoegd en direct ingeschreven.",
                    "success",
                )

            else:

                flash(
                    "Les toegevoegd. Inschrijven is momenteel "
                    "nog niet mogelijk; de automatische inschrijving "
                    "blijft actief.",
                    "success",
                )

        except Exception as error:

            flash(
                "Les toegevoegd, maar direct inschrijven "
                f"mislukte: {error}",
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
    methods=["GET", "POST"],
)
def bewerk_inschrijving(section):

    config = lees_config_parser()

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

        oude_waarden = dict(config[section])

        config[section]["dag"] = dag
        config[section]["tijd"] = tijd
        config[section]["les"] = les

        schrijf_log(
            f"INSCHRIJVING GEWIJZIGD: {section} "
            f"van={dict(oude_waarden)} naar={{'dag': dag, 'tijd': tijd, 'les': les}}"
        )

        schrijf_config(config)

        clear_section(section)

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

@app.get("/api/lessen")
def api_lessen():
    dag = request.args.get("dag", "").strip().lower()

    if dag not in DAGEN:
        return jsonify({
            "lessen": [],
            "error": "Ongeldige dag.",
        }), 400

    try:
        datum = volgende_datum(
            dag,
            "00:00",
        ).date()

        session = sportbit_api.create_session()
        sportbit_api.login(session)

        lessen = beschikbare_lessen_op_dag(
            session=session,
            datum=datum,
        )

    except Exception as error:
        schrijf_log(
            f"LESSEN OPHALEN MISLUKT: dag={dag} fout={error}",
            "error",
        )

        return jsonify({
            "lessen": [],
            "error": "Lessen konden niet worden opgehaald.",
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
def delete_inschrijving(section):

    config = lees_config_parser()

    if section not in config:

        flash(
            "Inschrijving bestaat niet.",
            "error",
        )

    else:

        schrijf_log(f"INSCHRIJVING VERWIJDERD: {section}")

        config.remove_section(
            section
        )

        schrijf_config(config)

        clear_section(section)
        verwijder_section(section)

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
    methods=["GET", "POST"],
)
def instellingen():

    if request.method == "POST":

        try:

            sla_instellingen_op()

            schrijf_log("Instellingen opgeslagen en runtime opnieuw geladen.")

            flash(
                "Instellingen opgeslagen.",
                "success",
            )

        except Exception as error:

            flash(
                f"Instellingen opslaan mislukt: {error}",
                "error",
            )

        return redirect(
            url_for("instellingen")
        )

    return render_template(
        "settings.html",
        settings=lees_instellingen(),
    )


# ============================================================
# DOCUMENTATIE
# ============================================================

@app.route("/documentatie")
def documentatie():

    return render_template(
        "documentation.html"
    )



# ============================================================
# TESTMAIL
# ============================================================

@app.post("/testmail")
def testmail():

    schrijf_log("TESTMAIL gestart.")

    import notify

    try:

        notify.send_test_mail()

        schrijf_log("TESTMAIL succesvol verstuurd.")

        flash(
            "Testmail is verstuurd.",
            "success",
        )

    except Exception as error:

        schrijf_log(
            f"TESTMAIL mislukt: {error}",
            "exception",
        )

        flash(
            f"Testmail mislukt: {error}",
            "error",
        )

    return redirect(
        url_for("instellingen")
    )


# ============================================================
# INGEBouwde SCHEDULER
# ============================================================

_scheduler_lock = threading.Lock()
_scheduler_last_run = None
_scheduler_started = False


def scheduler_instellingen():
    """Lees de schedulerinstellingen rechtstreeks uit de actuele .env."""

    waarden = dotenv_values(ENV_FILE)

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

    return enabled, tijd, timezone_naam




def voer_automatische_inschrijvingen_uit():
    """
    Voer automatische inschrijvingen uit voor concrete lessen
    waarvan het registratievenster vandaag opent.

    De bestaande functionaliteit voor handmatig overslaan,
    persistent afgehandeld-state en opnieuw proberen blijft
    behouden.
    """

    config = lees_config_parser()

    secties = [
        section
        for section in config.sections()
        if section.startswith("inschrijving_")
    ]

    # ---------------------------------------------------------
    # Tijdstip van deze scheduler-run
    # ---------------------------------------------------------

    try:

        _, _, timezone_naam = (
            scheduler_instellingen()
        )

        timezone = ZoneInfo(
            timezone_naam
        )

        nu = datetime.now(
            timezone
        )

    except Exception:

        nu = datetime.now()
        timezone_naam = "onbekend"

    vandaag = nu.date()

    schrijf_log("")
    schrijf_log("=" * 65)
    schrijf_log(
        "AUTOMATISCHE SPORTBIT-SCHEDULER"
    )
    schrijf_log("=" * 65)

    schrijf_log(
        f"Scheduler-run gestart: "
        f"{nu.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )

    schrijf_log(
        f"Tijdzone: {timezone_naam}"
    )

    schrijf_log(
        f"Datum: {vandaag}"
    )

    schrijf_log(
        f"Aantal geconfigureerde inschrijvingen: "
        f"{len(secties)}"
    )

    if not secties:

        schrijf_log(
            "Geen inschrijvingen geconfigureerd.",
            "warning",
        )

        schrijf_log(
            "Scheduler-run beëindigd."
        )

        schrijf_log("=" * 65)

        return

    # ---------------------------------------------------------
    # Iedere automatische inschrijving controleren
    # ---------------------------------------------------------

    for section in secties:

        schrijf_log("")
        schrijf_log(
            "-" * 65
        )
        schrijf_log(
            f"[{section}] START"
        )
        schrijf_log(
            "-" * 65
        )

        try:

            # -------------------------------------------------
            # Configuratie
            # -------------------------------------------------

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

            schrijf_log(
                f"[{section}] Configuratie:"
            )

            schrijf_log(
                f"[{section}]   Dag  : {dag}"
            )

            schrijf_log(
                f"[{section}]   Tijd : "
                f"{tijd.strftime('%H:%M')}"
            )

            schrijf_log(
                f"[{section}]   Les  : {les}"
            )

            # -------------------------------------------------
            # Twee concrete toekomstige lessen bepalen
            # -------------------------------------------------

            eerste = volgende_datum(
                dag,
                tijd,
            )

            if eerste is None:

                schrijf_log(
                    f"[{section}] Geen eerste doelmoment gevonden.",
                    "warning",
                )

                continue

            tweede = eerste + timedelta(
                days=7
            )

            schrijf_log(
                f"[{section}] Eerstvolgende les: "
                f"{eerste.strftime('%Y-%m-%d %H:%M')}"
            )

            schrijf_log(
                f"[{section}] Daaropvolgende les: "
                f"{tweede.strftime('%Y-%m-%d %H:%M')}"
            )

            # -------------------------------------------------
            # Zoek de concrete les waarvan de registratie
            # vandaag opent.
            # -------------------------------------------------

            doel = None

            for kandidaat in (
                eerste,
                tweede,
            ):

                openingsdatum = (
                    kandidaat.date()
                    - timedelta(days=7)
                )

                schrijf_log(
                    f"[{section}] Controle doel "
                    f"{kandidaat.strftime('%Y-%m-%d %H:%M')}: "
                    f"registratie opent op "
                    f"{openingsdatum}"
                )

                if openingsdatum == vandaag:

                    doel = kandidaat

                    schrijf_log(
                        f"[{section}] REGISTRATIE OPENT VANDAAG "
                        f"VOOR DEZE LES."
                    )

                    break

            # -------------------------------------------------
            # Geen les waarvan registratie vandaag opent
            # -------------------------------------------------

            if doel is None:

                schrijf_log(
                    f"[{section}] Geen concrete les gevonden "
                    f"waarvan de registratie vandaag opent."
                )

                schrijf_log(
                    f"[{section}] Geen actie nodig."
                )

                continue

            datum = doel.date()

            schrijf_log(
                f"[{section}] CONCRETE DOEL-LES:"
            )

            schrijf_log(
                f"[{section}]   Datum : {datum}"
            )

            schrijf_log(
                f"[{section}]   Tijd  : "
                f"{tijd.strftime('%H:%M')}"
            )

            schrijf_log(
                f"[{section}]   Les   : {les}"
            )

            # -------------------------------------------------
            # Handmatig overgeslagen?
            # -------------------------------------------------

            handmatig_overgeslagen = (
                is_handmatig_overgeslagen(
                    section,
                    datum,
                    les,
                    tijd,
                )
            )

            schrijf_log(
                f"[{section}] Handmatig overgeslagen: "
                f"{'JA' if handmatig_overgeslagen else 'NEE'}"
            )

            if handmatig_overgeslagen:

                schrijf_log(
                    f"[{section}] ACTIE: doel-les overslaan "
                    f"omdat deze handmatig is geannuleerd."
                )

                continue

            # -------------------------------------------------
            # Al automatisch afgehandeld?
            # -------------------------------------------------

            al_afgehandeld = (
                is_afgehandeld(
                    section,
                    datum,
                    les,
                    tijd,
                )
            )

            schrijf_log(
                f"[{section}] Automatisch afgehandeld: "
                f"{'JA' if al_afgehandeld else 'NEE'}"
            )

            if al_afgehandeld:

                schrijf_log(
                    f"[{section}] ACTIE: overslaan; "
                    f"{datum} "
                    f"{tijd.strftime('%H:%M')} "
                    f"({les}) is al afgehandeld."
                )

                continue

            # -------------------------------------------------
            # Controle registratie-opening
            # -------------------------------------------------

            schrijf_log(
                f"[{section}] Controleer of registratie "
                f"daadwerkelijk open is..."
            )

            if not inschrijving_open(
                datum
            ):

                schrijf_log(
                    f"[{section}] Registratie is nog niet open."
                )

                schrijf_log(
                    f"[{section}] Geen actie; volgende "
                    f"scheduler-run probeert opnieuw."
                )

                continue

            schrijf_log(
                f"[{section}] Registratie is OPEN."
            )

            # -------------------------------------------------
            # Inschrijving uitvoeren voor concrete doel-les
            # -------------------------------------------------

            schrijf_log(
                f"[{section}] ACTIE: inschrijving starten."
            )

            schrijf_log(
                f"[{section}] Doel: "
                f"{datum} "
                f"{tijd.strftime('%H:%M')} · "
                f"{les}"
            )

            resultaat = (
                voer_inschrijving_uit(
                    section,
                    doel=doel,
                )
            )

            schrijf_log(
                f"[{section}] Resultaat "
                f"voer_inschrijving_uit(): "
                f"{resultaat!r}"
            )

            # -------------------------------------------------
            # Succes
            # -------------------------------------------------

            if resultaat:

                schrijf_log(
                    f"[{section}] SUCCES: inschrijving "
                    f"uitgevoerd voor "
                    f"{datum} {tijd.strftime('%H:%M')}."
                )

                schrijf_log(
                    f"[{section}] Concrete doel-les "
                    f"markeren als afgehandeld..."
                )

                markeer_afgehandeld(
                    section,
                    datum,
                    les,
                    tijd,
                )

                schrijf_log(
                    f"[{section}] State succesvol opgeslagen."
                )

                schrijf_log(
                    f"[{section}] AUTOMATISCHE ACTIE VOLTOOID."
                )

            # -------------------------------------------------
            # Niet uitgevoerd
            # -------------------------------------------------

            else:

                schrijf_log(
                    f"[{section}] NIET UITGEVOERD."
                )

                schrijf_log(
                    f"[{section}] De doel-les is niet als "
                    f"afgehandeld gemarkeerd."
                )

                schrijf_log(
                    f"[{section}] Een volgende scheduler-run "
                    f"kan opnieuw proberen."
                )

        except Exception as error:

            schrijf_log(
                f"[{section}] FOUT tijdens automatische "
                f"inschrijving: {error}",
                "exception",
            )

        finally:

            schrijf_log(
                f"[{section}] EINDE"
            )

    # ---------------------------------------------------------
    # Scheduler-run afgerond
    # ---------------------------------------------------------

    schrijf_log("")
    schrijf_log("=" * 65)
    schrijf_log(
        "Scheduler-run beëindigd."
    )
    schrijf_log("=" * 65)
    schrijf_log("")





def scheduler_loop():
    """Achtergrondlus voor de dagelijkse automatische controle."""

    global _scheduler_last_run
    vorige_instellingen = None

    while True:
        try:
            enabled, ingestelde_tijd, timezone_naam = (
                scheduler_instellingen()
            )

            actuele_instellingen = (
                enabled,
                ingestelde_tijd,
                timezone_naam,
            )

            if actuele_instellingen != vorige_instellingen:
                schrijf_log(
                    "Scheduler-instellingen: "
                    f"enabled={enabled}, tijd={ingestelde_tijd}, "
                    f"timezone={timezone_naam}"
                )
                vorige_instellingen = actuele_instellingen

            if not enabled:
                time.sleep(10)
                continue

            try:
                timezone = ZoneInfo(timezone_naam)
            except Exception:
                schrijf_log(
                    f"Ongeldige scheduler-timezone: {timezone_naam}",
                    "error",
                )
                time.sleep(60)
                continue

            nu = datetime.now(timezone)
            huidige_tijd = nu.strftime("%H:%M")
            huidige_datum = nu.date()

            if (
                huidige_tijd == ingestelde_tijd
                and _scheduler_last_run != huidige_datum
            ):
                with _scheduler_lock:
                    if _scheduler_last_run != huidige_datum:
                        schrijf_log(
                            f"Scheduler gestart om "
                            f"{nu.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                        )

                        try:
                            voer_automatische_inschrijvingen_uit()
                        finally:
                            _scheduler_last_run = huidige_datum

            time.sleep(10)

        except Exception as error:
            schrijf_log(
                f"Fout in scheduler: {error}",
                "exception",
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

        enabled, ingestelde_tijd, timezone_naam = (
            scheduler_instellingen()
        )

        schrijf_log(
            "Ingebouwde scheduler gestart: "
            f"enabled={enabled}, "
            f"tijd={ingestelde_tijd}, "
            f"timezone={timezone_naam}"
        )


# Start ook wanneer Flask/Gunicorn deze module importeert.
start_ingebouwde_scheduler()

if not login_ingesteld():
    schrijf_log(
        "WAARSCHUWING: WEB_USERNAME/WEB_PASSWORD zijn niet ingesteld. "
        "De volledige webinterface (inclusief Instellingen) is hierdoor "
        "bereikbaar voor iedereen die deze server kan benaderen.",
        "warning",
    )


# ============================================================
# LOG
# ============================================================

def lees_logbestand(max_regels=500):
    """Lees de laatste logregels uit het permanente logbestand."""

    if not LOG_FILE.exists():
        return "Nog geen logbestand beschikbaar."

    try:
        with LOG_FILE.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as bestand:
            regels = bestand.readlines()

        if not regels:
            return "Logbestand is nog leeg."

        return "".join(regels[-max_regels:])

    except OSError as error:
        return f"Logbestand kon niet worden gelezen: {error}"


@app.route("/log")
def log():
    return render_template(
        "log.html",
        output=lees_logbestand(),
    )


@app.get("/api/log")
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

    print()
    print("=" * 55)
    print("Go Personal · SportBit webapp")
    print("=" * 55)
    print()

    if not login_ingesteld():
        print(
            "WAARSCHUWING: WEB_USERNAME/WEB_PASSWORD zijn niet "
            "ingesteld. De volledige webinterface (inclusief "
            "Instellingen) is hierdoor bereikbaar voor iedereen "
            "die deze server kan benaderen. Stel deze in via "
            ".env of de Instellingen-pagina voordat je de app "
            "buiten je eigen apparaat beschikbaar maakt."
        )
        print()

    print(
        "Luistert op: 0.0.0.0:5000"
    )

    print()

    print(
        "Gebruik Gunicorn voor productie."
    )

    print()


    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
