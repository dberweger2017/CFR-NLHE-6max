"""Six-player live-order key screen: #417's 10B against the live-order 10B.

Reuses the opponent-pressure screen's control, fields and fresh banks and the
traverser-admission screen's row classes, and applies the decision rule of
docs/nplayer-live-order-screen.md.
"""
import argparse
import json
from pathlib import Path

from scripts import nplayer_admission_screen as admission
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'live'
FORMAT = 'nplayer-live-order-screen-v1'
SCHEMA = 'nplayer-live-order-summary-equity-k50-v1'


def training(args):
    control = admission.header(admission.CONTROL_CHECKPOINT)
    arm = admission.header(args.checkpoint)
    if arm['game']['schema'] != SCHEMA or control['game']['schema'] == SCHEMA:
        raise ValueError('arm must use live-order keys and the control history keys')
    result = {'control': admission.telemetry(control, json.loads(Path(admission.CONTROL_MASS).read_text())),
              ARM: admission.telemetry(arm, json.loads((args.mass / 'receipt.json').read_text()))}
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'rows', 'training', 'report'):
        p = sub.add_parser(name)
        p.add_argument('--out', type=Path, required=True)
        if name == 'manifest':
            p.add_argument('--binary', type=Path, required=True)
        if name in ('manifest', 'training'):
            p.add_argument('--mass', type=Path, required=True)
        if name in ('rows', 'training'):
            p.add_argument('--checkpoint', type=Path, required=True)
        if name in ('scan', 'rows'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name == 'report':
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': lambda a: screen.manifest(a, arm=ARM), 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': lambda a: admission.rows(a, arm=ARM), 'training': training,
     'report': lambda a: admission.report(a, arm=ARM, fmt=FORMAT)}[args.command](args)


if __name__ == '__main__':
    main()
