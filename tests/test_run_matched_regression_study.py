from scripts import run_matched_regression_study as study
from scripts.nplayer_bb100_confirmation import matrix


def test_configuration_freezes_both_fresh_lineages_and_original_trace_roots(tmp_path):
    root=tmp_path/'run';study.configure(root,tmp_path/'cache','source-pin')
    c=study.load(root/'config.json')
    assert c['seeds']==[202610200601,202610200602] and c['heldout_worlds']==512 and c['discovery_worlds']==32
    assert c['dependency_source']=='c06fc565'
    for i,seed in enumerate(c['seeds']):
        assert set(c['models'][str(seed)])=={'baseline','candidate'}
        for t in c['traces'][str(seed)]:
            expected=next(r for r in matrix(i) if r['name']==t['field']+'-'+t['reached'])
            assert t['root']==expected['root'] and len(t['sha256'])==64
    assert not (root/'launch.json').exists()
