"""Standalone Python3.11 stdlib integrity verifier for the frozen v0.6.0 models.

The fixed whole-model hashes bind every float64 bit and original-mass tag to
PR367. Manifest part hashes diagnose damage; they cannot replace a pinned model.
No model loading, research run, asset upload or publication is performed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

VERSION = 'v0.6.0'
PART_BYTES = 1024**3
VERIFIER = 'verify_v060_bundle.py'
DOCS = ('INSTALL.md','MODEL_CARD.md','RELEASE_NOTES.md')
EVIDENCE = {
    'acceptance_pr': 367,
    'settled_results_sha256': '15c573e88d9b3b3c9ab81f6f3150eff6b91d577b6aa26fdad0a2af3045f32453',
    'simultaneous_gates_passed': 30,
    'adverse_relative_regressions_pr': 357,
}
CARD_TABLES = {'flop-k50.bin': {'bytes': 12867944,
                  'sha256': '084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111'},
 'turn-k50.bin': {'bytes': 139600524,
                  'sha256': 'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f'},
 'river-k50.bin': {'bytes': 1231562564,
                   'sha256': '70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'}}
MODELS = {'2026101935003': {'file': 'NP3-100BB-v060-seed-2026101935003.bin',
                   'bytes': 14149208746,
                   'sha256': 'd835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189',
                   'metadata': {'byte_order': 'little',
                                'dtype': 'float64',
                                'format': 'nplayer-policy-binary-v1',
                                'mass': {'keyset_sha256': 'a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425',
                                         'positive_mass_rows': 181458908,
                                         'receipt_sha256': '2d957c76b9e35690cf7eb56087bb96e703e034b6533b73f3be7c72e0aaea01a0',
                                         'zero_keys_sha256': '45af8328c11b51ca5fd53242306271d18ea4c08f3f4af74d3bbf288425b0c69a',
                                         'zero_mass_rows': 68541567},
                                'policy': {'continuation': 'none',
                                           'entries': 250000475,
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
                                                        'stacks': [10000, 10000, 10000],
                                                        'utility_unit': 'big-blind'},
                                           'last_average_street': 3,
                                           'missing': 'uniform',
                                           'players': 3,
                                           'source_checkpoint_sha256': '788e75acf8b98d88518faf3da683048ec05604ba001c8a59bb1ec5f740b52b80',
                                           'strategy': 'average'},
                                'record_bytes': 32,
                                'source_policy_sha256': 'a85364b71c478be213e0356c5201911755228c864472427b64699346191facbd'}},
 '202610200601': {'file': 'NP3-100BB-v060-seed-202610200601.bin',
                  'bytes': 14148446930,
                  'sha256': '23599816cf632a51cace45f25d70ed4918fe5e75875c33136d8629052a8a2a70',
                  'metadata': {'byte_order': 'little',
                               'dtype': 'float64',
                               'format': 'nplayer-policy-binary-v1',
                               'mass': {'keyset_sha256': 'd2e9bbadb39aa5f6504b077cdfd764fd5f41c4407706f9f5b6124325154a10a3',
                                        'positive_mass_rows': 181590424,
                                        'receipt_sha256': 'd1740074496f7bed582cb6829a9c1316ba43b2d1740fc2922a76d361bf1f5ad0',
                                        'zero_keys_sha256': '82f0d3bdc3def6e084eef1d09c9fcd505e3587dc88c620175e4cae30a81f06a0',
                                        'zero_mass_rows': 68410645},
                               'policy': {'continuation': 'none',
                                          'entries': 250001069,
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
                                                       'stacks': [10000, 10000, 10000],
                                                       'utility_unit': 'big-blind'},
                                          'last_average_street': 3,
                                          'missing': 'uniform',
                                          'players': 3,
                                          'source_checkpoint_sha256': 'd03db22316af0e8bd04e76f5303603709bd77b2bf13dcc13ea07482ca10170ca',
                                          'strategy': 'average'},
                               'record_bytes': 32,
                               'source_policy_sha256': 'fbb0b16f8459376519c9ea81c2c2d33b8c08d36efeb8cc2ca9d148eaf08b8843'}},
 '202610200602': {'file': 'NP3-100BB-v060-seed-202610200602.bin',
                  'bytes': 14148348082,
                  'sha256': '2911937c047c644324d7a78a944949192f19d44eda373ca333d94a0dcaec8984',
                  'metadata': {'byte_order': 'little',
                               'dtype': 'float64',
                               'format': 'nplayer-policy-binary-v1',
                               'mass': {'keyset_sha256': 'e99622c1ee718733cef4aa0df6ddfc7032e1e3dfd7fc08b5a9396fb7e34c73fd',
                                        'positive_mass_rows': 181434181,
                                        'receipt_sha256': '59ee0b8ae9169b49798dfe4672d6178f5e0777b06eb406ca4c8f6d1362a050b5',
                                        'zero_keys_sha256': 'a68c4bfea00334c388868e562d5d411df83d8399ba6cfe4f00919a3a1b0ee32f',
                                        'zero_mass_rows': 68566135},
                               'policy': {'continuation': 'none',
                                          'entries': 250000316,
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
                                                       'stacks': [10000, 10000, 10000],
                                                       'utility_unit': 'big-blind'},
                                          'last_average_street': 3,
                                          'missing': 'uniform',
                                          'players': 3,
                                          'source_checkpoint_sha256': '94836638f4818414307425278bdc291948a060107ed0064552f329d4960d7200',
                                          'strategy': 'average'},
                               'record_bytes': 32,
                               'source_policy_sha256': '8427dffd00de9b9cb490cc6842aecf279eab6d55a27752dcd3781df3d0c52ecf'}}}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def digest(value,n=64):
    return isinstance(value,str) and len(value)==n and all(c in '0123456789abcdef' for c in value)


def regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('bundle assets must be regular files: '+str(path))
    return path


def names(seed):
    if seed not in MODELS:raise ValueError('choose one frozen v0.6.0 seed')
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
    if (m.get('format')!='nplayer-v060-release-v1' or m.get('version')!=VERSION or m.get('seed')!=seed
            or m.get('model')!=MODELS[seed] or m.get('card_tables')!=CARD_TABLES or m.get('evidence')!=EVIDENCE
            or m.get('table')!=dict(players=3,stack_bb=100,small_blind=50,big_blind=100,search=False)
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


def verify_small_assets(directory,m,seed):
    directory=Path(directory)
    for name,pin in {**m['card_tables'],**m['source_assets']}.items():
        p=regular(directory/name)
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


def verify_bundle(directory,seed,expected_source=None,*,require_publication=False):
    m=read_manifest(directory,seed,expected_source,require_publication)
    verify_small_assets(directory,m,seed)
    model=stream_parts(directory,m,seed)
    return dict(status='passed',version=VERSION,seed=seed,source_commit=m['source_commit'],
        publication_approved=m['publication_approved'],model=model,parts=len(m['parts']),
        identity=MODELS[seed]['metadata']['policy']['identity'])


def assemble(directory,seed,destination,*,expected_source=None,require_publication=False):
    m=read_manifest(directory,seed,expected_source,require_publication)
    verify_small_assets(directory,m,seed)
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
    p.add_argument('--require-publication',action='store_true');p.add_argument('--assemble',type=Path)
    a=p.parse_args()
    if a.assemble:
        path=assemble(a.directory,a.seed,a.assemble,expected_source=a.expect_source,require_publication=a.require_publication)
        print(json.dumps(dict(status='passed',assembled=str(path),seed=a.seed,sha256=MODELS[a.seed]['sha256'])))
    else:print(json.dumps(verify_bundle(a.directory,a.seed,a.expect_source,require_publication=a.require_publication)))


if __name__=='__main__':main()
