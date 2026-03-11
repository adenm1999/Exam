import json
from unittest.mock import MagicMock, patch
import pytest

from etl.load import load_chapters, _serialise_coordinates


SAMPLE_CHAPTERS = [
    {
        "chapter_id": "1",
        "chapter_name": "UC Davis Chapter",
        "city": "Davis",
        "state": "CA",
        "coordinates": {"latitude": 38.54, "longitude": -121.74},
    },
    {
        "chapter_id": "2",
        "chapter_name": "UC Berkeley Chapter",
        "city": "Berkeley",
        "state": "CA",
        "coordinates": {"latitude": 37.87, "longitude": -122.26},
    },
]


class TestSerialiseCoordinates:
    def test_coordinates_become_json_string(self):
        chapter = {"coordinates": {"latitude": 37.87, "longitude": -122.26}}
        result = _serialise_coordinates(chapter)
        parsed = json.loads(result["coordinates"])
        assert parsed["latitude"] == 37.87

    def test_none_coordinates_remain_none(self):
        chapter = {"coordinates": None}
        result = _serialise_coordinates(chapter)
        assert result["coordinates"] is None

    def test_original_dict_not_mutated(self):
        chapter = {"coordinates": {"latitude": 1.0, "longitude": 2.0}}
        _serialise_coordinates(chapter)
        assert isinstance(chapter["coordinates"], dict)


class TestLoadChapters:
    def _mock_connection(self):
        """Build a psycopg2 connection mock that supports context managers."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return mock_conn, mock_cursor

    @patch("etl.load.psycopg2.extras.execute_batch")
    @patch("etl.load.psycopg2.connect")
    def test_calls_execute_batch(self, mock_connect, mock_execute_batch):
        mock_conn, _ = self._mock_connection()
        mock_connect.return_value = mock_conn

        result = load_chapters(SAMPLE_CHAPTERS, dsn="postgresql://fake")

        assert mock_execute_batch.called
        assert result == len(SAMPLE_CHAPTERS)

    @patch("etl.load.psycopg2.connect")
    def test_returns_zero_for_empty_input(self, mock_connect):
        result = load_chapters([], dsn="postgresql://fake")
        assert result == 0
        mock_connect.assert_not_called()

    @patch("etl.load.psycopg2.extras.execute_batch")
    @patch("etl.load.psycopg2.connect")
    def test_commits_after_batch(self, mock_connect, mock_execute_batch):
        mock_conn, _ = self._mock_connection()
        mock_connect.return_value = mock_conn

        load_chapters(SAMPLE_CHAPTERS, dsn="postgresql://fake")

        mock_conn.commit.assert_called_once()

    @patch("etl.load.psycopg2.connect")
    def test_propagates_connection_error(self, mock_connect):
        import psycopg2

        mock_connect.side_effect = psycopg2.OperationalError("Connection refused")
        with pytest.raises(psycopg2.OperationalError):
            load_chapters(SAMPLE_CHAPTERS, dsn="postgresql://fake")
