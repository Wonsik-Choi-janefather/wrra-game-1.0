#!/usr/bin/env python3
"""WRRA-Go 0.1: a playable Go engine built from the WRRA-Game studies.

This program keeps WRRA Core 1.0 frozen and supplies a Go Domain Profile:

* LAW / UPDATE: capture, suicide prohibition, simple ko, pass, two-pass end.
* STATE / RESIDUE: board, side to move, previous board, pass count.
* COMMON CARRIER: the finite orthogonal grid.
* RENDERER: explicit tactical and structural feature channels.
* PHENOTYPE: capture, rescue, atari, connection, cut pressure, extension, pass.
* LEDGER: candidate features, search visits, values, moves, and final score.

The decision shell is Monte Carlo Tree Search (MCTS), an established search
method.  WRRA supplies the sufficient state, legal transition mechanism,
feature renderer, priors, guided playout policy, and reproducible ledger.  The
program evaluates rule-permitted continuations; it does not claim to predict a
pre-existing future or to match specialist neural Go engines.

Author: Wonsik Choi
Contact: janefather@gmail.com
Date: 2026-09-17
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional, Protocol


EMPTY = 0
BLACK = 1
WHITE = -1
PASS = -1
COL_LABELS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def opponent(player: int) -> int:
    return -player


def colour_name(player: int) -> str:
    return "B" if player == BLACK else "W"


@dataclass(frozen=True, slots=True)
class GoState:
    board: tuple[int, ...]
    to_move: int = BLACK
    previous_board: Optional[tuple[int, ...]] = None
    passes: int = 0
    move_number: int = 0


@dataclass(frozen=True, slots=True)
class Transition:
    state: GoState
    action: int
    captured: int
    placed_group_size: int
    liberties: int


@dataclass(frozen=True, slots=True)
class MoveFeatures:
    action: int
    phenotype: str
    capture: int
    rescue: int
    atari: int
    connection: int
    cut_pressure: int
    liberties: int
    self_atari: int
    eye_fill: int
    area_delta: float
    position: float
    pass_readiness: float
    score: float


class GoRules:
    """Finite Go rules with simple ko and Tromp-Taylor-style area scoring."""

    def __init__(self, size: int = 9, komi: float = 5.5, max_moves: Optional[int] = None):
        if size < 2 or size > len(COL_LABELS):
            raise ValueError(f"board size must be between 2 and {len(COL_LABELS)}")
        self.size = size
        self.cells = size * size
        self.komi = float(komi)
        # This is an operational boundary for search and automated matches, not
        # an additional claim about the mathematical rules of Go.
        self.max_moves = max_moves if max_moves is not None else 3 * self.cells
        self.neighbours = tuple(self._make_neighbours(i) for i in range(self.cells))

    def _make_neighbours(self, pos: int) -> tuple[int, ...]:
        row, col = divmod(pos, self.size)
        result = []
        for rr, cc in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if 0 <= rr < self.size and 0 <= cc < self.size:
                result.append(rr * self.size + cc)
        return tuple(result)

    def initial_state(self) -> GoState:
        return GoState((EMPTY,) * self.cells)

    def group_and_liberties(self, board: tuple[int, ...], start: int) -> tuple[frozenset[int], frozenset[int]]:
        colour = board[start]
        if colour == EMPTY:
            return frozenset(), frozenset()
        group = {start}
        liberties: set[int] = set()
        stack = [start]
        while stack:
            pos = stack.pop()
            for nb in self.neighbours[pos]:
                value = board[nb]
                if value == EMPTY:
                    liberties.add(nb)
                elif value == colour and nb not in group:
                    group.add(nb)
                    stack.append(nb)
        return frozenset(group), frozenset(liberties)

    def neighbouring_groups(self, board: tuple[int, ...], action: int, colour: int) -> list[frozenset[int]]:
        groups: list[frozenset[int]] = []
        seen: set[int] = set()
        for nb in self.neighbours[action]:
            if board[nb] != colour or nb in seen:
                continue
            group, _ = self.group_and_liberties(board, nb)
            groups.append(group)
            seen.update(group)
        return groups

    def play(self, state: GoState, action: int, *, ignore_ko: bool = False) -> Optional[Transition]:
        if self.is_terminal(state):
            return None
        if action == PASS:
            nxt = GoState(
                board=state.board,
                to_move=opponent(state.to_move),
                previous_board=state.board,
                passes=min(2, state.passes + 1),
                move_number=state.move_number + 1,
            )
            return Transition(nxt, PASS, 0, 0, 0)
        if not 0 <= action < self.cells or state.board[action] != EMPTY:
            return None

        mover = state.to_move
        board = list(state.board)
        board[action] = mover
        captured: set[int] = set()
        checked: set[int] = set()
        interim = tuple(board)
        for nb in self.neighbours[action]:
            if interim[nb] != opponent(mover) or nb in checked:
                continue
            group, liberties = self.group_and_liberties(interim, nb)
            checked.update(group)
            if not liberties:
                captured.update(group)
        for pos in captured:
            board[pos] = EMPTY
        new_board = tuple(board)
        own_group, own_liberties = self.group_and_liberties(new_board, action)
        if not own_liberties:
            return None
        if not ignore_ko and state.previous_board is not None and new_board == state.previous_board:
            return None

        nxt = GoState(
            board=new_board,
            to_move=opponent(mover),
            previous_board=state.board,
            passes=0,
            move_number=state.move_number + 1,
        )
        return Transition(nxt, action, len(captured), len(own_group), len(own_liberties))

    def legal_transitions(self, state: GoState, include_pass: bool = True) -> list[Transition]:
        if self.is_terminal(state):
            return []
        result: list[Transition] = []
        for action, value in enumerate(state.board):
            if value != EMPTY:
                continue
            transition = self.play(state, action)
            if transition is not None:
                result.append(transition)
        if include_pass:
            passed = self.play(state, PASS)
            if passed is not None:
                result.append(passed)
        return result

    def legal_actions(self, state: GoState, include_pass: bool = True) -> list[int]:
        return [transition.action for transition in self.legal_transitions(state, include_pass)]

    def is_terminal(self, state: GoState) -> bool:
        return state.passes >= 2 or state.move_number >= self.max_moves

    def area_score(self, board: tuple[int, ...]) -> dict[str, float]:
        black_stones = sum(1 for value in board if value == BLACK)
        white_stones = sum(1 for value in board if value == WHITE)
        black_territory = 0
        white_territory = 0
        neutral = 0
        visited: set[int] = set()
        for start, value in enumerate(board):
            if value != EMPTY or start in visited:
                continue
            region = {start}
            boundary: set[int] = set()
            stack = [start]
            visited.add(start)
            while stack:
                pos = stack.pop()
                for nb in self.neighbours[pos]:
                    neighbour = board[nb]
                    if neighbour == EMPTY and nb not in visited:
                        visited.add(nb)
                        region.add(nb)
                        stack.append(nb)
                    elif neighbour != EMPTY:
                        boundary.add(neighbour)
            if boundary == {BLACK}:
                black_territory += len(region)
            elif boundary == {WHITE}:
                white_territory += len(region)
            else:
                neutral += len(region)
        black_area = black_stones + black_territory
        white_area = white_stones + white_territory
        margin = black_area - white_area - self.komi
        return {
            "black_stones": black_stones,
            "white_stones": white_stones,
            "black_territory": black_territory,
            "white_territory": white_territory,
            "neutral": neutral,
            "black_area": black_area,
            "white_area": white_area,
            "komi": self.komi,
            "black_margin": margin,
        }

    def outcome(self, state: GoState, perspective: int) -> float:
        margin = self.area_score(state.board)["black_margin"]
        if margin == 0:
            return 0.0
        black_result = 1.0 if margin > 0 else -1.0
        return black_result if perspective == BLACK else -black_result

    def coordinate(self, action: int) -> str:
        if action == PASS:
            return "pass"
        row, col = divmod(action, self.size)
        return f"{COL_LABELS[col]}{self.size - row}"

    def parse_coordinate(self, text: str) -> int:
        cleaned = text.strip().upper()
        if cleaned in {"P", "PASS"}:
            return PASS
        if len(cleaned) < 2 or cleaned[0] not in COL_LABELS[: self.size]:
            raise ValueError("좌표 형식은 D4 또는 pass입니다")
        col = COL_LABELS.index(cleaned[0])
        try:
            display_row = int(cleaned[1:])
        except ValueError as exc:
            raise ValueError("행 번호를 확인하십시오") from exc
        row = self.size - display_row
        if not 0 <= row < self.size:
            raise ValueError("판 밖의 좌표입니다")
        return row * self.size + col

    def display(self, state: GoState) -> str:
        lines = []
        for row in range(self.size):
            stones = " ".join("●" if v == BLACK else "○" if v == WHITE else "+" for v in state.board[row * self.size : (row + 1) * self.size])
            lines.append(f"{self.size - row:>2}  {stones}")
        lines.append("    " + " ".join(COL_LABELS[: self.size]))
        lines.append(f"차례 {colour_name(state.to_move)}   수 {state.move_number}   연속 패스 {state.passes}")
        return "\n".join(lines)


class WRRARenderer:
    """Transparent multi-channel action renderer; weights are fixed, not trained."""

    WEIGHTS = {
        "capture": 3.20,
        "rescue": 2.40,
        "atari": 1.35,
        "connection": 0.72,
        "cut_pressure": 0.42,
        "liberties": 0.20,
        "self_atari": -3.25,
        "eye_fill": -2.10,
        "area_delta": 0.32,
        "position": 0.28,
        "pass_readiness": 1.00,
    }

    def __init__(self, rules: GoRules):
        self.rules = rules

    def _position_value(self, action: int) -> float:
        row, col = divmod(action, self.rules.size)
        distance = min(row, col, self.rules.size - 1 - row, self.rules.size - 1 - col)
        target = 2 if self.rules.size >= 9 else 1
        return max(-1.0, 1.0 - abs(distance - target) / max(1, target + 1))

    def _group_keys(self, board: tuple[int, ...], action: int, colour: int) -> list[frozenset[int]]:
        return self.rules.neighbouring_groups(board, action, colour)

    def _settled_territory_balance(self, board: tuple[int, ...], mover: int) -> int:
        """Return the mover-relative balance of only small enclosed regions.

        Full-board area scoring is appropriate at termination, but it is a poor
        local move feature: on an otherwise empty board a single stone borders
        the one large open region and can therefore appear to own almost every
        empty point.  The Renderer avoids that artefact by counting only small
        closed regions here.  Terminal evaluation still uses the complete area
        score defined by :meth:`GoRules.area_score`.
        """
        maximum_region = max(2, self.rules.size // 2)
        black_territory = 0
        white_territory = 0
        visited: set[int] = set()
        for start, value in enumerate(board):
            if value != EMPTY or start in visited:
                continue
            region = {start}
            boundary: set[int] = set()
            stack = [start]
            visited.add(start)
            while stack:
                pos = stack.pop()
                for nb in self.rules.neighbours[pos]:
                    neighbour = board[nb]
                    if neighbour == EMPTY and nb not in visited:
                        visited.add(nb)
                        region.add(nb)
                        stack.append(nb)
                    elif neighbour != EMPTY:
                        boundary.add(neighbour)
            if len(region) > maximum_region:
                continue
            if boundary == {BLACK}:
                black_territory += len(region)
            elif boundary == {WHITE}:
                white_territory += len(region)
        balance = black_territory - white_territory
        return balance if mover == BLACK else -balance

    def features(self, state: GoState, transition: Transition) -> MoveFeatures:
        mover = state.to_move
        action = transition.action
        if action == PASS:
            margin = self.rules.area_score(state.board)["black_margin"]
            lead = margin if mover == BLACK else -margin
            empties = state.board.count(EMPTY)
            readiness = 0.0
            if state.passes == 1 and lead > 0:
                readiness = 4.0
            elif empties <= max(2, self.rules.size // 2) and lead > 0:
                readiness = 2.0
            else:
                readiness = -3.0
            return MoveFeatures(PASS, "pass", 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, readiness, readiness)

        friendly_before = self._group_keys(state.board, action, mover)
        enemy_before = self._group_keys(state.board, action, opponent(mover))
        rescue = sum(len(group) for group in friendly_before if len(self.rules.group_and_liberties(state.board, next(iter(group)))[1]) == 1)
        connection = max(0, len(friendly_before) - 1)
        cut_pressure = max(0, len(enemy_before) - 1)

        after = transition.state.board
        seen_enemy: set[int] = set()
        atari = 0
        for nb in self.rules.neighbours[action]:
            if after[nb] != opponent(mover) or nb in seen_enemy:
                continue
            group, liberties = self.rules.group_and_liberties(after, nb)
            seen_enemy.update(group)
            if len(liberties) == 1:
                atari += len(group)

        self_atari = int(transition.liberties == 1 and transition.captured == 0)
        neighbour_values = [state.board[nb] for nb in self.rules.neighbours[action]]
        eye_fill = int(neighbour_values and all(value == mover for value in neighbour_values) and transition.captured == 0)
        before_balance = self._settled_territory_balance(state.board, mover)
        after_balance = self._settled_territory_balance(after, mover)
        area_delta = after_balance - before_balance
        position = self._position_value(action)

        raw = {
            "capture": transition.captured,
            "rescue": rescue,
            "atari": atari,
            "connection": connection,
            "cut_pressure": cut_pressure,
            "liberties": min(transition.liberties, 6),
            "self_atari": self_atari,
            "eye_fill": eye_fill,
            "area_delta": area_delta,
            "position": position,
            "pass_readiness": 0.0,
        }
        score = sum(self.WEIGHTS[key] * value for key, value in raw.items())
        if transition.captured:
            phenotype = "capture"
        elif rescue:
            phenotype = "rescue"
        elif atari:
            phenotype = "atari"
        elif connection:
            phenotype = "connection"
        elif cut_pressure:
            phenotype = "cut_pressure"
        else:
            phenotype = "extension"
        return MoveFeatures(action, phenotype, score=score, **raw)

    def rank(self, state: GoState, transitions: Optional[list[Transition]] = None) -> list[tuple[Transition, MoveFeatures]]:
        transitions = transitions if transitions is not None else self.rules.legal_transitions(state)
        ranked = [(transition, self.features(state, transition)) for transition in transitions]
        ranked.sort(key=lambda pair: (pair[1].score, -pair[0].action), reverse=True)
        return ranked

    def priors(self, state: GoState, transitions: list[Transition], temperature: float = 1.35) -> dict[int, float]:
        if not transitions:
            return {}
        scored = [(transition.action, self.features(state, transition).score) for transition in transitions]
        maximum = max(score for _, score in scored)
        weights = [(action, math.exp(max(-18.0, min(18.0, (score - maximum) / temperature)))) for action, score in scored]
        total = sum(weight for _, weight in weights)
        return {action: weight / total for action, weight in weights}


@dataclass(slots=True)
class MCTSNode:
    state: GoState
    prior: float = 1.0
    action: Optional[int] = None
    parent: Optional["MCTSNode"] = None
    children: Optional[dict[int, "MCTSNode"]] = None
    visits: int = 0
    value_sum: float = 0.0

    @property
    def q(self) -> float:
        return self.value_sum / self.visits if self.visits else 0.0


class Agent(Protocol):
    name: str

    def select_action(self, state: GoState) -> tuple[int, dict[str, object]]:
        ...


class MCTSAgent:
    def __init__(
        self,
        rules: GoRules,
        simulations: int = 160,
        seed: int = 1,
        renderer_guided: bool = True,
        exploration: float = 1.35,
        rollout_limit: Optional[int] = None,
        name: Optional[str] = None,
    ):
        self.rules = rules
        self.simulations = simulations
        self.renderer_guided = renderer_guided
        self.exploration = exploration
        self.rollout_limit = rollout_limit if rollout_limit is not None else 2 * rules.cells
        self.renderer = WRRARenderer(rules)
        self.rng = random.Random(seed)
        self.name = name or ("WRRA-MCTS" if renderer_guided else "Uniform-MCTS")

    def _expand(self, node: MCTSNode) -> None:
        transitions = self.rules.legal_transitions(node.state)
        if self.renderer_guided:
            priors = self.renderer.priors(node.state, transitions)
        else:
            uniform = 1.0 / len(transitions) if transitions else 0.0
            priors = {transition.action: uniform for transition in transitions}
        node.children = {
            transition.action: MCTSNode(
                state=transition.state,
                prior=priors[transition.action],
                action=transition.action,
                parent=node,
            )
            for transition in transitions
        }

    def _select_child(self, node: MCTSNode, root_player: int) -> MCTSNode:
        assert node.children
        parent_scale = math.sqrt(max(1, node.visits))
        maximize = node.state.to_move == root_player

        def score(child: MCTSNode) -> tuple[float, float, int]:
            q = child.q if maximize else -child.q
            exploration = self.exploration * child.prior * parent_scale / (1 + child.visits)
            # Stable coordinate tie-break keeps seeded runs reproducible.
            tie = -(child.action if child.action is not None else PASS)
            return q + exploration, child.prior, tie

        return max(node.children.values(), key=score)

    def _sample_weighted(self, pairs: list[tuple[int, float]]) -> int:
        total = sum(weight for _, weight in pairs)
        pick = self.rng.random() * total
        cumulative = 0.0
        for action, weight in pairs:
            cumulative += weight
            if pick <= cumulative:
                return action
        return pairs[-1][0]

    def _rollout_action(self, state: GoState) -> int:
        transitions = self.rules.legal_transitions(state)
        if not transitions:
            return PASS
        placements = [transition for transition in transitions if transition.action != PASS]
        if not placements:
            return PASS
        if not self.renderer_guided:
            # Avoid arbitrary early passes in the uniform control while keeping
            # pass available near completion and after the opponent passes.
            if state.passes == 1 and self.rng.random() < 0.25:
                return PASS
            return self.rng.choice(placements).action

        ranked = self.renderer.rank(state, transitions)
        area = self.rules.area_score(state.board)["black_margin"]
        lead = area if state.to_move == BLACK else -area
        empty_count = state.board.count(EMPTY)
        allow_pass = state.passes == 1 and lead > 0
        candidates = [pair for pair in ranked if pair[0].action != PASS or allow_pass]
        if empty_count <= max(2, self.rules.size // 2) and lead > 0:
            candidates = ranked
        candidates = candidates[: min(8, len(candidates))]
        if self.rng.random() < 0.10:
            return self.rng.choice([transition.action for transition, _ in candidates])
        maximum = max(features.score for _, features in candidates)
        weighted = [
            (transition.action, math.exp(max(-12.0, min(12.0, (features.score - maximum) / 1.8))))
            for transition, features in candidates
        ]
        return self._sample_weighted(weighted)

    def _rollout(self, state: GoState, root_player: int) -> float:
        current = state
        for _ in range(self.rollout_limit):
            if self.rules.is_terminal(current):
                break
            action = self._rollout_action(current)
            transition = self.rules.play(current, action)
            if transition is None:
                # This should be unreachable because actions come from the legal set.
                transition = self.rules.play(current, PASS)
                assert transition is not None
            current = transition.state
        return self.rules.outcome(current, root_player)

    def select_action(self, state: GoState) -> tuple[int, dict[str, object]]:
        started = time.perf_counter()
        root_player = state.to_move
        root = MCTSNode(state=state)
        self._expand(root)
        if not root.children:
            return PASS, {"agent": self.name, "simulations": 0, "candidates": []}

        for _ in range(self.simulations):
            node = root
            path = [node]
            while node.children:
                node = self._select_child(node, root_player)
                path.append(node)
            if not self.rules.is_terminal(node.state):
                self._expand(node)
            value = self._rollout(node.state, root_player)
            for visited in path:
                visited.visits += 1
                visited.value_sum += value

        assert root.children
        chosen = max(
            root.children.values(),
            key=lambda child: (child.visits, child.q, child.prior, -(child.action or 0)),
        )
        ranked_features = {pair[0].action: pair[1] for pair in self.renderer.rank(state)}
        candidates = []
        for child in sorted(root.children.values(), key=lambda item: (item.visits, item.q), reverse=True)[:10]:
            features = ranked_features[child.action]
            candidates.append(
                {
                    "action": self.rules.coordinate(child.action),
                    "visits": child.visits,
                    "value": child.q,
                    "prior": child.prior,
                    "renderer_score": features.score,
                    "phenotype": features.phenotype,
                }
            )
        ledger = {
            "agent": self.name,
            "simulations": self.simulations,
            "selected": self.rules.coordinate(chosen.action if chosen.action is not None else PASS),
            "elapsed_seconds": time.perf_counter() - started,
            "candidates": candidates,
        }
        return chosen.action if chosen.action is not None else PASS, ledger


class RandomAgent:
    def __init__(self, rules: GoRules, seed: int = 1, name: str = "Random"):
        self.rules = rules
        self.rng = random.Random(seed)
        self.name = name

    def select_action(self, state: GoState) -> tuple[int, dict[str, object]]:
        placements = self.rules.legal_actions(state, include_pass=False)
        if not placements:
            action = PASS
        elif state.passes == 1 and state.board.count(EMPTY) <= max(2, self.rules.size // 2):
            action = PASS
        else:
            action = self.rng.choice(placements)
        return action, {"agent": self.name, "selected": self.rules.coordinate(action)}


def play_game(rules: GoRules, black: Agent, white: Agent) -> dict[str, object]:
    state = rules.initial_state()
    moves: list[dict[str, object]] = []
    total_decision_seconds = {"B": 0.0, "W": 0.0}
    while not rules.is_terminal(state):
        agent = black if state.to_move == BLACK else white
        mover = state.to_move
        action, ledger = agent.select_action(state)
        transition = rules.play(state, action)
        if transition is None:
            raise RuntimeError(f"{agent.name} selected illegal action {action}")
        total_decision_seconds[colour_name(mover)] += float(ledger.get("elapsed_seconds", 0.0))
        moves.append(
            {
                "ply": len(moves) + 1,
                "player": colour_name(mover),
                "action": rules.coordinate(action),
                "captured": transition.captured,
                "decision": ledger,
            }
        )
        state = transition.state
    score = rules.area_score(state.board)
    winner = "B" if score["black_margin"] > 0 else "W" if score["black_margin"] < 0 else "draw"
    return {
        "board_size": rules.size,
        "komi": rules.komi,
        "black_agent": black.name,
        "white_agent": white.name,
        "winner": winner,
        "moves": moves,
        "move_count": len(moves),
        "ended_by": "two_passes" if state.passes >= 2 else "operational_move_cap",
        "score": score,
        "decision_seconds": total_decision_seconds,
        "final_board": [
            "".join("B" if value == BLACK else "W" if value == WHITE else "." for value in state.board[row * rules.size : (row + 1) * rules.size])
            for row in range(rules.size)
        ],
    }


def sgf_from_game(game: dict[str, object]) -> str:
    size = int(game["board_size"])
    komi = float(game["komi"])
    rules = GoRules(size=size, komi=komi)
    nodes = [f"(;GM[1]FF[4]SZ[{size}]KM[{komi}]RU[WRRA-simple-ko-area]"]
    for move in game["moves"]:
        colour = str(move["player"])
        coordinate = str(move["action"])
        if coordinate == "pass":
            sgf_coord = ""
        else:
            action = rules.parse_coordinate(coordinate)
            row, col = divmod(action, size)
            sgf_coord = chr(ord("a") + col) + chr(ord("a") + row)
        nodes.append(f";{colour}[{sgf_coord}]")
    nodes.append(")")
    return "".join(nodes)


def wilson_interval(wins: int, games: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if games == 0:
        return 0.0, 0.0
    p = wins / games
    denominator = 1 + z * z / games
    centre = (p + z * z / (2 * games)) / denominator
    radius = z * math.sqrt(p * (1 - p) / games + z * z / (4 * games * games)) / denominator
    return centre - radius, centre + radius


def run_benchmark(
    size: int = 5,
    paired_games: int = 6,
    simulations: int = 72,
    komi: float = 2.5,
    seed: int = 20260917,
) -> dict[str, object]:
    """Paired WRRA-prior versus uniform-prior MCTS plus random control."""
    if paired_games < 1:
        raise ValueError("paired_games must be positive")
    started = time.perf_counter()
    records: list[dict[str, object]] = []
    matchups = (("uniform_mcts", True), ("random", False))
    for matchup, use_mcts in matchups:
        for pair in range(paired_games):
            for wrra_colour in (BLACK, WHITE):
                game_seed = seed + 1000 * (0 if matchup == "uniform_mcts" else 1) + pair * 17 + (0 if wrra_colour == BLACK else 1)
                rules = GoRules(size=size, komi=komi)
                wrra = MCTSAgent(rules, simulations=simulations, seed=game_seed, renderer_guided=True)
                if use_mcts:
                    control: Agent = MCTSAgent(
                        rules,
                        simulations=simulations,
                        seed=game_seed + 7,
                        renderer_guided=False,
                    )
                else:
                    control = RandomAgent(rules, seed=game_seed + 7)
                black, white = (wrra, control) if wrra_colour == BLACK else (control, wrra)
                game = play_game(rules, black, white)
                wrra_won = game["winner"] == colour_name(wrra_colour)
                records.append(
                    {
                        "matchup": matchup,
                        "pair": pair + 1,
                        "wrra_colour": colour_name(wrra_colour),
                        "winner": game["winner"],
                        "wrra_win": wrra_won,
                        "move_count": game["move_count"],
                        "black_margin": game["score"]["black_margin"],
                        "ended_by": game["ended_by"],
                        "decision_seconds": game["decision_seconds"],
                    }
                )

    summaries = {}
    for matchup, _ in matchups:
        subset = [record for record in records if record["matchup"] == matchup]
        wins = sum(bool(record["wrra_win"]) for record in subset)
        low, high = wilson_interval(wins, len(subset))
        summaries[matchup] = {
            "games": len(subset),
            "wrra_wins": wins,
            "wrra_losses": len(subset) - wins,
            "wrra_win_rate": wins / len(subset),
            "wilson_95_interval": [low, high],
            "mean_move_count": statistics.fmean(float(record["move_count"]) for record in subset),
            "two_pass_endings": sum(record["ended_by"] == "two_passes" for record in subset),
        }
    return {
        "metadata": {
            "profile": "WRRA-Go 0.1",
            "core": "WRRA Core 1.0 frozen",
            "author": "Wonsik Choi",
            "email": "janefather@gmail.com",
            "date": "2026-09-17",
            "seed": seed,
        },
        "rules": {
            "board": f"{size}x{size}",
            "komi": komi,
            "capture": True,
            "suicide_forbidden": True,
            "ko": "simple ko with one previous-board residue",
            "pass": True,
            "end": "two consecutive passes; operational cap for automated runs",
            "scoring": "area score",
        },
        "search": {
            "simulations_per_move": simulations,
            "paired_games_per_matchup": paired_games,
            "wrra_prior": "fixed transparent renderer channels",
            "control_prior": "uniform" if simulations else "not applicable",
        },
        "summary": summaries,
        "games": records,
        "elapsed_seconds": time.perf_counter() - started,
        "interpretation": (
            "This benchmark measures action selection under the stated finite rules. "
            "It is not an empirical forecast and not a claim of professional Go strength."
        ),
    }


def run_rule_tests() -> dict[str, object]:
    rules = GoRules(size=3, komi=0.5)

    def follow(actions: Iterable[int]) -> GoState:
        state = rules.initial_state()
        for action in actions:
            transition = rules.play(state, action)
            assert transition is not None, (state, action)
            state = transition.state
        return state

    # The shortest blocked-history witness independently found by Game 0.2.
    blocked_history = [2, 1, 4, 3, 0]
    blocked_state = follow(blocked_history)
    ko_attempt = rules.play(blocked_state, 1)
    ko_attempt_without_residue = rules.play(blocked_state, 1, ignore_ko=True)
    assert ko_attempt is None
    assert ko_attempt_without_residue is not None
    assert ko_attempt_without_residue.state.board == blocked_state.previous_board

    legal_history = [0, 3, 2, PASS, 4]
    legal_state = follow(legal_history)
    assert legal_state.board == blocked_state.board
    assert legal_state.to_move == blocked_state.to_move
    assert rules.play(legal_state, 1) is not None

    passed_once = rules.play(rules.initial_state(), PASS)
    assert passed_once is not None
    passed_twice = rules.play(passed_once.state, PASS)
    assert passed_twice is not None and rules.is_terminal(passed_twice.state)

    capture_board = (
        EMPTY, BLACK, EMPTY,
        BLACK, WHITE, BLACK,
        EMPTY, EMPTY, EMPTY,
    )
    captured = rules.play(GoState(capture_board, to_move=BLACK), 7)
    assert captured is not None and captured.captured == 1 and captured.state.board[4] == EMPTY

    suicide_board = (
        EMPTY, WHITE, EMPTY,
        WHITE, EMPTY, WHITE,
        EMPTY, WHITE, EMPTY,
    )
    assert rules.play(GoState(suicide_board, to_move=BLACK), 4) is None
    full_black = (BLACK,) * rules.cells
    assert rules.area_score(full_black)["black_margin"] == rules.cells - rules.komi

    # A first stone must not be credited with the whole open board by the
    # Renderer's local territory channel.  Full area scoring remains unchanged.
    renderer = WRRARenderer(rules)
    opening = rules.play(rules.initial_state(), 4)
    assert opening is not None
    assert renderer.features(rules.initial_state(), opening).area_delta == 0

    result = {
        "same_visible_board_witness": True,
        "simple_ko_blocks_repetition": True,
        "removing_residue_admits_repetition": True,
        "same_board_different_residue_changes_legality": True,
        "two_passes_terminate": True,
        "capture_removes_surrounded_group": True,
        "suicide_is_forbidden": True,
        "area_scoring_is_deterministic": True,
        "renderer_does_not_claim_open_board": True,
        "coordinate_round_trip": all(
            rules.parse_coordinate(rules.coordinate(action)) == action
            for action in range(rules.cells)
        ),
    }
    assert all(result.values())
    return result


def interactive_game(args: argparse.Namespace) -> None:
    rules = GoRules(size=args.size, komi=args.komi)
    human = BLACK if args.human.lower().startswith("b") else WHITE
    engine = MCTSAgent(rules, simulations=args.simulations, seed=args.seed, renderer_guided=True)
    state = rules.initial_state()
    ledger = []
    print(rules.display(state))
    while not rules.is_terminal(state):
        if state.to_move == human:
            raw = input("착수 좌표 D4, pass 또는 quit: ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                print("대국을 종료합니다.")
                return
            try:
                action = rules.parse_coordinate(raw)
            except ValueError as exc:
                print(exc)
                continue
            decision = {"agent": "Human", "selected": rules.coordinate(action)}
        else:
            action, decision = engine.select_action(state)
            print(f"WRRA 착수: {rules.coordinate(action)}")
        transition = rules.play(state, action)
        if transition is None:
            print("합법수가 아닙니다.")
            continue
        ledger.append({"player": colour_name(state.to_move), "action": rules.coordinate(action), "decision": decision})
        state = transition.state
        print(rules.display(state))
    score = rules.area_score(state.board)
    print(json.dumps({"score": score, "ledger": ledger}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Playable WRRA Go engine")
    sub = parser.add_subparsers(dest="command", required=True)

    play_parser = sub.add_parser("play", help="play against the engine")
    play_parser.add_argument("--size", type=int, default=9)
    play_parser.add_argument("--komi", type=float, default=5.5)
    play_parser.add_argument("--human", default="B", choices=("B", "W", "b", "w"))
    play_parser.add_argument("--simulations", type=int, default=72)
    play_parser.add_argument("--seed", type=int, default=20260917)

    bench_parser = sub.add_parser("benchmark", help="run paired reproducible matches")
    bench_parser.add_argument("--size", type=int, default=5)
    bench_parser.add_argument("--komi", type=float, default=2.5)
    bench_parser.add_argument("--paired-games", type=int, default=6)
    bench_parser.add_argument("--simulations", type=int, default=72)
    bench_parser.add_argument("--seed", type=int, default=20260917)
    bench_parser.add_argument("--output", type=Path, default=Path("wrra_go_0_1_benchmark.json"))

    self_parser = sub.add_parser("selfplay", help="create one WRRA self-play record")
    self_parser.add_argument("--size", type=int, default=9)
    self_parser.add_argument("--komi", type=float, default=5.5)
    self_parser.add_argument("--simulations", type=int, default=120)
    self_parser.add_argument("--seed", type=int, default=20260917)
    self_parser.add_argument("--output", type=Path, default=Path("wrra_go_0_1_selfplay.json"))

    test_parser = sub.add_parser("test", help="run deterministic rule tests")
    test_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "play":
        interactive_game(args)
        return
    if args.command == "test":
        result = run_rule_tests()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "benchmark":
        result = run_benchmark(args.size, args.paired_games, args.simulations, args.komi, args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "selfplay":
        rules = GoRules(size=args.size, komi=args.komi)
        black = MCTSAgent(rules, simulations=args.simulations, seed=args.seed, renderer_guided=True, name="WRRA-MCTS-B")
        white = MCTSAgent(rules, simulations=args.simulations, seed=args.seed + 1, renderer_guided=True, name="WRRA-MCTS-W")
        game = play_game(rules, black, white)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(game, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".sgf").write_text(sgf_from_game(game), encoding="utf-8")
        print(json.dumps(game, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
