# -*- coding: utf-8 -*-
"""Фаза Б: стартовая колода. Варианты:
- swap_<cid>: кандидат вместо карты старта того же вида (самой слабой по value), по всем ситуациям;
- drop_<cid>: стартовая карта заменена «пустой» (Щит паломника 4 щита — нейтральная защита), чтобы видеть вклад каждой карты;
- combo_<a>_<b>: пара малого комбо в старте против двух эталонных карт (Кара + Щит веры) на тех же местах.
python3 gen_b.py out.json P.json [n]"""
import json, sys
import burn2, priest
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
burn2.P.update(priest.DEFAULTS); burn2.P.update(P)
D = list(priest.DEFAULT_START)
kind = {c: priest.make(c).kind for c in priest.START_CAND}
val = {c: priest.make(c).value for c in priest.START_CAND}
V = [dict(label='base', cards=[], P=P, n=n)]
for c in priest.START_CAND:
    if c in D:
        continue
    same = [x for x in D if kind[x] == kind[c]] or D
    t = min(same, key=lambda x: (val[x], x))
    s = list(D); s[s.index(t)] = c
    V.append(dict(label='swap_' + c, start=s, cards=[], P=P, n=n))
for c in sorted(set(D)):
    s = list(D); s[s.index(c)] = 'z_pshield'
    V.append(dict(label='drop_' + c, start=s, cards=[], P=P, n=n))
json.dump(V, open(sys.argv[1], 'w'), ensure_ascii=False)
print(len(V), 'вариантов')
