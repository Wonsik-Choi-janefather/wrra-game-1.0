"""Verify the completed public game against the frozen pre-match policy."""
import hashlib,json,pathlib,sys
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent))
from strategy import plant,step,select,oracle

def verify(attempt=0):
    root=pathlib.Path(__file__).resolve().parent
    final=json.loads((root/'final.json').read_text())
    counts={'legal_actions':0,'commitments':0,'generations':0,'policy_reproductions':0,'continuity':0}
    previous=np.zeros((final['height'],final['width']),dtype=np.uint8)
    scores=[]
    for h in final['history']:
        r=h['round'];b=np.array(h['board_before'],dtype=np.uint8).reshape(h['height'],h['width'])
        assert np.array_equal(b,previous);counts['continuity']+=1
        for color in ['red','blue']:
            a=h[color+'_placements'];assert len(a)==h['seed_budget']==len(set(map(tuple,a)))
            assert all(b[y,x]==0 for x,y in a);counts['legal_actions']+=1
            canonical=json.dumps(dict(match_id=final['id'],round=r,placements=a,nonce=h['reveal_nonces'][color]),separators=(',',':'))
            assert hashlib.sha256(canonical.encode()).hexdigest()==h['commitments'][color];counts['commitments']+=1
        chosen,ledger=select(b,h['seed_budget'],h['generations'],2026100520+1000*attempt+r,round_number=r)
        assert list(map(list,chosen))==h['blue_placements'];counts['policy_reproductions']+=1
        b=plant(b,h['blue_placements'],h['red_placements'])
        assert b.ravel().tolist()==h['board_seeded']
        for _ in range(h['generations']):
            assert np.array_equal(step(b),oracle(b));b=step(b);counts['generations']+=1
        assert b.ravel().tolist()==h['board_after'];previous=b
        scores.append(dict(round=r,blue=int((b==2).sum()),red=int((b==1).sum()),neutral=int((b==3).sum())))
    assert previous.ravel().tolist()==final['board'] and final['status']=='complete'
    result=dict(passed=True,match_id=final['id'],strategy_commit='0646f21f8bbcacbb4a49052534d96148f13e3c6c',
                strategy_doi='10.5281/zenodo.23148756',checks=counts,scores=scores,
                winner_names=final['winner_names'],completion_reason=final['completion_reason'],
                final_margin=final['blue_score']-final['red_score'],state_hash=final['state_hash'])
    (root/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':verify(int(sys.argv[1]) if len(sys.argv)>1 else 0)
