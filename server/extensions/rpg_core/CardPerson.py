# SPDX-License-Identifier: AGPL-3.0-or-later
"""A SillyTavern character card as a wiki person, for chatting outside any scenario (operator: "a
character card imports as a wiki person with its voice … a reply speaks as that person"; Parity,
2026-11-23: rpg-ai's chat cast is wiki persons).

import_card_person: the requester's own "Characters" campaign (found, else made; one per requester)
gets an NPC (the AI plays them; not GM-only) from the card: its description and scenario as the
entry, its voice parts (wiki_shared/Cards.py, as st_import reads them), its alternate greetings as a
private property, its tags, and its picture (an https link, or an uploaded asset's id; a data URL is
refused, as fill_person refuses one). Not found by name: rpg-ai keeps the card's link, so two cards
of one name stay two people."""

import re
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel as PlainModel
from pydantic import ConfigDict, Field

ASSET_ID = re.compile(r"^[0-9a-fA-F-]{32,36}$")
GREETINGS_PROPERTY = "Alternate greetings"


class CardAsk(PlainModel):
    model_config = ConfigDict(extra="allow")
    name: str = Field(..., min_length=1, max_length=200, description="The character's name")


class CardEnvelope(PlainModel):
    card: CardAsk


class CardPersonImported(PlainModel):
    person_id: str
    campaign_id: str


def import_card_person(model_registry: Any, requester_id: str, card: dict[str, Any]) -> CardPersonImported:
    from zephyrex.extensions.genealogy.BLL_Genealogy import PersonManager
    from zephyrex.extensions.rpg_core.BLL_RPGCore import CampaignManager, CampaignModel, MetadataManagerOf, _every, _manager, _serves  # type: ignore[import-not-found]
    from zephyrex.extensions.wiki_shared.Cards import CHARACTERS, card_avatar, card_data, card_greetings, card_markdown, card_tags, card_voice  # type: ignore[import-not-found]
    from zephyrex.extensions.wiki_shared.Markdown import markdown_entry  # type: ignore[import-not-found]
    from zephyrex.extensions.world_taxonomy.BLL_WorldTaxonomy import EntityTaxonManager, TaxonManager  # type: ignore[import-not-found]
    from zephyrex.logic.AbstractLogicManager.models import FieldComparison

    name = str(card.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="A card names its character")
    try:
        avatar = card_avatar(card)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if avatar and not avatar.startswith("https://"):
        if not ASSET_ID.match(avatar):
            raise HTTPException(status_code=422, detail="An avatar is an https link or an uploaded asset's id")
        if not _serves(model_registry, "attachments"):
            raise HTTPException(status_code=422, detail="This back end keeps no uploaded pictures: give an https link")
    data = card_data(card)
    campaigns = _manager(model_registry, requester_id, CampaignManager)
    mine = [row for row in _every(campaigns, [FieldComparison(CampaignModel, "name", "eq", CHARACTERS)]) if not getattr(row, "is_scenario", None) and str(getattr(row, "created_by_user_id", "") or "") == str(requester_id)]
    campaign = mine[0] if mine else campaigns.create(name=CHARACTERS, description="Characters to chat with outside any scenario.")
    fields: dict[str, Any] = {"name": name, "kind": "npc", "campaign_id": str(campaign.id), "voice": card_voice(name, data)}
    markdown = card_markdown(data)
    if markdown:
        fields["entry"] = markdown_entry(markdown)
    if avatar and avatar.startswith("https://"):
        fields["picture_url"] = avatar
    person = _manager(model_registry, requester_id, PersonManager).create(**fields)
    person_id = str(person.id)
    if avatar and not avatar.startswith("https://"):
        from zephyrex.extensions.attachments.BLL_Attachments import AttachmentManager  # type: ignore[import-not-found]

        _manager(model_registry, requester_id, AttachmentManager).create(asset_id=avatar, target_entity_type="person", target_entity_id=person_id, role="primary_image")
    greetings = card_greetings(data)
    rows = MetadataManagerOf(model_registry)
    if greetings and rows is not None:
        rows.create(target_entity_type="person", target_entity_id=person_id, key=GREETINGS_PROPERTY, value="\n\n".join(greetings), value_type="text", is_private=True)
    tags = card_tags(data)
    if tags:
        taxa = _manager(model_registry, requester_id, TaxonManager)
        held = {str(row.name): str(row.id) for row in taxa.list(campaign_id=str(campaign.id), kind="tag") or []}
        links = _manager(model_registry, requester_id, EntityTaxonManager)
        for tag in tags:
            taxon = held.get(tag) or str(taxa.create(name=tag, kind="tag", campaign_id=str(campaign.id)).id)
            held[tag] = taxon
            links.create(taxon_id=taxon, target_entity_type="person", target_entity_id=person_id)
    return CardPersonImported(person_id=person_id, campaign_id=str(campaign.id))
