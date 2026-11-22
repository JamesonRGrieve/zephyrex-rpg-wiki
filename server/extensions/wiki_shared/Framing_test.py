# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Framing import framing_parts  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "framing-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["splits"], ids=lambda case: case["name"])
def test_splits_a_framing(case: dict[str, Any]) -> None:
    assert framing_parts(case["entry"]) == (case["public"], case["gm"])
    if case["entry"] is not None:
        assert framing_parts(json.dumps(case["entry"])) == (case["public"], case["gm"])
