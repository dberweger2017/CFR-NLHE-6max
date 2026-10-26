"""Start the pinned three-seat100BB v0.6.0 human or spectator table."""
import argparse
from pathlib import Path

from src.policies.v060_bundle import MODELS, VERSION, assemble, read_manifest


def table_arguments(bundle,seed,cache,*,allow_prepared=False,watch=False,binary=None,data_dir=None,port=8766):
    # The explicit seed chooses a qualified lineage, never the highest score.
    m=read_manifest(bundle,seed,require_publication=not allow_prepared)
    model=assemble(bundle,seed,Path(cache)/MODELS[seed]['file'],require_publication=not allow_prepared)
    alias=f'{VERSION}-{seed}'
    args=['--stack-bb','100','--card-buckets',str(bundle),'--policy',alias,str(model),MODELS[seed]['sha256'],
        '--seat','policy:'+alias if watch else 'human','--seat','policy:'+alias,'--seat','policy:'+alias,
        '--source-version',f'{VERSION}{"-prepared" if not m["publication_approved"] else ""}:{m["source_commit"]}',
        '--port',str(port)]
    if binary is not None:args += ['--binary',str(binary)]
    if data_dir is not None:args += ['--data-dir',str(data_dir)]
    return args


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--seed',choices=MODELS,required=True);p.add_argument('--cache-dir',type=Path,default=Path('models/v0.6.0/cache'))
    p.add_argument('--allow-prepared',action='store_true',help='Explicit local review of an unpublished bundle')
    p.add_argument('--watch',action='store_true',help='Three independently sampled bots share one model')
    p.add_argument('--binary',type=Path);p.add_argument('--data-dir',type=Path,default=Path('results/play-v060'))
    p.add_argument('--port',type=int,default=8766);a=p.parse_args(argv)
    if not 1<=a.port<=65535:p.error('port must be1–65535')
    args=table_arguments(a.bundle,a.seed,a.cache_dir,allow_prepared=a.allow_prepared,watch=a.watch,
                         binary=a.binary,data_dir=a.data_dir,port=a.port)
    from src.play_api.table_server import main as serve
    return serve(args)


if __name__=='__main__':raise SystemExit(main())
