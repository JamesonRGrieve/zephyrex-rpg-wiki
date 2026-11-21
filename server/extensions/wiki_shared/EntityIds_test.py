# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import ENTITY_IDS_CASES_PATH  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.EntityIds import EntityIdsError, entity_ids  # type: ignore[import-not-found]

CASES: dict[str, Any] = json.loads(ENTITY_IDS_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_reads_the_ids(case: dict[str, Any]) -> None:
    assert entity_ids(case["query"].split(",")) == case["ids"]


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_refuses(case: dict[str, Any]) -> None:
    with pytest.raises(EntityIdsError, match=case["error"]):
        entity_ids(case["query"].split(","))
