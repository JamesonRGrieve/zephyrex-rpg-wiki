# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Eras import era_visible  # type: ignore[import-not-found]

CASES: list[dict[str, Any]] = json.loads((REPOSITORY_ROOT / "contract" / "era-cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_era_visible(case: dict[str, Any]) -> None:
    assert era_visible(case["record"], case["campaign"]) is case["visible"]
