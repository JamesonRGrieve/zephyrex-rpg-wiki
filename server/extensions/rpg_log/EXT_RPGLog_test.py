"""Extension-level tests for rpg_log."""

import os

os.environ.setdefault("JWT_SECRET", "x" * 32)
os.environ.setdefault("PYTEST_CURRENT_TEST", "rpg_log_ext_test")

from zephyrex.extensions.rpg_log.BLL_RPGLog import ALL_MODELS
from zephyrex.extensions.rpg_log.EXT_RPGLog import RPGLogExtension


class TestExtensionMetadata:
    def test_name_and_description(self):
        assert RPGLogExtension.name == "rpg_log"
        assert "log" in RPGLogExtension.description.lower()

    def test_depends_on_rpg_state(self):
        declared = [(d.name, d.optional) for d in RPGLogExtension.dependencies.ext]
        assert declared == [("rpg_state", False)]

    def test_discovered_models_are_the_roster(self):
        assert RPGLogExtension.models == set(ALL_MODELS)
        assert len(ALL_MODELS) == 7  # bump when adding log tables.
