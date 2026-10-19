import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.nplayer_overnight import BOTS, SEEDS, Supervisor, cases, guard, preserve
from scripts.overnight_tensorboard import Scalars, crc32c, masked_crc


class OvernightTests(unittest.TestCase):
    def test_swap_is_telemetry_while_available_ram_still_stops(self):
        gib=1024**3
        initial=dict(SwapTotal=2*gib,SwapFree=2*gib-200*1024**2,MemAvailable=50*gib)
        used=dict(initial,SwapFree=initial['SwapFree']-gib)
        low_ram=dict(used,MemAvailable=7*gib)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';cache=Path(tmp)/'cache';root.mkdir();cache.mkdir()
            with patch.object(guard,'memory',side_effect=[initial,used,low_ram]), \
                 patch.object(guard,'sensors',return_value={'Package id 0':60,'Thermistor 15':70}), \
                 patch.object(guard,'fan_rpm',return_value=1000), \
                 patch.object(guard.os,'statvfs',return_value=SimpleNamespace(f_bavail=1000*gib,f_frsize=1)), \
                 patch.object(guard,'BUDGET',guard.BUDGET),patch.object(guard,'FLOOR',guard.FLOOR):
                logs=Mock();s=Supervisor(root,cache,0,3600,logs)
                self.assertIsNone(s.swap_limit_bytes)
                sample=s.sample(None,'train',20_000_000_000)
                self.assertEqual(sample['swap_growth_bytes'],gib)
                self.assertEqual(sample['swap_used_bytes'],gib+200*1024**2)
                logs.add.assert_any_call('resources/swap_used_bytes',sample['swap_used_bytes'],unittest.mock.ANY)
                with self.assertRaisesRegex(RuntimeError,'memory stop'):
                    s.sample(None,'train',20_000_000_000)

    def test_frozen_matrix_and_independent_roots(self):
        matrix=cases()
        self.assertEqual(len(matrix),36)
        self.assertEqual(sum(c['blocks']*6 for c in matrix),1769472)
        self.assertEqual(len({c['name'] for c in matrix}),36)
        self.assertEqual(len({c['root'] for c in matrix}),18)
        self.assertTrue({c['root'] for c in matrix}.isdisjoint(c['root'] for c in cases(True)))
        self.assertEqual({c['seed'] for c in matrix},set(SEEDS))
        for left,right in zip(matrix[::2],matrix[1::2]):
            self.assertEqual(left['root'],right['root'])
            if left['group']=='bot':
                self.assertEqual(left['pair'],right['pair'])
                self.assertIn(left['bot'],BOTS)
            else:self.assertEqual((left['singleton'],left['pair']),(right['pair'],right['singleton']))

    def test_tensorboard_records_have_castagnoli_checksums(self):
        self.assertEqual(crc32c(b'123456789'),0xe3069283)
        with tempfile.TemporaryDirectory() as root:
            writer=Scalars(Path(root)/'events');writer.add('nodes',123,123);writer.close()
            data=writer.path.read_bytes();records=[]
            while data:
                size=data[:8];length=struct.unpack('<Q',size)[0]
                self.assertEqual(struct.unpack('<I',data[8:12])[0],masked_crc(size))
                value=data[12:12+length]
                self.assertEqual(struct.unpack('<I',data[12+length:16+length])[0],masked_crc(value))
                records.append(value);data=data[16+length:]
            self.assertEqual(len(records),2)
            self.assertIn(b'brain.Event:2',records[0]);self.assertIn(b'nodes',records[1])

    def test_preservation_refuses_changed_destination_and_keeps_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';cache=Path(tmp)/'cache';source.mkdir();cache.mkdir()
            path=source/'checkpoint';path.write_bytes(b'original')
            preserve(source,cache,['checkpoint'])
            self.assertEqual(path.read_bytes(),b'original')
            (cache/'checkpoint').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):preserve(source,cache,['checkpoint'])
            self.assertEqual(path.read_bytes(),b'original')


if __name__=='__main__':unittest.main()
