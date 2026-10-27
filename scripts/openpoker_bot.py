"""Play one bounded Open Poker session, or a local sandbox dry run (docs/openpoker-client.md).

The API key is read from OPENPOKER_API_KEY and sent only in the Authorization header; it is
never printed or journaled. `--sandbox` serves the documented protocol locally with scripted
opponents and needs no key. Live play is owner-authorized work; this entry point only runs it.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path

from src.openpoker.agent import Agent, parse_routes
from src.openpoker.client import Journal, Session
from src.play_api.native_decisions import NativeDecisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes', type=Path, required=True, help='JSON: players -> {"agent": ..., "view": ...}')
    parser.add_argument('--policy', nargs=3, action='append', default=[], metavar=('NAME', 'PATH', 'SHA256'))
    parser.add_argument('--card-buckets', type=Path)
    parser.add_argument('--journal', type=Path, required=True, help='new JSONL file; never overwritten')
    parser.add_argument('--max-hands', type=int, required=True)
    parser.add_argument('--buy-in', type=int, default=2000)
    parser.add_argument('--stop-file', type=Path)
    parser.add_argument('--seed', type=int, default=20261027)
    parser.add_argument('--url', default='wss://openpoker.ai/ws')
    parser.add_argument('--sandbox', action='store_true', help='play the local sandbox instead of Open Poker')
    parser.add_argument('--sandbox-seats', type=Path, help='JSON: seat -> [agent, stack]; one seat is "bot"')
    args = parser.parse_args()
    if not 1 <= args.max_hands <= 100_000:
        parser.error('--max-hands must be 1..100000')
    routes = parse_routes(json.loads(args.routes.read_text()))
    native = NativeDecisions(card_buckets=args.card_buckets, policies={n: (Path(p), s) for n, p, s in args.policy})
    journal = Journal(args.journal)
    journal.write('session', {'routes': json.loads(args.routes.read_text()), 'policies': native.policies,
                              'buy_in': args.buy_in, 'max_hands': args.max_hands, 'sandbox': args.sandbox,
                              'url': 'sandbox' if args.sandbox else args.url})
    session = Session(Agent(native, routes, args.seed), journal, buy_in=args.buy_in, max_hands=args.max_hands,
                      stop_file=args.stop_file)
    try:
        if args.sandbox:
            seats = None
            if args.sandbox_seats:
                seats = {int(s): v for s, v in json.loads(args.sandbox_seats.read_text()).items()}
            asyncio.run(sandbox_session(native, session, seats))
        else:
            key = os.environ.get('OPENPOKER_API_KEY')
            if not key:
                parser.error('set OPENPOKER_API_KEY')
            asyncio.run(session.run(args.url, key))
    finally:
        journal.write('summary', {'hands': session.hands, **session.stats})
        journal.close()
        native.close()
    print(json.dumps({'hands': session.hands, **session.stats}))


async def sandbox_session(native, session, seats):
    from src.openpoker import sandbox

    started = asyncio.get_running_loop().create_future()
    bot = next((s for s, v in seats.items() if v[0] == 'bot'), None) if seats else 2
    server = asyncio.create_task(sandbox.serve(native, token='sandbox', hands=session.max_hands + 1, started=started,
                                               seats=seats, bot_seat=bot))
    port = await started
    await session.run(f'ws://127.0.0.1:{port}', 'sandbox')
    server.cancel()


if __name__ == '__main__':
    main()
