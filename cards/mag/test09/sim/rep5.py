# -*- coding: utf-8 -*-
"""Сводка теста билда №5: парные разности с базой, сила [С 8.8], проблемные карты [С 8.9]."""
import json, sys, math, statistics as st
import burn2, burn5; burn2.P.update(burn5.DEFAULTS); from burn5 import M_bank
SITS = ['I', 'II', 'EL']; HP = 34
R = [r for r in json.load(open(sys.argv[1])) if 'error' not in r]
if len(sys.argv) > 2:
    R += [r for r in json.load(open(sys.argv[2])) if 'error' not in r and r['v'] != 'base']
by = {}
for r in R:
    by.setdefault(r['v'], {}).setdefault(r['sit'], {})[r['i']] = r
base = by['base']
def m(x): return sum(x) / len(x) if x else 0
def summary(v):
    d = by[v]; out = {}
    for s in SITS:
        ids = sorted(set(d[s]) & set(base[s]))
        dr = [d[s][i]['rounds'] - base[s][i]['rounds'] for i in ids]
        dt = [d[s][i]['taken'] - base[s][i]['taken'] for i in ids]
        comb = [-a / 0.3 - b / 1.5 for a, b in zip(dr, dt)]
        out[s] = dict(r=m([d[s][i]['rounds'] for i in ids]), t=m([d[s][i]['taken'] for i in ids]),
                      w=m([d[s][i]['won'] for i in ids]), var=m([d[s][i]['var'] for i in ids]),
                      pl=m([d[s][i]['played'] for i in ids]), dr=m(dr), dt=m(dt),
                      se=st.pstdev(comb) / math.sqrt(len(comb)),
                      burned=m([d[s][i].get('burned', 0) for i in ids]), ally=m([d[s][i].get('ally_burn', 0) for i in ids]),
                      spent=m([d[s][i].get('spent', 0) for i in ids]), stuck=sum(d[s][i].get('stuck', False) for i in ids))
    S = m([-out[s]['dr'] / 0.3 - out[s]['dt'] / 1.5 for s in SITS])
    se = math.sqrt(sum(out[s]['se'] ** 2 for s in SITS)) / 3
    pl = m([out[s]['pl'] for s in SITS])
    return dict(sits=out, S=S, se=se, pl=pl)
res = {v: summary(v) for v in by if v != 'base'}
res['base'] = {'sits': {s: dict(r=m([x['rounds'] for x in base[s].values()]), t=m([x['taken'] for x in base[s].values()]),
                                w=m([x['won'] for x in base[s].values()]), var=m([x['var'] for x in base[s].values()]),
                                burned=m([x.get('burned', 0) for x in base[s].values()]),
                                ally=m([x.get('ally_burn', 0) for x in base[s].values()]),
                                spent=m([x.get('spent', 0) for x in base[s].values()])) for s in SITS}}
json.dump(res, open(sys.argv[1] + '.sum.json', 'w'), ensure_ascii=False, indent=1)
name = {c.cid: c.name for c in M_bank()}
for s in SITS:
    b = res['base']['sits'][s]
    print('БАЗА', s, {k: round(v, 2) for k, v in b.items()})
for v, x in sorted(res.items(), key=lambda kv: -kv[1].get('S', 99)):
    if v == 'base': continue
    print(f"{name.get(v, v):28s} S={x['S']:+.2f}±{x['se']:.2f} pl={x['pl']:.2f} " +
          ' '.join(f"{s}:{x['sits'][s]['dr']:+.2f}/{x['sits'][s]['dt']:+.1f}" for s in SITS))
