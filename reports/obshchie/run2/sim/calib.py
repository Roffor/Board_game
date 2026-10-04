import sys, random
from engine import *
from cards import *
def upgrade(g, n, rs):
    for k,U in (('M',M_upgrades()),('P',P_upgrades())):
        rs.shuffle(U); h=g.H[k]
        for c in U[:n]:
            old=min(h.deck,key=lambda x:x.value)
            if c.value>old.value: h.deck.remove(old); h.deck.append(c)
def run(pools, nup, reps=4, seed=1):
    out=[]
    for tier,pool in pools:
        for ed in pool:
            rr=[];loss=[]
            for s in range(reps):
                g=Game(seed*1000+s,[]); upgrade(g,nup,random.Random(s))
                r=g.fight(ed,tier,LOCATIONS[s%len(LOCATIONS)])
                rr.append(r['rounds'] if r['won'] else -r['rounds']); loss.append(r['hp_loss']['M']+r['hp_loss']['P'])
            out.append((tier,ed['name'],rr,loss))
    return out
nup=int(sys.argv[1])
pools=[(1,TIER1),(2,TIER2),('elite',ELITES)] if nup<6 else [(2,TIER2),('elite',ELITES),('boss',[BOSS])]
for x in run(pools,nup): print(x)
