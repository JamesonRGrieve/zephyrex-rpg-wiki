# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import generic_unnamed, unnamed_as_text  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads((REPOSITORY_ROOT / "contract" / "unnamed-as-cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["stored"], ids=lambda case: case["name"])
def test_unnamed_as(case: dict[str, Any]) -> None:
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            unnamed_as_text(case["value"])
    else:
        assert unnamed_as_text(case["value"]) == case["stored"]


@pytest.mark.parametrize("case", CASES["generic"], ids=lambda case: case["name"])
def test_generic_unnamed(case: dict[str, Any]) -> None:
    assert generic_unnamed(case["species"], case["role"], case["gender"]) == case["generic"]
