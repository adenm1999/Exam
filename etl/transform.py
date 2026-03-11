import logging
from typing import Any

logger = logging.getLogger(__name__)

FIELD_MAP = {
    "chapter_id": "ChapterID",
    "chapter_name": "University_Chapter",
    "city": "City",
    "state": "State",
}

_STATE_FIELD = FIELD_MAP["state"]
_ID_FIELD = FIELD_MAP["chapter_id"]
_NAME_FIELD = FIELD_MAP["chapter_name"]
_CITY_FIELD = FIELD_MAP["city"]


def _extract_coordinates(feature: dict[str, Any]) -> dict[str, float] | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None

    geo_type = geometry.get("type", "")
    coords = geometry.get("coordinates")

    if geo_type == "Point" and coords and len(coords) >= 2:
        return {"longitude": coords[0], "latitude": coords[1]}

    return None


def filter_and_map(
    features: list[dict[str, Any]],
    target_state: str = "CA",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    skipped = 0

    for feature in features:
        props = feature.get("properties", {})

        state_value = props.get(_STATE_FIELD, "")
        if state_value != target_state:
            continue

        chapter_id = props.get(_ID_FIELD)
        chapter_name = props.get(_NAME_FIELD)
        city = props.get(_CITY_FIELD)

        if chapter_id is None or chapter_name is None:
            logger.warning("Skipping record missing mandatory fields: %s", props)
            skipped += 1
            continue

        results.append(
            {
                "chapter_id": str(chapter_id),
                "chapter_name": str(chapter_name),
                "city": str(city) if city else None,
                "state": state_value,
                "coordinates": _extract_coordinates(feature),
            }
        )

    logger.info(
        "Transform complete. Kept=%d Skipped=%d for state=%s",
        len(results),
        skipped,
        target_state,
    )
    return results
