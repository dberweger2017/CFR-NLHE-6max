import json

from scripts import openpoker_audit


def line(kind, payload):
    return json.dumps({'t': 0, 'kind': kind, 'payload': payload})


def test_raises_are_read_against_the_street_the_board_announces(tmp_path):
    """Live labels: the call that closes preflop arrives as `flop`, before the flop cards."""
    act = lambda seat, action, delta, street, amount=None, mode='incremental': line('in', {
        'type': 'player_action', 'seat': seat, 'action': action, 'amount': amount, 'amount_mode': mode,
        'street': street, 'contribution_delta': delta})
    journal = tmp_path / 'journal.jsonl'
    journal.write_text('\n'.join([
        line('in', {'type': 'hand_start', 'hand_id': 'h', 'seat': 0, 'dealer_seat': 0}),
        act(0, 'raise', 60, 'preflop', 60, 'to_total'),   # button opens to 60
        act(1, 'raise', 170, 'preflop', 180, 'to_total'),  # small blind (10 in) 3-bets to 180
        act(2, 'fold', 0, 'preflop'),
        act(0, 'call', 120, 'flop'),                       # closes preflop; labeled with the next street
        line('in', {'type': 'community_cards', 'cards': ['Kd', 'Th', '5d'], 'street': 'flop'}),
        act(1, 'raise', 100, 'flop', 100, 'to_total'),
        act(0, 'raise', 300, 'flop', 300, 'to_total'),
        act(1, 'fold', 0, 'showdown'),
        line('in', {'type': 'hand_result', 'hand_id': 'h', 'final_stacks': {'0': 2000}}),
    ]) + '\n')
    report = openpoker_audit.audit(journal)
    assert report['raise_amount_meaning'] == {'raise-to total': 4}
    assert report['amount_modes'] == {'raise: to_total': 4, 'fold: incremental': 2, 'call: incremental': 1}
    assert report['hands'] == 1
