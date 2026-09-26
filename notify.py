import os
import smtplib
from email.message import EmailMessage

import requests

from sportbit_logging import schrijf_log


def _enabled():
    return (
        os.getenv(
            "NOTIFY_ENABLED",
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
    )

def _success_mail_enabled():
    return (
        os.getenv(
            "NOTIFY_SUCCESS_ENABLED",
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
    )


def _ntfy_success_enabled():
    return (
        os.getenv(
            "NTFY_NOTIFY_SUCCESS",
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
    )

def _ntfy_enabled():
    return (
        os.getenv(
            "NTFY_ENABLED",
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
    )


def _mail_settings():
    host = os.getenv(
        "SMTP_HOST",
        "",
    ).strip()

    port = int(
        os.getenv(
            "SMTP_PORT",
            "587",
        )
    )

    username = os.getenv(
        "SMTP_USERNAME",
        "",
    ).strip()

    password = os.getenv(
        "SMTP_PASSWORD",
        "",
    )

    gebruik_tls = (
        os.getenv(
            "SMTP_USE_TLS",
            "true",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    afzender = os.getenv(
        "NOTIFY_FROM",
        "",
    ).strip()

    ontvanger = os.getenv(
        "NOTIFY_EMAIL_TO",
        "",
    ).strip()

    if not host:
        raise RuntimeError(
            "SMTP_HOST ontbreekt in .env"
        )

    if not afzender:
        raise RuntimeError(
            "NOTIFY_FROM ontbreekt in .env"
        )

    if not ontvanger:
        raise RuntimeError(
            "NOTIFY_EMAIL_TO ontbreekt in .env"
        )

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "use_tls": gebruik_tls,
        "from": afzender,
        "to": ontvanger,
    }


def _ntfy_settings():
    url = os.getenv(
        "NTFY_URL",
        "",
    ).strip().rstrip("/")

    topic = os.getenv(
        "NTFY_TOPIC",
        "",
    ).strip()

    token = os.getenv(
        "NTFY_TOKEN",
        "",
    ).strip()

    if not url:
        raise RuntimeError(
            "NTFY_URL ontbreekt in .env"
        )

    if not topic:
        raise RuntimeError(
            "NTFY_TOPIC ontbreekt in .env"
        )

    return {
        "url": url,
        "topic": topic,
        "token": token,
    }


def _smtp_send(
    message,
):
    instellingen = _mail_settings()

    with smtplib.SMTP(
        instellingen["host"],
        instellingen["port"],
        timeout=20,
    ) as smtp:

        if instellingen["use_tls"]:

            smtp.starttls()

        if (
            instellingen["username"]
            and instellingen["password"]
        ):

            smtp.login(
                instellingen["username"],
                instellingen["password"],
            )

        smtp.send_message(
            message
        )


def _ntfy_send(
    titel,
    bericht,
    prioriteit="default",
):
    instellingen = _ntfy_settings()

    headers = {
        "Title": titel,
        "Priority": prioriteit,
    }

    if instellingen["token"]:
        headers["Authorization"] = (
            f"Bearer {instellingen['token']}"
        )

    response = requests.post(
        (
            f"{instellingen['url']}/"
            f"{instellingen['topic']}"
        ),
        data=bericht.encode("utf-8"),
        headers=headers,
        timeout=10,
    )

    response.raise_for_status()


def _notify(
    titel,
    bericht,
    prioriteit="default",
):
    """Verstuur een notificatie via mail en/of ntfy."""

    if not _enabled() and not _ntfy_enabled():
        return

    if _enabled():
        # Mail wordt door de bestaande functies afgehandeld.

        pass

    if _ntfy_enabled():
        _ntfy_send(
            titel,
            bericht,
            prioriteit=prioriteit,
        )


def send_test_mail():
    """Verstuur een testmail."""

    if not _enabled():
        raise RuntimeError(
            "Notificaties zijn uitgeschakeld."
        )

    instellingen = _mail_settings()

    message = EmailMessage()

    message["Subject"] = (
        "SportBit testmail"
    )

    message["From"] = (
        instellingen["from"]
    )

    message["To"] = (
        instellingen["to"]
    )

    message.set_content(
        "Dit is een testmail van de "
        "SportBit-applicatie.\n\n"
        "De e-mailnotificaties werken."
    )

    schrijf_log(
        "Testmail wordt verstuurd.",
        onderwerp="notificatie",
    )

    _smtp_send(
        message
    )

    schrijf_log(
        "Testmail succesvol verstuurd.",
        onderwerp="notificatie",
    )

def send_test_ntfy():
    """Verstuur een testnotificatie naar ntfy."""

    if not _ntfy_enabled():
        raise RuntimeError(
            "ntfy-notificaties zijn uitgeschakeld."
        )

    titel = "SportBit testnotificatie"

    bericht = (
        "Dit is een testnotificatie van de "
        "SportBit-applicatie.\n\n"
        "De ntfy-notificaties werken."
    )

    schrijf_log(
        "Testnotificatie naar ntfy wordt verstuurd.",
        onderwerp="notificatie",
    )

    _ntfy_send(
        titel,
        bericht,
    )

    schrijf_log(
        "Testnotificatie naar ntfy succesvol verstuurd.",
        onderwerp="notificatie",
    )


def notify_les_ontbreekt(
    section,
    datum,
    les,
    tijd,
):
    """Meld dat een verwachte les niet gevonden is."""

    if not _enabled() and not _ntfy_enabled():
        return

    onderwerp = (
        f"SportBit les niet gevonden: {les}"
    )

    inhoud = (
        "De SportBit-applicatie kon de "
        "verwachte les niet vinden.\n\n"
        f"Inschrijving: {section}\n"
        f"Datum: {datum}\n"
        f"Tijd: {tijd}\n"
        f"Les: {les}\n"
    )

    schrijf_log(
        f"Les-ontbreekt-notificatie wordt "
        f"verstuurd voor {section}.",
        onderwerp="notificatie",
    )

    if _enabled():
        instellingen = _mail_settings()

        message = EmailMessage()

        message["Subject"] = onderwerp
        message["From"] = instellingen["from"]
        message["To"] = instellingen["to"]

        message.set_content(
            inhoud
        )

        _smtp_send(
            message
        )

    if _ntfy_enabled():
        _ntfy_send(
            onderwerp,
            inhoud,
        )

    schrijf_log(
        f"Les-ontbreekt-notificatie succesvol "
        f"verstuurd voor {section}.",
        onderwerp="notificatie",
    )


def notify_inschrijving_mislukt(
    section,
    fout,
    log="",
):
    """Meld dat een automatische inschrijving mislukt is."""

    if not _enabled() and not _ntfy_enabled():
        return

    onderwerp = (
        f"SportBit inschrijving mislukt: {section}"
    )

    inhoud = (
        "Een SportBit-inschrijving is mislukt.\n\n"
        f"Inschrijving: {section}\n"
        f"Fout: {fout}\n"
    )

    if log:
        inhoud += (
            "\nLog:\n"
            "----------------------------------------\n"
            f"{log}\n"
            "----------------------------------------\n"
        )

    schrijf_log(
        f"Mislukte-inschrijving-notificatie "
        f"wordt verstuurd voor {section}.",
        onderwerp="notificatie",
    )

    if _enabled():
        instellingen = _mail_settings()

        message = EmailMessage()

        message["Subject"] = onderwerp
        message["From"] = instellingen["from"]
        message["To"] = instellingen["to"]

        message.set_content(
            inhoud
        )

        _smtp_send(
            message
        )

    if _ntfy_enabled():
        _ntfy_send(
            onderwerp,
            inhoud,
            prioriteit="high",
        )

    schrijf_log(
        f"Mislukte-inschrijving-notificatie "
        f"succesvol verstuurd voor {section}.",
        onderwerp="notificatie",
    )

def notify_inschrijving_gelukt(
    section,
    datum,
    les,
    tijd,
):
    """Meld dat een inschrijving succesvol is uitgevoerd."""

    onderwerp = (
        f"SportBit inschrijving gelukt: {les}"
    )

    inhoud = (
        "De SportBit-inschrijving is succesvol uitgevoerd.\n\n"
        f"Inschrijving: {section}\n"
        f"Datum: {datum}\n"
        f"Tijd: {tijd}\n"
        f"Les: {les}\n"
    )

    mail_versturen = (
        _enabled()
        and _success_mail_enabled()
    )

    ntfy_versturen = (
        _ntfy_enabled()
        and _ntfy_success_enabled()
    )

    if not mail_versturen and not ntfy_versturen:
        return

    schrijf_log(
        f"Succesnotificatie wordt verstuurd voor {section}.",
        onderwerp="notificatie",
    )

    if mail_versturen:

        instellingen = _mail_settings()

        message = EmailMessage()

        message["Subject"] = onderwerp
        message["From"] = instellingen["from"]
        message["To"] = instellingen["to"]

        message.set_content(
            inhoud
        )

        _smtp_send(
            message
        )

    if ntfy_versturen:

        _ntfy_send(
            onderwerp,
            inhoud,
            prioriteit="default",
        )

    schrijf_log(
        f"Succesnotificatie succesvol verstuurd "
        f"voor {section}.",
        onderwerp="notificatie",
    )
