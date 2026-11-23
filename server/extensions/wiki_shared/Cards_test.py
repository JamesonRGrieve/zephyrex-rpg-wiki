# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Cards import card_avatar, card_data, card_greetings, card_markdown, card_tags, card_voice  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]

CASES: list[dict[str, Any]] = json.loads((REPOSITORY_ROOT / "contract" / "card-cases.json").read_text(encoding="utf-8"))["cards"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_a_card_as_a_person(case: dict[str, Any]) -> None:
    data = card_data(case["card"])
    assert card_voice(case["card"]["name"], data) == case["voice"]
    assert card_markdown(data) == case["markdown"]
    assert card_greetings(data) == case["greetings"]
    assert card_tags(data) == case["tags"]


def test_a_data_url_avatar_is_uploaded_first() -> None:
    with pytest.raises(ValueError, match="Upload the avatar first"):
        card_avatar({"avatar": "data:image/png;base64,AAAA"})
    assert card_avatar({"avatar": "https://example.invalid/v.png"}) == "https://example.invalid/v.png"
    assert card_avatar({}) is None
