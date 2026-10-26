# Why live-order keys lose value against check-call: preflop ranges

This is a descriptive diagnosis of #431's −110.7 BB/100 check-call harm flag, on #431's saved traces. It used no new deals. `scripts/nplayer_preflop_ranges.py` reconstructs each focal hand's hole cards and classifies the bot's first preflop action by hand strength, using the scripted bots' preflop card score (pairs from 0.61; AKs 0.655). Results are realized, not all-in adjusted ([data](check-call-preflop-ranges.json)).

Against check-call every opponent only checks or calls, so the focal bot always acts in an unraised pot.

**First preflop action by strength tier, check-call field** (share of that tier's hands; contribution to the field's BB/100):

| Tier | Control: raise / call / fold | Live-order: raise / call / fold | Tier contribution, control → live-order |
|---|---|---|---|
| Weak (score < 0.30) | 19.4% / 4.9% / 69.0% | **25.0%** / 4.7% / 64.3% | −114.2 → **−164.8** |
| Medium (0.30–0.45) | 28.0% / 8.8% / 56.9% | 24.3% / 9.4% / 59.9% | −7.1 → −9.3 |
| Good (0.45–0.60) | 51.0% / 19.7% / 23.3% | 40.6% / 14.0% / **40.4%** | +173.2 → **+129.2** |
| Strong (≥ 0.60) | 54.9% / 24.9% / 13.9% | 54.9% / 23.4% / 15.9% | +238.4 → +232.7 |

The remaining shares are checks from the big blind.

- **Raising weak hands costs most.** The live-order bot raises 5.6 points more of its weak hands. Against five players who call everything, those raises lose 14.2 BB each, against 11.6 for the control's. The weak tier drops by −50.6 BB/100.
- **Folding good hands gives up value.** It folds 17 points more of its good hands instead of raising or calling, so the good tier drops by −44.0.
- **Strong hands play the same.**
- **Together, weak and good hands account for about −95** of the field's −110.7.

**The trained field shows the second trait as well, but not the first.** There the live-order bot folds more good hands too (28.2% → 41.3%), while weak-hand raising barely moves (2.2% → 3.0%). Strong hands raise more (54.3% → 59.6%) and earn more (+72.1 → +111.7). So the extra folding of good hands is a general trait of the new policy. Self-play rewards it, and a field that never folds punishes it.

**Reading:**
- The −111 is mostly preflop range, not the untrained multiway postflop play shared by both arms.
- **Weak-hand raises:** live-order keys merge spots into one row. A raise into five limpers then shares that row with raises that win pots in self-play, so it carries the steal frequency that self-play rewards. That's a hypothesis.
- **The fix:** training has to visit such pots, for example against calling opponents. Coarser keys alone won't change this.
