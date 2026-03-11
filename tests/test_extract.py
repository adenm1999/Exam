import pytest
import requests

from unittest.mock import MagicMock, patch

from etl.extract import fetch_chapters


MOCK_FEATURE = {
    "type": "Feature",
    "properties": {
        "OBJECTID": 1,
        "Chapter_Name": "UC Davis Chapter",
        "City": "Davis",
        "State": "CA",
    },
    "geometry": {"type": "Point", "coordinates": [-121.74, 38.54]},
}


def _make_response(features: list, status_code: int = 200) -> MagicMock:
    """Helper: build a mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"type": "FeatureCollection", "features": features}
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
    return mock_resp


class TestFetchChapters:
    def test_returns_features_on_success(self):
        with patch("etl.extract.requests.get") as mock_get:
            mock_get.return_value = _make_response([MOCK_FEATURE])
            result = fetch_chapters("http://fake-url/query")

        assert len(result) == 1
        assert result[0]["properties"]["Chapter_Name"] == "UC Davis Chapter"

    def test_paginates_until_empty_page(self):
        """
        Simulate: first call returns PAGE_SIZE records, second returns 0.
        Should make exactly two requests.
        """
        from etl.extract import PAGE_SIZE

        full_page = [MOCK_FEATURE] * PAGE_SIZE
        with patch("etl.extract.requests.get") as mock_get:
            mock_get.side_effect = [
                _make_response(full_page),
                _make_response([]),          # signals end of data
            ]
            result = fetch_chapters("http://fake-url/query")

        assert mock_get.call_count == 2
        assert len(result) == PAGE_SIZE

    def test_raises_on_http_error(self):
        with patch("etl.extract.requests.get") as mock_get:
            mock_get.return_value = _make_response([], status_code=500)
            with pytest.raises(requests.HTTPError):
                fetch_chapters("http://fake-url/query")

    def test_raises_on_invalid_json(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch("etl.extract.requests.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="Could not parse"):
                fetch_chapters("http://fake-url/query")

    def test_passes_correct_query_params(self):
        with patch("etl.extract.requests.get") as mock_get:
            mock_get.return_value = _make_response([])
            fetch_chapters("http://fake-url/query")

        call_kwargs = mock_get.call_args
        params = call_kwargs[1]["params"]
        assert params["f"] == "geojson"
        assert params["outFields"] == "*"
        assert params["returnGeometry"] == "true"
