"""Deployment check for an Open Poker route set (docs/openpoker-client.md).

Loads every policy into one decision service, then plays sandbox hands at random tables: 2–6
dealt players in random seats, each stack drawn log-uniformly from 10–250 BB and kept across
hands, scripted opponents. Reports load time, the service's peak memory, per-decision latency,
decision statuses, fallback reasons and the routes used, and checks them against the limits
below. Needs no key and never connects to Open Poker.
"""
import argparse
import asyncio
import json
import math
import random
import time
from collections import Counter
from pathlib import Path

from src.openpoker.agent import Agent, parse_routes
from src.openpoker.sandbox import Table
from src.openpoker.tracker import Hand
from src.play_api.native_decisions import SCRIPTS, NativeDecisions

# Open Poker allows 45 s per action; the client gives a decision 30 s.
MAX_DECISION_SECONDS = 5.0
ALLOWED_FALLBACKS = ('possible all-in blind',)


def peak_memory_gb(pid):
    """The service's peak resident memory (Linux VmHWM), or None elsewhere."""
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmHWM:'):
                return int(line.split()[1]) / 2**20
    except OSError:
        return None


async def play(table, agent, hands, latencies):
    records, state = [], {}

    async def send(message):
        kind = message['type']
        if kind == 'hand_start':
            state['hand'] = Hand.start(message)
        elif kind in ('hole_cards', 'community_cards', 'player_action', 'table_state'):
            getattr(state['hand'], kind)(message)

    async def act(turn):
        started = time.perf_counter()
        action, record = agent.decide(state['hand'], turn)
        latencies.append(time.perf_counter() - started)
        records.append(record)
        return action

    for _ in range(hands):
        if not await table.hand(send, act):
            break
    return records


def random_seats(rng):
    n = rng.randint(2, 6)
    seats = sorted(rng.sample(range(6), n))
    stacks = {s: round(20 * math.exp(rng.uniform(math.log(10), math.log(250)))) for s in seats}
    bot = rng.choice(seats)
    return {s: ['bot' if s == bot else f'script:{rng.choice(SCRIPTS)}', stacks[s]] for s in seats}, bot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes', type=Path, required=True)
    parser.add_argument('--policy', nargs=3, action='append', default=[], metavar=('NAME', 'PATH', 'SHA256'))
    parser.add_argument('--card-buckets', type=Path)
    parser.add_argument('--tables', type=int, default=200)
    parser.add_argument('--hands-per-table', type=int, default=20)
    parser.add_argument('--seed', type=int, default=20261027)
    parser.add_argument('--out', type=Path, required=True, help='new JSON report; never overwritten')
    args = parser.parse_args()
    routes = parse_routes(json.loads(args.routes.read_text()))
    started = time.perf_counter()
    native = NativeDecisions(card_buckets=args.card_buckets, policies={n: (Path(p), s) for n, p, s in args.policy})
    load_seconds = time.perf_counter() - started
    rng = random.Random(args.seed)
    agent = Agent(native, routes, args.seed)
    latencies, statuses, reasons, used, tables = [], Counter(), Counter(), Counter(), Counter()
    try:
        for index in range(args.tables):
            seats, bot = random_seats(rng)
            tables[len(seats)] += 1
            table = Table(native, seats, bot_seat=bot, seed=args.seed * 1000 + index)
            for r in asyncio.run(play(table, agent, args.hands_per_table, latencies)):
                statuses[r['status']] += 1
                if r['status'] == 'fallback':
                    reasons[r['reason'].split(' at ')[0].split(':')[0]] += 1
                else:
                    used[f"{r['players']} players: {r['route']}"] += 1
        memory = peak_memory_gb(native.process.pid)
    finally:
        native.close()
    latencies.sort()
    q = lambda p: latencies[min(len(latencies) - 1, int(p * len(latencies)))] if latencies else None
    report = {'policies': {n: s for n, _, s in args.policy}, 'routes': json.loads(args.routes.read_text()),
              'load_seconds': load_seconds, 'peak_memory_gb': memory, 'tables_by_players': dict(sorted(tables.items())),
              'decisions': dict(statuses), 'fallback_reasons': dict(reasons), 'routes_used': dict(sorted(used.items())),
              'latency_seconds': {'p50': q(0.5), 'p99': q(0.99), 'max': latencies[-1] if latencies else None}}
    report['passed'] = bool(latencies) and latencies[-1] <= MAX_DECISION_SECONDS and set(reasons) <= set(ALLOWED_FALLBACKS)
    with args.out.open('x') as f:
        f.write(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
