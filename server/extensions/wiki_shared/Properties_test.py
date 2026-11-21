# SPDX-License-Identifier: AGPL-3.0-or-later
"""A property kit's keys against contract/property-kit-cases.json, which the lite edition's
properties.test.ts reads too."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import KIT_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Properties import KitError, checked_kit  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(KIT_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_a_kit_is_normalised(case: dict[str, Any]) -> None:
    assert checked_kit(case["properties"]) == case["checked"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_a_kit_the_contract_refuses(case: dict[str, Any]) -> None:
    with pytest.raises(KitError) as refused:
        checked_kit(case["properties"])
    assert str(refused.value) == case["message"]


def test_a_kit_has_at_most_the_records_keys() -> None:
    with pytest.raises(KitError, match="at most 200"):
        checked_kit([{"key": f"k{index}"} for index in range(201)])
