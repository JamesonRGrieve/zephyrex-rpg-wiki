# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import re
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import ROUTINE_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Routine import clock, motivations, routine  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(ROUTINE_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["routines"], ids=lambda case: case["name"])
def test_reads_a_routine(case: dict[str, Any]) -> None:
    assert routine(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid_routines"], ids=lambda case: case["name"])
def test_refuses_a_routine(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=re.escape(case["message"])):
        routine(case["value"])


@pytest.mark.parametrize("case", CASES["motivations"], ids=lambda case: case["name"])
def test_reads_motivations(case: dict[str, Any]) -> None:
    assert motivations(case["value"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid_motivations"], ids=lambda case: case["name"])
def test_refuses_motivations(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=re.escape(case["message"])):
        motivations(case["value"])


@pytest.mark.parametrize("case", CASES["clocks"], ids=lambda case: case["name"])
def test_reads_a_clock(case: dict[str, Any]) -> None:
    assert clock(case["minutes"]) == case["clock"]
