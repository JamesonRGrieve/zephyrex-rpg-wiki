# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m compendium_import <system dir> --setting SLUG [--packs a,b] [--dry-run]
       (--base-url URL [--lite]  |  --app module:factory --owner USER_ID)

Imports a Foundry system's compendium packs (today dnd5e's SRD packs) into the setting's canon,
provenance official; a second run changes only what differs. The connection is vault_import's: over
HTTP (WIKI_TOKEN for a SaaS server) or in process as --owner."""

import argparse
import sys
from pathlib import Path

from compendium_import import dnd5e
from compendium_import.foundry import read_packs
from compendium_import.importer import CompendiumImporter
from vault_import.connect import connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compendium_import", description="Import a Foundry system's compendium packs into a setting's canon")
    parser.add_argument("system", type=Path, help="The system's folder (system.json and packs/_source beside it)")
    parser.add_argument("--setting", required=True, help="The setting's slug (dnd, …)")
    parser.add_argument("--packs", help="Comma-separated packs (default: the system's mapped packs)")
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
    packs = args.packs.split(",") if args.packs else list(dnd5e.PACKS)
    documents = read_packs(args.system, packs)
    with connection(args.base_url, args.lite, args.app, args.owner) as api:
        report = CompendiumImporter(api, args.setting, dry_run=args.dry_run).run(documents)
    print(report.text(args.dry_run))
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main())
