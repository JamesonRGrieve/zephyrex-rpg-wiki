"""Test configuration for zephyrex-rpg-wiki.

Sets up the extensions path so test imports like
``from zephyrex.extensions.rpg_state.BLL_RPGState import ...``
resolve to the local ``./extensions/`` directory.
"""

import os
from typing import Any
import tempfile
import sys
from pathlib import Path

# Add the extensions directory to sys.path so Python can find
# the consumer extensions under the zephyrex.extensions namespace.
_project_root = Path(__file__).resolve().parent
_extensions_dir = _project_root / "extensions"

# Make extensions importable as zephyrex.extensions.* by extending
# the zephyrex.extensions namespace package path.
os.environ.setdefault("EXTENSIONS_PATH", str(_extensions_dir))
os.environ.setdefault("DATABASE_TYPE", "sqlite")
# Assigned, never setdefault: the xdist controller loads this file first, so with setdefault every
# worker would inherit its name and they would all share and seed one database (SOP Python §11).
os.environ["DATABASE_NAME"] = f"test_zephyrex_rpg_wiki_{os.environ.get('PYTEST_XDIST_WORKER', 'main')}"
os.environ.setdefault("DATABASE_PATH", tempfile.mkdtemp(prefix="rpg-wiki-db-"))
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-32-bytes-or-more-aaaaaa")
os.environ.setdefault("SEED_DATA", "true")

import zephyrex.extensions  # noqa: E402

if str(_extensions_dir) not in zephyrex.extensions.__path__:
    zephyrex.extensions.__path__ = [str(_extensions_dir)] + list(zephyrex.extensions.__path__)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limit_counts_between_tests() -> None:
    """Each test starts with no sign-ins counted against the rate limits, as in the framework's own
    conftest: every test signs in from the same test-client address, so earlier tests' sign-ins
    would refuse later ones (standards page Testing)."""
    from zephyrex.lib.InboundSecurity import reset_rate_limit_counts

    reset_rate_limit_counts()


@pytest.fixture
def memory_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """The cloud extension's storage, kept in memory (its own tests cover its providers): for tests
    that upload pictures (rpg_core's pictures, both importers)."""
    from zephyrex.extensions.cloud.EXT_Cloud import EXT_Cloud

    files: dict[str, bytes] = {}

    async def upload_file(cls: Any, path: str, content: bytes, provider: Any = None) -> dict[str, Any]:
        files[path] = content
        return {"provider": "memory", "path": path}

    async def download_file(cls: Any, provider: str, path: str) -> bytes:
        return files[path]

    monkeypatch.setattr(EXT_Cloud, "upload_file", classmethod(upload_file))
    monkeypatch.setattr(EXT_Cloud, "download_file", classmethod(download_file))
    return files
