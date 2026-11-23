# SPDX-License-Identifier: AGPL-3.0-or-later
"""Era scoping (contract/era-cases.json; the client's lib/eras.ts computes the same): a setting's
canon record with eras reaches a campaign only when they share one; one with none reaches every
campaign; a campaign with no era sees all."""

from typing import Iterable

ERA = "era"  # the taxon kind


def era_names(values: Iterable[str]) -> set[str]:
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def era_visible(record_eras: Iterable[str], campaign_eras: Iterable[str]) -> bool:
    record, campaign = era_names(record_eras), era_names(campaign_eras)
    return not record or not campaign or bool(record & campaign)
