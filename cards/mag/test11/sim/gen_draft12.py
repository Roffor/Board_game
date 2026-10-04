# -*- coding: utf-8 -*-
"""Драфт серии №11: N колод по 5 апгрейдов (для II и элиты берутся первые 3, для босса все 5).
Каждый выбор — 1 из 3 случайных карт концепта; игрок держится билда, который набирает (буквы С/П/М),
среди подходящих берёт случайную (силу карт не используем — Никита 2026-09-30).
python3 gen_draft12.py out.json [N] [боёв на ситуацию] [P.json]"""
import json, sys, random
import burn11
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150; nf = int(sys.argv[3]) if len(sys.argv) > 3 else 3
P = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
burn11.M_bank(); B = burn11.BUILD; pool = burn11.CONCEPT; rng = random.Random(4242)
L = lambda c: set(ch for ch in B.get(c, '') if ch in 'СПМ')
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
    V.append({'label': f'draft_{k:03d}', 'cards': deck, 'noup': True, 'draft': True, 'n': nf, 'P': P})
for b in 'СПМ':
    pure = [c for c in pool if L(c) == {b}]
    for k in range(10):
        V.append({'label': f'build{b}_{k:02d}', 'cards': rng.sample(pure, 5), 'noup': True, 'draft': True, 'n': nf, 'P': P})
json.dump(V, open(sys.argv[1], 'w'), ensure_ascii=False)
print('колод', N)
