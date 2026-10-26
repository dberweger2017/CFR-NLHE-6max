"""Operational integration fixture: readout evidence must not collide with logs."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_six_player_counterfactual_m4 as r

class RunnerPathTests(unittest.TestCase):
    def test_stage_logs_are_separate_from_exclusive_readout_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);root=base/'main'
            # Provide local lock parents; the fixture never uses actual host locks.
            local=base/'Local';local.mkdir()
            config=dict(thermal='mock',model=str(base/'model.bin'),tables=str(base),
                        binary='native-fixture',python='python-fixture',inventory='inventory',
                        owner_admission_sha256='a'*64)
            (base/'model.bin').write_bytes(b'model')
            for name in r.TABLES:(base/name).write_bytes(b'table')
            for key in ['mode','belief_root','threads','model_sha256','states','states_sha256',
                        'discovery_worlds','heldout_worlds','owner_admission']:
                config[key]='fixture'
            commands=[]
            def guarded(stage,c,*,phase,command,owner_stop):
                commands.append((phase,stage))
                if phase=='readout':
                    out=Path(command[-1])
                    self.assertEqual(out,root/'readout')
                    self.assertFalse(out.exists())  # The historical collision.
                    out.mkdir(exist_ok=False)
                    (out/'verified.json').write_text(json.dumps(dict(status='passed',roots=36,no_exclusions=True,fixture_only=False)))
                    (out/'results.json').write_text('{}')
                return dict(phase=phase,returncode=0,wall_seconds=.01)
            sensor=dict(available_ram_bytes=10*2**30,disk_free_bytes=20*2**30,thermal_state='nominal')
            with patch.object(r.platform,'system',return_value='Darwin'),patch.object(r.subprocess,'check_output',side_effect=['Apple M4','AC Power']),\
                 patch.object(r.Path,'home',return_value=base),patch.object(r,'validate'),patch.object(r,'sample',return_value=sensor),patch.object(r,'run_guarded',side_effect=guarded):
                r.run(root,config)
            self.assertEqual([x[0] for x in commands],['native-main','readout'])
            self.assertTrue((root/'COMPLETE.json').is_file())
            self.assertTrue((root/'stages/readout/config.json').is_file())

if __name__=='__main__':unittest.main()
