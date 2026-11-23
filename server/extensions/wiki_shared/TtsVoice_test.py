# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Any

import pytest
from zephyrex.extensions.wiki_shared.Contract import REPOSITORY_ROOT  # type: ignore[import-not-found]
from zephyrex.extensions.wiki_shared.Names import tts_voice_text  # type: ignore[import-not-found]

CASES: list[dict[str, Any]] = json.loads((REPOSITORY_ROOT / "contract" / "tts-voice-cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_tts_voice(case: dict[str, Any]) -> None:
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            tts_voice_text(case["value"])
    else:
        assert tts_voice_text(case["value"]) == case["stored"]
