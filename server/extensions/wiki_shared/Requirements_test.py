# SPDX-License-Identifier: AGPL-3.0-or-later
"""A hook's requirement and state, held to the cases the lite edition is held to
(contract/requirement-cases.json)."""

import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Requirements import (  # type: ignore[import-not-found]
    RequirementError,
    checked,
    hook_state,
    leaves,
)

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "requirement-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"], ids=[case["name"] for case in CASES["cases"]])
def test_state(case: dict[str, Any]) -> None:
    if case["requires"] is not None:
        checked(case["requires"])
    assert hook_state(case["requires"], case["resolved"], case["self_resolved"]) == case["state"]


@pytest.mark.parametrize("case", CASES["leaves"])
def test_leaves(case: dict[str, Any]) -> None:
    assert leaves(case["requires"]) == case["hooks"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=[case["name"] for case in CASES["invalid"]])
def test_invalid(case: dict[str, Any]) -> None:
    with pytest.raises(RequirementError):
        checked(case["requires"])
