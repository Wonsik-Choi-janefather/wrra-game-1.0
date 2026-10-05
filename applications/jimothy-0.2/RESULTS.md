# Public results: WRRA Jimothy 0.1 → 0.2

**The revised strategy won its first rematch 139–4 against hosted 0xtopus.** The initial 0.1 loss is retained. Both policies were published on GitHub and Zenodo before their corresponding match started, and neither was altered during play.

| Public match | WRRA (blue) | 0xtopus (red) | Result |
|---|---:|---:|---|
| 0.1, b86b363c-64cb-4c45-b845-c607d9900a34 | 42 | 58 | Loss |
| 0.2 attempt 0, e48b5ac6-ea0a-429d-9993-a72c066193b9 | 139 | 4 | Win |

Total observed public results: **one win, one loss**. Only one 0.2 match was needed, so the predeclared stopping rule ended the run; attempt indices 1 and 2 were not played. This does not establish a win rate or isolate the contribution of WRRA from more compute, changed opponent scenarios, random initial interaction, and a different match.

## Winning game by round

| Round | WRRA | 0xtopus |
|---|---:|---:|
|1|19|16|
|2|32|11|
|3|62|3|
|4|67|5|
|5|97|16|
|6|137|10|
|7|139|4|

The server reports winner `wrraresearchledger` and completion reason `played`, not a forfeit. Final state hash: `87fd2bee53f0122eecfb0fe3e0117929fd877e7759a8361f6e8d1379b5a58611`.

## What was verified

For **each** public game, all 14 legal actions, 14 SHA-256 commit/reveal proofs, 56 generation transitions, 7 exact policy reproductions, and 7 board-continuity checks passed. The independently written scalar oracle agrees with the optimized engine and every final server round board. The revised action seeds were `2026100520 + round`, exactly as published for attempt 0. No actual red reveal was used when choosing a blue action.

## Why the revision is useful

Instead of treating the opponent as random, 0.2 searches hypothetical attacks and repairs, rechecks promising blue moves against a counter-response, and checks whether colonies survive beyond the first scoring tick. This is a concrete state–law–resource–renderer–action–provenance application of WRRA. The full board still suffices for exact dynamics; history supports auditing and failure diagnosis. The win is evidence that this implementation can complete and win a real hosted game under the stated rules, not proof of universal game strength.

## Evidence and reproduction

- Frozen 0.2 strategy DOI: https://doi.org/10.5281/zenodo.23148756
- Frozen 0.2 GitHub commit: `0646f21f8bbcacbb4a49052534d96148f13e3c6c`
- Frozen 0.1 DOI: https://doi.org/10.5281/zenodo.23148630
- Winning public transcript: https://k8r.food/jimothyislife/api/matches/e48b5ac6-ea0a-429d-9993-a72c066193b9/transcript
- First losing public transcript: https://k8r.food/jimothyislife/api/matches/b86b363c-64cb-4c45-b845-c607d9900a34/transcript
- [Winning verification ledger](live-results-0/verification.json)
- [Winning public record archive](live-results-0/PublicMatchRecord.zip)
- [First loss record](../jimothy-0.1/live-results/README.md)

Unzip the winning archive and run `python live-results-0/verify.py 0` with NumPy 2.3.5. Its root contains the exact published strategy and rule-engine files. The archive includes final server state, normalized public transcript, pre-commit decision ledgers, and audit code. Tokens and private unrevealed values are excluded.

Wonsik Choi · ORCID https://orcid.org/0009-0001-4263-9772 · Copyright (C) 2026 Wonsik Choi. Original report/code CC BY 4.0. Attribute the author, DOI and source; preserve game/operator and Conway credits. Results recorded 5 October 2026.
