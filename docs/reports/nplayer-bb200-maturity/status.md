# PR402: training complete, planned post-processing running

[Protocol and transparent controller correction](../../nplayer-bb200-maturity.md),
[launch receipts](launch.json), [training/correction/source/resources](training-and-correction.json).

Training successfully reaches **1,000,008,098 nodes**, retaining **250,002,537 entries**.
It exits0:467.20sprocesswall,114.80sactive traversal,129.26ssave,
223.13sload/hash/other. Added499,980,671nodes imply4.355Mnodes/s.
CheckpointSHA256`55d89c553ba1756eac1af117847b30e8b18e4f901afba942ee5a906bc00249ad`,8,788,049,377bytes.
Peak20.73GiBsampledRSS,CPU73/Thermistor15 84°C, zeroobservedswapgrowth.

The new controller incorrectly required exactly250Mentries and stopped before
export. Existing native semantics merge one whole iteration before freezing at
>=250M; the checkpoint reader accepts that overshoot.2,537extraentries are0.001015%
of the threshold. Freezeiteration38,253 is bracketed by telemetry at959.895M and
962.122Mnodes; all19later frozen samples retain exactly the same entrycount.
Finaldiscardedkeys6,536,832/discardedvisits2,560,884 are censored update counts,
not distinct unreached states or held-out fallback frequency.

**No training retry.** Originalcontrollerfailure/source/status/costs/checkpoint
remain under `main-v1`. Correctionsource`a6ff4cce162c1a5a04322475cce11177f7131215`
adds native-consistent validation and13passingfocusedtests, including exact
overshoot and invalidfreeze cases. A one-use completion-only command consumes
that exact successful checkpoint and pins the oldconfig/error/nativeinputs.
It cannot invoke training and refuses any prior export/audit/coverage attempt.

At18:35:32UTC /20:35:32Madrid, supervisor842477 is running **final-1b-export** in
fresh `/home/dberweger/nplayer-bb200-maturity-20261022/completion-v1`;
CPU51/Thermistor15 49°C, no newfailure. Originalsave/export/full-rowaudit/four
128-block descriptivecoverage/replay/reproduction scope stays unchanged.
Forecast15–25minremaining, conditional on measured costs; no elapsedkill.

Finalcoverage/capacityjudgment and completeworkflowcosts remain pending. No
strengthreadout/furthercostpilot/fulltraining/seeds/search/default/release/merge.
Alloriginals/protectedinputs retained. Archivepending; no copy/upload/deletion.
A passive completionobserver waits for this exactpostprocessPID; no newtimer.
