# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scenario repair and validation through the wiki's own API (vault_import's Api), as the owner:
works on any build that serves rpg_core, over HTTP or in process.

repair(api, dry_run=True, origins=..., seated=...) mends every scenario and its playthroughs:
1. a person with no kind becomes an NPC (a playthrough's seated person a PC);
2. a framing whose Opening Situation only points elsewhere gets one written from the scenario's
   description and its player briefing's first telling section, the pointer kept as "Sources:";
3. a Starting Location section (rules.start_place);
4. each scenario's origin: a category tag ("Imported" or "Stereotypical") and an "Origin" property
   ("transcript import" or "generated"). A campaign's source stays as it is: the provenance rule
   keeps source for official or adapted books (homebrew has none).

validate(api, campaign_id) names what makes one unplayable; vault_import runs it on every campaign
it touched."""

from dataclasses import dataclass, field
from typing import Any, Optional

from scenario_repair.rules import START, blocks_of, sections, unmended, unqualified_places, briefing_text, is_briefing, is_framing_name, is_pointer, mended_framing, opening_of, scenario_problems, start_place, written_opening
from vault_import.api import Api

ORIGINS = {"imported": ("Imported", "transcript import"), "stereotypical": ("Stereotypical", "generated")}
ORIGIN_PROPERTY = "Origin"
ORIGIN_TAXON_KIND = "category"
VAULT_PATH = "vault_path"


@dataclass
class Mended:
    campaign: str
    campaign_id: str
    scenario: bool
    kinds: dict[str, int] = field(default_factory=dict)
    framing_kind: Optional[str] = None
    opening: Optional[str] = None
    start: Optional[str] = None
    origin: Optional[str] = None
    unqualified: list[str] = field(default_factory=list)
    problems_before: list[str] = field(default_factory=list)
    problems_after: list[str] = field(default_factory=list)

    def line(self) -> str:
        parts = [f"{'scenario' if self.scenario else 'playthrough'} {self.campaign} ({self.campaign_id})"]
        if self.framing_kind:
            parts.append(f"framing {self.framing_kind!r} made kind campaign_framing")
        if self.kinds:
            parts.append("kinds " + ", ".join(f"{count} → {kind}" for kind, count in sorted(self.kinds.items())))
        if self.opening:
            parts.append(f"opening written ({len(self.opening)} characters): {self.opening[:200]!r}")
        if self.start:
            parts.append(f"starts at {self.start}")
        if self.origin:
            parts.append(f"origin {self.origin}")
        if self.unqualified:
            parts.append(f"{len(self.unqualified)} places reach no planet or region: " + "; ".join(self.unqualified[:5]) + ("…" if len(self.unqualified) > 5 else ""))
        if self.problems_before:
            parts.append("was: " + "; ".join(self.problems_before))
        parts.append("now: " + ("; ".join(self.problems_after) if self.problems_after else "playable"))
        return " | ".join(parts)


def _framing(api: Api, campaign_id: str) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    journals = [row for row in api.list("journal", campaign_id=campaign_id) if not row.get("is_template") and not row.get("deleted_at")]
    framings = sorted((row for row in journals if row.get("kind") == "campaign_framing"), key=lambda row: str(row.get("name") or ""))
    # None of that kind: a framing by its name (imported as lore before campaign_framing was a kind).
    framings = framings or sorted((row for row in journals if is_framing_name(str(row.get("name") or ""))), key=lambda row: str(row.get("name") or ""))
    briefings = sorted((row for row in journals if is_briefing(str(row.get("name") or ""))), key=lambda row: str(row.get("name") or ""))
    return (framings[0] if framings else None), (briefings[0] if briefings else None)


SHEETS = "rpg_traits"  # VTT's: a person's character sheet is its person_trait rows


def _sheetless(api: Api, persons: list[dict[str, Any]]) -> list[str]:
    """The PCs with no character sheet, where the back end serves sheets (VTT's rpg_traits)."""
    pcs = [row for row in persons if row.get("kind") == "pc"]
    if not pcs or SHEETS not in api.extensions():
        return []
    return [str(row.get("name") or row["id"]) for row in pcs if not api.list("person_trait", person_id=str(row["id"]))]


def validate(api: Api, campaign_id: str) -> list[str]:
    """What makes the campaign unplayable (empty when it's fine)."""
    persons = api.list("person", campaign_id=campaign_id)
    locations = api.list("location", campaign_id=campaign_id)
    framing, _briefing = _framing(api, campaign_id)
    problems = scenario_problems(persons, blocks_of(framing.get("entry")) if framing else None, locations, _sheetless(api, persons))
    if framing is not None and framing.get("kind") != "campaign_framing":
        # The narrator's framing (campaign_framing) reads that kind alone.
        problems.append(f"the framing {framing.get('name')!r} is kind {framing.get('kind')!r}, not campaign_framing")
    return problems


def _origin_of(api: Api, campaign: dict[str, Any], framing: Optional[dict[str, Any]], origins: dict[str, str]) -> Optional[str]:
    for key in (str(campaign["id"]), str(campaign.get("name") or "")):
        if key in origins:
            return origins[key]
    if framing is not None and any(row.get("key") == VAULT_PATH for row in api.properties("journal", str(framing["id"]))):
        return "imported"
    return None


def _tag(api: Api, campaign_id: str, origin: str, taxa: dict[str, str]) -> None:
    name, word = ORIGINS[origin]
    if name not in taxa:
        taxa[name] = str(api.create("taxon", name=name, kind=ORIGIN_TAXON_KIND)["id"])
    linked = {str(row.get("taxon_id")) for row in api.list("entity_taxon", target_entity_type="campaign", target_entity_id=campaign_id)}
    if taxa[name] not in linked:
        api.create("entity_taxon", taxon_id=taxa[name], target_entity_type="campaign", target_entity_id=campaign_id)
    held = [row for row in api.properties("campaign", campaign_id) if row.get("key") == ORIGIN_PROPERTY]
    if not held:
        api.add_property("campaign", campaign_id, ORIGIN_PROPERTY, word)
    elif held[0].get("value") != word:
        api.change_property(held[0], word)


def mend(
    api: Api,
    campaign: dict[str, Any],
    scenario: bool,
    dry_run: bool = True,
    origins: Optional[dict[str, str]] = None,
    seated: Optional[set[str]] = None,
    taxa: Optional[dict[str, str]] = None,
) -> Mended:
    """One campaign mended (or, dry, only reported): kinds, opening, start place, and a scenario's origin."""
    campaign_id = str(campaign["id"])
    mended = Mended(str(campaign.get("name") or ""), campaign_id, scenario)
    mended.problems_before = validate(api, campaign_id)
    persons = api.list("person", campaign_id=campaign_id)
    locations = api.list("location", campaign_id=campaign_id)
    mended.unqualified = unqualified_places(locations)
    for person in persons:
        if not person.get("kind"):
            kind = "pc" if str(person["id"]) in (seated or set()) else "npc"
            mended.kinds[kind] = mended.kinds.get(kind, 0) + 1
            if not dry_run:
                api.update("person", str(person["id"]), kind=kind)
    framing, briefing = _framing(api, campaign_id)
    if framing is not None and framing.get("kind") != "campaign_framing":
        mended.framing_kind = str(framing.get("name") or "")
        if not dry_run:
            api.update("journal", str(framing["id"]), kind="campaign_framing")
    if framing is not None:
        held = blocks_of(framing.get("entry"))
        # Mended from the framing as it was (an earlier repair's blocks taken off), so a repair whose
        # rules have improved writes its opening again; one that would write the same changes nothing.
        blocks = unmended(held)
        found = opening_of(blocks)
        opening = None
        if found is None or is_pointer(found[2], found[3]):
            opening = written_opening(str(campaign.get("description") or ""), briefing_text(blocks_of(briefing.get("entry"))) if briefing else "") or None
        current = opening if opening else (found[2] if found else str(campaign.get("description") or ""))
        place = start_place(current, locations, persons)
        mended_blocks = mended_framing(blocks, opening, place)
        mended.opening = opening
        if place is not None and not any(START.match(text) for text, *_rest in sections(blocks)):
            mended.start = str(place.get("name") or "")
        if mended_blocks == held:
            mended.opening = None
            mended.start = None
        elif not dry_run:
            api.update("journal", str(framing["id"]), entry=mended_blocks)
    if scenario:
        origin = _origin_of(api, campaign, framing, origins or {})
        if origin is not None:
            mended.origin = ORIGINS[origin][0]
            if not dry_run:
                _tag(api, campaign_id, origin, taxa if taxa is not None else _origin_taxa(api))
    mended.problems_after = validate(api, campaign_id) if not dry_run else _predicted(mended)
    return mended


def _origin_taxa(api: Api) -> dict[str, str]:
    names = {name for name, _word in ORIGINS.values()}
    return {str(row["name"]): str(row["id"]) for row in api.list("taxon", kind=ORIGIN_TAXON_KIND) if row.get("name") in names}


def repair(api: Api, dry_run: bool = True, origins: Optional[dict[str, str]] = None, seated: Optional[set[str]] = None) -> list[Mended]:
    """Every scenario of the owner and its playthroughs mended (or, dry, only reported)."""
    origins = {key: value.lower() for key, value in (origins or {}).items()}
    unknown = sorted({value for value in origins.values() if value not in ORIGINS})
    if unknown:
        raise ValueError(f"origins are imported or stereotypical, not {', '.join(unknown)}")
    campaigns = [row for row in api.list("campaign") if not row.get("deleted_at")]
    scenarios = {str(row["id"]) for row in campaigns if row.get("is_scenario")}
    wanted = [row for row in campaigns if str(row["id"]) in scenarios or str(row.get("scenario_id") or "") in scenarios]
    taxa = _origin_taxa(api)
    return [
        mend(api, campaign, str(campaign["id"]) in scenarios, dry_run, origins, seated, taxa)
        for campaign in sorted(wanted, key=lambda row: (str(row["id"]) not in scenarios, str(row.get("name") or "")))
    ]


def _predicted(mended: Mended) -> list[str]:
    """A dry run's guess at what would remain: the problems no step above mends."""
    return [
        problem
        for problem in mended.problems_before
        if not (mended.kinds and "have no kind" in problem)
        and not (mended.opening and "Opening Situation" in problem)
        and not (mended.framing_kind and "not campaign_framing" in problem)
    ]
