# -*- coding: utf-8 -*-
"""Фаза Г, дотест: варианты чисел Суда и защиты Чудотворца на одних и тех же колодах (парно).
python3 gen_g2.py out.json core.json n"""
import json, sys, random
import burn11
out, coref, nf = sys.argv[1], sys.argv[2], int(sys.argv[3])
core = json.load(open(coref))['core']
burn11.M_bank(); MB = burn11.BUILD
mpure = {b: [c for c in burn11.CONCEPT if set(ch for ch in MB.get(c, '') if ch in 'СПМ') == {b}] for b in 'СПМ'}
VAR = {
 'V0': ({}, {}),
 'V1': ({'hh.big': 7, 'arch.b': 2, 'vk.b': 1, 'name.m': 2, 'tp.sh': 3, 'msh.s': 2}, {}),
 'V2': ({'hh.big': 7, 'arch.b': 2, 'vk.b': 1, 'name.m': 2, 'pillar.d': 2, 'brand.d': 1, 'vk.now': 2, 'tp.sh': 3, 'msh.s': 2}, {}),
 'V1s': ({'hh.big': 7, 'arch.b': 2, 'vk.b': 1, 'name.m': 2, 'tp.sh': 3, 'msh.s': 2}, {'y_brand': 'y_blind'}),
}
V = []
for name, (P, swap) in VAR.items():
    cr = {b: [swap.get(c, c) for c in l] for b, l in core.items()}
    rng = random.Random(777)
    for b in 'СЧ':
        for k in range(20):
            V.append(dict(sid='СЧ'.index(b) * 100 + k + 1, label=f'{name}|pure{b}_{k:02d}', cards=rng.sample(cr[b], 5), noup=True, draft=True, n=nf, P=P, sits=['EL', 'BOSS']))
    for b, mb in [('С', 'С'), ('С', 'П'), ('Ч', 'П')]:
        for k in range(10):
            V.append(dict(sid=300 + ['СС', 'СП', 'ЧП'].index(b + mb) * 100 + k + 1, label=f'{name}|pair{b}{mb}_{k:02d}', cards=rng.sample(cr[b], 5), mcards=rng.sample(mpure[mb], 5),
                          noup=True, draft=True, n=nf, P=P, sits=['EL', 'BOSS']))
json.dump(V, open(out, 'w'), ensure_ascii=False)
print('вариантов', len(V), 'боёв', sum(v['n'] * len(v['sits']) for v in V))
