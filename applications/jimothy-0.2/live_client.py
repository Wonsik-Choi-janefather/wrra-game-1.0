"""Join only after the strategy release has been published. Secrets stay local."""
import argparse,hashlib,json,os,pathlib,secrets,time,urllib.request
import numpy as np
from strategy import select
BASE='https://k8r.food/jimothyislife/api'

def request(path,data=None,token=None):
    headers={'Content-Type':'application/json','User-Agent':'WRRA-Jimothy/0.2'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)

def run(private,output,attempt=0):
    private=pathlib.Path(private);out=pathlib.Path(output);out.mkdir(exist_ok=True)
    if private.exists():creds=json.loads(private.read_text());mid=creds['match_id'];token=creds['player_token']
    else:
        lobby=request('/lobby')['matches']
        match=next(m for m in lobby if m['status']=='open' and m.get('hosted') and not m.get('reserved'))
        mid=match['id'];joined=request('/matches/'+mid+'/join',{'agent_name':'wrraresearchledger'})
        token=joined['player_token'];creds=dict(match_id=mid,player_token=token)
        private.write_text(json.dumps(creds));os.chmod(private,0o600)
        assert joined['player']=='blue',joined['player']
        print('JOINED',mid,flush=True)
    while True:
        m=request('/matches/'+mid)['match']
        if m['status']=='complete':break
        assert m['max_rounds']==7 and m['width']==m['height']==24, 'This policy is frozen for Classic'
        r=m['round'];prefix=out/f'round-{r}'
        pending=private.with_name(private.name+'.pending-'+str(r))
        if m['phase']=='commit' and not m['committed']['blue']:
            b=np.array(m['board'],dtype=np.uint8).reshape(m['height'],m['width'])
            move,ledger=select(b,m['seed_budget'],m['generations_this_round'],2026100520+1000*attempt+r,round_number=r)
            nonce=secrets.token_hex(24)
            payload=dict(match_id=mid,round=r,placements=move,nonce=nonce)
            commitment=hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
            pending.write_text(json.dumps(payload));os.chmod(pending,0o600)
            ledger.update(match_id=mid,round=r,commitment=commitment,opponent_reveal_used=False)
            prefix.with_suffix('.decision.json').write_text(json.dumps(ledger,indent=2))
            prefix.with_suffix('.before.json').write_text(json.dumps(m,indent=2))
            request('/matches/'+mid+'/commit',{'commitment':commitment},token)
            print('COMMIT round',r,flush=True)
        elif m['phase']=='reveal' and not m['revealed']['blue']:
            p=json.loads(pending.read_text())
            request('/matches/'+mid+'/reveal',dict(placements=p['placements'],nonce=p['nonce']),token)
            after=request('/matches/'+mid)['match']
            prefix.with_suffix('.after.json').write_text(json.dumps(after,indent=2))
            print('RESOLVED round',r,'blue',after['blue_score'],'red',after['red_score'],flush=True)
        else:
            print('WAIT',m['phase'],'round',r,flush=True);time.sleep(3)
    out.joinpath('final.json').write_text(json.dumps(m,indent=2))
    transcript=request('/matches/'+mid+'/transcript')
    out.joinpath('transcript.json').write_text(json.dumps(transcript,indent=2))
    print('COMPLETE',json.dumps({k:m.get(k) for k in ['id','blue_score','red_score','winner_names','completion_reason','state_hash']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private',required=True);p.add_argument('--output',default='live-results');p.add_argument('--attempt',type=int,default=0);a=p.parse_args();assert 0<=a.attempt<=2;run(a.private,a.output,a.attempt)
