# Contributing and technical review

Independent reproduction, counterexamples, and narrowly scoped corrections are welcome.

Useful review targets include:

1. **State sufficiency:** provide two reachable histories that the implementation maps to one complete state but that have different legal actions or incompatible next-state updates.
2. **Certified reduction:** provide a reachable 4×4 Connect-K state for which baseline minimax and the certified Renderer gate return different values.
3. **Transition correctness:** provide a deterministic capture, suicide, ko, pass, or scoring case that disagrees with the stated rule profile.
4. **Renderer ablation:** compare action selection with one or more explicit channels removed while preserving the same rules, colours, seeds, and computation budget.
5. **External engine evaluation:** add reproducible GTP matches with documented board size, rule profile, time or simulation budget, seeds, colours, and confidence intervals.

Please include:

- the exact command used;
- Python and operating-system versions;
- the smallest reproducible state or game record;
- expected and observed results;
- machine-readable output when available.

Conceptual objections are most useful when tied to a state definition, transition, finite counterexample, or executable test.
