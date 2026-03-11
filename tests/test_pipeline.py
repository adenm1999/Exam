import sys
from unittest.mock import MagicMock, patch

import pytest

from etl.pipeline import _configure_logging, _require_env, run


class TestConfigureLogging:
    def test_defaults_to_info(self):
        with patch("etl.pipeline.logging.basicConfig") as mock_config:
            with patch.dict("os.environ", {}, clear=False):
                import os
                os.environ.pop("LOG_LEVEL", None)
                _configure_logging()
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs["level"] == "INFO"

    def test_respects_log_level_env(self):
        with patch("etl.pipeline.logging.basicConfig") as mock_config:
            with patch.dict("os.environ", {"LOG_LEVEL": "debug"}):
                _configure_logging()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs["level"] == "DEBUG"


class TestRequireEnv:
    def test_returns_value_when_set(self):
        with patch.dict("os.environ", {"MY_VAR": "hello"}):
            assert _require_env("MY_VAR") == "hello"

    def test_exits_when_missing(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("MY_VAR", None)
            with pytest.raises(SystemExit):
                _require_env("MY_VAR")


class TestRun:
    def _make_patches(self, features=None, chapters=None, loaded=5):
        if features is None:
            features = [{"type": "Feature"}]
        if chapters is None:
            chapters = [{"chapter_id": "1"}]
        return {
            "fetch": patch("etl.pipeline.fetch_chapters", return_value=features),
            "filter": patch("etl.pipeline.filter_and_map", return_value=chapters),
            "load": patch("etl.pipeline.load_chapters", return_value=loaded),
            "config": patch("etl.pipeline._configure_logging"),
        }

    def test_happy_path(self):
        env = {"DU_API_URL": "http://fake", "DATABASE_URL": "postgresql://fake"}
        patches = self._make_patches()
        with patch.dict("os.environ", env):
            with patches["config"], patches["fetch"] as mock_fetch, \
                 patches["filter"] as mock_filter, patches["load"] as mock_load:
                run()
        mock_fetch.assert_called_once_with("http://fake")
        mock_filter.assert_called_once()
        mock_load.assert_called_once()

    def test_uses_default_target_state(self):
        env = {"DU_API_URL": "http://fake", "DATABASE_URL": "postgresql://fake"}
        patches = self._make_patches()
        with patch.dict("os.environ", env):
            with patches["config"], patches["fetch"], \
                 patches["filter"] as mock_filter, patches["load"]:
                run()
        _, kwargs = mock_filter.call_args
        assert kwargs.get("target_state") == "CA"

    def test_uses_custom_target_state(self):
        env = {"DU_API_URL": "http://fake", "DATABASE_URL": "postgresql://fake", "TARGET_STATE": "TX"}
        patches = self._make_patches()
        with patch.dict("os.environ", env):
            with patches["config"], patches["fetch"], \
                 patches["filter"] as mock_filter, patches["load"]:
                run()
        _, kwargs = mock_filter.call_args
        assert kwargs.get("target_state") == "TX"

    def test_exits_on_exception(self):
        env = {"DU_API_URL": "http://fake", "DATABASE_URL": "postgresql://fake"}
        with patch.dict("os.environ", env):
            with patch("etl.pipeline._configure_logging"):
                with patch("etl.pipeline.fetch_chapters", side_effect=RuntimeError("boom")):
                    with pytest.raises(SystemExit):
                        run()
