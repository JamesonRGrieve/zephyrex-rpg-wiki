# SPDX-License-Identifier: AGPL-3.0-or-later
"""python -m vault_import <vault> [<vault> …] --setting SLUG [--dry-run]
       (--base-url URL [--lite]  |  --app module:factory --owner USER_ID)

Over HTTP, the wiki's token is read from WIKI_TOKEN (a SaaS server); a lite edition needs none.
In process (--app), it boots the server app in this process, as VTT's import does, with the app's
environment loaded: run it from the app's server directory. It signs in as --owner for an hour (a
session the auth_session extension records and can revoke) and goes through the app's own routes,
so every rule holds as over HTTP. Several vaults import in the order given: a setting's canon
before the campaigns that link to it.
"""

import argparse
import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from vault_import.api import Api
from vault_import.importer import Importer
from vault_import.notes import read_vault

SESSION_HOURS = 1


@contextmanager
def _over_http(base_url: str, lite: bool) -> Iterator[Api]:
    import httpx

    token = os.environ.get("WIKI_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if lite:
        # The lite edition refuses cross-site writes; a same-origin fetch says so.
        headers["Sec-Fetch-Site"] = "same-origin"
    with httpx.Client(base_url=base_url, timeout=60) as http:
        yield Api(http, headers, prefix="/api" if lite else "")


@contextmanager
def _in_process(app_path: str, owner: str) -> Iterator[Api]:
    from fastapi.testclient import TestClient
    from zephyrex.lib.Environment import env
    from zephyrex.logic.BLL_Auth import UserManager

    sys.path.insert(0, os.getcwd())
    module, _, factory = app_path.partition(":")
    app: Any = getattr(importlib.import_module(module), factory or "create")()
    with TestClient(app) as http:
        registry = app.state.model_registry
        user = UserManager(requester_id=env("ROOT_ID"), model_registry=registry).get(id=owner)
        token = UserManager.generate_jwt_token(
            user_id=str(user.id), email=str(user.email), expiration_hours=SESSION_HOURS, model_registry=registry
        )
        yield Api(http, {"Authorization": f"Bearer {token}"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault_import", description="Import Obsidian vaults into the wiki")
    parser.add_argument("vaults", type=Path, nargs="+", help="Vault folders, imported in this order")
    parser.add_argument("--setting", help="The setting's slug for the vaults' campaigns (dnd, warhammer-40000, …)")
    parser.add_argument("--dry-run", action="store_true", help="Read and report; write nothing")
    parser.add_argument("--base-url", help="Over HTTP: the wiki's address, e.g. http://localhost:2000")
    parser.add_argument("--lite", action="store_true", help="Over HTTP to a lite edition: the API is under /api")
    parser.add_argument("--app", help="In process: the server app's factory, module:function (rpg_ai_app:create)")
    parser.add_argument("--owner", help="In process: the user id whose records these become")
    args = parser.parse_args(argv)
    if (args.app is None) == (args.base_url is None):
        parser.error("give --base-url (over HTTP) or --app with --owner (in process)")
    if args.app is not None and not args.owner:
        parser.error("--app needs --owner")
    connect = _in_process(args.app, args.owner) if args.app else _over_http(args.base_url, args.lite)
    notes = [note for vault in args.vaults for note in read_vault(vault)]
    with connect as api:
        report = Importer(api, setting_slug=args.setting, dry_run=args.dry_run).run(notes)
    print(report.text(args.dry_run))
    return 1 if report.refused else 0


if __name__ == "__main__":
    sys.exit(main())
