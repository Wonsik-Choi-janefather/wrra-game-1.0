# Reproducibility

This document distinguishes fast deterministic checks, controlled game runs, and the heavier exhaustive enumeration.

## Environment

- Python 3.11 or newer recommended
- `matplotlib==3.10.8` for Game 0.1 figures and report generation
- Game 0.2 and WRRA Go 0.1 otherwise use the Python standard library

```bash
python -m pip install -r requirements.txt
```

## 1. Deterministic rule tests

```bash
python src/wrra_go_0_1.py test \
  --output data/reproduced_rule_tests.json
```

Expected result: 10/10 tests are `true`, including the shortest same-visible-board witness, simple-ko blocking, capture, suicide prohibition, two-pass termination, deterministic area scoring, open-region handling, and coordinate round trip.

## 2. Constructive Game 0.1 cases

```bash
python src/wrra_game_0_1.py \
  --output-dir data/reproduced_game_0_1
```

Expected key values:

- 71 legal Omok candidates
- one multiple-outlet candidate at `(4, 4)`
- four next-turn winning outlets
- 70 defensive replies checked
- zero replies that remove all four outlets
- 18 legal Go actions with residue and 19 without residue

## 3. Exhaustive Game 0.2 run

```bash
python src/wrra_game_0_2.py \
  --output data/reproduced_game_0_2_results.json
```

Expected Connect-K values:

- 6,036,001 reachable states
- 23,453,344 directed legal edges
- zero all-state minimax-value mismatches
- empty-board alpha-beta nodes: 245,560 baseline; 15,686 Renderer order; 32 certified reduction

Expected 3×3 simple-ko Go values:

- 132,161 reachable complete states
- 420,710 directed legal edges
- 72,987 visible-state classes
- 20,538 classes with multiple reachable residues
- 752 classes with residue-dependent legal-action sets
- 768 ko-sensitive complete states

## 4. Paired-colour control

```bash
python src/wrra_go_0_1.py benchmark \
  --size 5 --paired-games 8 --simulations 48 \
  --komi 2.5 --seed 20260917 \
  --output data/reproduced_benchmark.json
```

Published ledger:

- WRRA MCTS vs uniform MCTS: 15 wins, 1 loss
- WRRA MCTS vs random legal play: 16 wins, 0 losses
- Colours alternate within each pair
- The simulation count is identical for WRRA MCTS and uniform MCTS

## 5. 9×9 self-play

```bash
python src/wrra_go_0_1.py selfplay \
  --size 9 --simulations 24 --komi 5.5 \
  --seed 20260917 \
  --output data/reproduced_selfplay_9x9.json
```

Published ledger:

- 82 moves
- termination by two consecutive passes
- Black area 38; White area 41; komi 5.5
- Black margin −8.5; White wins

The JSON ledger includes candidate visits, mean values, priors, Renderer scores, phenotypes, and timing. The matching SGF is stored in `data/wrra_go_0_1_selfplay_9x9.sgf`.

## 6. Human-versus-engine play

```bash
python src/wrra_go_0_1.py play --size 9 --human B
```

Enter coordinates such as `D4` or `pass`. Column `I` is skipped in standard Go notation.

## Interpretation boundary

Residue is current constraint information required for exact legality; it is not a prediction of the future. MCTS generates and evaluates rule-permitted successors; it does not observe a pre-existing future.
