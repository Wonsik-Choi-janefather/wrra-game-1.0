#!/usr/bin/env python3
"""WRRA-Game 0.2 exhaustive small-board validation.

WRRA Core 1.0 remains frozen.  This domain-profile extension tests two claims:

1. A Connect-K renderer can reduce exact search without changing minimax value.
2. Under simple ko, a visible Go board plus side-to-move is not a sufficient
   state; a one-board residue can change the legal action set.

The experiments are finite, deterministic, and exhaustively reproducible on
the stated small boards.  They do not claim general playing strength.

Author: Wonsik Choi
Contact: janefather@gmail.com
Date: 2026-09-17
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional


BLACK = 1
WHITE = -1
PASS = -1


def opponent(player: int) -> int:
    return -player


def iter_bits(mask: int) -> Iterable[int]:
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def bit_count(mask: int) -> int:
    return mask.bit_count()


@dataclass
class SearchStats:
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    immediate_win_gates: int = 0
    mandatory_block_gates: int = 0
    forced_loss_certificates: int = 0
    max_depth: int = 0


class ConnectKLab:
    """Finite placement game used as a fully enumerable Omok laboratory."""

    def __init__(self, rows: int = 4, cols: int = 4, k: int = 3):
        self.rows = rows
        self.cols = cols
        self.k = k
        self.cells = rows * cols
        self.full_mask = (1 << self.cells) - 1
        self.win_masks = tuple(sorted(set(self._make_win_masks())))
        self.cell_window_count = tuple(
            sum(1 for mask in self.win_masks if mask & (1 << i))
            for i in range(self.cells)
        )

    def _make_win_masks(self) -> Iterable[int]:
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for r in range(self.rows):
                for c in range(self.cols):
                    rr = r + (self.k - 1) * dr
                    cc = c + (self.k - 1) * dc
                    if not (0 <= rr < self.rows and 0 <= cc < self.cols):
                        continue
                    mask = 0
                    for i in range(self.k):
                        mask |= 1 << ((r + i * dr) * self.cols + c + i * dc)
                    yield mask

    def has_win(self, stones: int) -> bool:
        return any(stones & line == line for line in self.win_masks)

    def masks_for_player(self, black: int, white: int, player: int) -> tuple[int, int]:
        return (black, white) if player == BLACK else (white, black)

    def legal_moves(self, black: int, white: int) -> list[int]:
        return list(iter_bits(self.full_mask ^ (black | white)))

    def immediate_wins(self, black: int, white: int, player: int) -> list[int]:
        mine, _ = self.masks_for_player(black, white, player)
        return [m for m in self.legal_moves(black, white) if self.has_win(mine | (1 << m))]

    def play(self, black: int, white: int, player: int, move: int) -> tuple[int, int, int]:
        bit = 1 << move
        if (black | white) & bit:
            raise ValueError("occupied Connect-K cell")
        if player == BLACK:
            black |= bit
        else:
            white |= bit
        return black, white, opponent(player)

    def live_line_score(self, black: int, white: int, player: int, move: int) -> tuple[int, int, int]:
        mine, theirs = self.masks_for_player(black, white, player)
        mine |= 1 << move
        fork_outlets = len(self.immediate_wins(*self._restore_masks(mine, theirs, player), player))
        seeded = 0
        open_windows = 0
        for line in self.win_masks:
            if line & (1 << move) and not (line & theirs):
                open_windows += 1
                seeded = max(seeded, bit_count(line & mine))
        return fork_outlets, seeded, open_windows

    @staticmethod
    def _restore_masks(mine: int, theirs: int, player: int) -> tuple[int, int]:
        return (mine, theirs) if player == BLACK else (theirs, mine)

    def renderer_plan(
        self,
        black: int,
        white: int,
        player: int,
        safe_gate: bool,
    ) -> tuple[list[int], str]:
        legal = self.legal_moves(black, white)
        own_wins = self.immediate_wins(black, white, player)
        if safe_gate and own_wins:
            return own_wins, "immediate_win"

        threats = self.immediate_wins(black, white, opponent(player))
        if safe_gate and len(threats) == 1:
            return threats, "mandatory_block"
        if safe_gate and len(threats) >= 2:
            return [], "forced_loss"

        centre_r = (self.rows - 1) / 2
        centre_c = (self.cols - 1) / 2

        def priority(move: int) -> tuple[float, ...]:
            r, c = divmod(move, self.cols)
            fork_outlets, seeded, open_windows = self.live_line_score(
                black, white, player, move
            )
            blocks = 1 if move in threats else 0
            distance = abs(r - centre_r) + abs(c - centre_c)
            return (
                blocks,
                fork_outlets,
                seeded,
                open_windows,
                self.cell_window_count[move],
                -distance,
                -move,
            )

        return sorted(legal, key=priority, reverse=True), "ordered"

    def enumerate_reachable(self) -> tuple[set[tuple[int, int, int]], dict[str, int]]:
        start = (0, 0, BLACK)
        seen = {start}
        queue = deque([start])
        edge_count = 0
        terminal_wins = 0
        terminal_draws = 0
        while queue:
            black, white, player = queue.popleft()
            prior = white if player == BLACK else black
            if self.has_win(prior):
                terminal_wins += 1
                continue
            moves = self.legal_moves(black, white)
            if not moves:
                terminal_draws += 1
                continue
            for move in moves:
                edge_count += 1
                nxt = self.play(black, white, player, move)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen, {
            "directed_legal_edges": edge_count,
            "terminal_win_states": terminal_wins,
            "terminal_draw_states": terminal_draws,
        }

    def make_exact_solver(self, renderer_gate: bool):
        @lru_cache(maxsize=None)
        def solve(black: int, white: int, player: int) -> int:
            prior = white if player == BLACK else black
            if self.has_win(prior):
                return -1
            legal = self.legal_moves(black, white)
            if not legal:
                return 0
            if renderer_gate:
                moves, status = self.renderer_plan(black, white, player, True)
                if status == "forced_loss":
                    return -1
            else:
                moves = legal
            best = -1
            for move in moves:
                nb, nw, np = self.play(black, white, player, move)
                value = -solve(nb, nw, np)
                if value > best:
                    best = value
                if best == 1:
                    break
            return best

        return solve

    def alpha_beta(self, mode: str) -> tuple[int, SearchStats]:
        stats = SearchStats()

        def search(black: int, white: int, player: int, alpha: int, beta: int, depth: int) -> int:
            stats.nodes += 1
            stats.max_depth = max(stats.max_depth, depth)
            prior = white if player == BLACK else black
            if self.has_win(prior):
                stats.leaves += 1
                return -1
            legal = self.legal_moves(black, white)
            if not legal:
                stats.leaves += 1
                return 0

            if mode == "baseline":
                moves = legal
                status = "baseline"
            elif mode == "renderer_order":
                moves, status = self.renderer_plan(black, white, player, False)
            elif mode == "renderer_gate":
                moves, status = self.renderer_plan(black, white, player, True)
                if status == "immediate_win":
                    stats.immediate_win_gates += 1
                elif status == "mandatory_block":
                    stats.mandatory_block_gates += 1
                elif status == "forced_loss":
                    stats.forced_loss_certificates += 1
                    stats.leaves += 1
                    return -1
            else:
                raise ValueError(f"unknown mode: {mode}")

            best = -1
            for move in moves:
                nb, nw, np = self.play(black, white, player, move)
                value = -search(nb, nw, np, -beta, -alpha, depth + 1)
                if value > best:
                    best = value
                if value > alpha:
                    alpha = value
                if alpha >= beta:
                    stats.cutoffs += 1
                    break
            return best

        value = search(0, 0, BLACK, -1, 1, 0)
        return value, stats

    def phenotype_census(self, states: Iterable[tuple[int, int, int]]) -> dict[str, int]:
        census = Counter()
        for black, white, player in states:
            prior = white if player == BLACK else black
            if self.has_win(prior):
                census["terminal_win"] += 1
                continue
            if black | white == self.full_mask:
                census["terminal_draw"] += 1
                continue
            own_wins = self.immediate_wins(black, white, player)
            if own_wins:
                census["immediate_win"] += 1
                continue
            threats = self.immediate_wins(black, white, opponent(player))
            if len(threats) == 1:
                census["mandatory_block"] += 1
            elif len(threats) >= 2:
                census["forced_loss_certificate"] += 1
            else:
                census["open_search"] += 1
        return dict(sorted(census.items()))


GoBoard = tuple[int, int]
GoState = tuple[int, int, int, int, int, int]


class Go3x3Lab:
    """Exhaustive 3x3 Go graph with capture, suicide, pass, and simple ko."""

    def __init__(self, size: int = 3):
        self.size = size
        self.cells = size * size
        self.full_mask = (1 << self.cells) - 1
        self.neighbour_masks = tuple(self._neighbour_mask(i) for i in range(self.cells))

    def _neighbour_mask(self, pos: int) -> int:
        r, c = divmod(pos, self.size)
        mask = 0
        for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= rr < self.size and 0 <= cc < self.size:
                mask |= 1 << (rr * self.size + cc)
        return mask

    def group_and_liberties(self, stones: int, occupied: int, start: int) -> tuple[int, int]:
        start_bit = 1 << start
        if not stones & start_bit:
            return 0, 0
        group = 0
        frontier = start_bit
        while frontier:
            group |= frontier
            neighbours = 0
            for pos in iter_bits(frontier):
                neighbours |= self.neighbour_masks[pos]
            frontier = (neighbours & stones) & ~group
        neighbours = 0
        for pos in iter_bits(group):
            neighbours |= self.neighbour_masks[pos]
        liberties = neighbours & ~occupied
        return group, liberties

    def play_placement(self, state: GoState, move: int, ignore_ko: bool = False) -> Optional[GoState]:
        black, white, player, prev_black, prev_white, _passes = state
        bit = 1 << move
        if (black | white) & bit:
            return None

        mine = black if player == BLACK else white
        theirs = white if player == BLACK else black
        mine |= bit
        occupied = mine | theirs

        checked = 0
        captured = 0
        for nb in iter_bits(self.neighbour_masks[move] & theirs):
            nb_bit = 1 << nb
            if checked & nb_bit:
                continue
            group, liberties = self.group_and_liberties(theirs, occupied, nb)
            checked |= group
            if liberties == 0:
                captured |= group
        theirs &= ~captured
        occupied = mine | theirs
        _own_group, own_liberties = self.group_and_liberties(mine, occupied, move)
        if own_liberties == 0:
            return None

        if player == BLACK:
            new_black, new_white = mine, theirs
        else:
            new_black, new_white = theirs, mine

        if not ignore_ko and prev_black >= 0 and (new_black, new_white) == (prev_black, prev_white):
            return None
        return (new_black, new_white, opponent(player), black, white, 0)

    def pass_move(self, state: GoState) -> GoState:
        black, white, player, _prev_black, _prev_white, passes = state
        return (black, white, opponent(player), black, white, min(2, passes + 1))

    def legal_placement_mask(self, state: GoState, ignore_ko: bool = False) -> int:
        if state[5] >= 2:
            return 0
        black, white = state[0], state[1]
        mask = 0
        for move in iter_bits(self.full_mask ^ (black | white)):
            if self.play_placement(state, move, ignore_ko=ignore_ko) is not None:
                mask |= 1 << move
        return mask

    def enumerate_reachable(self):
        start: GoState = (0, 0, BLACK, -1, -1, 0)
        seen = {start}
        parent: dict[GoState, tuple[Optional[GoState], Optional[int]]] = {
            start: (None, None)
        }
        depth = {start: 0}
        queue = deque([start])
        edges = 0
        placement_edges = 0
        pass_edges = 0
        while queue:
            state = queue.popleft()
            if state[5] >= 2:
                continue
            legal = self.legal_placement_mask(state)
            for move in iter_bits(legal):
                nxt = self.play_placement(state, move)
                assert nxt is not None
                edges += 1
                placement_edges += 1
                if nxt not in seen:
                    seen.add(nxt)
                    parent[nxt] = (state, move)
                    depth[nxt] = depth[state] + 1
                    queue.append(nxt)
            nxt = self.pass_move(state)
            edges += 1
            pass_edges += 1
            if nxt not in seen:
                seen.add(nxt)
                parent[nxt] = (state, PASS)
                depth[nxt] = depth[state] + 1
                queue.append(nxt)
        return seen, parent, depth, {
            "directed_legal_edges": edges,
            "placement_edges": placement_edges,
            "pass_edges": pass_edges,
            "terminal_two_pass_states": sum(1 for state in seen if state[5] == 2),
        }

    def path_to(self, state: GoState, parent) -> list[dict[str, object]]:
        reverse: list[tuple[int, int]] = []
        current = state
        while True:
            prev, action = parent[current]
            if prev is None:
                break
            mover = prev[2]
            reverse.append((mover, int(action)))
            current = prev
        result = []
        for ply, (player, action) in enumerate(reversed(reverse), start=1):
            if action == PASS:
                rendered: object = "pass"
            else:
                rendered = list(divmod(action, self.size))
            result.append({"ply": ply, "player": "B" if player == BLACK else "W", "action": rendered})
        return result

    def analyse_residue(self, states, parent, depth) -> dict[str, object]:
        # Hold board, side-to-move, and pass count fixed; vary only previous-board residue.
        groups: dict[tuple[int, int, int, int], list[GoState]] = defaultdict(list)
        legal_masks: dict[GoState, int] = {}
        ko_sensitive = 0
        blocked_move_histogram = Counter()
        for state in states:
            black, white, player, _pb, _pw, passes = state
            visible = (black, white, player, passes)
            groups[visible].append(state)
            legal = self.legal_placement_mask(state)
            legal_masks[state] = legal
            if passes < 2:
                no_residue_state = (black, white, player, -1, -1, passes)
                no_residue = self.legal_placement_mask(no_residue_state, ignore_ko=True)
                blocked = no_residue & ~legal
                if blocked:
                    ko_sensitive += 1
                    blocked_move_histogram[bit_count(blocked)] += 1

        multi_residue = {
            visible: members
            for visible, members in groups.items()
            if len({(s[3], s[4]) for s in members}) > 1
        }
        differing = {
            visible: members
            for visible, members in multi_residue.items()
            if len({legal_masks[s] for s in members}) > 1
        }
        affected_states = sum(len(members) for members in differing.values())
        max_action_sets = max((len({legal_masks[s] for s in m}) for m in groups.values()), default=0)
        max_residues = max((len({(s[3], s[4]) for s in m}) for m in groups.values()), default=0)

        # Choose the shortest pair of reachable histories that proves board-only insufficiency.
        witness = None
        candidates = sorted(
            differing.items(),
            key=lambda item: (
                min(max(depth[s1], depth[s2])
                    for s1 in item[1]
                    for s2 in item[1]
                    if legal_masks[s1] != legal_masks[s2]),
                item[0],
            ),
        )
        if candidates:
            visible, members = candidates[0]
            pair = min(
                ((s1, s2) for s1 in members for s2 in members if legal_masks[s1] != legal_masks[s2]),
                key=lambda p: (max(depth[p[0]], depth[p[1]]), depth[p[0]] + depth[p[1]], p),
            )
            s1, s2 = pair
            diff = legal_masks[s1] ^ legal_masks[s2]
            action = min(iter_bits(diff))
            if legal_masks[s1] & (1 << action):
                legal_state, blocked_state = s1, s2
            else:
                legal_state, blocked_state = s2, s1
            black, white, player, passes = visible
            attempted = self.play_placement(blocked_state, action, ignore_ko=True)
            assert attempted is not None
            restores_previous = (attempted[0], attempted[1]) == (blocked_state[3], blocked_state[4])
            witness = {
                "board_rows": self.board_rows(black, white),
                "to_move": "B" if player == BLACK else "W",
                "pass_count": passes,
                "differing_action": list(divmod(action, self.size)),
                "legal_history_depth": depth[legal_state],
                "blocked_history_depth": depth[blocked_state],
                "legal_history": self.path_to(legal_state, parent),
                "blocked_history": self.path_to(blocked_state, parent),
                "legal_previous_board_rows": self.board_rows(legal_state[3], legal_state[4]),
                "blocked_previous_board_rows": self.board_rows(blocked_state[3], blocked_state[4]),
                "legal_action_set": [list(divmod(m, self.size)) for m in iter_bits(legal_masks[legal_state])],
                "blocked_action_set": [list(divmod(m, self.size)) for m in iter_bits(legal_masks[blocked_state])],
                "blocked_move_restores_previous_board": restores_previous,
            }

        return {
            "unique_visible_state_classes": len(groups),
            "classes_with_multiple_reachable_residues": len(multi_residue),
            "classes_with_residue_dependent_legal_actions": len(differing),
            "full_states_in_action_differing_classes": affected_states,
            "ko_sensitive_full_states": ko_sensitive,
            "max_reachable_residues_per_visible_state": max_residues,
            "max_distinct_legal_action_sets_per_visible_state": max_action_sets,
            "blocked_moves_per_ko_sensitive_state": dict(sorted(blocked_move_histogram.items())),
            "witness": witness,
        }

    def board_rows(self, black: int, white: int) -> list[str]:
        if black < 0:
            return ["none"]
        rows = []
        for r in range(self.size):
            chars = []
            for c in range(self.size):
                bit = 1 << (r * self.size + c)
                chars.append("B" if black & bit else "W" if white & bit else ".")
            rows.append("".join(chars))
        return rows


def run_experiments() -> dict[str, object]:
    started = time.perf_counter()

    connect = ConnectKLab(4, 4, 3)
    connect_started = time.perf_counter()
    states, graph_stats = connect.enumerate_reachable()
    census = connect.phenotype_census(states)

    exact = connect.make_exact_solver(renderer_gate=False)
    renderer_exact = connect.make_exact_solver(renderer_gate=True)
    mismatch_count = 0
    value_counts = Counter()
    for state in states:
        value = exact(*state)
        rendered_value = renderer_exact(*state)
        value_counts[value] += 1
        if value != rendered_value:
            mismatch_count += 1
    root_exact = exact(0, 0, BLACK)
    root_renderer = renderer_exact(0, 0, BLACK)

    search_results = {}
    for mode in ("baseline", "renderer_order", "renderer_gate"):
        value, stats = connect.alpha_beta(mode)
        search_results[mode] = {"value": value, **asdict(stats)}
    baseline_nodes = search_results["baseline"]["nodes"]
    ordered_nodes = search_results["renderer_order"]["nodes"]
    gated_nodes = search_results["renderer_gate"]["nodes"]
    connect_seconds = time.perf_counter() - connect_started

    go = Go3x3Lab(3)
    go_started = time.perf_counter()
    go_states, parent, depth, go_graph = go.enumerate_reachable()
    residue = go.analyse_residue(go_states, parent, depth)
    go_seconds = time.perf_counter() - go_started

    result = {
        "metadata": {
            "profile": "WRRA-Game 0.2",
            "parent_profile": "WRRA-Game 0.1 preserved",
            "core": "WRRA Core 1.0 frozen",
            "author": "Wonsik Choi",
            "email": "janefather@gmail.com",
            "date": "2026-09-17",
        },
        "core_contract": [
            "SOURCE",
            "RELATION/LAW",
            "STATE/RESIDUE",
            "BOUNDARY",
            "COMMON CARRIER",
            "UPDATE",
            "RENDERER",
            "PHENOTYPE",
            "OBSERVABLE/RECORD/LEDGER",
        ],
        "connect_k": {
            "role": "fully enumerable Omok laboratory; not the standard 15x15 game",
            "board": "4x4",
            "win_length": 3,
            "rules": "alternating placement; at least k contiguous stones wins; stop at first win",
            "win_masks": len(connect.win_masks),
            "reachable_full_states": len(states),
            **graph_stats,
            "phenotype_census": census,
            "exact_value_counts_current_player_perspective": {
                "loss_-1": value_counts[-1],
                "draw_0": value_counts[0],
                "win_1": value_counts[1],
            },
            "root_exact_value": root_exact,
            "root_renderer_value": root_renderer,
            "all_state_value_mismatches": mismatch_count,
            "exact_solver_cache": {
                "states_evaluated": exact.cache_info().currsize,
                "hits": exact.cache_info().hits,
                "misses": exact.cache_info().misses,
            },
            "renderer_solver_cache": {
                "states_evaluated": renderer_exact.cache_info().currsize,
                "hits": renderer_exact.cache_info().hits,
                "misses": renderer_exact.cache_info().misses,
            },
            "root_alpha_beta": search_results,
            "node_reduction_vs_baseline": {
                "renderer_order_fraction": 1 - ordered_nodes / baseline_nodes,
                "renderer_gate_fraction": 1 - gated_nodes / baseline_nodes,
                "renderer_gate_factor": baseline_nodes / gated_nodes,
            },
            "minimal_sufficient_state": "board occupancy plus side-to-move",
            "elapsed_seconds": connect_seconds,
        },
        "go": {
            "board": "3x3",
            "rules": "orthogonal liberties; capture; suicide forbidden; simple ko; pass; two passes terminate",
            "reachable_full_states": len(go_states),
            **go_graph,
            **residue,
            "minimal_sufficient_state": "board, side-to-move, previous-board residue, and pass count",
            "elapsed_seconds": go_seconds,
        },
        "claim_status": {
            "core_modified": False,
            "connect_k_full_reachable_graph_enumerated": True,
            "renderer_optimal_value_preserved_on_every_reachable_connect_k_state": mismatch_count == 0,
            "go_full_reachable_graph_enumerated": True,
            "board_only_go_state_sufficiency_refuted_for_stated_rules": residue[
                "classes_with_residue_dependent_legal_actions"
            ] > 0,
            "standard_15x15_omok_solved": False,
            "standard_19x19_go_solved": False,
            "specialized_engine_superiority_claimed": False,
        },
        "elapsed_seconds_total": time.perf_counter() - started,
    }

    assert root_exact == root_renderer
    assert mismatch_count == 0
    assert residue["classes_with_residue_dependent_legal_actions"] > 0
    assert residue["witness"] is not None
    assert residue["witness"]["blocked_move_restores_previous_board"] is True
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("wrra_game_0_2_results.json"))
    args = parser.parse_args()
    result = run_experiments()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
