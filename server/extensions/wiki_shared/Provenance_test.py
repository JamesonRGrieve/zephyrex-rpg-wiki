# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import PROVENANCE_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Provenance import provenance  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(PROVENANCE_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_reads_a_provenance(case: dict[str, Any]) -> None:
    assert provenance(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_refuses(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=case["message"]):
        provenance(case["value"])
