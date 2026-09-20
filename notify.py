"""E-mailnotificaties voor mislukte SportBit-inschrijvingen.

De module staat bewust los van de Flask/SportBit-logica. Mail wordt alleen
verstuurd wanneer een daadwerkelijke inschrijfpoging mislukt, bijvoorbeeld
wanneer een vaste les niet bestaat op de doel-datum (feestdag/kerstWOD) of
wanneer SportBit de inschrijving niet bevestigt.

Configuratie via .env:
    NOTIFY_ENABLED=true
    NOTIFY_EMAIL_TO=jij@example.com
    SMTP_HOST=smtp.example.com
    SMTP_PORT=587
    SMTP_USERNAME=jij@example.com
    SMTP_PASSWORD=...
    SMTP_USE_TLS=true
    NOTIFY_FROM=jij@example.com   # optioneel
"""

import json
import os
import smtplib
from datetime import date, time
from pathlib import Path
from email.message import EmailMessage


def _enabled():
    return os.getenv("NOTIFY_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _smtp_send(message):
    host = os.getenv("SMTP_HOST", "").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT moet een geldig getal zijn") from exc

    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }

    if not host:
        raise RuntimeError("SMTP_HOST ontbreekt in .env")

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def _mail_settings():
    ontvanger = os.getenv("NOTIFY_EMAIL_TO", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    afzender = os.getenv("NOTIFY_FROM", "").strip() or username

    if not ontvanger:
        raise RuntimeError("NOTIFY_EMAIL_TO ontbreekt in .env")
    if not afzender:
        raise RuntimeError("NOTIFY_FROM of SMTP_USERNAME ontbreekt in .env")

    return ontvanger, afzender


def send_test_mail():
    """Stuur een eenvoudige testmail met dezelfde SMTP-configuratie."""
    ontvanger, afzender = _mail_settings()

    message = EmailMessage()
    message["Subject"] = "SportBit · testmail"
    message["From"] = afzender
    message["To"] = ontvanger
    message.set_content(
        "Dit is een testmail van de Go Personal SportBit-webapp.\n\n"
        "De e-mailnotificatie is correct geconfigureerd en bereikbaar."
    )

    _smtp_send(message)
    return True


def notify_les_ontbreekt(*, section, les, datum: date, tijd: time):
    """Stuur maximaal één mail per inschrijving en doel-datum als de les ontbreekt."""
    if not _enabled():
        return False

    ontvanger, afzender = _mail_settings()
    state_file = Path(__file__).resolve().with_name("notify_state.json")

    try:
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    except (OSError, json.JSONDecodeError):
        state = {}

    key = f"missing:{section}:{datum.isoformat()}:{tijd.strftime('%H:%M')}:{les.casefold()}"
    if state.get(key):
        return False

    onderwerp = f"SportBit les ontbreekt: {les} {datum:%d-%m-%Y} {tijd:%H:%M}"
    body = (
        "De dagelijkse SportBit-controle heeft de verwachte les niet gevonden.\n\n"
        f"Inschrijving : {section}\n"
        f"Les          : {les}\n"
        f"Datum        : {datum:%d-%m-%Y}\n"
        f"Tijd         : {tijd:%H:%M}\n\n"
        "De les kan bijvoorbeeld zijn geannuleerd, vervangen of nog niet door SportBit zijn gepubliceerd.\n"
        "Er is daarom geen automatische inschrijving voor deze les uitgevoerd.\n"
    )

    message = EmailMessage()
    message["Subject"] = onderwerp
    message["From"] = afzender
    message["To"] = ontvanger
    message.set_content(body)

    _smtp_send(message)

    state[key] = True
    tijdelijke = state_file.with_suffix(".tmp")
    tijdelijke.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tijdelijke.replace(state_file)
    return True


def notify_inschrijving_mislukt(*, section, les, datum: date, tijd: time, reden, log=""):
    """Stuur een e-mail als een inschrijfpoging niet lukt.

    Als notificaties niet zijn ingeschakeld of geen ontvanger is ingesteld,
    doet deze functie niets.
    """
    if not _enabled():
        return False

    ontvanger = os.getenv("NOTIFY_EMAIL_TO", "").strip()
    if not ontvanger:
        raise RuntimeError("NOTIFY_EMAIL_TO ontbreekt in .env")

    ontvanger, afzender = _mail_settings()

    onderwerp = f"SportBit inschrijving mislukt: {les} {datum:%d-%m-%Y} {tijd:%H:%M}"
    body = (
        "De automatische SportBit-inschrijving is niet gelukt.\n\n"
        f"Inschrijving : {section}\n"
        f"Les          : {les}\n"
        f"Datum        : {datum:%d-%m-%Y}\n"
        f"Tijd         : {tijd:%H:%M}\n"
        f"Reden        : {reden}\n\n"
        "Dit kan bijvoorbeeld gebeuren als de vaste les op deze datum niet "
        "bestaat of is vervangen door een andere les.\n\n"
        "SportBit-output:\n"
        f"{log or '(geen output)'}"
    )

    message = EmailMessage()
    message["Subject"] = onderwerp
    message["From"] = afzender
    message["To"] = ontvanger
    message.set_content(body)

    _smtp_send(message)

    return True
