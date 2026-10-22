import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.river_arena_expectation import expectation_parity, trace_prefix, value_signature


class ArenaExpectationTests(unittest.TestCase):
    def data(self):
        roots=[{'id':'trained/0000/0001','hand':0},{'id':'trained/0030/0001','hand':30}]
        arm={'complete':True,'expected_chips':4.,'visited':3,'terminals':2,'policy_rows':{'blueprint':1},'seconds':.1}
        value={'id':roots[0]['id'],'method':'full-positive-support-enumeration','complete_contrast':True,
               'contrast_chips':-3.,'profile_sha256':'fixture','on':{**arm,'expected_chips':1.},'off':arm,
               'solver_advances':0,'profile_reconstructions':0,'total_seconds':.2}
        oracle={r['id']:{**copy.deepcopy(value),'id':r['id']} for r in roots}
        return roots,oracle,[value]

    def test_every_eligible_root_and_adverse_value_is_retained(self):
        roots,oracle,rows=self.data()
        proof=expectation_parity(roots,oracle,rows,4)
        self.assertEqual(proof['roots'],1)
        self.assertTrue(proof['no_exclusions'])
        with self.assertRaises(ValueError):expectation_parity(roots,oracle,[],4)
        with self.assertRaises(ValueError):expectation_parity(roots,oracle,rows*2,4)
        with self.assertRaises(ValueError):expectation_parity(roots,oracle,rows,128)

    def test_float64_profile_partial_values_and_duplicate_work_are_rejected(self):
        roots,oracle,rows=self.data()
        for key,value in [('contrast_chips',-3.000000000000001),('profile_sha256','changed'),
                          ('complete_contrast',False),('solver_advances',1),('profile_reconstructions',1)]:
            bad=copy.deepcopy(rows);bad[0][key]=value
            with self.assertRaises(ValueError):expectation_parity(roots,oracle,bad,4)
        zero=copy.deepcopy(rows[0]);zero['contrast_chips']=0.
        other=copy.deepcopy(zero);other['contrast_chips']=-0.
        self.assertNotEqual(value_signature(zero),value_signature(other))
        timing=copy.deepcopy(rows[0]);timing['on']['seconds']=50.
        self.assertEqual(value_signature(rows[0]),value_signature(timing))

    def test_original_hand_bytes_and_header_identity_must_stay_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'new',Path(tmp)/'old'
            h={'blocks':1,'hands':6,'seed':123,'policies':['frozen']}
            lines=[json.dumps({'hand':i,'draw':.25,'actions':['check']})+'\n' for i in range(6)]
            a.write_text(json.dumps(h)+'\n'+''.join(lines))
            b.write_text(json.dumps({**h,'blocks':128,'hands':768})+'\n'+''.join(lines))
            self.assertEqual(trace_prefix(a,b,1),6)
            a.write_text(json.dumps({**h,'seed':124})+'\n'+''.join(lines))
            with self.assertRaises(ValueError):trace_prefix(a,b,1)
            a.write_text(json.dumps(h)+'\n'+''.join(lines).replace('check','raise',1))
            with self.assertRaises(ValueError):trace_prefix(a,b,1)


if __name__=='__main__':unittest.main()
