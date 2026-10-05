# WRRA Jimothy 0.2

## Adversarial Repair Search and Multi-Horizon Survival

Wonsik Choi · Independent Researcher · ORCID https://orcid.org/0009-0001-4263-9772

Copyright (C) 2026 Wonsik Choi · 0.2.0 · 5 October 2026.

Release DOI: https://doi.org/10.5281/zenodo.23148756

## Why this version exists

The first public 0.1 match against hosted **0xtopus** ended **WRRA 42, 0xtopus 58**. All 14 actions and commitments, 56 automaton generations, and seven frozen-policy reproductions passed. The game engine was correct; the strategy's scenario coverage and short planning horizon were insufficient for this opponent. The 0.1 pre-match release remains intact at https://doi.org/10.5281/zenodo.23148630. The loss and complete public record are retained with this release.

## What changed

1. Search candidate red repair/attack placements rather than assume only random and isolated-pattern opponents. A 448-candidate red search proposes four strong and partially diverse scenarios.
2. Add pattern, uniform, and no-new-red stress scenarios. The last is a deliberately hypothetical counterfactual, not a legal six-seed opponent turn. It stops our action depending on the opponent damaging its own surviving colony.
3. Search 256 blue candidates, then three 128-candidate elite mutation stages. Mutations can repair existing structures, perturb enemy neighborhoods, or seed new patterns.
4. After the first blue stage, run a second 448-candidate red search against that provisional blue move. Add four adversarial responses and re-evaluate all retained blue elites. These are internally generated hypothetical opponent actions, never actual red reveals.
5. Evaluate both this round's scoring tick and one additional eight-generation interval with no future reinforcements. This is a heuristic persistence test, not a solved multi-round game. The final round uses only its actual scoring horizon.

For each action, utility is:

`0.45 mean current margin + 0.25 worst current margin + 0.20 mean future margin + 0.10 worst future margin`.

Margin is blue live cells minus red live cells. Ties use stable candidate order. The first stage has 7 scenarios; subsequent stages have 11. Total blue rollouts: 6,016 per move. Both red searches together evaluate 896 candidates. The final selected cells, resource budget, state digest, scenario margins and utility are recorded before commit.

The optimized two-player transition engine was compared with the original all-color engine and an independently written scalar oracle on 50 randomized boards: all passed. It supports only dead/red/blue/neutral boards. The live client asserts the Classic 24×24, seven-round format.

## Retrospective diagnosis, not a new game

The final policy was run separately on each of the seven positions from the 0.1 loss. Recorded red moves were introduced only after selecting each replacement blue action. Five of seven final margins improved; summed per-position margins changed from −110 to −43. These are seven counterfactual positions on the old trajectory, not a coherent 0.2 match. The algorithm was developed after viewing this match, and uses more compute; this is neither held-out validation nor an equal-budget performance comparison. Full action ledgers are in diagnostic.json.

| Old position / round | 0.1 blue:red | 0.2 counterfactual blue:red |
|---|---:|---:|
|1|45:46|31:46|
|2|52:53|56:37|
|3|33:52|35:40|
|4|43:55|37:27|
|5|15:59|37:51|
|6|30:47|26:57|
|7|42:58|32:39|

## Frozen live protocol

Publish this release before joining a fresh unreserved hosted 0xtopus match. Do not alter the policy during play. Attempt indices 0, 1, and 2 use RNG seed `2026100520 + 1000 * attempt + round`. Up to three fresh matches may be played, stopping after a win; every completed result, including losses, must be retained and reported. This stopping rule does not estimate a long-run win rate. Tokens and unrevealed nonces stay private.

```bash
python -m pip install -r requirements.txt
python strategy.py test
python strategy.py diagnostic --first-match first-match/final.json --output reproduced-diagnostic.json
python live_client.py --private /private/location/v02-match0.json --attempt 0 --output live-results-0
```

## WRRA continuity and attribution

The same state–law–resource–renderer–action–provenance contract is used. Current board suffices for exact automaton evolution. Historical residue now includes the first failure and its measured forecast errors, motivating a wider, adversarial renderer; it does not change Conway's law. WRRA provides a shared executable tool for humans and AI to inspect the world.

WRRA Core 1.0: https://doi.org/10.5281/zenodo.22650956. WRRA Game 1.0: https://doi.org/10.5281/zenodo.22985378. Game/protocol by its operator: https://k8r.food/jimothyislife/agent-api.md. Original implementation and report are CC BY 4.0. Cite Wonsik Choi, this release DOI, and the GitHub source; preserve third-party credits. AI assisted implementation and documentation under the author's research direction.

Source: https://github.com/Wonsik-Choi-janefather/wrra-game-1.0/tree/main/applications/jimothy-0.2
