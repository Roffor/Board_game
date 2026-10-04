# -*- coding: utf-8 -*-
"""Фаза В: каждый апгрейд Жреца против базы (парные бои), ситуации II / элита / босс.
python3 gen_v.py out.json P.json n [pool.json] [start.json]"""
import json, sys
import priest
P = json.load(open(sys.argv[2])); n = int(sys.argv[3])
pool = json.load(open(sys.argv[4])) if len(sys.argv) > 4 and sys.argv[4] != '-' else priest.UPGRADES
start = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
S = ['II', 'EL', 'BOSS']
V = [dict(label='base', cards=[], P=P, n=n, sits=S, pool=pool)]
for c in pool:
    V.append(dict(label=c, cards=[c], P=P, n=n, sits=S, pool=pool))
if start:
    for v in V:
        v['start'] = start
json.dump(V, open(sys.argv[1], 'w'), ensure_ascii=False)
print(len(V), 'вариантов')
