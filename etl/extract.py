import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)
PAGE_SIZE = 1000


def fetch_chapters(base_url: str, timeout: int = 30) -> list[dict[str, Any]]:
    all_features: list[dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "outFields": "ChapterID,University_Chapter,City,State",
            "returnGeometry": "true",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }

        logger.info("Fetching records offset=%d count=%d", offset, PAGE_SIZE)
        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError(
                f"Could not parse API response as JSON. Status={response.status_code}"
            ) from exc

        features: list[dict[str, Any]] = data.get("features", [])
        all_features.extend(features)

        logger.info("Retrieved %d features (running total: %d)", len(features), len(all_features))

        if len(features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    logger.info("Extraction complete. Total features fetched: %d", len(all_features))
    return all_features
