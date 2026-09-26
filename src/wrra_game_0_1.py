#!/usr/bin/env python3
"""WRRA-Game 0.1 proof-of-concept for Omok and Go.

This module keeps WRRA Core 1.0 fixed and implements two domain profiles.
It is deliberately small, deterministic, and auditable.  The objective is not
to beat specialized game engines but to test whether the same execution
contract can derive non-trivial phenotypes from simple rules.

Author: Wonsik Choi
Contact: janefather@gmail.com
Date: 2026-09-16
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import matplotlib.pyplot as plt
from matplotlib import font_manager


EMPTY = 0
BLACK = 1
WHITE = -1
Coord = tuple[int, int]
BoardHash = tuple[tuple[int, ...], ...]


def opponent(player: int) -> int:
    return -player


def board_hash(board: Sequence[Sequence[int]]) -> BoardHash:
    return tuple(tuple(int(v) for v in row) for row in board)


def board_copy(board: Sequence[Sequence[int]]) -> list[list[int]]:
    return [list(row) for row in board]


def in_bounds(size: int, move: Coord) -> bool:
    r, c = move
    return 0 <= r < size and 0 <= c < size


def korean_font() -> str:
    candidates = ["WRRA Korean Sans", "Noto Sans KR", "Noto Sans CJK KR", "DejaVu Sans"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    return next((name for name in candidates if name in available), "DejaVu Sans")


plt.rcParams["font.family"] = korean_font()
plt.rcParams["axes.unicode_minus"] = False


@dataclass(frozen=True)
class WRRAMetrics:
    """Cross-game metric vector; no arbitrary scalar weights are imposed."""

    legal_actions: int
    boundary_points: int
    ownership_ambiguity: int
    residue_units: int
    phenotype_events: int


@dataclass(frozen=True)
class OmokState:
    board: BoardHash
    to_move: int = BLACK
    k: int = 5

    @property
    def size(self) -> int:
        return len(self.board)

    @staticmethod
    def empty(size: int = 15, k: int = 5) -> "OmokState":
        return OmokState(tuple(tuple(0 for _ in range(size)) for _ in range(size)), BLACK, k)

    def legal_moves(self) -> list[Coord]:
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.board[r][c] == EMPTY
        ]

    def place_for(self, move: Coord, player: int) -> "OmokState":
        if not in_bounds(self.size, move) or self.board[move[0]][move[1]] != EMPTY:
            raise ValueError(f"illegal Omok move: {move}")
        b = board_copy(self.board)
        b[move[0]][move[1]] = player
        return OmokState(board_hash(b), opponent(player), self.k)

    def play(self, move: Coord) -> "OmokState":
        return self.place_for(move, self.to_move)

    def line_length(self, move: Coord, player: int, direction: Coord) -> int:
        dr, dc = direction
        total = 1
        for sign in (-1, 1):
            r, c = move
            while True:
                r += sign * dr
                c += sign * dc
                if not in_bounds(self.size, (r, c)) or self.board[r][c] != player:
                    break
                total += 1
        return total

    def is_win_at(self, move: Coord, player: int) -> bool:
        if self.board[move[0]][move[1]] != player:
            return False
        return any(
            self.line_length(move, player, d) >= self.k
            for d in ((1, 0), (0, 1), (1, 1), (1, -1))
        )

    def immediate_wins(self, player: int) -> list[Coord]:
        wins: list[Coord] = []
        for move in self.legal_moves():
            nxt = self.place_for(move, player)
            if nxt.is_win_at(move, player):
                wins.append(move)
        return wins

    def threat_outlets(self, move: Coord, player: int) -> list[Coord]:
        """Distinct next-turn winning cells created by a non-winning move."""
        nxt = self.place_for(move, player)
        if nxt.is_win_at(move, player):
            return []
        return nxt.immediate_wins(player)

    def fork_moves(self, player: int, minimum_outlets: int = 2) -> dict[Coord, list[Coord]]:
        forks: dict[Coord, list[Coord]] = {}
        for move in self.legal_moves():
            outlets = self.threat_outlets(move, player)
            if len(outlets) >= minimum_outlets:
                forks[move] = outlets
        return forks

    def _windows(self) -> Iterable[tuple[Coord, ...]]:
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for r in range(self.size):
                for c in range(self.size):
                    end = (r + (self.k - 1) * dr, c + (self.k - 1) * dc)
                    if in_bounds(self.size, end):
                        yield tuple((r + i * dr, c + i * dc) for i in range(self.k))

    def active_line_points(self, player: int) -> set[Coord]:
        """Empty points in live k-windows already seeded by the given player."""
        points: set[Coord] = set()
        for window in self._windows():
            values = [self.board[r][c] for r, c in window]
            if opponent(player) not in values and player in values:
                points.update((r, c) for r, c in window if self.board[r][c] == EMPTY)
        return points

    def ownership_ambiguity_points(self) -> set[Coord]:
        return self.active_line_points(BLACK) & self.active_line_points(WHITE)

    def boundary_points(self) -> set[Coord]:
        """Empty 8-neighbour frontier points touching both owners."""
        result: set[Coord] = set()
        for r, c in self.legal_moves():
            owners: set[int] = set()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if in_bounds(self.size, (rr, cc)) and self.board[rr][cc] != EMPTY:
                        owners.add(self.board[rr][cc])
            if owners == {BLACK, WHITE}:
                result.add((r, c))
        return result

    def metrics(self, player: Optional[int] = None) -> WRRAMetrics:
        p = self.to_move if player is None else player
        immediate = self.immediate_wins(p)
        forks = self.fork_moves(p)
        phenotype_events = len(immediate) + len(forks)
        return WRRAMetrics(
            legal_actions=len(self.legal_moves()),
            boundary_points=len(self.boundary_points()),
            ownership_ambiguity=len(self.ownership_ambiguity_points()),
            residue_units=0,  # freestyle Omok is Markovian in board + side-to-move
            phenotype_events=phenotype_events,
        )


@dataclass(frozen=True)
class GoMoveResult:
    state: "GoState"
    captured: int


@dataclass(frozen=True)
class GoState:
    board: BoardHash
    to_move: int = BLACK
    previous_board: Optional[BoardHash] = None
    history: frozenset[BoardHash] = frozenset()
    ko_rule: str = "simple"  # none, simple, positional_superko

    @property
    def size(self) -> int:
        return len(self.board)

    @staticmethod
    def empty(size: int = 9, ko_rule: str = "simple") -> "GoState":
        b = tuple(tuple(0 for _ in range(size)) for _ in range(size))
        return GoState(b, BLACK, None, frozenset({b}), ko_rule)

    def neighbours(self, move: Coord) -> list[Coord]:
        r, c = move
        return [
            (rr, cc)
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if in_bounds(self.size, (rr, cc))
        ]

    def group_and_liberties(
        self, start: Coord, board: Optional[Sequence[Sequence[int]]] = None
    ) -> tuple[set[Coord], set[Coord]]:
        b = self.board if board is None else board
        color = b[start[0]][start[1]]
        if color == EMPTY:
            return set(), set()
        group = {start}
        liberties: set[Coord] = set()
        stack = [start]
        while stack:
            point = stack.pop()
            for nb in self.neighbours(point):
                value = b[nb[0]][nb[1]]
                if value == EMPTY:
                    liberties.add(nb)
                elif value == color and nb not in group:
                    group.add(nb)
                    stack.append(nb)
        return group, liberties

    def groups(self, player: Optional[int] = None) -> list[tuple[set[Coord], set[Coord], int]]:
        seen: set[Coord] = set()
        result: list[tuple[set[Coord], set[Coord], int]] = []
        for r in range(self.size):
            for c in range(self.size):
                color = self.board[r][c]
                if color == EMPTY or (player is not None and color != player) or (r, c) in seen:
                    continue
                group, liberties = self.group_and_liberties((r, c))
                seen.update(group)
                result.append((group, liberties, color))
        return result

    def play(self, move: Optional[Coord]) -> GoMoveResult:
        if move is None:  # pass is always legal
            current = board_hash(self.board)
            new_history = frozenset(set(self.history) | {current})
            return GoMoveResult(
                GoState(self.board, opponent(self.to_move), current, new_history, self.ko_rule), 0
            )
        if not in_bounds(self.size, move) or self.board[move[0]][move[1]] != EMPTY:
            raise ValueError(f"illegal Go move: {move}")
        b = board_copy(self.board)
        b[move[0]][move[1]] = self.to_move
        captured_points: set[Coord] = set()
        for nb in self.neighbours(move):
            if b[nb[0]][nb[1]] != opponent(self.to_move):
                continue
            group, liberties = self.group_and_liberties(nb, b)
            if not liberties:
                captured_points.update(group)
        for r, c in captured_points:
            b[r][c] = EMPTY
        own_group, own_liberties = self.group_and_liberties(move, b)
        if not own_group or not own_liberties:
            raise ValueError(f"suicide is not allowed: {move}")
        new_hash = board_hash(b)
        if self.ko_rule == "simple" and self.previous_board is not None and new_hash == self.previous_board:
            raise ValueError(f"simple-ko recapture is not allowed: {move}")
        if self.ko_rule == "positional_superko" and new_hash in self.history:
            raise ValueError(f"positional-superko repetition is not allowed: {move}")
        new_history = frozenset(set(self.history) | {new_hash})
        return GoMoveResult(
            GoState(new_hash, opponent(self.to_move), board_hash(self.board), new_history, self.ko_rule),
            len(captured_points),
        )

    def legal_moves(self, player: Optional[int] = None) -> list[Coord]:
        state = self if player is None or player == self.to_move else GoState(
            self.board, player, self.previous_board, self.history, self.ko_rule
        )
        result: list[Coord] = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] != EMPTY:
                    continue
                try:
                    state.play((r, c))
                    result.append((r, c))
                except ValueError:
                    pass
        return result

    def capture_moves(self, player: Optional[int] = None) -> dict[Coord, int]:
        p = self.to_move if player is None else player
        state = self if p == self.to_move else GoState(
            self.board, p, self.previous_board, self.history, self.ko_rule
        )
        captures: dict[Coord, int] = {}
        for move in state.legal_moves():
            result = state.play(move)
            if result.captured:
                captures[move] = result.captured
        return captures

    def atari_groups(self) -> list[tuple[set[Coord], set[Coord], int]]:
        return [entry for entry in self.groups() if len(entry[1]) == 1]

    def empty_regions(self) -> list[tuple[set[Coord], set[int]]]:
        seen: set[Coord] = set()
        regions: list[tuple[set[Coord], set[int]]] = []
        for r in range(self.size):
            for c in range(self.size):
                start = (r, c)
                if self.board[r][c] != EMPTY or start in seen:
                    continue
                region = {start}
                bordering: set[int] = set()
                stack = [start]
                seen.add(start)
                while stack:
                    point = stack.pop()
                    for nb in self.neighbours(point):
                        value = self.board[nb[0]][nb[1]]
                        if value == EMPTY and nb not in seen:
                            seen.add(nb)
                            region.add(nb)
                            stack.append(nb)
                        elif value != EMPTY:
                            bordering.add(value)
                regions.append((region, bordering))
        return regions

    def territory(self) -> dict[str, set[Coord]]:
        result = {"black": set(), "white": set(), "contested": set(), "neutral": set()}
        for region, bordering in self.empty_regions():
            if bordering == {BLACK}:
                result["black"].update(region)
            elif bordering == {WHITE}:
                result["white"].update(region)
            elif bordering == {BLACK, WHITE}:
                result["contested"].update(region)
            else:
                result["neutral"].update(region)
        return result

    def boundary_points(self) -> set[Coord]:
        """Points participating in a black-white ownership interface."""
        result: set[Coord] = set()
        for r in range(self.size):
            for c in range(self.size):
                value = self.board[r][c]
                neighbour_values = {
                    self.board[rr][cc] for rr, cc in self.neighbours((r, c))
                }
                if value == EMPTY:
                    owners = set(neighbour_values)
                    owners.discard(EMPTY)
                    if owners == {BLACK, WHITE}:
                        result.add((r, c))
                elif opponent(value) in neighbour_values:
                    result.add((r, c))
        return result

    def metrics(self) -> WRRAMetrics:
        territory = self.territory()
        captures = self.capture_moves()
        atari_count = len(self.atari_groups())
        residue_units = 0
        if self.ko_rule == "simple" and self.previous_board is not None:
            residue_units = 1
        elif self.ko_rule == "positional_superko":
            residue_units = len(self.history)
        return WRRAMetrics(
            legal_actions=len(self.legal_moves()) + 1,  # pass included
            boundary_points=len(self.boundary_points()),
            ownership_ambiguity=len(territory["contested"]),
            residue_units=residue_units,
            phenotype_events=len(captures) + atari_count,
        )


def omok_constructive_state() -> OmokState:
    size = 9
    b = [[EMPTY for _ in range(size)] for _ in range(size)]
    for r, c in ((4, 2), (4, 3), (4, 5), (2, 4), (3, 4), (5, 4)):
        b[r][c] = BLACK
    # One white stone touches the black structure so the interface boundary is
    # non-empty, without changing the four-outlet constructive proof.
    for r, c in ((1, 1), (1, 7), (3, 3), (7, 7)):
        b[r][c] = WHITE
    return OmokState(board_hash(b), BLACK, 5)


def go_ko_state(ko_rule: str = "simple") -> GoState:
    size = 5
    b = [[EMPTY for _ in range(size)] for _ in range(size)]
    for r, c in ((1, 2), (3, 2), (2, 1)):
        b[r][c] = BLACK
    for r, c in ((2, 2), (1, 3), (3, 3), (2, 4)):
        b[r][c] = WHITE
    h = board_hash(b)
    return GoState(h, BLACK, None, frozenset({h}), ko_rule)


def go_territory_state() -> GoState:
    size = 7
    b = [[EMPTY for _ in range(size)] for _ in range(size)]
    for r, c in ((2, 3), (3, 2), (3, 4), (4, 3)):
        b[r][c] = BLACK
    for r, c in ((0, 1), (1, 0), (1, 2), (2, 1)):
        b[r][c] = WHITE
    h = board_hash(b)
    return GoState(h, BLACK, None, frozenset({h}), "simple")


def raw_state_bounds() -> dict[str, dict[str, str | float | int]]:
    omok_15 = 3 ** (15 * 15)
    go_19 = 3 ** (19 * 19)
    omok_first_10_sequences = math.prod(range(225 - 10 + 1, 225 + 1))
    return {
        "omok_15x15": {
            "raw_ternary_configurations": str(omok_15),
            "log10_raw_configurations": math.log10(omok_15),
            "ordered_first_10_move_sequences_ignoring_early_terminal_states": str(
                omok_first_10_sequences
            ),
            "log10_first_10_sequences": math.log10(omok_first_10_sequences),
        },
        "go_19x19": {
            "raw_ternary_configurations_upper_bound": str(go_19),
            "log10_raw_configurations_upper_bound": math.log10(go_19),
        },
    }


def run_experiments() -> dict:
    # Omok: a single move creates four distinct next-turn winning outlets.
    omok = omok_constructive_state()
    center = (4, 4)
    forks = omok.fork_moves(BLACK)
    center_outlets = forks.get(center, [])
    after_omok = omok.play(center)
    assert not after_omok.is_win_at(center, BLACK)
    assert set(center_outlets) == {(4, 1), (4, 6), (1, 4), (6, 4)}
    assert len(center_outlets) == 4
    assert after_omok.immediate_wins(WHITE) == []
    omok_escape_responses: list[Coord] = []
    for response in after_omok.legal_moves():
        responded = after_omok.play(response)
        if responded.is_win_at(response, WHITE) or not responded.immediate_wins(BLACK):
            omok_escape_responses.append(response)
    assert omok_escape_responses == []

    # Go: one move captures a stone and creates a simple-ko residue.
    go_before = go_ko_state("simple")
    capture = (2, 3)
    recapture = (2, 2)
    go_result = go_before.play(capture)
    assert go_result.captured == 1
    go_after = go_result.state
    ko_blocked = False
    try:
        go_after.play(recapture)
    except ValueError:
        ko_blocked = True
    assert ko_blocked

    # Same visible board without the one-step residue permits the recapture.
    no_residue = GoState(
        go_after.board,
        WHITE,
        None,
        frozenset({go_after.board}),
        "simple",
    )
    free_recapture = no_residue.play(recapture)
    assert free_recapture.captured == 1
    assert free_recapture.state.board == go_before.board
    legal_with_residue = len(go_after.legal_moves()) + 1
    legal_without_residue = len(no_residue.legal_moves()) + 1
    assert legal_without_residue == legal_with_residue + 1

    # Go territory: exact empty-region ownership is derived from bordering colors.
    territory_state = go_territory_state()
    territory = territory_state.territory()
    assert (3, 3) in territory["black"]
    assert (1, 1) in territory["white"]

    omok_metrics = omok.metrics(BLACK)
    go_before_metrics = go_before.metrics()
    go_after_metrics = go_after.metrics()

    return {
        "metadata": {
            "profile": "WRRA-Game 0.1",
            "core": "WRRA Core 1.0 frozen",
            "author": "Wonsik Choi",
            "email": "janefather@gmail.com",
            "date": "2026-09-16",
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
        "omok": {
            "board_size": 9,
            "win_length": 5,
            "ruleset": "freestyle; five or more wins; no forbidden-move rule",
            "tested_move": list(center),
            "immediate_win": False,
            "created_next_turn_win_outlets": [list(x) for x in sorted(center_outlets)],
            "outlet_count": len(center_outlets),
            "defensive_replies_checked": len(after_omok.legal_moves()),
            "defensive_replies_escaping_all_immediate_wins": len(omok_escape_responses),
            "forced_win_in_two_plies_from_tested_move": True,
            "all_fork_moves": {
                str(move): [list(x) for x in sorted(outlets)] for move, outlets in sorted(forks.items())
            },
            "legal_move_count": len(omok.legal_moves()),
            "fork_candidate_count": len(forks),
            "candidate_reduction_fraction": 1 - len(forks) / len(omok.legal_moves()),
            "metrics_before": asdict(omok_metrics),
            "minimal_residue": "board plus side-to-move; no additional history for freestyle rules",
        },
        "go": {
            "board_size": 5,
            "ruleset": "orthogonal liberties; capture; suicide forbidden; simple ko; pass allowed",
            "tested_capture_move": list(capture),
            "captured_stones": go_result.captured,
            "tested_recapture_move": list(recapture),
            "recapture_with_residue": "illegal",
            "recapture_without_residue": "legal",
            "recapture_restores_prior_board": free_recapture.state.board == go_before.board,
            "legal_actions_with_residue": legal_with_residue,
            "legal_actions_without_residue": legal_without_residue,
            "metrics_before": asdict(go_before_metrics),
            "metrics_after": asdict(go_after_metrics),
            "minimal_residue": "one previous-board hash under simple ko; visited-state set under positional superko",
            "territory_test": {
                "black_exact_region_points": len(territory["black"]),
                "white_exact_region_points": len(territory["white"]),
                "contested_points": len(territory["contested"]),
                "black_center_owned": (3, 3) in territory["black"],
                "white_center_owned": (1, 1) in territory["white"],
            },
        },
        "state_space": raw_state_bounds(),
        "claim_status": {
            "core_mapping": "IMPLEMENTED",
            "constructive_phenotype_tests": "PASSED",
            "ko_residue_test": "PASSED",
            "general_playing_strength": "NOT_TESTED",
            "superiority_to_specialized_engines": "NOT_CLAIMED",
        },
    }


def draw_board(
    state_board: BoardHash,
    ax: plt.Axes,
    title: str,
    highlights: Optional[dict[Coord, tuple[str, str]]] = None,
) -> None:
    size = len(state_board)
    ax.set_facecolor("#D9A85F")
    for i in range(size):
        ax.plot([0, size - 1], [i, i], color="#3A2A1F", lw=0.8, zorder=0)
        ax.plot([i, i], [0, size - 1], color="#3A2A1F", lw=0.8, zorder=0)
    for r in range(size):
        for c in range(size):
            value = state_board[r][c]
            if value == EMPTY:
                continue
            color = "#111111" if value == BLACK else "#F5F5F5"
            edge = "#000000" if value == BLACK else "#777777"
            ax.scatter(c, size - 1 - r, s=390 if size <= 7 else 260, c=color, edgecolors=edge, zorder=3)
    if highlights:
        for (r, c), (symbol, color) in highlights.items():
            ax.scatter(c, size - 1 - r, s=520 if size <= 7 else 360, facecolors="none", edgecolors=color, linewidths=2.3, zorder=4)
            ax.text(c, size - 1 - r, symbol, color=color, ha="center", va="center", fontsize=10, fontweight="bold", zorder=5)
    ax.set_xlim(-0.6, size - 0.4)
    ax.set_ylim(-0.6, size - 0.4)
    ax.set_aspect("equal")
    ax.set_xticks(range(size), [str(i) for i in range(size)])
    ax.set_yticks(range(size), [str(size - 1 - i) for i in range(size)])
    ax.tick_params(length=0, labelsize=8)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)


def create_figures(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    omok = omok_constructive_state()
    move = (4, 4)
    after = omok.play(move)
    outlets = omok.threat_outlets(move, BLACK)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.8), constrained_layout=True)
    draw_board(omok.board, axes[0], "오목 착수 전", {move: ("M", "#D62728")})
    markers = {p: ("T", "#1F77B4") for p in outlets}
    markers[move] = ("M", "#D62728")
    draw_board(after.board, axes[1], "중앙 착수 뒤 발생한 4개 승리 출구", markers)
    fig.suptitle("동일한 국소 규칙에서 복수위협 표현형의 발생", fontsize=14, fontweight="bold")
    omok_path = output_dir / "figure_omok_fork.png"
    fig.savefig(omok_path, dpi=220, facecolor="white")
    plt.close(fig)

    before = go_ko_state("simple")
    result = before.play((2, 3))
    go_after = result.state
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.4), constrained_layout=True)
    draw_board(before.board, axes[0], "바둑 포획 전", {(2, 3): ("M", "#D62728")})
    draw_board(go_after.board, axes[1], "포획 뒤 패 residue 발생", {(2, 2): ("K", "#9467BD")})
    fig.suptitle("한 번의 갱신이 포획과 반복금지 상태를 함께 만든다", fontsize=14, fontweight="bold")
    go_ko_path = output_dir / "figure_go_ko.png"
    fig.savefig(go_ko_path, dpi=220, facecolor="white")
    plt.close(fig)

    territory_state = go_territory_state()
    territory = territory_state.territory()
    highlights: dict[Coord, tuple[str, str]] = {}
    highlights.update({p: ("B", "#1F77B4") for p in territory["black"]})
    highlights.update({p: ("W", "#D62728") for p in territory["white"]})
    fig, ax = plt.subplots(figsize=(5.8, 5.4), constrained_layout=True)
    draw_board(territory_state.board, ax, "빈 영역의 경계 소유자에서 영역 표현형 도출", highlights)
    territory_path = output_dir / "figure_go_territory.png"
    fig.savefig(territory_path, dpi=220, facecolor="white")
    plt.close(fig)

    return {
        "omok_fork": str(omok_path),
        "go_ko": str(go_ko_path),
        "go_territory": str(territory_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("wrra_game_output"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    results = run_experiments()
    results["figures"] = create_figures(args.output_dir)
    result_path = args.output_dir / "wrra_game_0_1_results.json"
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nSaved results to {result_path}")


if __name__ == "__main__":
    main()
