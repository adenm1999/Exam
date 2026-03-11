import pytest

from etl.transform import filter_and_map, _extract_coordinates


def _make_feature(
    object_id=1,
    name="Test Chapter",
    city="Sacramento",
    state="CA",
    coordinates=[-121.49, 38.58],
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "ChapterID": object_id,
            "University_Chapter": name,
            "City": city,
            "State": state,
        },
        "geometry": {"type": "Point", "coordinates": coordinates},
    }


class TestFilterAndMap:
    def test_filters_to_target_state(self):
        features = [
            _make_feature(object_id=1, state="CA"),
            _make_feature(object_id=2, state="OR"),
            _make_feature(object_id=3, state="WA"),
        ]
        result = filter_and_map(features, target_state="CA")
        assert len(result) == 1
        assert result[0]["state"] == "CA"

    def test_maps_fields_correctly(self):
        feature = _make_feature(object_id=42, name="Golden Gate Chapter", city="San Francisco", state="CA")
        result = filter_and_map([feature], target_state="CA")

        assert len(result) == 1
        row = result[0]
        assert row["chapter_id"] == "42"
        assert row["chapter_name"] == "Golden Gate Chapter"
        assert row["city"] == "San Francisco"
        assert row["state"] == "CA"

    def test_coordinates_extracted(self):
        feature = _make_feature(coordinates=[-122.41, 37.77])
        result = filter_and_map([feature], target_state="CA")

        coords = result[0]["coordinates"]
        assert coords == {"longitude": -122.41, "latitude": 37.77}

    def test_skips_records_missing_chapter_id(self):
        feature = _make_feature()
        feature["properties"]["ChapterID"] = None
        result = filter_and_map([feature], target_state="CA")
        assert len(result) == 0

    def test_skips_records_missing_chapter_name(self):
        feature = _make_feature()
        feature["properties"]["University_Chapter"] = None
        result = filter_and_map([feature], target_state="CA")
        assert len(result) == 0

    def test_returns_empty_list_when_no_matches(self):
        features = [_make_feature(state="TX"), _make_feature(state="FL")]
        result = filter_and_map(features, target_state="CA")
        assert result == []

    def test_handles_empty_input(self):
        assert filter_and_map([], target_state="CA") == []

    def test_handles_missing_geometry(self):
        feature = _make_feature()
        feature["geometry"] = None
        result = filter_and_map([feature], target_state="CA")
        assert result[0]["coordinates"] is None

    def test_chapter_id_coerced_to_string(self):
        feature = _make_feature(object_id=99)
        result = filter_and_map([feature], target_state="CA")
        assert isinstance(result[0]["chapter_id"], str)


class TestExtractCoordinates:
    def test_point_geometry(self):
        feature = {"geometry": {"type": "Point", "coordinates": [-121.5, 38.5]}}
        result = _extract_coordinates(feature)
        assert result == {"longitude": -121.5, "latitude": 38.5}

    def test_missing_geometry_returns_none(self):
        assert _extract_coordinates({"geometry": None}) is None

    def test_unsupported_geometry_returns_none(self):
        feature = {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}}
        assert _extract_coordinates(feature) is None
