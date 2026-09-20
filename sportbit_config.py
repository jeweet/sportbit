"""Lezen en schrijven van sportbit.conf."""

import configparser
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "sportbit.conf"


def lees_config():
    """Lees alle inschrijvingen uit sportbit.conf."""

    config = configparser.ConfigParser()

    if not CONFIG_FILE.exists():
        return []

    config.read(
        CONFIG_FILE,
        encoding="utf-8",
    )

    resultaten = []

    for section in config.sections():

        if not section.startswith("inschrijving_"):
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


def lees_config_parser():
    """Geef een ConfigParser terug met de huidige configuratie."""

    config = configparser.ConfigParser()

    if CONFIG_FILE.exists():
        config.read(
            CONFIG_FILE,
            encoding="utf-8",
        )

    return config


def schrijf_config(config):
    """Schrijf de configuratie atomair naar sportbit.conf."""

    tijdelijke_file = CONFIG_FILE.with_suffix(".tmp")

    with tijdelijke_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        config.write(file)

    tijdelijke_file.replace(CONFIG_FILE)


def volgende_nummer(config):
    """Bepaal het eerstvolgende nummer voor een inschrijving."""

    nummers = []

    for section in config.sections():

        if not section.startswith("inschrijving_"):
            continue

        try:
            nummer = int(
                section.split("_", 1)[1]
            )

            nummers.append(nummer)

        except (ValueError, IndexError):
            pass

    return max(nummers) + 1 if nummers else 1
