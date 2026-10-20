"""Small real-format bundles exercise integrity/refusal without mature models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts import build_v060_bundle as builder
from scripts import play_v060 as launcher
from src.policies import v060_bundle as v


def fixture(model,seed):
    metadata=deepcopy(v.MODELS[seed]['metadata'])
    metadata['policy']['entries']=1
    metadata['mass'].update(positive_mass_rows=1,zero_mass_rows=0,keyset_sha256=hashlib.sha256(b'a'*16).hexdigest())
    h=json.dumps(metadata,separators=(',',':')).encode();record=b'a'*16+struct.pack('<Q',0)+bytes([0,0,3,2])+bytes(4)
    payload=record+struct.pack('<dd',.5,.5);start=128+len(h);total=start+len(payload)
    prefix=bytearray(128);prefix[:8]=b'NPLBIN01';struct.pack_into('<6Q',prefix,8,len(h),1,2,start,start+32,total)
    prefix[56:88]=hashlib.sha256(h).digest();prefix[88:120]=hashlib.sha256(payload).digest()
    model.write_bytes(prefix+h+payload)
    return dict(file=v.MODELS[seed]['file'],bytes=total,sha256=v.sha(model),metadata=metadata)


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.seed=next(iter(v.MODELS));self.source=self.root/'source.bin';pin=fixture(self.source,self.seed)
        tables=self.root/'tables';tables.mkdir();cards={}
        for name in v.CARD_TABLES:
            (tables/name).write_bytes(name.encode());cards[name]=dict(bytes=len(name),sha256=v.sha(tables/name))
        self.tables=tables
        patches=[patch.dict(v.MODELS,{self.seed:pin}),patch.object(v,'PART_BYTES',256),
            patch.dict(v.CARD_TABLES,cards,clear=True),patch.object(builder,'CARD_TABLES',v.CARD_TABLES),
            patch.object(builder,'checked_source',return_value=Path(__file__).resolve().parents[1])]
        for p in patches:p.start();self.addCleanup(p.stop)
        self.bundle=self.root/'bundle'
        builder.build(self.seed,self.source,tables,self.bundle,'a'*40)

    def rewrite_sums(self):
        name,sums=v.names(self.seed);m=json.loads((self.bundle/name).read_text())
        rows={p['file']:p['sha256'] for p in m['parts']};rows.update({n:p['sha256'] for n,p in {**m['card_tables'],**m['source_assets']}.items()});rows[name]=v.sha(self.bundle/name)
        (self.bundle/sums).write_text(''.join(f'{pin}  {n}\n' for n,pin in sorted(rows.items())))

    def test_exact_reconstruction_and_standalone_integrity(self):
        x=v.verify_bundle(self.bundle,self.seed,'a'*40);self.assertEqual(x['model']['sha256'],v.sha(self.source))
        dst=self.root/'assembled.bin';v.assemble(self.bundle,self.seed,dst)
        self.assertEqual(dst.read_bytes(),self.source.read_bytes());v.assemble(self.bundle,self.seed,dst)
        self.assertFalse(dst.with_name(dst.name+'.assembling').exists())

    def test_shipped_verifier_has_no_runtime_dependencies(self):
        done = subprocess.run([sys.executable, '-I', '-S', str(self.bundle/v.VERIFIER), '--help'],
                              check=True, text=True, capture_output=True)
        self.assertIn('--require-publication', done.stdout)

    def test_missing_part_and_changed_evidence_refuse(self):
        first = self.bundle/v.layout(self.seed)[0]['file']
        first.unlink()
        with self.assertRaises(ValueError):
            v.verify_bundle(self.bundle, self.seed)
        name, _ = v.names(self.seed)
        m = json.loads((self.bundle/name).read_text())
        m['evidence']['simultaneous_gates_passed'] = 29
        (self.bundle/name).write_text(json.dumps(m))
        with self.assertRaises(ValueError):
            v.read_manifest(self.bundle, self.seed)

    def test_valid_cached_model_does_not_need_parts_but_verifier_does(self):
        dst = self.root/'cached.bin'
        v.assemble(self.bundle, self.seed, dst)
        for part in v.layout(self.seed):
            (self.bundle/part['file']).unlink()
        self.assertEqual(v.assemble(self.bundle, self.seed, dst), dst)
        with self.assertRaises(ValueError):
            v.verify_bundle(self.bundle, self.seed)

    def test_publication_and_source_refusal(self):
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed,'b'*40)
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed,require_publication=True)
        with self.assertRaises(ValueError):launcher.table_arguments(self.bundle,self.seed,self.root/'cache')
        name,_=v.names(self.seed);m=json.loads((self.bundle/name).read_text());m['publication_approved']=True;(self.bundle/name).write_text(json.dumps(m));self.rewrite_sums()
        self.assertTrue(v.verify_bundle(self.bundle,self.seed,require_publication=True)['publication_approved'])

    def test_rehashed_corruption_cannot_replace_pinned_whole_model(self):
        name,_=v.names(self.seed);m=json.loads((self.bundle/name).read_text());p=self.bundle/m['parts'][-1]['file']
        data=bytearray(p.read_bytes());data[-1]^=1;p.write_bytes(data);m['parts'][-1]['sha256']=v.sha(p)
        (self.bundle/name).write_text(json.dumps(m));self.rewrite_sums()
        with self.assertRaisesRegex(ValueError,'pinned model'):v.verify_bundle(self.bundle,self.seed)
        dst=self.root/'partial.bin'
        with self.assertRaises(ValueError):v.assemble(self.bundle,self.seed,dst)
        self.assertFalse(dst.exists());self.assertTrue(dst.with_name(dst.name+'.assembling').exists())
        with self.assertRaises(FileExistsError):v.assemble(self.bundle,self.seed,dst)

    def test_missing_swapped_parts_and_traversal(self):
        name,_=v.names(self.seed);m=json.loads((self.bundle/name).read_text());m['parts'][0]['file']='../source.bin';(self.bundle/name).write_text(json.dumps(m))
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed)
        m['parts'][0]=v.layout(self.seed)[0]|dict(sha256='a'*64);m['parts'].reverse();(self.bundle/name).write_text(json.dumps(m))
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed)

    def test_truncation_symlinks_and_foreign_existing_output(self):
        first=self.bundle/v.layout(self.seed)[0]['file'];data=first.read_bytes();first.write_bytes(data[:-1])
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed)
        first.unlink();first.symlink_to(self.source)
        with self.assertRaises(ValueError):v.verify_bundle(self.bundle,self.seed)
        output=self.root/'foreign';output.write_bytes(b'keep')
        with self.assertRaises(ValueError):v.assemble(self.bundle,self.seed,output)
        self.assertEqual(output.read_bytes(),b'keep')

    def test_launcher_is_fixed_three_seat_100bb_and_shares_weights(self):
        args=launcher.table_arguments(self.bundle,self.seed,self.root/'cache',allow_prepared=True)
        self.assertEqual(args[:2],['--stack-bb','100']);self.assertEqual(args.count('--policy'),1)
        seats=[args[i+1] for i,x in enumerate(args) if x=='--seat'];self.assertEqual(len(seats),3);self.assertEqual(seats[0],'human');self.assertEqual(seats[1],seats[2])
        watch=launcher.table_arguments(self.bundle,self.seed,self.root/'cache',allow_prepared=True,watch=True)
        seats=[watch[i+1] for i,x in enumerate(watch) if x=='--seat'];self.assertEqual(len(set(seats)),1)

    def test_overwrite_and_header_dtype_refusal(self):
        with self.assertRaises(FileExistsError):builder.build(self.seed,self.source,self.tables,self.bundle,'a'*40)
        bad=deepcopy(v.MODELS[self.seed]['metadata']);bad['dtype']='float32';header=json.dumps(bad).encode();prefix=bytearray(self.source.read_bytes()[:128]);struct.pack_into('<Q',prefix,8,len(header));prefix[56:88]=hashlib.sha256(header).digest()
        with self.assertRaises(ValueError):v.check_header(prefix,header,self.seed)


if __name__=='__main__':unittest.main()
