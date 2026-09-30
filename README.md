# WRRA Game 1.0

## Minimal Sufficient State, Exhaustive Validation, and a Playable Go Engine

**Wonsik Choi** · Independent Researcher · [janefather@gmail.com](mailto:janefather@gmail.com)  
Version 1.0 · 17 September 2026

[English report (PDF)](paper/WRRA_Game_1.0_Minimal_Sufficient_State_and_a_Playable_Go_Engine_Wonsik_Choi_2026-09-17.pdf) · [English report (DOCX)](paper/WRRA_Game_1.0_Minimal_Sufficient_State_and_a_Playable_Go_Engine_Wonsik_Choi_2026-09-17.docx) · [한국어 안내](README_KR.md)

WRRA Game 1.0 connects constructive game analysis, exhaustive finite-state validation, and an executable Go agent under one unchanged WRRA Core 1.0 contract. It is not only a conceptual mapping: the release contains runnable Python code, complete machine-readable ledgers, deterministic rule tests, controlled matches, and an SGF self-play record.

## Main results

| Study | Executed scope | Result |
|---|---:|---:|
| 4×4 Connect K, three in a row | 6,036,001 reachable states; 23,453,344 legal directed edges | 0 minimax-value mismatches under the certified Renderer reduction |
| Empty-board alpha-beta | Same exact root value | 245,560 → 15,686 → 32 visited nodes |
| 3×3 simple-ko Go | 132,161 complete states; 420,710 legal directed edges | 752 visible-state classes whose legal actions depend on residue |
| Deterministic engine tests | Capture, suicide, ko, pass termination, scoring, coordinates, and witness replay | 10/10 PASS |
| 5×5 paired-colour control | WRRA MCTS vs equal-budget uniform MCTS | 15/16 wins (93.75%) |
| 5×5 paired-colour control | WRRA MCTS vs random legal play | 16/16 wins |
| 9×9 self-play | 24 simulations per move | 82 moves; two-pass ending; White by 8.5 |

The controlled matches establish executable action selection under the stated rules and budgets. They are not presented as a professional Go-strength claim.

## What is new in the combined result

1. **Minimal sufficient state is tested, not assumed.** Histories that collapse to the same visible Go board are grouped and compared. The exhaustive search identifies 752 classes in which changing only the reachable previous-board residue changes the legal-action set.
2. **Reduction carries a finite proof obligation.** The Connect-K Renderer gate is compared with baseline minimax at every reachable state. Zero mismatches show that this specific reduction preserves value on the specified finite system.
3. **Correctness and computational efficiency are separated.** Removing residue changes legality. Removing Renderer guidance can leave the exact value unchanged while increasing search cost.
4. **Exact validation scales into bounded action.** The verified transition rules are reused in a playable 9×9 engine rather than replaced by an unrelated implementation.
5. **Decisions remain inspectable.** Eleven explicit Renderer channels, fixed weights, visits, mean values, priors, and phenotypes are stored for each selected move.

## Exact terminology

Residue does **not** predict or preserve the future. It includes current constraint information that the visible board does not contain but the selected law requires for exact legality and state update.

Search does **not** observe a pre-existing future. It generates and compares successor states permitted by the current rules.

## Quick start

Python 3.11 or newer is recommended.

```bash
python -m pip install -r requirements.txt
python src/wrra_go_0_1.py test
python src/wrra_go_0_1.py play --size 9 --human B
```

Reproduce the paired control and self-play ledgers:

```bash
python src/wrra_go_0_1.py benchmark \
  --size 5 --paired-games 8 --simulations 48 \
  --komi 2.5 --seed 20260917 \
  --output data/reproduced_benchmark.json

python src/wrra_go_0_1.py selfplay \
  --size 9 --simulations 24 --komi 5.5 \
  --seed 20260917 \
  --output data/reproduced_selfplay_9x9.json
```

The exhaustive Game 0.2 run is computationally heavier:

```bash
python src/wrra_game_0_2.py \
  --output data/reproduced_game_0_2_results.json
```

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the complete procedure and expected values.

## Repository structure

```text
wrra-game-1.0/
├── README.md
├── README_KR.md
├── CITATION.cff
├── LICENSE
├── LICENSE-CODE
├── LICENSE-CONTENT
├── SHA256SUMS.txt
├── REPRODUCIBILITY.md
├── CONTRIBUTING.md
├── requirements.txt
├── paper/              # English and Korean DOCX/PDF reports
├── src/                # Game 0.1, Game 0.2, and WRRA Go 0.1
├── data/               # Published JSON ledgers and SGF record
└── tools/              # Report-generation scripts
```

## Core lineage

WRRA Core 1.0 remains frozen throughout this release.

- **WRRA Core 1.0:** [https://doi.org/10.5281/zenodo.22650956](https://doi.org/10.5281/zenodo.22650956)
- **Game 0.1:** constructive Omok forced-win and Go ko examples
- **Game 0.2:** exhaustive Connect-K value preservation and Go residue sufficiency
- **WRRA Go 0.1:** playable MCTS engine with a transparent Renderer and decision ledger

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). **This game's own Zenodo record:** [10.5281/zenodo.22985378](https://doi.org/10.5281/zenodo.22985378). The WRRA Core DOI above cites a separate foundational work.

## Review questions

Technical review is especially welcome on three independently testable points:

1. Is the complete-state definition sufficient for the implemented rule profile?
2. Is the certified Connect-K reduction lossless under the enumerated transition system?
3. Which Renderer channels or benchmark controls should be ablated next?

Please use GitHub Issues after publication or contact the author directly at [janefather@gmail.com](mailto:janefather@gmail.com).

## License

This release uses a scope-based dual license:

- Source code in `src/` and `tools/` is licensed under the **MIT License**.
- Reports, documentation, figures, machine-readable data, and the SGF record are licensed under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**.

See [`LICENSE`](LICENSE), [`LICENSE-CODE`](LICENSE-CODE), and [`LICENSE-CONTENT`](LICENSE-CONTENT) for the exact scope and terms.

---

## Central corpus index

This work is part of the open research and publishing corpus of **Wonsik Choi (최원식)**.

- [Central Research & Publications Index](https://github.com/Wonsik-Choi-janefather/minimal-computing-cosmology-research-history/blob/main/PUBLICATIONS.md)
- [Public GitBook index](https://independent-research.gitbook.io/mcc-and-wrra-research-history/publications)
- [Machine-readable corpus index](https://github.com/Wonsik-Choi-janefather/minimal-computing-cosmology-research-history/blob/main/works.json)
- Identity: [janefather@gmail.com](mailto:janefather@gmail.com)

Rights remain those stated in this repository and its linked archival record.

**Copyright (C) 2026 Wonsik Choi**


**ORCID:** [0009-0001-4263-9772](https://orcid.org/0009-0001-4263-9772)
