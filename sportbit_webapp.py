#!/usr/bin/env python3

import configparser
import io
import os
import threading
import time as time_module
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from jinja2 import DictLoader


# ============================================================
# PADEN / OMGEVING
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"
CONFIG_FILE = BASE_DIR / "sportbit.conf"

load_dotenv(ENV_FILE)


# ============================================================
# SPORTBIT
# ============================================================

import sportbit2
import notify


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "sportbit-local-secret-key",
)


# Voorkomt dat meerdere SportBit-acties tegelijk
# worden uitgevoerd.
run_lock = threading.Lock()


# Laatste SportBit-output voor de logpagina.
last_output = ""


# Status wordt tijdens runtime in geheugen bewaard.
statuses = {}

# Cache voor de twee eerstvolgende lessen per inschrijving.
next_lessons_cache = {}

# Statuscontrole wordt maximaal eenmaal per 5 minuten
# per inschrijving uitgevoerd.
STATUS_CACHE_SECONDS = 5 * 60


# ============================================================
# DAGEN
# ============================================================

DAGEN = {
    "maandag": 0,
    "dinsdag": 1,
    "woensdag": 2,
    "donderdag": 3,
    "vrijdag": 4,
    "zaterdag": 5,
    "zondag": 6,
}


# ============================================================
# LOGO
# ============================================================

LOGO_SVG = """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 520 130"
    role="img"
    aria-label="CrossFit Go Personal"
>
    <style>
        .crossfit {
            fill: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .main {
            fill: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: 900;
            letter-spacing: -3px;
        }

        .accent {
            fill: #8bc34a;
            font-family: Arial, Helvetica, sans-serif;
            font-weight: 900;
            letter-spacing: -2px;
        }
    </style>

    <text x="8" y="31" class="crossfit" font-size="22">
        CROSSFIT
    </text>

    <text x="5" y="82" class="main" font-size="55">
        GO
    </text>

    <text x="102" y="82" class="accent" font-size="55">
        PERSONAL
    </text>

    <rect
        x="7"
        y="96"
        width="500"
        height="5"
        fill="#8bc34a"
    />
</svg>
"""


# ============================================================
# CSS
# ============================================================

CSS = r"""
:root {
    --black: #080808;
    --black-2: #101010;
    --black-3: #171717;
    --black-4: #202020;

    --green: #8bc34a;
    --green-bright: #9ccc50;
    --green-dark: #648f35;

    --white: #ffffff;
    --gray: #a5a5a5;
    --gray-2: #777777;

    --border: #292929;

    --success: #8bc34a;
    --warning: #f0b429;
    --danger: #ef4444;
}


* {
    box-sizing: border-box;
}


html {
    background: var(--black);
}

body {
    margin: 0;
    min-height: 100vh;

    background:
        radial-gradient(
            circle at 85% 0%,
            rgba(139, 195, 74, .08),
            transparent 30%
        ),
        var(--black);

    color: var(--white);

    font-family:
        "Arial Narrow",
        "Roboto Condensed",
        Arial,
        Helvetica,
        sans-serif;

    -webkit-tap-highlight-color: transparent;
}

button,
a,
input,
select {
    -webkit-tap-highlight-color: transparent;
}

.button,
.header,
.logo,
.status {
    user-select: none;
    -webkit-user-select: none;
}

/* ============================================================
   HEADER
   ============================================================ */


@media (max-width: 700px) {

    .header-inner {
        min-height: 65px;
        padding: 8px 12px;
    }

    .logo {
        width: 155px;
    }

    .header-title {
        display: none;
    }

    .header-inner > .button {
        min-height: 36px;
        padding: 8px 11px;
        font-size: 10px;
    }

    .container {
        padding:
            20px 12px 45px;
    }

}







.header {
    position: sticky;
    top: 0;
    z-index: 1000;

    background: #050505;

    border-bottom:
        4px solid var(--green);

    box-shadow:
        0 5px 25px rgba(0, 0, 0, .45);
}

.header-inner {
    max-width: 1100px;

    min-height: 88px;

    margin: 0 auto;

    padding:
        12px 20px;

    display: flex;

    align-items: center;

    gap: 20px;
}


.logo {
    display: block;

    width: 220px;

    height: auto;
}


.header-title {
    margin-left: auto;

    color: var(--gray);

    font-size: 12px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: 2px;
}


/* ============================================================
   CONTAINER
   ============================================================ */

.container {
    max-width: 1100px;

    margin: 0 auto;

    padding:
        35px 20px 60px;
}


.page-title {
    margin-bottom: 28px;

    padding-bottom: 18px;

    border-bottom:
        1px solid var(--border);
}


.page-title h1 {
    margin: 0;

    font-size: 38px;

    line-height: 1;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: -1px;
}


.page-title h1::after {
    content: "";

    display: block;

    width: 55px;

    height: 5px;

    margin-top: 13px;

    background: var(--green);
}


.page-title p {
    margin:
        13px 0 0;

    color: var(--gray);

    font-size: 14px;

    text-transform: uppercase;

    letter-spacing: 1px;
}


/* ============================================================
   CARDS
   ============================================================ */

.cards {
    display: grid;

    gap: 18px;
}


.card {
    position: relative;

    background:
        linear-gradient(
            135deg,
            var(--black-2),
            var(--black-3)
        );

    border:
        1px solid var(--border);

    border-left:
        5px solid var(--green);

    border-radius: 0;

    padding: 23px;

    box-shadow:
        0 10px 30px rgba(0, 0, 0, .25);
}


.card-header {
    display: flex;

    justify-content: space-between;

    align-items: flex-start;

    gap: 20px;
}


.card h2 {
    margin: 0;

    color: var(--white);

    font-size: 27px;

    line-height: 1;

    font-weight: 900;

    text-transform: uppercase;
}


.schedule {
    margin-top: 8px;

    color: var(--gray);

    font-size: 15px;

    font-weight: 700;

    text-transform: uppercase;

    letter-spacing: .8px;
}




/* ============================================================
   VOLGENDE TWEE LESSEN
   ============================================================ */

.next-lessons {
    margin-top: 20px;

    display: grid;

    gap: 8px;
}

.next-lesson {
    padding: 14px 16px;

    background: rgba(0, 0, 0, .30);

    border: 1px solid var(--border);

    border-left: 3px solid #444;

    display: grid;

    grid-template-columns: 1fr auto;

    align-items: center;

    gap: 15px;
}

.next-lesson-date {
    color: var(--white);

    font-size: 15px;

    font-weight: 900;

    text-transform: uppercase;
}

.next-lesson-meta {
    margin-top: 4px;

    color: var(--gray-2);

    font-size: 11px;
}

@media (max-width: 700px) {
    .next-lesson {
        grid-template-columns: 1fr;
        gap: 10px;
    }
}


/* ============================================================
   STATUS
   ============================================================ */

.status {
    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding:
        7px 11px;

    font-size: 11px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: .8px;

    white-space: nowrap;

    border: 1px solid;
}


.status::before {
    content: "";

    width: 8px;

    height: 8px;

    border-radius: 50%;

    background: currentColor;

    box-shadow:
        0 0 7px currentColor;
}


.status-ingeschreven {
    color: var(--success);

    background:
        rgba(139, 195, 74, .08);

    border-color:
        rgba(139, 195, 74, .35);
}


.status-wachtlijst {
    color: var(--warning);

    background:
        rgba(240, 180, 41, .08);

    border-color:
        rgba(240, 180, 41, .35);
}


.status-gesloten {
    color: var(--gray);

    background:
        rgba(255, 255, 255, .04);

    border-color:
        #444;
}


.status-niet-ingeschreven {
    color: var(--gray);

    background:
        rgba(255, 255, 255, .04);

    border-color:
        #444;
}


.status-geen-event {
    color: var(--danger);

    background:
        rgba(239, 68, 68, .08);

    border-color:
        rgba(239, 68, 68, .35);
}


.status-onbekend {
    color: var(--gray-2);

    background:
        rgba(255, 255, 255, .03);

    border-color:
        #333;
}


/* ============================================================
   STATUS BOX
   ============================================================ */

.status-box {
    margin-top: 20px;

    padding:
        13px 16px;

    background:
        rgba(0, 0, 0, .30);

    border:
        1px solid var(--border);

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 15px;
}


.status-label {
    color: var(--gray);

    font-size: 10px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: 1.5px;
}


.checked {
    margin-top: 6px;

    color: var(--gray-2);

    font-size: 11px;
}


/* ============================================================
   EVENT INFO
   ============================================================ */

.event-info {
    margin-top: 12px;

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 1px;

    background:
        var(--border);
}


.event-item {
    padding:
        11px 13px;

    background:
        var(--black-3);
}


.event-label {
    color: var(--gray-2);

    font-size: 9px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: 1px;
}


.event-value {
    margin-top: 4px;

    color: var(--white);

    font-size: 14px;

    font-weight: 900;
}


/* ============================================================
   NEXT LES
   ============================================================ */

.next {
    margin-top: 12px;

    padding:
        14px 16px;

    background:
        rgba(0, 0, 0, .30);

    border:
        1px solid var(--border);

    border-left:
        2px solid var(--green);

    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 15px;
}


.next-label {
    color: var(--gray);

    font-size: 10px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: 1.5px;
}


.next strong {
    color: var(--green);

    font-size: 18px;

    font-weight: 900;

    text-transform: uppercase;
}


/* ============================================================
   BUTTONS
   ============================================================ */

.actions {
    margin-top: 20px;

    display: flex;

    flex-wrap: wrap;

    gap: 8px;
}


.button {
    display: inline-flex;

    align-items: center;

    justify-content: center;

    min-height: 40px;

    padding:
        9px 15px;

    border:
        1px solid #444;

    border-radius: 0;

    background:
        transparent;

    color:
        var(--white);

    text-decoration: none;

    font-family: inherit;

    font-size: 11px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: .8px;

    cursor: pointer;

    transition:
        background .15s,
        border-color .15s,
        color .15s;
}


.button:hover {
    background:
        var(--black-4);

    border-color:
        #555;
}


.button-primary {
    background:
        var(--green);

    border-color:
        var(--green);

    color:
        #050505;
}


.button-primary:hover {
    background:
        var(--green-bright);

    border-color:
        var(--green-bright);

    color:
        #050505;
}


.button-danger {
    color:
        #ff7777;

    border-color:
        #572323;
}


.button-danger:hover {
    background:
        #2a1010;

    border-color:
        var(--danger);
}


.actions form {
    margin: 0;
}


/* ============================================================
   ALERTS
   ============================================================ */

.alert {
    margin-bottom: 18px;

    padding:
        14px 16px;

    border-left:
        4px solid var(--green);

    background:
        #151d0f;

    color:
        var(--white);

    font-size: 14px;

    font-weight: 700;
}


.alert-error {
    border-left-color:
        var(--danger);

    background:
        #211010;
}


.alert-warning {
    border-left-color:
        var(--warning);

    background:
        #211b0c;
}


/* ============================================================
   FORMS
   ============================================================ */

.form-card {
    max-width: 650px;
}


.form-card h1 {
    margin-top: 0;

    font-size: 30px;

    font-weight: 900;

    text-transform: uppercase;
}


form label {
    display: block;

    margin-top: 20px;

    margin-bottom: 7px;

    color: var(--gray);

    font-size: 12px;

    font-weight: 900;

    text-transform: uppercase;

    letter-spacing: 1px;
}


form input,
form select {
    width: 100%;

    min-height: 45px;

    padding:
        10px 12px;

    border:
        1px solid #3a3a3a;

    border-radius: 0;

    background:
        #080808;

    color:
        var(--white);

    font-family: inherit;

    font-size: 15px;

    font-weight: 600;
}


form input:focus,
form select:focus {
    outline: none;

    border-color:
        var(--green);

    box-shadow:
        0 0 0 2px
        rgba(139, 195, 74, .15);
}


form select option {
    background:
        #111;

    color:
        white;
}


.hint {
    margin-top: 7px;

    color: var(--gray-2);

    font-size: 12px;
}


.form-actions {
    margin-top: 27px;

    display: flex;

    justify-content: flex-end;

    gap: 8px;
}


/* ============================================================
   LOG
   ============================================================ */

.log {
    margin-top: 20px;

    padding:
        18px;

    background:
        #050505;

    border:
        1px solid var(--border);

    border-left:
        3px solid var(--green);

    color:
        #d6d6d6;

    white-space:
        pre-wrap;

    word-break:
        break-word;

    overflow-x:
        auto;

    font-family:
        "Courier New",
        monospace;

    font-size: 12px;

    line-height: 1.55;
}


/* ============================================================
   EMPTY
   ============================================================ */

.empty {
    padding:
        55px 20px;

    text-align: center;
}


.empty h2 {
    text-transform: uppercase;
}


.empty p {
    color:
        var(--gray);
}


.help-button {
    width: 42px;
    min-width: 42px;
    max-width: 42px;
    height: 42px;
    min-height: 42px;
    max-height: 42px;
    padding: 0;
    flex: 0 0 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    font-weight: 800;
    font-size: 18px;
    box-sizing: border-box;
}


/* ============================================================
   DOCUMENTATIE
   ============================================================ */

.documentation h2 {
    margin-top: 28px;
    margin-bottom: 10px;
}

.documentation h2:first-child {
    margin-top: 0;
}

.documentation p,
.documentation li {
    color: #d0d0d0;
    line-height: 1.65;
}

.documentation ul {
    padding-left: 22px;
}

.documentation code {
    color: #ffffff;
    background: #111111;
    padding: 2px 5px;
    border-radius: 4px;
}


/* ============================================================
   MOBILE
   ============================================================ */

@media (max-width: 700px) {

    .header-inner {
        min-height: 75px;

        padding:
            10px 13px;
    }


    .logo {
        width: 170px;
    }


    .header-title {
        display: none;
    }


    .container {
        padding:
            24px 12px 45px;
    }


    .page-title h1 {
        font-size: 30px;
    }


    .card {
        padding:
            17px;

        border-left-width:
            4px;
    }


    .card h2 {
        font-size: 22px;
    }


    .card-header {
        flex-direction: column;

        gap: 12px;
    }


    .status-box {
        align-items:
            flex-start;

        flex-direction:
            column;
    }


    .event-info {
        grid-template-columns:
            repeat(2, 1fr);
    }


    .next {
        align-items:
            flex-start;

        flex-direction:
            column;
    }


    .actions {
        flex-direction:
            column;
    }


    .actions > *,
    .actions form,
    .actions .button,
    .actions form .button {
        width: 100%;
    }


    .button {
        width: 100%;
    }


    .form-actions {
        flex-direction:
            column-reverse;
    }


    .form-actions .button {
        width: 100%;
    }

}
"""


# ============================================================
# TEMPLATES
# ============================================================

BASE_TEMPLATE = """
<!doctype html>

<html lang="nl">

<head>

    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <meta
        name="theme-color"
        content="#080808"
    >

    <link
        rel="manifest"
        href="{{ url_for('static', filename='manifest.json') }}"
    >

    <link
        rel="icon"
        type="image/svg+xml"
        href="{{ url_for('static', filename='icon.svg') }}"
    >

    <meta
        name="mobile-web-app-capable"
        content="yes"
    >

    <meta
        name="apple-mobile-web-app-capable"
        content="yes"
    >

    <meta
        name="apple-mobile-web-app-status-bar-style"
        content="black"
    >

    <meta
        name="apple-mobile-web-app-title"
        content="SportBit"
    >

    <title>
        Go Personal · SportBit
    </title>

    <style>
        {{ css|safe }}
    </style>

</head>


<body>

<header class="header">

    <div class="header-inner">

        <a href="{{ url_for('index') }}">

            <img
                class="logo"
                src="{{ logo }}"
                alt="CrossFit Go Personal"
            >

        </a>


        <div class="header-title">
            Automatische inschrijvingen
        </div>


        <a
            href="{{ url_for('nieuwe_inschrijving') }}"
            class="button button-primary"
        >
            + Toevoegen
        </a>

    </div>

</header>


<main class="container">

    {% with messages = get_flashed_messages(
        with_categories=true
    ) %}

        {% if messages %}

            {% for category, message in messages %}

                <div
                    class="alert alert-{{ category }}"
                >
                    {{ message }}
                </div>

            {% endfor %}

        {% endif %}

    {% endwith %}


    {% block content %}{% endblock %}

</main>

<script>
if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/static/sw.js")
            .then(function (registration) {
                console.log(
                    "SportBit PWA actief:",
                    registration.scope
                );
            })
            .catch(function (error) {
                console.error(
                    "PWA service worker fout:",
                    error
                );
            });
    });
}
</script>

</body>

</html>
"""


INDEX_TEMPLATE = """
{% extends "base.html" %}

{% block content %}

<div class="page-title" style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">

    <h1>
        Mijn inschrijvingen
    </h1>

    <a
        href="{{ url_for('documentatie') }}"
        class="button help-button"
        title="Documentatie"
        aria-label="Documentatie"
    >
        ?
    </a>

</div>


{% if inschrijvingen %}

<div class="cards">

{% for item in inschrijvingen %}

<section class="card">

    <div class="card-header">

        <div>

            <h2>
                {{ item.les }}
            </h2>

            <div class="schedule">

                {{ item.dag|capitalize }}

                &nbsp;·&nbsp;

                {{ item.tijd }}

            </div>


        </div>


    </div>


    <div class="next-lessons">

        <div class="status-label">
            Eerstvolgende 2 lessen
        </div>

        {% for les in item.lessen %}

        <div class="next-lesson">

            <div>
                <div class="next-lesson-date">
                    {{ ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"][les.datum.weekday()] }} {{ les.datum.strftime("%d-%m-%Y · %H:%M") }}
                </div>

                <div class="next-lesson-meta">
                    {{ item.les }}
                    {% if les.event %}
                        · {{ les.event.get('aantalDeelnemers', '-') }}/{{ les.event.get('maxDeelnemers', '-') }} deelnemers
                    {% endif %}
                </div>
            </div>

            <span class="status status-{{ les.status.css }}">
                {{ les.status.text }}
            </span>

        </div>

        {% endfor %}

    </div>


    <div class="actions">

        {% if item.status.code == "niet-ingeschreven" %}

        <form
            method="post"
            action="{{
                url_for(
                    'run_inschrijving',
                    section=item.naam
                )
            }}"
        >

            <button
                type="submit"
                class="button button-primary"
                onclick="
                    return confirm(
                        'Nu proberen in te schrijven?'
                    );
                "
            >
                Nu inschrijven
            </button>

        </form>

        {% endif %}


        <a
            href="{{
                url_for(
                    'bewerk_inschrijving',
                    section=item.naam
                )
            }}"
            class="button"
        >
            Bewerken
        </a>


        <form
            method="post"
            action="{{
                url_for(
                    'delete_inschrijving',
                    section=item.naam
                )
            }}"
        >

            <button
                type="submit"
                class="button button-danger"
                onclick="
                    return confirm(
                        'Deze inschrijving verwijderen?'
                    );
                "
            >
                Verwijderen
            </button>

        </form>

    </div>

</section>

{% endfor %}

</div>


{% else %}

<section class="card empty">

    <h2>
        Geen inschrijvingen
    </h2>

    <p>
        Voeg je eerste SportBit-inschrijving toe.
    </p>

    <a
        href="{{ url_for('nieuwe_inschrijving') }}"
        class="button button-primary"
    >
        Inschrijving toevoegen
    </a>

</section>

{% endif %}


<section class="card" style="margin-top: 25px;">

    <h2 style="font-size: 18px;">
        Informatie
    </h2>

    <p
        style="
            color: #a5a5a5;
            font-size: 14px;
            line-height: 1.6;
        "
    >
        De configuratie wordt opgeslagen in
        <code>sportbit.conf</code>.
        De SportBit-inloggegevens worden uit
        <code>.env</code> gelezen.
    </p>


    <div style="display: flex; gap: 10px; flex-wrap: wrap;">

        <a
            href="{{ url_for('log') }}"
            class="button"
        >
            Laatste log bekijken
        </a>

        <form
            method="post"
            action="{{ url_for('testmail') }}"
            style="margin: 0;"
        >
            <button
                type="submit"
                class="button button-primary"
            >
                Stuur testmail
            </button>
        </form>

    </div>

</section>

{% endblock %}
"""


EDIT_TEMPLATE = """
{% extends "base.html" %}

{% block content %}

<section class="card form-card">

    <h1>

        {% if nieuw %}
            Inschrijving toevoegen
        {% else %}
            Inschrijving bewerken
        {% endif %}

    </h1>


    <form method="post">

        <label for="dag">
            Dag
        </label>

        <select
            id="dag"
            name="dag"
            required
        >

            {% for dag in dagen %}

            <option
                value="{{ dag }}"
                {% if item.dag == dag %}
                    selected
                {% endif %}
            >
                {{ dag|capitalize }}
            </option>

            {% endfor %}

        </select>


        <label for="tijd">
            Tijd
        </label>

        <input
            id="tijd"
            name="tijd"
            type="time"
            value="{{ item.tijd }}"
            required
        >


        <label for="les">
            Les
        </label>

        <input
            id="les"
            name="les"
            type="text"
            value="{{ item.les }}"
            placeholder="Bijvoorbeeld Crossfit"
            required
        >


        <p class="hint">
            De lesnaam wordt hoofdletterongevoelig
            met SportBit vergeleken.
        </p>


        <div class="form-actions">

            <a
                href="{{ url_for('index') }}"
                class="button"
            >
                Annuleren
            </a>


            <button
                type="submit"
                class="button button-primary"
            >
                Opslaan
            </button>

        </div>

    </form>

</section>

{% endblock %}
"""


LOG_TEMPLATE = """
{% extends "base.html" %}

{% block content %}

<div class="page-title">

    <h1>
        Laatste log
    </h1>

    <p>
        SportBit activiteit
    </p>

</div>


<section class="card">

    <pre class="log">{{ output }}</pre>

    <br>

    <a
        href="{{ url_for('index') }}"
        class="button"
    >
        Terug
    </a>

</section>

{% endblock %}
"""


DOCUMENTATION_TEMPLATE = """
{% extends "base.html" %}

{% block content %}

<div class="page-title">
    <h1>Documentatie</h1>
    <p>Hoe de automatische SportBit-inschrijvingen en notificaties werken.</p>
</div>

<section class="card documentation">

    <h2>1. Automatische inschrijving</h2>
    <p>
        Voor iedere inschrijving uit <code>sportbit.conf</code> wordt de eerstvolgende
        les op de ingestelde weekdag en tijd bepaald. De automatische registratie
        is gericht op de les precies één week later.
    </p>
    <p>
        Rond <strong>00:01</strong> op de dag waarop de inschrijving opent wordt
        SportBit gecontroleerd. De les wordt gezocht op <strong>lesnaam + tijd</strong>.
        Het event-ID wordt dus niet vooraf vastgelegd.
    </p>

    <h2>2. Dagelijkse controle om 00:01</h2>
    <p>
        De webapp heeft een achtergrondcontrole die dagelijks rond 00:01 kijkt
        voor welke geconfigureerde lessen die dag de boekingsperiode opent.
    </p>
    <p>
        Als de verwachte les niet bestaat, bijvoorbeeld omdat een WOD is vervangen
        door een andere les, wordt <strong>geen inschrijving uitgevoerd</strong> en
        kan direct een notificatiemail worden verstuurd.
    </p>
    <p>
        Een technische fout bij het ophalen van SportBit wordt niet automatisch
        als “les ontbreekt” beschouwd. Zo voorkomen we een verkeerde melding door
        bijvoorbeeld een tijdelijke netwerk- of SportBit-storing.
    </p>

    <h2>3. Wanneer wordt een e-mail gestuurd?</h2>
    <ul>
        <li><strong>Les ontbreekt:</strong> de dagelijkse controle vindt de verwachte les niet op de doel-datum en het ingestelde tijdstip.</li>
        <li><strong>Inschrijving mislukt:</strong> een daadwerkelijke automatische inschrijfpoging levert een fout op of de inschrijving kan niet worden bevestigd.</li>
        <li><strong>Testmail:</strong> via <strong>Stuur testmail</strong> kan handmatig worden gecontroleerd of de SMTP-configuratie werkt.</li>
    </ul>

    <h2>4. Wanneer wordt géén melding gestuurd?</h2>
    <ul>
        <li>Als je al bent ingeschreven.</li>
        <li>Als je al op de wachtlijst staat.</li>
        <li>Als de boekingsperiode nog niet geopend is.</li>
        <li>Als een tijdelijke technische fout niet kan worden vastgesteld als een ontbrekende les.</li>
    </ul>

    <h2>5. Dubbele meldingen voorkomen</h2>
    <p>
        Voor een ontbrekende les wordt per inschrijving en doel-datum maximaal één
        melding verstuurd. De registratie hiervan staat in <code>notify_state.json</code>.
        Hierdoor veroorzaakt een herhaalde controle niet steeds opnieuw dezelfde mail.
    </p>

    <h2>6. E-mailconfiguratie</h2>
    <p>
        De notificaties gebruiken de SMTP-instellingen uit <code>.env</code>.
        De module <code>notify.py</code> bevat uitsluitend de e-mailafhandeling;
        de SportBit- en Flask-logica staat in de webapp.
    </p>

    <h2>7. Statussen in de webapp</h2>
    <ul>
        <li><strong>INGESCHREVEN</strong> — SportBit meldt dat de registratie gelukt is.</li>
        <li><strong>WACHTLIJST</strong> — je staat op de wachtlijst.</li>
        <li><strong>NIET INGESCHREVEN</strong> — de les bestaat en registratie is mogelijk.</li>
        <li><strong>INSCHRIJVING GESLOTEN</strong> — de les bestaat, maar het boekingsmoment is nog niet aangebroken.</li>
        <li><strong>GEEN EVENT</strong> — de verwachte les is niet gevonden.</li>
        <li><strong>STATUS ONBEKEND</strong> — de controle kon niet betrouwbaar worden uitgevoerd.</li>
    </ul>

    <div class="form-actions">
        <a href="{{ url_for('index') }}" class="button">Terug</a>
    </div>

</section>

{% endblock %}
"""


app.jinja_loader = DictLoader({
    "base.html": BASE_TEMPLATE,
    "index.html": INDEX_TEMPLATE,
    "edit.html": EDIT_TEMPLATE,
    "log.html": LOG_TEMPLATE,
    "documentation.html": DOCUMENTATION_TEMPLATE,
})


# ============================================================
# TEMPLATE RENDERER
# ============================================================

def render_page(template, **kwargs):

    logo = (
        "data:image/svg+xml,"
        + LOGO_SVG
        .replace("#", "%23")
        .replace("<", "%3C")
        .replace(">", "%3E")
        .replace('"', "%22")
        .replace("\n", "")
    )

    return render_template(
        template,
        css=CSS,
        logo=logo,
        **kwargs,
    )


# ============================================================
# CONFIG LEZEN
# ============================================================

def lees_config():

    config = configparser.ConfigParser()

    if not CONFIG_FILE.exists():
        return []

    config.read(
        CONFIG_FILE,
        encoding="utf-8",
    )

    resultaten = []

    for section in config.sections():

        if not section.startswith(
            "inschrijving_"
        ):
            continue

        resultaten.append({
            "naam": section,

            "dag": config.get(
                section,
                "dag",
                fallback="",
            ).strip().lower(),

            "tijd": config.get(
                section,
                "tijd",
                fallback="",
            ).strip(),

            "les": config.get(
                section,
                "les",
                fallback="",
            ).strip(),
        })

    return resultaten


# ============================================================
# CONFIG SCHRIJVEN
# ============================================================

def schrijf_config(config):

    tijdelijke_file = (
        CONFIG_FILE.with_suffix(".tmp")
    )

    with tijdelijke_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        config.write(file)

    tijdelijke_file.replace(
        CONFIG_FILE
    )


def volgende_nummer(config):

    nummers = []

    for section in config.sections():

        if not section.startswith(
            "inschrijving_"
        ):
            continue

        try:

            nummer = int(
                section.split("_", 1)[1]
            )

            nummers.append(nummer)

        except (
            ValueError,
            IndexError,
        ):

            pass

    return (
        max(nummers) + 1
        if nummers
        else 1
    )


# ============================================================
# TIJD PARSEN
# ============================================================

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


    # Belangrijk:
    # datetime.time is al een geldige tijd.
    #
    # We mogen deze NIET opnieuw door
    # datetime.strptime() sturen.

    if hasattr(tijd, "hour") and hasattr(
        tijd,
        "minute",
    ):

        return tijd


    raise ValueError(
        f"Ongeldig tijdstype: "
        f"{type(tijd).__name__}"
    )


# ============================================================
# VOLGENDE DATUM
# ============================================================

def volgende_datum(dag, tijd):

    """
    Bepaal de eerstvolgende datum/tijd
    voor de opgegeven weekdag.

    'tijd' mag zowel een string als
    datetime.time zijn.
    """

    dag = str(
        dag
    ).strip().lower()


    if dag not in DAGEN:

        return None


    tijd_obj = parse_tijd(
        tijd
    )


    nu = datetime.now(
        sportbit2.TIMEZONE
    )


    dagen_tot = (
        DAGEN[dag]
        - nu.weekday()
    ) % 7


    doel_datum = (
        nu.date()
        + timedelta(
            days=dagen_tot
        )
    )


    doel = datetime.combine(
        doel_datum,
        tijd_obj,
        tzinfo=sportbit2.TIMEZONE,
    )


    # Als het tijdstip vandaag al voorbij is,
    # pak de volgende week.

    if doel <= nu:

        doel += timedelta(
            days=7
        )


    return doel


# ============================================================
# EVENTS UIT SPORTBIT RESPONSE HALEN
# ============================================================

def extract_events(data):

    if isinstance(data, list):

        if all(
            isinstance(x, dict)
            for x in data
        ):

            return data


    if isinstance(data, dict):

        mogelijke_keys = (
            "events",
            "data",
            "items",
            "result",
            "results",
            "ochtend",
            "middag",
            "avond",
        )


        for key in mogelijke_keys:

            value = data.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                if all(
                    isinstance(x, dict)
                    for x in value
                ):

                    return value


        # Eén niveau dieper zoeken.

        for value in data.values():

            if isinstance(
                value,
                dict,
            ):

                nested = extract_events(
                    value
                )

                if nested is not None:

                    return nested


    return None


# ============================================================
# EVENT ZOEKEN
# ============================================================

def zoek_event(
    session,
    datum,
    les,
    tijd,
):

    tijd_obj = parse_tijd(
        tijd
    )


    print(
        f"Events ophalen voor {datum} "
        f"({les} om "
        f"{tijd_obj.strftime('%H:%M')})..."
    )


    response = session.get(
        sportbit2.EVENTS_URL,

        params={
            "datum": datum.isoformat()
        },

        headers={
            "Origin":
                sportbit2.BASE_URL,

            "Referer":
                f"{sportbit2.BASE_URL}/web/nl/",
        },

        timeout=15,
    )


    response.raise_for_status()


    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "SportBit gaf geen geldige JSON terug."
        )


    events = extract_events(
        data
    )


    if events is None:

        raise RuntimeError(
            "Onverwachte events-response. "
            f"Type: {type(data).__name__}"
        )


    print(
        f"{len(events)} events ontvangen."
    )


    # ========================================================
    # HOOFDLETTERONGEVOELIG
    # ========================================================

    gewenste_les = (
        str(les)
        .strip()
        .casefold()
    )


    for event in events:

        titel = str(
            event.get(
                "titel",
                "",
            )
        ).strip()


        start_string = event.get(
            "start"
        )


        if not start_string:

            continue


        try:

            start = datetime.fromisoformat(
                start_string
            )

        except (
            ValueError,
            TypeError,
        ):

            continue


        if (
            titel.casefold()
            == gewenste_les
            and start.hour
            == tijd_obj.hour
            and start.minute
            == tijd_obj.minute
        ):

            return event


    return None


# ============================================================
# STATUS OBJECT MAKEN
# ============================================================

def maak_status(
    code,
    text,
    event=None,
):

    checked_at = datetime.now(
        sportbit2.TIMEZONE
    )


    return {
        "code": code,

        "css": code,

        "text": text,

        "event": event,

        "checked_at":
            checked_at.strftime(
                "%d-%m-%Y %H:%M:%S"
            ),

        # Voor de 5-minuten cache.
        "checked_at_ts": checked_at.timestamp(),
    }


# ============================================================
# EERSTVOLGENDE TWEE LESSEN
# ============================================================

def inschrijving_open(datum):
    """
    Een les kan pas worden geboekt vanaf 00:00 op de dag
    die precies zeven dagen vóór de lesdatum ligt.
    """

    nu = datetime.now(sportbit2.TIMEZONE)

    openingsdatum = datum - timedelta(days=7)
    openingsmoment = datetime.combine(
        openingsdatum,
        datetime.min.time(),
        tzinfo=sportbit2.TIMEZONE,
    )

    return nu >= openingsmoment


def volgende_twee_datums(dag, tijd):

    eerste = volgende_datum(dag, tijd)

    if eerste is None:
        return []

    return [
        eerste,
        eerste + timedelta(days=7),
    ]


def automatische_volgende_twee_controle(section):
    """Controleer de twee eerstvolgende lessen, met 5-minutencache."""

    bestaande = next_lessons_cache.get(section)

    if bestaande:
        checked_at_ts = bestaande.get("checked_at_ts")
        if checked_at_ts:
            leeftijd = (
                datetime.now(sportbit2.TIMEZONE).timestamp()
                - checked_at_ts
            )
            if leeftijd < STATUS_CACHE_SECONDS:
                return bestaande.get("lessen", [])

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if section not in config:
        return []

    dag = config.get(section, "dag").strip().lower()
    tijd = parse_tijd(config.get(section, "tijd").strip())
    les = config.get(section, "les").strip()

    datums = volgende_twee_datums(dag, tijd)
    if not datums:
        return []

    resultaten = []

    try:
        with run_lock:
            session = sportbit2.create_session()
            sportbit2.login(session)

            for doel in datums:
                event = zoek_event(
                    session=session,
                    datum=doel.date(),
                    les=les,
                    tijd=tijd,
                )

                if event is None:
                    status = maak_status("geen-event", "GEEN EVENT")
                elif event.get("aangemeld"):
                    status = maak_status("ingeschreven", "INGESCHREVEN", event)
                elif event.get("opWachtlijst"):
                    status = maak_status("wachtlijst", "WACHTLIJST", event)
                elif not inschrijving_open(doel.date()):
                    status = maak_status("gesloten", "INSCHRIJVING GESLOTEN", event)
                else:
                    status = maak_status("niet-ingeschreven", "NIET INGESCHREVEN", event)

                resultaten.append({
                    "datum": doel,
                    "status": status,
                    "event": event,
                })

    except Exception:
        if bestaande and bestaande.get("lessen"):
            return bestaande["lessen"]

        onbekend = {
            "code": "onbekend",
            "css": "onbekend",
            "text": "STATUS ONBEKEND",
            "event": None,
            "checked_at": None,
            "checked_at_ts": None,
        }
        return [
            {"datum": datum, "status": onbekend, "event": None}
            for datum in datums
        ]

    next_lessons_cache[section] = {
        "lessen": resultaten,
        "checked_at_ts": datetime.now(sportbit2.TIMEZONE).timestamp(),
    }

    if resultaten:
        statuses[section] = resultaten[0]["status"]

    return resultaten


# ============================================================
# DAGELIJKSE CONTROLE OM 00:01
# ============================================================

def controleer_verwachte_lessen_en_mail():
    """Controleer rond 00:01 de lessen waarvoor vandaag boeken opent."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    vandaag = datetime.now(sportbit2.TIMEZONE).date()

    for section in config.sections():
        if not section.startswith("inschrijving_"):
            continue

        try:
            dag = config.get(section, "dag").strip().lower()
            tijd = parse_tijd(config.get(section, "tijd").strip())
            les = config.get(section, "les").strip()

            if dag not in DAGEN or not les:
                continue

            doel = volgende_datum(dag, tijd)
            if doel is None or doel.date() - timedelta(days=7) != vandaag:
                continue

            with run_lock:
                session = sportbit2.create_session()
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
            # Een technische fout is geen bewijs dat de les ontbreekt.
            print(f"Dagelijkse lescontrole mislukt voor {section}: {error}")


def start_dagelijkse_controle():
    """Start één achtergrondthread die dagelijks rond 00:01 controleert."""
    def worker():
        laatste_controle_datum = None

        while True:
            try:
                nu = datetime.now(sportbit2.TIMEZONE)
                vandaag = nu.date()

                if nu.hour == 0 and nu.minute >= 1 and laatste_controle_datum != vandaag:
                    controleer_verwachte_lessen_en_mail()
                    laatste_controle_datum = vandaag

                time_module.sleep(20)

            except Exception as error:
                print(f"Dagelijkse scheduler-fout: {error}")
                time_module.sleep(20)

    thread = threading.Thread(
        target=worker,
        name="sportbit-dagelijkse-controle",
        daemon=True,
    )
    thread.start()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    inschrijvingen = lees_config()

    for item in inschrijvingen:
        item["volgende"] = volgende_datum(
            item["dag"],
            item["tijd"],
        )

        item["lessen"] = automatische_volgende_twee_controle(
            item["naam"]
        )

        item["status"] = (
            item["lessen"][0]["status"]
            if item["lessen"]
            else get_status(item["naam"])
        )

    return render_page(
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

    try:

        resultaat = (
            voer_inschrijving_uit(
                section
            )
        )


        if resultaat:

            flash(
                "SportBit-actie succesvol uitgevoerd.",
                "success",
            )

        else:

            flash(
                "SportBit-actie mislukt.",
                "error",
            )


    except Exception as error:

        flash(
            f"Inschrijving mislukt: {error}",
            "error",
        )


    return redirect(
        url_for("index")
    )


# ============================================================
# INSCHRIJVEN
# ============================================================

def voer_inschrijving_uit(section):
    global last_output

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if section not in config:
        raise RuntimeError(f"Onbekende inschrijving: {section}")

    dag = config.get(section, "dag").strip().lower()
    tijd_string = config.get(section, "tijd").strip()
    les = config.get(section, "les").strip()
    tijd = parse_tijd(tijd_string)
    doel = volgende_datum(dag, tijd)

    if doel is None:
        raise RuntimeError("Kon doelmoment niet bepalen.")

    # Bescherm ook directe/automatische aanroepen: boeken kan pas
    # vanaf 00:00 op de dag die zeven dagen voor de les ligt.
    if not inschrijving_open(doel.date()):
        return False

    output = io.StringIO()
    resultaat = False

    try:
        with run_lock:
            with redirect_stdout(output):
                print("=" * 50)
                print(f"Inschrijven: {section}")
                print(f"Les   : {les}")
                print(f"Datum : {doel.date()}")
                print(f"Tijd  : {tijd.strftime('%H:%M')}")
                print()

                session = sportbit2.create_session()
                sportbit2.login(session)
                event = zoek_event(session=session, datum=doel.date(), les=les, tijd=tijd)

                if event is None:
                    raise RuntimeError(
                        f"Geen '{les}' gevonden om {tijd.strftime('%H:%M')} op {doel.date()}. "
                        "Mogelijk is de les gewijzigd, geannuleerd of vervangen (bijvoorbeeld feestdag/kerstWOD)."
                    )

                print("Event gevonden:")
                print(f"  ID         : {event.get('id')}")
                print(f"  Titel      : {event.get('titel')}")
                print(f"  Start      : {event.get('start')}")
                print(f"  Deelnemers : {event.get('aantalDeelnemers')}")
                print(f"  Maximum    : {event.get('maxDeelnemers')}")

                if event.get("aangemeld"):
                    print("\nJe bent al aangemeld.")
                    resultaat = True
                elif event.get("opWachtlijst"):
                    print("\nJe staat al op de wachtlijst.")
                    resultaat = True
                else:
                    resultaat = sportbit2.inschrijven(session, event)

                if not resultaat:
                    raise RuntimeError("SportBit heeft de inschrijving niet bevestigd.")

                try:
                    nieuw_event = zoek_event(session=session, datum=doel.date(), les=les, tijd=tijd)
                    if nieuw_event:
                        if nieuw_event.get("aangemeld"):
                            statuses[section] = maak_status("ingeschreven", "INGESCHREVEN", nieuw_event)
                        elif nieuw_event.get("opWachtlijst"):
                            statuses[section] = maak_status("wachtlijst", "WACHTLIJST", nieuw_event)
                        else:
                            statuses[section] = maak_status("niet-ingeschreven", "NIET INGESCHREVEN", nieuw_event)
                except Exception:
                    pass

    except Exception as error:
        print(f"\nFout: {error}")
        last_output = output.getvalue()
        try:
            notify.notify_inschrijving_mislukt(
                section=section,
                les=les,
                datum=doel.date(),
                tijd=tijd,
                reden=str(error),
                log=last_output,
            )
        except Exception as notify_error:
            print(f"\nNotificatie mislukt: {notify_error}")
        raise

    last_output = output.getvalue()
    return resultaat


def get_status(section):
    status = statuses.get(section)
    if status:
        return status
    return {
        "code": "onbekend",
        "css": "onbekend",
        "text": "NIET GECONTROLEERD",
        "event": None,
        "checked_at": None,
    }


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

            parse_tijd(
                tijd
            )

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


            return render_page(
                "edit.html",

                nieuw=True,

                item={
                    "dag": dag,
                    "tijd": tijd,
                    "les": les,
                },

                dagen=DAGEN,
            )


        config = configparser.ConfigParser()


        if CONFIG_FILE.exists():

            config.read(
                CONFIG_FILE,
                encoding="utf-8",
            )


        nummer = volgende_nummer(
            config
        )


        section = (
            f"inschrijving_{nummer}"
        )


        config[section] = {
            "dag": dag,
            "tijd": tijd,
            "les": les,
        }


        schrijf_config(
            config
        )


        flash(
            "Inschrijving toegevoegd.",
            "success",
        )


        return redirect(
            url_for("index")
        )


    return render_page(
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

    config = configparser.ConfigParser()


    config.read(
        CONFIG_FILE,
        encoding="utf-8",
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

            parse_tijd(
                tijd
            )

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


            return render_page(
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


        config[section]["dag"] = dag

        config[section]["tijd"] = tijd

        config[section]["les"] = les


        schrijf_config(
            config
        )


        # Oude status is niet meer betrouwbaar
        # omdat de configuratie is gewijzigd.

        statuses.pop(
            section,
            None,
        )

        next_lessons_cache.pop(
            section,
            None,
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


    return render_page(
        "edit.html",

        nieuw=False,

        item=item,

        section=section,

        dagen=DAGEN,
    )


# ============================================================
# VERWIJDEREN
# ============================================================

@app.post(
    "/inschrijving/<section>/verwijderen"
)
def delete_inschrijving(section):

    config = configparser.ConfigParser()


    config.read(
        CONFIG_FILE,
        encoding="utf-8",
    )


    if section not in config:

        flash(
            "Inschrijving bestaat niet.",
            "error",
        )


    else:

        config.remove_section(
            section
        )


        schrijf_config(
            config
        )


        statuses.pop(
            section,
            None,
        )

        next_lessons_cache.pop(
            section,
            None,
        )


        flash(
            "Inschrijving verwijderd.",
            "success",
        )


    return redirect(
        url_for("index")
    )


# ============================================================
# DOCUMENTATIE
# ============================================================

@app.route("/documentatie")
def documentatie():

    return render_page(
        "documentation.html"
    )


# ============================================================
# LOG
# ============================================================

@app.route("/log")
def log():

    return render_page(
        "log.html",

        output=(
            last_output
            or
            "Nog geen SportBit-actie uitgevoerd."
        ),
    )


@app.post("/testmail")
def testmail():

    try:
        notify.send_test_mail()
        flash(
            "Testmail is verstuurd.",
            "success",
        )
    except Exception as error:
        flash(
            f"Testmail mislukt: {error}",
            "error",
        )

    return redirect(url_for("index"))


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 55)
    print("Go Personal · SportBit webapp")
    print("=" * 55)
    print()
    print(
        "Luistert op: 0.0.0.0:5000"
    )
    print()
    print(
        "Gebruik Gunicorn voor productie."
    )
    print()


    start_dagelijkse_controle()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
