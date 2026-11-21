# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import PICTURE_URL_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Pictures import picture_url  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(PICTURE_URL_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_reads_a_link(case: dict[str, Any]) -> None:
    assert picture_url(case["value"]) == case["url"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_refuses(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=case["message"]):
        picture_url(case["value"])
