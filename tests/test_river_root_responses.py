from scripts.qualify_river_root_responses import MENUS, jobs, response_type, diagnosis_summary


def test_jobs_alternate_arm_order_and_cover_both_menus():
    work = jobs('projected', range(4))
    assert work[:4] == [(0, MENUS[0]), (0, MENUS[1]), (1, MENUS[1]), (1, MENUS[0])]
    assert {m for _, m in work} == set(MENUS) and len(work) == 8


def test_diagnosis_summary_ranks_only_omitted_responses():
    def response(path, action, label, facing, gain, omitted=True):
        return {'path': path, 'action': action, 'label': label, 'facing_bet': facing,
                'leave_one_out_wc_improvement_bb': gain, 'omitted': omitted}
    row = {'case_index': 7, 'menu': MENUS[1], 'diagnosis': {'result': {'actual': {'responses': [
        response([['raise', 100]], ['raise', 200], 3, True, 2.5),
        response([['check', 0]], ['raise', 100], 3, False, 0.5),
        response([['raise', 100]], ['call', 0], 2, True, 9.0, omitted=False)]}}}}
    out = diagnosis_summary([row])[MENUS[1]]
    assert out['cases'] == 1
    assert out['per_case_top'][0]['leave_one_out_wc_improvement_bb'] == 2.5
    assert out['per_case_top'][0]['type'] == response_type(row['diagnosis']['result']['actual']['responses'][0])
    assert out['ranking'][0]['leave_one_out_wc_improvement_bb'] == 2.5
