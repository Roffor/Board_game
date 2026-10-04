import sys, json
from bench import *
cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
def hpf(key):
    v = cfg.get(key)
    if v is None: return None
    if isinstance(v, dict): return lambda ed: v.get(ed['name'], ed['hp'])
    return lambda ed: int(round(ed['hp'] * v))
A = lambda k: cfg.get(k, 1.0)
groups = [
 ('I ранний (0 апгр.)', TIER1, 1, 0, False, hpf('hp1'), A('a1'), cfg.get('sh1')),
 ('I середина (2 апгр.)', TIER1, 1, 2, False, hpf('hp1'), A('a1'), cfg.get('sh1')),
 ('II (5 апгр.+лег.)', TIER2, 2, 5, True, hpf('hp2'), A('a2'), cfg.get('sh2')),
 ('Элита рано (2 апгр.)', ELITES, 'elite', 2, False, hpf('hpe'), A('ae'), cfg.get('she')),
 ('Элита поздно (5+лег.)', ELITES, 'elite', 5, True, hpf('hpe'), A('ae'), cfg.get('she')),
 ('Босс (7+лег.)', [BOSS], 'boss', 7, True, hpf('hpb'), A('ab')),
]
import bench; bench.VERBOSE = bool(cfg.get('v'))
run(groups, reps=int(cfg.get('reps', 8)))
