# -*- coding: utf-8 -*-
"""Драфт: N колод по 6 апгрейдов, каждый выбор 1 из 3 случайных карт банка.
Игрок: держится билда, который уже набирает (буквы С/П/М), среди подходящих берёт сильнейшую;
в 25% выборов — вторую по силе ([С 8.1] «средний игрок»).
python3 gen_draft.py sum.json pool.json out.json [N] [боёв на ситуацию]"""
import json, sys, random
import burn2, burn10
burn2.P.update(burn10.DEFAULTS)
S = json.load(open(sys.argv[1])); pool = json.load(open(sys.argv[2]))
N = int(sys.argv[4]) if len(sys.argv) > 4 else 200; nf = int(sys.argv[5]) if len(sys.argv) > 5 else 6
B = burn10.BUILD
rng = random.Random(4242)


def letters(cid):
    return set(ch for ch in B.get(cid, '') if ch in 'СПМ')


V = []; clean = 0; by_build = {}
for k in range(N):
    deck = []
    for _ in range(6):
        cand = rng.sample([c for c in pool if c not in deck], 3)
        cnt = {}
        for c in deck:
            for l in letters(c):
                cnt[l] = cnt.get(l, 0) + 1
        main = max(cnt, key=cnt.get) if cnt else None
        fit = [c for c in cand if main and main in letters(c)] or cand
        fit.sort(key=lambda c: -S.get(c, {}).get('S', 0))
        pick = fit[1] if (len(fit) > 1 and rng.random() < 0.25) else fit[0]
        deck.append(pick)
    common = set.intersection(*[letters(c) for c in deck])
    if common:
        clean += 1
        for l in common:
            by_build[l] = by_build.get(l, 0) + 1
    V.append({'label': f'draft_{k:03d}', 'cards': deck, 'noup': True, 'n': nf})
json.dump(V, open(sys.argv[3], 'w'), ensure_ascii=False)
print('колод', N, 'чистых билдов', clean, by_build)
