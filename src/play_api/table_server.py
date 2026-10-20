"""Loopback-only HTTP entrypoint for one 2–6 seat table.

Each --seat names one physical seat in clockwise order: `human` (at most one),
`policy:NAME` for a hash-pinned native n-player export loaded with --policy, or
`script:NAME` for one of the native scripted controls. Example, one human
against two 100 BB three-player models:

    python -m src.play_api.table_server --stack-bb 100 --card-buckets TABLES \\
        --policy 10b PATH SHA256 --policy 3b PATH SHA256 \\
        --seat human --seat policy:10b --seat policy:3b
"""

import argparse
import os
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.play_api.native_decisions import BINARY, NativeDecisions
from src.play_api.server import handler_for, token_file
from src.play_api.table_service import STACKS_BB, SeatTable, TableService

ASSETS = {"/": ("table.html", "text/html; charset=utf-8"),
          "/table.js": ("table.js", "text/javascript; charset=utf-8"),
          "/table.css": ("table.css", "text/css; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seat", action="append", required=True, dest="seats",
                        help="human, policy:NAME or script:random|check-call|tight-aggressive|pot-pressure")
    parser.add_argument("--policy", action="append", nargs=3, default=[], metavar=("NAME", "PATH", "SHA256"))
    parser.add_argument("--card-buckets", type=Path, help="Pinned K50 tables; required with --policy")
    parser.add_argument("--stack-bb", type=int, choices=STACKS_BB, default=100)
    parser.add_argument("--binary", type=Path, default=BINARY)
    parser.add_argument("--data-dir", type=Path, default=Path("results/play-web-tables"))
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--source-version", default="unknown")
    parser.add_argument("--verify-session")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be 1–65535")
    if args.policy and args.card_buckets is None:
        parser.error("--policy needs --card-buckets")
    try:
        table = SeatTable(tuple(args.seats), stack=100 * args.stack_bb)
    except ValueError as error:
        parser.error(str(error))
    os.umask(0o077)
    decisions = NativeDecisions(card_buckets=args.card_buckets,
                                policies={name: (path, sha) for name, path, sha in args.policy},
                                binary=args.binary)
    try:
        # One journal per table configuration; sessions check their identity on load.
        label = "-".join(a.replace(":", "_") for a in table.agents)
        service = TableService(args.data_dir / f"{args.stack_bb}bb-{label}" / "private.sqlite", table, decisions,
                               source_version=args.source_version)
        try:
            if args.verify_session:
                print(f"Verified {service.verify_replay(args.verify_session)} completed hands")
                return 0
            token_path = args.data_dir / "access.token"
            token = token_file(token_path)
            server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(service, token, args.port, ASSETS))
            print(f"Local table: http://127.0.0.1:{args.port}/", flush=True)
            print(f"Enter the access token stored at {token_path}; it is not put in a URL or log.", flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
        finally:
            service.close()
    finally:
        decisions.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
