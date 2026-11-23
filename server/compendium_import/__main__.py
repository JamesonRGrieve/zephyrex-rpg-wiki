# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m compendium_import <dir> --setting SLUG [--system dnd5e|wh40k] [--packs a,b] [--dry-run]
       (--base-url URL [--lite]  |  --app module:factory --owner USER_ID)

Imports a Foundry system's compendium packs into the setting's canon: dnd5e's SRD packs (<dir> is
the system, system.json beside packs/_source), or wh40k-rpg's official packs (<dir> is its
src/packs-private; --packs names line folders, dark-heresy-2,…),
provenance official; a second run changes only what differs. The connection is vault_import's: over
HTTP (WIKI_TOKEN for a SaaS server) or in process as --owner."""

import argparse
import sys
from pathlib import Path

from compendium_import import dnd5e
from compendium_import.foundry import read_packs
from compendium_import import wh40k
from compendium_import.importer import CompendiumImporter, wh40k_system
from vault_import.connect import connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compendium_import", description="Import a Foundry system's compendium packs into a setting's canon")
    parser.add_argument("dir", type=Path, help="dnd5e: the system's folder; wh40k: its src/packs-private")
    parser.add_argument("--setting", required=True, help="The setting's slug (it must exist: POST /v1/setting)")
    parser.add_argument("--system", choices=("dnd5e", "wh40k"), default="dnd5e", help="Whose packs these are")
    parser.add_argument("--packs", help="Comma-separated packs, or line folders for wh40k (default: all mapped)")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition: the API is under /api")
    parser.add_argument("--app", help="In process: the server app's factory, module:function")
    parser.add_argument("--owner", help="In process: the user id whose records these become")
    args = parser.parse_args(argv)
    if (args.app is None) == (args.base_url is None):
        parser.error("give --base-url (over HTTP) or --app with --owner (in process)")
    if args.app is not None and not args.owner:
        parser.error("--app needs --owner")
    chosen = args.packs.split(",") if args.packs else None
    if args.system == "wh40k":
        documents = wh40k.read_lines(args.dir, chosen)
        system = wh40k_system()
    else:
        documents = read_packs(args.dir, chosen or list(dnd5e.PACKS))
        system = None
    with connection(args.base_url, args.lite, args.app, args.owner) as api:
        report = CompendiumImporter(api, args.setting, dry_run=args.dry_run, system=system).run(documents)
    print(report.text(args.dry_run))
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main())
