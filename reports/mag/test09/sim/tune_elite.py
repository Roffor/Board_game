import sys, json
from bench import *
import bench; bench.VERBOSE=True
cfg=json.loads(sys.argv[1])
hp=cfg['hpe']; 
def mk(ae):
    return lambda ed: hp.get(ed['name'], ed['hp'])
groups=[]
for ed in ELITES:
    a=cfg['ae'].get(ed['name'],1.0)
    groups.append((ed['name']+' рано',[ed],'elite',2,False,mk(a),a))
    groups.append((ed['name']+' поздно',[ed],'elite',5,True,mk(a),a))
run(groups,reps=cfg.get('reps',16))
