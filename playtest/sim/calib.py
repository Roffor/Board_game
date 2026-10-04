import sys, time
from engine import *
from cards import *
seed=int(sys.argv[1]) if len(sys.argv)>1 else 1
res=[]
t=time.time()
for tier,pool in ((1,TIER1),(2,TIER2),('elite',ELITES)):
    for ed in pool:
        for s in range(3):
            g=Game(seed*100+s,[])
            r=g.fight(ed,tier,LOCATIONS[s%len(LOCATIONS)])
            res.append((tier,ed['name'],r['won'],r['rounds'],round(r['sec']/60,1),r['hp_loss']))
for x in res: print(x)
print('time',time.time()-t)
