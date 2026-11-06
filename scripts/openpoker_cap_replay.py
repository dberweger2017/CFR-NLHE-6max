"""Replay live Open Poker journals offline with and without the stack cap (docs/openpoker-client.md).

Each journal's server messages go through the client's own message handling again. At every
turn three agents decide on the same tracked hand:
- `session`: the session's own routes, uncapped, as it played; its policy decisions by route and
  trained flag must match the journal's, which checks the replay;
- `uncapped`: today's routes without the cap;
- `capped`: today's routes with the cap.
The report counts, per agent, decisions by status, routes and trained rows, and lists every
decision where the cap changed the route or the trained flag. Nothing is sent anywhere.
"""
import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from src.openpoker.agent import Agent, parse_routes
from src.openpoker.client import Session
from src.play_api.native_decisions import NativeDecisions


class Twin:
    """Runs every agent on the turn; the session acts on the first one's answer."""

    def __init__(self, agents):
        self.agents, self.records = agents, []

    def decide(self, hand, turn):
        decided = {name: agent.decide(hand, turn) for name, agent in self.agents.items()}
        self.records.append({name: record for name, (_, record) in decided.items()})
        return next(iter(decided.values()))


class Null:
    def write(self, kind, payload):
        pass


class Socket:
    async def send(self, text):
        pass


async def replay(path: Path, twin: Twin):
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    session = Session(twin, Null())
    start = len(twin.records)
    for line in lines:
        if line['kind'] == 'in':
            await session.handle(Socket(), line['payload'])
    return twin.records[start:], [line['payload'] for line in lines if line['kind'] == 'decision']


def policy_counts(records):
    return Counter(f"{r['route']}|{'trained' if r['trained'] else 'untrained'}" for r in records if r['status'] == 'policy')


def summary(records, name):
    statuses, routes, trained = Counter(), Counter(), Counter()
    for r in (r[name] for r in records):
        statuses[r['status']] += 1
        if r['status'] == 'policy':
            routes[r['route']] += 1
            trained[bool(r['trained'])] += 1
        else:
            statuses[f"fallback: {r['reason'].split(' at ')[0].split(':')[0]}"] += 1
    return {'decisions': dict(statuses), 'routes': dict(routes), 'trained': trained[True], 'untrained': trained[False]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journals', type=Path, nargs='+')
    parser.add_argument('--routes', type=Path, required=True, help="today's routes")
    parser.add_argument('--policy', nargs=3, action='append', default=[], metavar=('NAME', 'PATH', 'SHA256'))
    parser.add_argument('--card-buckets', type=Path)
    parser.add_argument('--seed', type=int, default=20261027)
    parser.add_argument('--out', type=Path, required=True, help='new JSON report; never overwritten')
    args = parser.parse_args()
    native = NativeDecisions(card_buckets=args.card_buckets, policies={n: (Path(p), s) for n, p, s in args.policy})
    today = parse_routes(json.loads(args.routes.read_text()))
    report = {'journals': {}, 'changed': []}
    try:
        for path in args.journals:
            first = json.loads(path.read_text().splitlines()[0])
            if first['kind'] != 'session':
                raise ValueError(f'{path}: no session line')
            twin = Twin({'session': Agent(native, parse_routes(first['payload']['routes']), args.seed, cap=False),
                         'uncapped': Agent(native, today, args.seed, cap=False),
                         'capped': Agent(native, today, args.seed)})
            records, played = asyncio.run(replay(path, twin))
            journal, again = policy_counts(played), policy_counts([r['session'] for r in records])
            report['journals'][str(path)] = {
                'agent_turns': len(records), 'journal_decisions': len(played), 'journal_policy': dict(journal),
                'session_matches_journal': journal == again,
                **{name: summary(records, name) for name in twin.agents}}
            for r in records:
                u, c = r['uncapped'], r['capped']
                if (u.get('route'), u.get('trained'), u['status']) != (c.get('route'), c.get('trained'), c['status']):
                    report['changed'].append({'journal': path.name, 'hand_id': c.get('hand_id'),
                                              'raw_stacks_bb': c.get('raw_stacks_bb') or c.get('stacks_bb'),
                                              'stacks_bb': c.get('stacks_bb'),
                                              'uncapped': {k: u.get(k) for k in ('status', 'route', 'trained', 'native_action', 'reason')},
                                              'capped': {k: c.get(k) for k in ('status', 'route', 'trained', 'native_action', 'reason')}})
    finally:
        native.close()
    with args.out.open('x') as f:
        f.write(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
