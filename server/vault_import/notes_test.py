# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading a vault: notes with an entity_type, templates and hidden folders left out, links by name."""

from pathlib import Path

from vault_import.notes import link_name, read_vault

FIXTURE = Path(__file__).parent / "fixtures" / "vault"


def test_the_vault_reads_every_note_with_an_entity_type_but_its_templates() -> None:
    notes = read_vault(FIXTURE)
    assert len(notes) == 13
    assert all(not note.path.startswith("Templates") for note in notes)
    holst = next(note for note in notes if note.name == "Holst")
    # His picture sits beside his note under his name; Dingus has none.
    assert (holst.picture is not None and holst.picture.name, next(note for note in notes if note.name == "Dingus").picture) == ("Holst.png", None)
    assert (holst.entity_type, holst.meta["campaign"], holst.meta["relations"][0]["attitude"]) == ("person", "The Split Antler", "wary")
    assert "Bought the stable" in holst.body


def test_a_link_names_its_note() -> None:
    assert link_name('"[[Holst]]"') == "Holst"
    assert link_name("[[Brindlemarsh Stable|stable]]") == "Brindlemarsh Stable"
    assert link_name("[[Holst#History]]") == "Holst"
    assert link_name("Holst") == "Holst"
    assert link_name("") is None
    assert link_name(None) is None
