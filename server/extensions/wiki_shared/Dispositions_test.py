# SPDX-License-Identifier: AGPL-3.0-or-later
"""Whom a person regards how, held to the cases the lite edition is held to
(contract/disposition-cases.json)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Dispositions import band, checked_attitude, current  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "disposition-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]])
def test_current(case: dict[str, Any]) -> None:
    assert current(case["entries"], case["resolved"]) == case["current"]


@pytest.mark.parametrize("case", CASES["bands"], ids=[case["attitude"] for case in CASES["bands"]])
def test_band(case: dict[str, Any]) -> None:
    assert band(case["attitude"]) == case["band"]


def test_an_attitude_outside_the_scale_is_refused() -> None:
    with pytest.raises(ValueError):
        checked_attitude("smug")
