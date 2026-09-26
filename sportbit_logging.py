"""Centrale logging voor de SportBit-applicatie."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "sportbit.log"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


_logger = logging.getLogger("sportbit")
_logger.setLevel(logging.INFO)
_logger.propagate = False


if not _logger.handlers:

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )

    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s"
        )
    )

    _logger.addHandler(
        file_handler
    )


def schrijf_log(
    bericht,
    niveau="info",
    onderwerp="app",
):
    """Schrijf een uniform logbericht."""

    onderwerp = (
        str(onderwerp)
        .strip()
        .lower()
        or "app"
    )

    bericht = str(
        bericht
    ).strip()

    # Voorkom dubbele onderwerpen wanneer een
    # oud logbericht nog een [TAG] bevat.
    if (
        bericht.startswith("[")
        and "]" in bericht
    ):
        sluiting = bericht.find("]")
        bericht = (
            bericht[sluiting + 1:]
            .strip()
        )

    logregel = (
        f"[{onderwerp}] "
        f"{bericht}"
    )

    logfunctie = getattr(
        _logger,
        niveau,
        _logger.info,
    )

    logfunctie(logregel)
