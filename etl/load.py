import json
import logging
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

UPSERT_SQL = """
    INSERT INTO du_chapters (chapter_id, chapter_name, city, state, coordinates)
    VALUES (%(chapter_id)s, %(chapter_name)s, %(city)s, %(state)s, %(coordinates)s)
    ON CONFLICT (chapter_id) DO UPDATE SET
        chapter_name = EXCLUDED.chapter_name,
        city         = EXCLUDED.city,
        state        = EXCLUDED.state,
        coordinates  = EXCLUDED.coordinates;
"""


def _serialise_coordinates(chapter: dict[str, Any]) -> dict[str, Any]:
    """
    psycopg2 needs JSONB values passed as JSON strings (or via Json adapter).
    Returns a copy of the chapter dict with coordinates serialised.
    """
    record = dict(chapter)
    coords = record.get("coordinates")
    record["coordinates"] = json.dumps(coords) if coords is not None else None
    return record


def load_chapters(chapters: list[dict[str, Any]], dsn: str) -> int:
    if not chapters:
        logger.info("No chapters to load.")
        return 0

    records = [_serialise_coordinates(c) for c in chapters]

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, UPSERT_SQL, records, page_size=100)
        conn.commit()

    logger.info("Loaded %d chapters into du_chapters.", len(records))
    return len(records)
