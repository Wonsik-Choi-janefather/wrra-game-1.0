"""WRRA Jimothy 0.1: budgeted, robust trajectory renderer. CC BY 4.0."""
import argparse, hashlib, json, pathlib
import numpy as np

OFFSETS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
PATTERNS = [
    [(0,0),(1,0),(0,1),(1,1)], # block
    [(0,0),(1,0),(2,0)],       # blinker
    [(1,0),(2,1),(0,2),(1,2),(2,2)], # glider
    [(1,0),(2,0),(0,1),(1,1),(1,2)], # R-pentomino
    [(0,0),(1,0),(2,0),(0,1),(1,2)], # five-cell seed
    [(1,0),(2,0),(0,1),(3,1),(1,2),(2,2)], # beehive
]

def neighbors(a):
    return sum(np.roll(a, (dy, dx), axis=(-2,-1)) for dy,dx in OFFSETS)

def step(board):
    """Works on HxW or batched NxHxW; implements all eight allegiances."""
    n = neighbors((board != 0).astype(np.int16))
    counts = np.stack([neighbors((board == c).astype(np.int16)) for c in (1,2,4,5,6,7,8,9)])
    largest = counts.max(axis=0)
    colors = np.array([1,2,4,5,6,7,8,9], dtype=np.uint8)
    owner = colors[counts.argmax(axis=0)]
    owner = np.where((largest == 0) | ((counts == largest).sum(axis=0) > 1), 3, owner)
    return np.where((board != 0) & ((n == 2) | (n == 3)), board,
                    np.where((board == 0) & (n == 3), owner, 0)).astype(np.uint8)

def plant(board, blue, red):
    b = board.copy()
    for x,y in blue: b[y,x] = 2
    for x,y in red: b[y,x] = 3 if b[y,x] == 2 else 1
    return b

def random_move(board, budget, rng):
    h,w = board.shape
    ids = rng.choice(np.flatnonzero(board.ravel() == 0), budget, replace=False)
    return [(int(i%w),int(i//w)) for i in ids]

def pattern_move(board, budget, rng):
    h,w = board.shape
    cells = set()
    for _ in range(100):
        p = PATTERNS[int(rng.integers(len(PATTERNS)))]
        x,y = int(rng.integers(w)),int(rng.integers(h))
        rot = int(rng.integers(4))
        shifted = []
        for dx,dy in p:
            for _ in range(rot): dx,dy = -dy,dx
            shifted.append(((x+dx)%w,(y+dy)%h))
        if len(cells)+len(shifted) <= budget and all(board[yy,xx] == 0 and (xx,yy) not in cells for xx,yy in shifted):
            cells.update(shifted)
        if len(cells) == budget: break
    dead = [(int(i%w),int(i//w)) for i in rng.permutation(np.flatnonzero(board.ravel() == 0))]
    for c in dead:
        if len(cells) == budget: break
        cells.add(c)
    return sorted(cells,key=lambda c:(c[1],c[0]))

def select(board, budget, generations, seed, mode='wrra', candidates=96, scenarios=4):
    """Equal candidate/scenario/tick budget for WRRA and mean-only ablation.

    WRRA utility: .6 mean score margin + .4 worst scenario margin
    + .1 mean late-generation margin. Baseline uses mean terminal margin.
    No live opponent reveal is used; historical residue is an audit only in v0.1.
    """
    rng = np.random.default_rng(seed)
    moves = [pattern_move(board,budget,rng) if i%4 else random_move(board,budget,rng)
             for i in range(candidates)]
    opponents = [pattern_move(board,budget,rng) if i%2 else random_move(board,budget,rng)
                 for i in range(scenarios)]
    boards = np.stack([plant(board,a,o) for a in moves for o in opponents])
    late = []
    for t in range(generations):
        boards = step(boards)
        if t >= max(0,generations-3):
            late.append((boards == 2).sum(axis=(-2,-1))-(boards == 1).sum(axis=(-2,-1)))
    margins = ((boards == 2).sum(axis=(-2,-1))-(boards == 1).sum(axis=(-2,-1))).reshape(candidates,scenarios)
    late_margin = np.mean(late,axis=0).reshape(candidates,scenarios).mean(axis=1)
    means, worst = margins.mean(axis=1), margins.min(axis=1)
    utility = means if mode == 'mean' else .6*means+.4*worst+.1*late_margin
    best = int(np.argmax(utility))
    chosen = sorted(moves[best],key=lambda c:(c[1],c[0]))
    assert len(chosen) == len(set(chosen)) == budget and all(board[y,x] == 0 for x,y in chosen)
    ledger = dict(seed=int(seed),mode=mode,candidates=candidates,scenarios=scenarios,
                  budget=budget,generations=generations,selected_candidate=best,
                  mean_terminal_margin=float(means[best]),worst_terminal_margin=int(worst[best]),
                  late_margin=float(late_margin[best]),utility=float(utility[best]),
                  placements=chosen,scenario_margins=margins[best].tolist(),
                  board_sha256=hashlib.sha256(board.tobytes()).hexdigest())
    return chosen,ledger

def oracle(board):
    out = np.zeros_like(board);h,w = board.shape
    for y in range(h):
        for x in range(w):
            ns=[int(board[(y+dy)%h,(x+dx)%w]) for dy,dx in OFFSETS]
            live=[c for c in ns if c]
            if board[y,x] and len(live) in (2,3): out[y,x]=board[y,x]
            elif not board[y,x] and len(live) == 3:
                counts={c:live.count(c) for c in set(live) if c != 3}
                mx=max(counts.values(),default=0);winners=[c for c,n in counts.items() if n==mx]
                out[y,x]=winners[0] if len(winners)==1 else 3
    return out

def tests():
    rng=np.random.default_rng(101)
    for _ in range(40):
        b=rng.choice([0,0,0,1,2,3,4,5,6,7,8,9],size=(12,13)).astype(np.uint8)
        assert np.array_equal(step(b),oracle(b))
    b=np.zeros((12,12),dtype=np.uint8)
    b[0,11]=b[0,0]=b[0,1]=2
    s=step(b); assert s[11,0]==s[0,0]==s[1,0]==2 and (s==2).sum()==3
    for parents,expected in [([1,2,3],3),([1,3,3],1),([3,3,3],3),([1,2,4],3),([2,2,1],2)]:
        b[:]=0;b[4,4],b[4,5],b[4,6]=parents;assert step(b)[5,5]==expected
    b[:]=0;assert plant(b,[(0,0)],[(0,0)])[0,0]==3
    print('47 independent rule/edge checks PASS')

def benchmark(out, games=12):
    records=[]
    for k in range(games):
        opponent_kind=['random','pattern'][k%2]
        for mode in ['wrra','mean']:
            b=np.zeros((24,24),dtype=np.uint8);rng=np.random.default_rng(30000+k)
            turns=[]
            for r in range(1,8):
                budget=20 if r==1 else 6
                a,ledger=select(b,budget,8,20261005+k*100+r,mode,candidates=48,scenarios=4)
                o=(random_move if opponent_kind=='random' else pattern_move)(b,budget,rng)
                b=plant(b,a,o)
                for _ in range(8):b=step(b)
                ledger.update(round=r,blue=int((b==2).sum()),red=int((b==1).sum()))
                turns.append(ledger)
            margin=int((b==2).sum()-(b==1).sum())
            records.append(dict(game=k,opponent=opponent_kind,mode=mode,margin=margin,rounds=turns))
            print(k,opponent_kind,mode,margin,flush=True)
    summary={m:dict(wins=sum(x['margin']>0 for x in records if x['mode']==m),
                    draws=sum(x['margin']==0 for x in records if x['mode']==m),
                    losses=sum(x['margin']<0 for x in records if x['mode']==m),
                    mean_margin=float(np.mean([x['margin'] for x in records if x['mode']==m]))) for m in ['wrra','mean']}
    data=dict(version='0.1',date='2026-10-05',games_per_policy=games,search_rollouts_per_move=192,
              note='Synthetic local opponents, not 0xtopus. Paired opponent RNG seeds; boards diverge across policies.',summary=summary,records=records)
    pathlib.Path(out).write_text(json.dumps(data,indent=2));print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['test','benchmark']);p.add_argument('--output',default='benchmark.json');p.add_argument('--games',type=int,default=12)
    args=p.parse_args()
    if args.command=='test':tests()
    else:benchmark(args.output,args.games)
