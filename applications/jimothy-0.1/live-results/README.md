# First public match: WRRA Jimothy 0.1 vs 0xtopus

**Completed legally; WRRA lost 42–58.** Match b86b363c-64cb-4c45-b845-c607d9900a34, 5 October 2026.

The policy was published before joining: https://doi.org/10.5281/zenodo.23148630; GitHub strategy commit 17083ea1d146966458507fec77d570f6bd3e54b8. It was not changed during play.

| Round | WRRA (blue) | 0xtopus (red) |
|---|---:|---:|
| 1 |45|46|
| 2 |52|53|
| 3 |33|52|
| 4 |43|55|
| 5 |15|59|
| 6 |30|47|
| 7 |42|58|

Replay checks passed: 14 legal actions, 14 SHA-256 commitments, 56 generation transitions, 7 exact blue-policy reproductions, and 7 board-continuity checks. The scalar oracle and vector engine agree with all server round outcomes. Winner is 0xtopus; completion reason is played, not timeout.

The local 12/12 wins against simple synthetic opponents did not transfer to this stronger hosted opponent. Actual final margins in several rounds fell below every hypothetical scenario used by the policy. The candidate library, opponent scenario coverage, and short horizon need improvement. The failure is retained as evidence; it is not omitted or relabeled as a win.

Public transcript: https://k8r.food/jimothyislife/api/matches/b86b363c-64cb-4c45-b845-c607d9900a34/transcript

Download PublicMatchRecord.zip for final server state, transcript, seven pre-commit decision ledgers, verification.json and verify.py. To reproduce the audit, unzip its live-results directory next to the original strategy.py and run python live-results/verify.py.

Wonsik Choi · ORCID https://orcid.org/0009-0001-4263-9772 · Copyright (C) 2026 Wonsik Choi. Original report/code CC BY 4.0; preserve game/operator credits.
