# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m vault_import <vault> --base-url URL [--setting SLUG] [--lite] [--dry-run]

The wiki's token is read from WIKI_TOKEN (a SaaS server); a lite edition needs none."""

import argparse
import os
import sys
from pathlib import Path

import httpx

from vault_import.api import Api
from vault_import.importer import Importer
from vault_import.notes import read_vault


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault_import", description="Import an Obsidian vault into the wiki")
    parser.add_argument("vault", type=Path)
    parser.add_argument("--base-url", required=True, help="The wiki's address, e.g. http://localhost:2000")
    parser.add_argument("--setting", help="The setting's slug for the vault's campaigns (dnd, warhammer-40000, …)")
    parser.add_argument("--lite", action="store_true", help="A lite edition: the API is under /api")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    args = parser.parse_args(argv)
    token = os.environ.get("WIKI_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if args.lite:
        # The lite edition refuses cross-site writes; a same-origin fetch says so.
        headers["Sec-Fetch-Site"] = "same-origin"
    with httpx.Client(base_url=args.base_url, timeout=60) as http:
        importer = Importer(Api(http, headers, prefix="/api" if args.lite else ""), setting_slug=args.setting, dry_run=args.dry_run)
        report = importer.run(read_vault(args.vault))
    print(report.text(args.dry_run))
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main())
