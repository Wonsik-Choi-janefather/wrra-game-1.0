# WRRA Jimothy 0.1

## A Budgeted Robust-Trajectory Strategy for Competitive Cellular Automata

Wonsik Choi · Independent Researcher · ORCID [0009-0001-4263-9772](https://orcid.org/0009-0001-4263-9772)

Copyright (C) 2026 Wonsik Choi. Version 0.1.0 · 5 October 2026.

Release DOI: https://doi.org/10.5281/zenodo.23148630

WRRA lets humans and AI examine a world through a common executable tool. Here that tool turns a cellular-automaton position into legal seed placements, possible future trajectories, a score, and an inspectable decision ledger. The practical question is simple: **which limited seeds still belong to us after growth, death, and interference?**

This is a new application of the frozen WRRA Core 1.0 contract, not a modification of Conway's laws and not a claim that a general theory guarantees winning play.

## Playbook

1. Read the complete board, the exact seed budget, and generations for this round.
2. Generate 96 candidate actions: one quarter uniform placements, three quarters assemblies of blocks, blinkers, gliders, five-cell growth seeds, and beehives. Rotation and toroidal translation vary each assembly.
3. Generate four hidden-opponent scenarios: two uniform, two pattern assemblies. They are hypothetical placements generated before committing, never the opponent's actual reveal.
4. Render all 384 candidate–opponent trajectories through the official number of generations. Colliding seeds become neutral; neutral neighbors affect survival but carry no scoring allegiance.
5. Score each candidate by `0.6 * mean terminal margin + 0.4 * worst terminal margin + 0.1 * mean margin across the last three generations`. Margin means blue live cells minus red live cells. Pick the first maximum for deterministic tie-breaking.
6. Validate exact seed count, distinctness, and dead-cell legality. Save the board digest, parameters, candidate index, scenario margins, utility, and chosen cells.
7. Commit SHA-256 of the canonical sorted action and private nonce; reveal that unchanged action. Start again from the new resolved board.

In ordinary language: seed compact structures, simulate their survival, and avoid relying on one favorable guess about the opponent. Reinforcements are evaluated on the actual surviving board rather than added blindly.

## WRRA mapping

| Contract element | Concrete implementation |
|---|---|
| State | Complete toroidal board with allegiance |
| Law | Conway B3/S23 plus the game's ownership and collision rules |
| Resource | Exactly 20 seeds initially and 6 per later Classic round |
| Renderer | Batched explicit successor-board generation |
| Action selection | Robust terminal margin plus late-trajectory persistence |
| Residue / provenance | Prior board digests, action ledgers, resolved rounds, commit/reveal proofs |
| Output | Legal action, survival score, public replay, falsifiable match result |

**Minimal state matters:** the full current board suffices for deterministic automaton evolution. Unlike Go's ko example, historical residue is not required to determine legal cellular-automaton transitions. In v0.1 the prior-round ledger supports audit and replay; it does not secretly add predictive information or adapt the opponent model.

## Frozen experiment before the first public match

Publication must precede joining the hosted opponent. The live policy is fixed at 96 candidates, 4 scenarios, the formula above, and NumPy RNG seed `2026100500 + round`. No tuning based on a revealed opponent move is allowed. Score and winner come from the server's final board, not cumulative populations. Success means completing a legal, reproducible match; winning is an additional empirical outcome.

Classic: 24×24 torus, 7 rounds, 8 generations per round, 20 opening seeds and 6 reinforcements. Always read the server's actual format. The first experiment joins the standing unreserved hosted `0xtopus` match under `wrraresearchledger`.

## Executed local controls

47 checks passed: 40 randomized comparisons against an independently written scalar rule oracle, toroidal edge behavior, 5 allegiance/neutral birth cases, and collision neutrality.

Twelve paired local Classic games per policy were completed against six uniform and six pattern-assembly synthetic opponents. Each policy received exactly 48 candidates × 4 opponent scenarios × 8 generations per move. The ablation changes only action utility to mean terminal margin; both still compute the same trajectories and late margins.

| Policy | Wins / draws / losses | Mean final margin |
|---|---:|---:|
| WRRA robust utility | 12 / 0 / 0 | +88.75 |
| Mean-only utility ablation | 12 / 0 / 0 | +95.00 |

These controls establish executable strong play against these simple local opponents. **They do not show an advantage for the robust utility:** the mean-only ablation had the larger average margin. These were not matches against 0xtopus. Paired seeds match random streams, but legal-move sets and boards diverge across policies, so the realized opponent cells need not be identical. Full per-round ledgers are in `benchmark.json`.

The small sample, simple opponents, fixed candidate library, four-scenario coverage, and absence of long-term reinforcement search limit conclusions. No professional strength, guaranteed win, or superiority over other search algorithms is asserted.

## Reproduce

Python 3.11+ and NumPy 2.3.5 were used.

```bash
python -m pip install -r requirements.txt
python strategy.py test
python strategy.py benchmark --games 12 --output benchmark-reproduced.json
# Only after publication; private credential file MUST stay outside the repository.
python live_client.py --private /private/location/jimothy.json --output live-results
```

The game is hosted and designed by its operator, not by Wonsik Choi. This release includes original strategy code and a fetched public rules snapshot for precise protocol provenance. It does not claim ownership over the game or Conway's Game of Life.

## References and use

- WRRA Core 1.0: https://doi.org/10.5281/zenodo.22650956
- WRRA Game 1.0: https://doi.org/10.5281/zenodo.22985378
- Game rules/API: https://k8r.food/jimothyislife/agent-api.md and https://k8r.food/jimothyislife/api/rules
- Source: https://github.com/Wonsik-Choi-janefather/wrra-game-1.0/tree/main/applications/jimothy-0.1

Original code and documentation: CC BY 4.0. Use, modify, and redistribute with attribution to Wonsik Choi, the release DOI, and the source repository. Preserve third-party credits. AI assisted implementation and documentation under the author's research direction.
