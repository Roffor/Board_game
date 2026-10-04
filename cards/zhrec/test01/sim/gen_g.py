# -*- coding: utf-8 -*-
"""Фаза Г теста Жреца: драфт Жреца, чистые билды Жреца, матрица пар билд Жреца × билд мага.
Драфт: 5 выборов «1 из 3» из пула, игрок держится билда (буквы С/П/Ч), среди подходящих берёт случайную.
У мага в драфте и чистых билдах Жреца — случайные апгрейды концепта (как в фазе В).
python3 gen_g.py out.json pool.json P.json [N драфтов] [боёв на ситуацию] [core.json — чистые билды по основным 10]"""
import json, sys, random
import priest, burn11
out, poolf, Pf = sys.argv[1:4]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 200; nf = int(sys.argv[5]) if len(sys.argv) > 5 else 10
NP = int(sys.argv[7]) if len(sys.argv) > 7 else 10
pool = json.load(open(poolf)); P = json.load(open(Pf)); rng = random.Random(5151)
S = ['II', 'EL', 'BOSS']
L = lambda c: set(ch for ch in priest.INFO[c][1] if ch in 'СПЧ')
V = []
for k in range(N):
    deck = []
    for _ in range(5):
        cand = rng.sample([c for c in pool if c not in deck], 3)
        cnt = {}
        for c in deck:
            for l in L(c):
                cnt[l] = cnt.get(l, 0) + 1
        main = max(cnt, key=cnt.get) if cnt else None
        fit = [c for c in cand if main and main in L(c)] or cand
        deck.append(rng.choice(fit))
    V.append(dict(label=f'draft_{k:03d}', cards=deck, noup=True, draft=True, n=nf, P=P, sits=S, pool=pool))
core = json.load(open(sys.argv[6]))['core'] if len(sys.argv) > 6 else None
pure = core or {b: [c for c in pool if L(c) == {b}] for b in 'СПЧ'}
for b in 'СПЧ':
    for k in range(20):
        V.append(dict(label=f'pure{b}_{k:02d}', cards=rng.sample(pure[b], 5), noup=True, draft=True, n=nf, P=P, sits=S, pool=pool))
burn11.M_bank(); MB = burn11.BUILD
mpure = {b: [c for c in burn11.CONCEPT if set(ch for ch in MB.get(c, '') if ch in 'СПМ') == {b}] for b in 'СПМ'}
for b in 'СПЧ':
    for mb in 'СПМ':
        for k in range(NP):
            V.append(dict(label=f'pair{b}{mb}_{k:02d}', cards=rng.sample(pure[b], 5), mcards=rng.sample(mpure[mb], 5),
                          noup=True, draft=True, n=nf, P=P, sits=['EL', 'BOSS'], pool=pool))
for j, v in enumerate(V):
    v['sid'] = j + 1   # своя серия врагов у каждой колоды
json.dump(V, open(out, 'w'), ensure_ascii=False)
print('вариантов', len(V), 'боёв', sum(v['n'] * len(v['sits']) for v in V), {b: len(x) for b, x in pure.items()}, {b: len(x) for b, x in mpure.items()})
