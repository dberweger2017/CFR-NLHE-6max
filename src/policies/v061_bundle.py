"""Standalone Python3.11 stdlib integrity verifier for the frozen v0.6.1 models.

The fixed whole-model hashes bind every float64 bit and original-mass tag to
PR404. Manifest part hashes diagnose damage; they cannot replace a pinned model.
No model loading, research run, asset upload or publication is performed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

VERSION = 'v0.6.1'
PART_BYTES = 1024**3
VERIFIER = 'verify_v061_bundle.py'
DOCS = ('INSTALL.md','MODEL_CARD.md','RELEASE_NOTES.md')
EVIDENCE = {'acceptance_pr': 404,
 'adverse_relative_regressions_pr': 357,
 'committed_results_sha256': '3784cd2d4b5b3d79a5461510bf206577aaff0927708ac407a6a4c1008d06e26d',
 'frozen_source': 'f11edfe5227882980f57925ab0ca93b3a2f790a7',
 'initial_hands': 10543104,
 'original_results_sha256': '6909662e4b2372c13981467723759ba5a37ffde7daa3899514e8d52c72c969b8',
 'reproduction_hands': 10543104,
 'research_merge': 'bbb71f408db6b1964541e22978628f8c60105313',
 'simultaneous_gates_passed': 30}
CARD_TABLES = {'flop-k50.bin': {'bytes': 12867944,
                  'sha256': '084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111'},
 'turn-k50.bin': {'bytes': 139600524,
                  'sha256': 'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f'},
 'river-k50.bin': {'bytes': 1231562564,
                   'sha256': '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'}}
MODELS = {'2026102240001': {'bytes': 14304919746,
                   'file': 'NP3-200BB-v061-seed-2026102240001.bin',
                   'metadata': {'byte_order': 'little',
                                'dtype': 'float64',
                                'format': 'nplayer-policy-binary-v1',
                                'mass': {'keyset_sha256': 'c37fdf1c6d0a2e92d6193ae285db4c990e5fbecd859c734a33268ae34d41bb11',
                                         'positive_mass_rows': 184507886,
                                         'receipt_sha256': 'b6202c4eaa665f1391f08457308fb5c05e6f1eaeb5a494b1093af355a5331252',
                                         'zero_keys_sha256': 'a40c9f1a82c588e764470671607b6ef42d7523bae88f7f510ece8242a955757f',
                                         'zero_mass_rows': 65494651},
                                'policy': {'continuation': 'none',
                                           'entries': 250002537,
                                           'format': 'nplayer-policy-v1',
                                           'identity': {'big_blind': 100,
                                                        'card_tables': ['084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
                                                                        'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
                                                                        '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'],
                                                        'game': 'nlhe-cash',
                                                        'menu': 'min-pot-conditional-jam-v1',
                                                        'players': 3,
                                                        'schema': 'nplayer-button-live-actor-history-equity-k50-v1',
                                                        'small_blind': 50,
                                                        'stacks': [20000, 20000, 20000],
                                                        'utility_unit': 'big-blind'},
                                           'last_average_street': 3,
                                           'missing': 'uniform',
                                           'players': 3,
                                           'source_checkpoint_sha256': '9e824a45b87e0722385e82452f4ea4574f802edd784e9e91181bf24e17f32570',
                                           'strategy': 'average'},
                                'record_bytes': 32,
                                'source_policy_sha256': 'f6ca935e809ebda4f93e6ecd1c87ff74189c6d64d8a5687b2c3ebfc03c01f563'},
                   'sha256': 'c29eac794d048793988c30f1f9e5024bf970e87883e026cfd72f0d006f24bfa3'},
 '2026102261001': {'bytes': 14307166826,
                   'file': 'NP3-200BB-v061-seed-2026102261001.bin',
                   'metadata': {'byte_order': 'little',
                                'dtype': 'float64',
                                'format': 'nplayer-policy-binary-v1',
                                'mass': {'keyset_sha256': '858641b78b74fc9aaef08c2c2c1bb9edec398d1d7f76131b103d4fee7a1906b5',
                                         'positive_mass_rows': 184429066,
                                         'receipt_sha256': 'ac86bdecdc9cfc6441fcaff1adf37dc7107987e9ab44b4a9ff0fef3029629e9c',
                                         'zero_keys_sha256': 'dfa1c44ea8c5df36be8281a9aa8e6720f9917d74cef4977bdc8a2996b5e4d0c0',
                                         'zero_mass_rows': 65571858},
                                'policy': {'continuation': 'none',
                                           'entries': 250000924,
                                           'format': 'nplayer-policy-v1',
                                           'identity': {'big_blind': 100,
                                                        'card_tables': ['084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
                                                                        'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
                                                                        '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'],
                                                        'game': 'nlhe-cash',
                                                        'menu': 'min-pot-conditional-jam-v1',
                                                        'players': 3,
                                                        'schema': 'nplayer-button-live-actor-history-equity-k50-v1',
                                                        'small_blind': 50,
                                                        'stacks': [20000, 20000, 20000],
                                                        'utility_unit': 'big-blind'},
                                           'last_average_street': 3,
                                           'missing': 'uniform',
                                           'players': 3,
                                           'source_checkpoint_sha256': '18f83931565fd6d1cc906bea52ae481b656cef276545306d8063250bd8ba2245',
                                           'strategy': 'average'},
                                'record_bytes': 32,
                                'source_policy_sha256': '2382722430095e9f3b03b91846d849cc921243ea4a3088f5f9fd11cb1ccaef78'},
                   'sha256': '7c5403929333e6d3260185d7c67667b1302a667745c5485147f87dd7a71ad076'},
 '2026102261002': {'bytes': 14306896906,
                   'file': 'NP3-200BB-v061-seed-2026102261002.bin',
                   'metadata': {'byte_order': 'little',
                                'dtype': 'float64',
                                'format': 'nplayer-policy-binary-v1',
                                'mass': {'keyset_sha256': 'a02d6573e785054455661d5fe54a1808df20109b1cc43ada687df6c90eb8ccf5',
                                         'positive_mass_rows': 184597770,
                                         'receipt_sha256': '847557af8852d2ad3296b2183eef757b97e4b8c4f73f767d41277724c90928cb',
                                         'zero_keys_sha256': 'c9725c2d94fa4ba74de9ad6c9169d75857345597268ad57fc2fc336acd357467',
                                         'zero_mass_rows': 65404167},
                                'policy': {'continuation': 'none',
                                           'entries': 250001937,
                                           'format': 'nplayer-policy-v1',
                                           'identity': {'big_blind': 100,
                                                        'card_tables': ['084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
                                                                        'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
                                                                        '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'],
                                                        'game': 'nlhe-cash',
                                                        'menu': 'min-pot-conditional-jam-v1',
                                                        'players': 3,
                                                        'schema': 'nplayer-button-live-actor-history-equity-k50-v1',
                                                        'small_blind': 50,
                                                        'stacks': [20000, 20000, 20000],
                                                        'utility_unit': 'big-blind'},
                                           'last_average_street': 3,
                                           'missing': 'uniform',
                                           'players': 3,
                                           'source_checkpoint_sha256': 'c5e79990c9fb60775b324547d815f7ca9e5df1cff6b7557576fda4b2fc1e47e2',
                                           'strategy': 'average'},
                                'record_bytes': 32,
                                'source_policy_sha256': '844bb1a6e1ef9f2b94d32443d50a55d6c104abecdd65cab0262bfe89d16d89e1'},
                   'sha256': '7ae4460ba0615af24cc66c8dd86bc868595c6f6e4622372314d5bf141628b3ed'}}
RESEARCH = {'baseline-2026102240001': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-baseline-train.gz',
                            'checkpoint_sha256': '435a664c7dceacd2f8f1cda972ddd060ec30faa9ba291cd7b1546a37ad28e41e',
                            'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-baseline-mass',
                            'mass_sha256': 'd62aae5489e368d7d714a8c7bcf744c7fca92da8388bd21c4ada8999fd33bd73',
                            'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-baseline.bin',
                            'sha256': '1d79e8e114c9abb1674759f028e0f02aa2cd1fa9cddd1daaf8d7e062d08f8dd7',
                            'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-baseline-average.gz',
                            'source_policy_sha256': '3771d8d8f348e317e840ca9722d97f8e10a17d4eac4350c569e8799c891e7127'},
 'baseline-2026102261001': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-baseline-train.gz',
                            'checkpoint_sha256': '0448795425421bba8d9558175e2e8d517defcabfdfbaab2616a240eab5c487bc',
                            'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-baseline-mass',
                            'mass_sha256': 'f1219dbdcd02cd293d1cc6314a2fa8e7df8bbedccc7f8aab066edc1ea3e0742e',
                            'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-baseline.bin',
                            'sha256': '7e9437a77542c84d992366cd08d6a9a92d76f3c3a94115e6c1762b4ddd29ff46',
                            'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-baseline-average.gz',
                            'source_policy_sha256': 'f8a0eea1f9b250cf4521da79c80f4ee484e7cfd7bfce6a0f41f2880555f44ae2'},
 'baseline-2026102261002': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-baseline-train.gz',
                            'checkpoint_sha256': '2aa5058ac56cbfd27854e01e95fb91bc19728b3a042eb292d08d87f6384593c2',
                            'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-baseline-mass',
                            'mass_sha256': '027f883423dfca39a8e53108dd687865a27840d6a284d46543eb59108b6d3151',
                            'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-baseline.bin',
                            'sha256': '7c85a47d38787f5606f355440c4f0da52cb5d22ed66fe34c57e7b4beec2a332a',
                            'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-baseline-average.gz',
                            'source_policy_sha256': 'f8a6c808b1b9602348927b08cb3bd3beb71f28e8a08fe666b07eebeba3d5fcea'},
 'candidate-2026102240001': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-candidate-train.gz',
                             'checkpoint_sha256': '9e824a45b87e0722385e82452f4ea4574f802edd784e9e91181bf24e17f32570',
                             'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-candidate-mass',
                             'mass_sha256': 'b6202c4eaa665f1391f08457308fb5c05e6f1eaeb5a494b1093af355a5331252',
                             'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-candidate.bin',
                             'sha256': 'c29eac794d048793988c30f1f9e5024bf970e87883e026cfd72f0d006f24bfa3',
                             'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102240001-candidate-average.gz',
                             'source_policy_sha256': 'f6ca935e809ebda4f93e6ecd1c87ff74189c6d64d8a5687b2c3ebfc03c01f563'},
 'candidate-2026102261001': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-candidate-train.gz',
                             'checkpoint_sha256': '18f83931565fd6d1cc906bea52ae481b656cef276545306d8063250bd8ba2245',
                             'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-candidate-mass',
                             'mass_sha256': 'ac86bdecdc9cfc6441fcaff1adf37dc7107987e9ab44b4a9ff0fef3029629e9c',
                             'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-candidate.bin',
                             'sha256': '7c5403929333e6d3260185d7c67667b1302a667745c5485147f87dd7a71ad076',
                             'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261001-candidate-average.gz',
                             'source_policy_sha256': '2382722430095e9f3b03b91846d849cc921243ea4a3088f5f9fd11cb1ccaef78'},
 'candidate-2026102261002': {'checkpoint': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-candidate-train.gz',
                             'checkpoint_sha256': 'c5e79990c9fb60775b324547d815f7ca9e5df1cff6b7557576fda4b2fc1e47e2',
                             'mass': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-candidate-mass',
                             'mass_sha256': '847557af8852d2ad3296b2183eef757b97e4b8c4f73f767d41277724c90928cb',
                             'path': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-candidate.bin',
                             'sha256': '7ae4460ba0615af24cc66c8dd86bc868595c6f6e4622372314d5bf141628b3ed',
                             'source_policy': '/home/dberweger/nplayer-bb200-model-campaign-20261022/main-v1/2026102261002-candidate-average.gz',
                             'source_policy_sha256': '844bb1a6e1ef9f2b94d32443d50a55d6c104abecdd65cab0262bfe89d16d89e1'}}
DEPENDENCIES = {'flop-k50.bin': {'bytes': 12867944,
                  'sha256': '084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
                  'url': 'https://github.com/dberweger2017/CFR-NLHE-6max/releases/download/v0.5.3/flop-k50.bin'},
 'river-k50.bin': {'bytes': 1231562564,
                   'sha256': '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629',
                   'url': 'https://github.com/dberweger2017/CFR-NLHE-6max/releases/download/v0.5.3/river-k50.bin'},
 'turn-k50.bin': {'bytes': 139600524,
                  'sha256': 'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
                  'url': 'https://github.com/dberweger2017/CFR-NLHE-6max/releases/download/v0.5.3/turn-k50.bin'}}

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def digest(value,n=64):
    return isinstance(value,str) and len(value)==n and all(c in '0123456789abcdef' for c in value)


def regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('bundle assets must be regular files: '+str(path))
    return path


def names(seed):
    if seed not in MODELS:raise ValueError('choose one frozen v0.6.1 seed')
    stem=MODELS[seed]['file'][:-4]
    return stem+'.manifest.json',stem+'.SHA256SUMS'


def layout(seed):
    p=MODELS[seed]
    return [dict(file=p['file']+f'.part-{i:03d}',bytes=min(PART_BYTES,p['bytes']-offset))
        for i,offset in enumerate(range(0,p['bytes'],PART_BYTES),1)]


def check_header(prefix,header,seed):
    if len(prefix)!=128 or prefix[:8]!=b'NPLBIN01' or any(prefix[120:]):raise ValueError('unsupported binary prefix')
    length,rows,floats,start,values,total=struct.unpack_from('<6Q',prefix,8)
    pin=MODELS[seed]
    if (not 0<length<=65536 or length!=len(header) or start!=128+length or values!=start+32*rows
            or total!=values+8*floats or total!=pin['bytes'] or rows!=pin['metadata']['policy']['entries']
            or not rows<=floats<=6*rows or hashlib.sha256(header).digest()!=prefix[56:88]
            or json.loads(header)!=pin['metadata']):
        raise ValueError('binary source/schema/count/header differs from qualified model')


def verify_model(path,seed):
    path=regular(path);p=MODELS[seed]
    if path.stat().st_size!=p['bytes'] or sha(path)!=p['sha256']:raise ValueError('pinned model bytes/SHA256 differ')
    with path.open('rb') as f:
        prefix=f.read(128)
        if len(prefix)!=128:raise ValueError('truncated binary prefix')
        length=struct.unpack_from('<Q',prefix,8)[0]
        if not 0<length<=65536:raise ValueError('binary header length')
        check_header(prefix,f.read(length),seed)


def read_manifest(directory,seed,expected_source=None,require_publication=False):
    directory=Path(directory);name,_=names(seed);m=json.loads(regular(directory/name).read_text())
    if (m.get('format')!='nplayer-v061-release-v1' or m.get('version')!=VERSION or m.get('seed')!=seed
            or m.get('model')!=MODELS[seed] or m.get('card_tables')!=CARD_TABLES or m.get('evidence')!=EVIDENCE
            or m.get('dependencies')!=DEPENDENCIES
            or m.get('table')!=dict(players=3,stack_bb=200,small_blind=50,big_blind=100,search=False)
            or not digest(m.get('source_commit'),40) or type(m.get('publication_approved')) is not bool
            or expected_source is not None and m['source_commit']!=expected_source
            or require_publication and not m['publication_approved']):
        raise ValueError('release/version/source/approval/pins differ')
    planned=layout(seed);parts=m.get('parts')
    if not isinstance(parts,list) or len(parts)!=len(planned):raise ValueError('part count differs')
    for actual,wanted in zip(parts,planned):
        if not isinstance(actual,dict) or set(actual)!= {'file','bytes','sha256'} or any(actual[k]!=v for k,v in wanted.items()) or not digest(actual['sha256']):
            raise ValueError('part order/path/layout/hash differs')
    assets=m.get('source_assets')
    if not isinstance(assets,dict) or set(assets)!=set(DOCS+(VERIFIER,)):
        raise ValueError('source asset list differs')
    for a in assets.values():
        if not isinstance(a,dict) or set(a)!={'bytes','sha256'} or type(a['bytes']) is not int or a['bytes']<=0 or not digest(a['sha256']):
            raise ValueError('source asset pin differs')
    return m


def verify_small_assets(directory,m,seed,tables=None):
    directory=Path(directory)
    for name,pin in {**m['card_tables'],**m['source_assets']}.items():
        p=regular((Path(tables) if tables is not None and name in CARD_TABLES else directory)/name)
        if p.stat().st_size!=pin['bytes'] or sha(p)!=pin['sha256']:raise ValueError('asset bytes/SHA256 differ: '+name)
    # A verifier imported from the source checkout also binds its shipped copy.
    if sha(directory/VERIFIER)!=sha(Path(__file__)):raise ValueError('verifier differs from checked source')
    manifest_name,sums_name=names(seed)
    checks={p['file']:p['sha256'] for p in m['parts']}
    checks.update({n:v['sha256'] for n,v in {**m['card_tables'],**m['source_assets']}.items()})
    checks[manifest_name]=sha(directory/manifest_name)
    expected=''.join(f'{pin}  {name}\n' for name,pin in sorted(checks.items()))
    if regular(directory/sums_name).read_text()!=expected:raise ValueError('checksum file differs from exact asset list')


def stream_parts(directory,m,seed,target=None):
    whole=hashlib.sha256();head=bytearray();count=0
    for part in m['parts']:
        p=regular(Path(directory)/part['file'])
        if p.stat().st_size!=part['bytes']:raise ValueError('part byte count differs')
        local=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(4*1024**2),b''):
                local.update(chunk);whole.update(chunk);count+=len(chunk)
                if len(head)<128+65536:head.extend(chunk[:128+65536-len(head)])
                if target is not None:target.write(chunk)
        if local.hexdigest()!=part['sha256']:raise ValueError('part SHA256 differs')
    pin=MODELS[seed]
    if count!=pin['bytes'] or whole.hexdigest()!=pin['sha256']:raise ValueError('rehashed parts cannot substitute the pinned model')
    if len(head)<128:raise ValueError('truncated combined prefix')
    length=struct.unpack_from('<Q',head,8)[0]
    if not 0<length<=65536:raise ValueError('combined header length')
    check_header(head[:128],head[128:128+length],seed)
    return dict(bytes=count,sha256=whole.hexdigest())


def verify_bundle(directory,seed,expected_source=None,*,require_publication=False,tables=None):
    m=read_manifest(directory,seed,expected_source,require_publication)
    verify_small_assets(directory,m,seed,tables)
    model=stream_parts(directory,m,seed)
    return dict(status='passed',version=VERSION,seed=seed,source_commit=m['source_commit'],
        publication_approved=m['publication_approved'],model=model,parts=len(m['parts']),
        identity=MODELS[seed]['metadata']['policy']['identity'])


def assemble(directory,seed,destination,*,expected_source=None,require_publication=False,tables=None):
    m=read_manifest(directory,seed,expected_source,require_publication)
    verify_small_assets(directory,m,seed,tables)
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        verify_model(destination,seed);return destination
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_name(destination.name+'.assembling')
    # Preserve every partial on error. A fresh file is published only after its
    # ordered parts, whole digest and source/schema header all reconcile.
    with temp.open('xb') as out:
        stream_parts(directory,m,seed,out);out.flush();os.fsync(out.fileno())
    os.link(temp,destination);temp.unlink()
    return destination


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    p.add_argument('--seed',choices=MODELS,required=True);p.add_argument('--expect-source')
    p.add_argument('--card-tables',type=Path);p.add_argument('--require-publication',action='store_true');p.add_argument('--assemble',type=Path)
    a=p.parse_args()
    if a.assemble:
        path=assemble(a.directory,a.seed,a.assemble,expected_source=a.expect_source,require_publication=a.require_publication,tables=a.card_tables)
        print(json.dumps(dict(status='passed',assembled=str(path),seed=a.seed,sha256=MODELS[a.seed]['sha256'])))
    else:print(json.dumps(verify_bundle(a.directory,a.seed,a.expect_source,require_publication=a.require_publication,tables=a.card_tables)))


if __name__=='__main__':main()
