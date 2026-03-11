import logging
import os
import sys

from etl.extract import fetch_chapters
from etl.load import load_chapters
from etl.transform import filter_and_map


def _configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logging.getLogger(__name__).error("Required environment variable '%s' is not set.", name)
        sys.exit(1)
    return value


def run() -> None:
    _configure_logging()
    logger = logging.getLogger(__name__)

    api_url = _require_env("DU_API_URL")
    database_url = _require_env("DATABASE_URL")
    target_state = os.getenv("TARGET_STATE", "CA")

    logger.info("Pipeline starting. target_state=%s", target_state)

    try:
        raw_features = fetch_chapters(api_url)
        chapters = filter_and_map(raw_features, target_state=target_state)
        loaded = load_chapters(chapters, dsn=database_url)
        logger.info("Pipeline complete. Rows upserted: %d", loaded)
    except Exception:
        logger.exception("Pipeline failed with an unhandled exception.")
        sys.exit(1)


if __name__ == "__main__":
    run()
