# Public results: WRRA Jimothy 0.1 → 0.2

**The unchanged 0.2 strategy won four consecutive public games against hosted 0xtopus: 139–4, 105–21, 86–10, and 114–24.** The initial 0.1 loss is retained. Both policies were published on GitHub and Zenodo before their corresponding match started, and neither was altered during play.

| Public match | WRRA (blue) | 0xtopus (red) | Result |
|---|---:|---:|---|
| 0.1, b86b363c-64cb-4c45-b845-c607d9900a34 | 42 | 58 | Loss |
| 0.2 attempt 0, e48b5ac6-ea0a-429d-9993-a72c066193b9 | 139 | 4 | Win |
| 0.2 series game 1, f2420a19-ce49-4aec-a92a-9cf1059176ae | 105 | 21 | Win |
| 0.2 series game 2, 52426a8d-7764-4e98-a352-808173364901 | 86 | 10 | Win |
| 0.2 series game 3, 09ba4903-0b99-403b-950e-3aa2a000bb9b | 114 | 24 | Win |

Total observed public results: **four wins, one loss**; version 0.2 has **four wins from four completed games** against this hosted opponent. The first rematch stopped after its win; attempt indices 1 and 2 were not played. The user then requested a separate, fixed-length three-game series; all three games were completed without policy changes. Its attempt indices were 3, 4 and 5, with seeds `2026100520 + 1000*attempt + round`. This does not establish a win rate or isolate the contribution of WRRA from more compute, changed opponent scenarios, random initial interaction, and a different match.

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

## Fixed-length three-game series

# WRRA Jimothy 0.2 — Three consecutive public games

2026-10-05 KST. Author: Wonsik Choi. ORCID: 0009-0001-4263-9772.

Frozen strategy DOI: https://doi.org/10.5281/zenodo.23148756
Opponent: 0xtopus. Classic 24×24, seven rounds, eight generations per round. Three games played consecutively without strategy changes or stopping after a win. RNG attempt indices 3, 4, 5; seed = 2026100520 + 1000*attempt + round.

| Game | WRRA blue | Opponent red | Result | Public transcript |
|---|---:|---:|---|---|
| 1 | 105 | 21 | Win | https://k8r.food/jimothyislife/api/matches/f2420a19-ce49-4aec-a92a-9cf1059176ae/transcript |
| 2 | 86 | 10 | Win | https://k8r.food/jimothyislife/api/matches/52426a8d-7764-4e98-a352-808173364901/transcript |
| 3 | 114 | 24 | Win | https://k8r.food/jimothyislife/api/matches/09ba4903-0b99-403b-950e-3aa2a000bb9b/transcript |

Series: 3 wins, 0 losses. Combined final populations: 305 vs 55. Mean final margin: 83.3333 cells. All 42 actions, 42 commitments, 168 generations, 21 policy reproductions, and 21 continuity checks passed.

Including earlier games: WRRA 0.2 has four wins from four hosted games against this opponent. All versions combined: four wins and one loss. These are observed results against one hosted opponent, not a universal win-rate estimate.

Verification input → WRRA transformation → output → falsification:
Input: public boards, legal seed budgets, frozen policy and declared seeds. Transformation: adversarial scenario search, repair mutations, current/future survival scoring. Output: 105:21, 86:10, 114:24. Falsification: illegal actions, failed commitment hashes, scalar replay differences, or frozen-policy reproduction failures; none observed.

Reproduce: extract ZIP, install numpy, and run python series-20261005-game-1/verify.py 3; python series-20261005-game-2/verify.py 4; python series-20261005-game-3/verify.py 5.

Copyright (C) 2026 Wonsik Choi. CC BY 4.0 for original code and report; attribute author, DOI, and source. Preserve game/operator and Conway credits.


[Three-game reproducibility archive](series-20261005/WRRA_Jimothy_Three_Games_2026-10-05.zip). All five games together passed 70 legal-action checks, 70 commitment proofs, 280 generation transitions, 35 policy reproductions and 35 continuity checks.
