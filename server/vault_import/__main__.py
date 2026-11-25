# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m vault_import <vault> [<vault> …] --setting SLUG [--dry-run]
       (--base-url URL [--lite]  |  --app module:factory (--owner USER_ID | --system [--setting-name NAME]))

Over HTTP, the wiki's token is read from WIKI_TOKEN (a SaaS server); a lite edition needs none.
In process (--app), it boots the server app in this process, as VTT's import does, with the app's
environment loaded: run it from the app's server directory. It signs in as --owner for an hour (a
session the auth_session extension records and can revoke) and goes through the app's own routes,
so every rule holds as over HTTP. Several vaults import in the order given: a setting's canon
before the campaigns that link to it.

--system (in process) writes as SYSTEM instead: system-level content, the SRD's setting canon,
scenarios and pregens (operator, 2026-11-25), which every account reads and plays a copy of, and
only the server changes. The setting decides: a system import writes only into a system setting
(made, named --setting-name, when there is none with the slug), an owner import only into their
own. Either matches only the rows its writer made.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

from vault_import.connect import connection
from vault_import.notes import read_vault


def with_default_campaign(notes: list[Any], campaign: str) -> None:
    """--default-campaign: a note that names no campaign and isn't setting_wide (a campaign vault's own
    root notes) belongs to `campaign`; every other note keeps its own."""
    for note in notes:
        if not note.meta.get("campaign") and note.meta.get("setting_wide") is not True:
            note.meta["campaign"] = campaign


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault_import", description="Import Obsidian vaults into the wiki")
    parser.add_argument("vaults", type=Path, nargs="+", help="Vault folders, imported in this order")
    parser.add_argument("--setting", help="The setting's slug for the vaults' campaigns (it must exist: POST /v1/setting)")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    parser.add_argument("--force", action="store_true", help="Write every matched record's fields as its note gives them, changed or not")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address, e.g. http://localhost:2000")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition: the API is under /api")
    parser.add_argument("--app", help="In process: the server app's factory, module:function (rpg_ai_app:create)")
    parser.add_argument("--owner", help="In process: the user id whose records these become")
    parser.add_argument("--system", action="store_true", help="In process: system level, as SYSTEM (the SRD's content), instead of --owner")
    parser.add_argument("--setting-name", help="With --system: the system setting's name, to make it when no setting has the slug")
    parser.add_argument(
        "--default-campaign",
        help="The campaign of a note that names none and isn't setting_wide (a campaign vault's own root notes)",
    )
    args = parser.parse_args(argv)
    if (args.app is None) == (args.base_url is None):
        parser.error("give --base-url (over HTTP) or --app with --owner (in process)")
    if args.app is not None and bool(args.owner) == args.system:
        parser.error("--app needs --owner, or --system (not both)")
    if args.system and args.app is None:
        parser.error("--system runs in process only (--app)")
    connect = connection(args.base_url, args.lite, args.app, args.owner, args.system)
    notes = [note for vault in args.vaults for note in read_vault(vault)]
    if args.default_campaign:
        with_default_campaign(notes, args.default_campaign)
    with connect as api:
        # The importer imports the wiki's shared code (zephyrex.extensions.wiki_shared), which exists
        # only once the connection has made the app (in process) or put the checkout's on the path.
        from vault_import.importer import Importer

        report = Importer(api, setting_slug=args.setting, dry_run=args.dry_run, force=args.force, setting_name=args.setting_name).run(notes)
    print(report.text(args.dry_run))
    return 1 if report.refused or report.unplayable else 0


if __name__ == "__main__":
    sys.exit(main())
