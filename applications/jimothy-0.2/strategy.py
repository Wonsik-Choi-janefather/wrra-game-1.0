"""WRRA Jimothy 0.2: adversarial repairs and survival beyond the scoring tick."""
import hashlib,json,pathlib,argparse
import numpy as np
from rules_engine import neighbors,plant,random_move,pattern_move,oracle,step as full_step

def step(b):
    n=neighbors((b!=0).astype(np.int16));r=neighbors((b==1).astype(np.int16));u=neighbors((b==2).astype(np.int16))
    owner=np.where(r>u,1,np.where(u>r,2,3))
    return np.where((b!=0)&((n==2)|(n==3)),b,np.where((b==0)&(n==3),owner,0)).astype(np.uint8)

def mutate(board,move,budget,rng):
    h,w=board.shape;cells=set(move);remove=int(rng.integers(1,min(budget,5)+1))
    for i in rng.choice(len(move),remove,replace=False):cells.remove(move[int(i)])
    occupied=np.argwhere(board!=0)
    for _ in range(300):
        if len(cells)==budget:break
        kind=int(rng.integers(3))
        if kind==0 and occupied.size:
            y,x=occupied[int(rng.integers(len(occupied)))];x=(int(x)+int(rng.integers(-2,3)))%w;y=(int(y)+int(rng.integers(-2,3)))%h
        elif kind==1 and cells:
            x,y=sorted(cells)[int(rng.integers(len(cells)))];x=(x+int(rng.integers(-2,3)))%w;y=(y+int(rng.integers(-2,3)))%h
        else:x,y=int(rng.integers(w)),int(rng.integers(h))
        if board[y,x]==0:cells.add((x,y))
    for c in random_move(board,budget,rng):
        if len(cells)==budget:break
        cells.add(c)
    return sorted(cells,key=lambda c:(c[1],c[0]))

def pool(board,budget,rng,n):
    out=[]
    for i in range(n):
        a=pattern_move(board,budget,rng) if i%3 else random_move(board,budget,rng)
        if i%3==2:a=mutate(board,a,budget,rng)
        out.append(a)
    return out

def evolve(boards,generations,horizon):
    terminal=None
    for t in range(horizon):
        boards=step(boards)
        if t+1==generations:terminal=boards.copy()
    return terminal,boards

def margin(boards):return (boards==2).sum(axis=(-2,-1))-(boards==1).sum(axis=(-2,-1))

def red_scenarios(board,budget,generations,horizon,rng,blue_hint=()):
    """Search red repair/attack moves independently, without seeing our move."""
    candidates=pool(board,budget,rng,192)
    scores=None
    for stage in range(3):
        bs=np.stack([plant(board,blue_hint,a) for a in candidates])
        terminal,future=evolve(bs,generations,horizon)
        red_now=(terminal==1).sum(axis=(-2,-1));red_future=(future==1).sum(axis=(-2,-1))
        scores=-.45*margin(terminal)-.35*margin(future)+.1*red_now+.1*red_future
        elite=np.argsort(-scores,kind='stable')[:8]
        if stage<2:candidates=[candidates[int(i)] for i in elite]+[mutate(board,candidates[int(elite[j%8])],budget,rng) for j in range(120)]
    chosen=[]
    for i in np.argsort(-scores,kind='stable'):
        a=candidates[int(i)]
        if a not in chosen and all(len(set(a)&set(c)) <= max(1,budget//2) for c in chosen):chosen.append(a)
        if len(chosen)==4:break
    for i in np.argsort(-scores,kind='stable'):
        a=candidates[int(i)]
        if len(chosen)==4:break
        if a not in chosen:chosen.append(a)
    chosen += [pattern_move(board,budget,rng),random_move(board,budget,rng),[]]
    return chosen

def select(board,budget,generations,seed,round_number=1):
    assert not np.any(board>3),'v0.2 supports two-player games only'
    rng=np.random.default_rng(seed)
    horizon=generations if round_number==7 else 2*generations
    opponents=red_scenarios(board,budget,generations,horizon,rng)
    candidates=pool(board,budget,rng,256);nsc=len(opponents)
    evaluations=0;best_utility=-1e30;best_move=None;best_summary=None
    for stage in range(4):
        bs=np.stack([plant(board,a,o) for a in candidates for o in opponents])
        terminal,future=evolve(bs,generations,horizon)
        now=margin(terminal).reshape(len(candidates),nsc);later=margin(future).reshape(len(candidates),nsc)
        # Stress scenario with zero red recharge is intentionally hypothetical.
        # It keeps our own repair from relying on the opponent disrupting itself.
        utilities=.45*now.mean(axis=1)+.25*now.min(axis=1)+.2*later.mean(axis=1)+.1*later.min(axis=1)
        order=np.argsort(-utilities,kind='stable');idx=int(order[0]);evaluations+=len(candidates)*nsc
        if utilities[idx]>best_utility:
            best_utility=float(utilities[idx]);best_move=candidates[idx]
            best_summary=dict(scenario_terminal_margins=now[idx].tolist(),scenario_future_margins=later[idx].tolist(),
                              mean_terminal_margin=float(now[idx].mean()),worst_terminal_margin=int(now[idx].min()))
        if stage<3:
            elites=[candidates[int(i)] for i in order[:8]]
            candidates=elites+[mutate(board,elites[j%8],budget,rng) for j in range(120)]
            if stage==0:
                extra=red_scenarios(board,budget,generations,horizon,rng,blue_hint=best_move)[:4]
                opponents+=extra;nsc=len(opponents)
                # Candidate utilities before/after the adversarial update cannot
                # be compared directly; retained elites are re-evaluated next.
                best_utility=-1e30
    chosen=sorted(best_move,key=lambda c:(c[1],c[0]))
    assert len(chosen)==len(set(chosen))==budget and all(board[y,x]==0 for x,y in chosen)
    ledger=dict(version='0.2.0',seed=int(seed),round_number=round_number,budget=budget,generations=generations,
                horizon=horizon,blue_rollouts=evaluations,opponent_scenarios=nsc,opponent_search_candidates=896,
                utility=best_utility,placements=chosen,opponent_reveal_used=False,
                board_sha256=hashlib.sha256(board.tobytes()).hexdigest(),**best_summary)
    return chosen,ledger

def test():
    rng=np.random.default_rng(20261005)
    for _ in range(50):
        b=rng.choice([0,0,0,1,2,3],size=(24,24)).astype(np.uint8)
        assert np.array_equal(step(b),full_step(b)) and np.array_equal(step(b),oracle(b))
    print('50 optimized-engine/full-engine/scalar-oracle comparisons PASS')

def replay_positions(first_match,out):
    m=json.loads(pathlib.Path(first_match).read_text());rows=[]
    for h in m['history']:
        r=h['round'];b=np.array(h['board_before'],dtype=np.uint8).reshape(24,24)
        a,d=select(b,h['seed_budget'],h['generations'],2026100520+r,r)
        p=plant(b,a,h['red_placements'])
        for _ in range(h['generations']):p=step(p)
        row=dict(round=r,v01_blue=h['board_score']['blue'],v01_red=h['board_score']['red'],
                 v02_blue=int((p==2).sum()),v02_red=int((p==1).sum()),decision=d)
        rows.append(row);print({k:v for k,v in row.items() if k!='decision'},flush=True)
    data=dict(note='Retrospective diagnostic on seven fixed v0.1 positions. Recorded red actions are used only after selecting each blue action. These are not a coherent v0.2 game or held-out validation; improvement can overfit this first match.',rows=rows)
    pathlib.Path(out).write_text(json.dumps(data,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['test','diagnostic']);p.add_argument('--first-match');p.add_argument('--output',default='diagnostic.json');a=p.parse_args()
    if a.command=='test':test()
    else:replay_positions(a.first_match,a.output)
