# SPDX-License-Identifier: AGPL-3.0-or-later
"""Foundry's HTML and enrichers as plain Markdown."""

from compendium_import.richtext import enrichers, to_markdown


def test_enrichers_become_their_labels_or_the_owners_name() -> None:
    text = "@UUID[Compendium.dnd5e.spells.Item.x]{Fire Bolt} for [[/r 2d6]] (&Reference[blinded apply=false]); the [[lookup @name lowercase]]{monster}"
    assert enrichers(text, {"@name": "Vampire"}) == "Fire Bolt for 2d6 (blinded); the vampire"
    # The SRD packs' own typos read too.
    assert enrichers("the [[l;ookup @name]]{monster} keeps &Reference[Concentration} up", {"@name": "Mage"}) == "the Mage keeps Concentration up"


def test_html_as_markdown_paragraphs_lists_and_table_rows() -> None:
    html = "<p>One &amp;Reference[prone].</p><h3>More</h3><ul><li><strong>A.</strong> a</li><li>b</li></ul><table><tr><td>1</td><td>Ash</td></tr></table>"
    assert to_markdown(html) == "One prone.\n\n### More\n\n- **A.** a\n- b\n\n1 — Ash"
