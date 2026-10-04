# -*- coding: utf-8 -*-
"""Каждая карта во всех вариантах разыгрывается без ошибок: в бою и в копии для планирования.
Запуск: python -m engine.tests.test_karty  (из папки playtest/stend)"""
import os, sys, traceback
from engine import load_game, Fight, Choices, CardInst

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')  # корень репозитория


def fight_with(g, enemy, seed=1):
    decks = {h: g.start_deck(h) for h in g.heroes}
    loc = None
    f = Fight(g, decks, enemy, loc, seed, Choices())
    f.start_round()
    return f


def run():
    g = load_game(ROOT)
    errs = []; n = 0
    enemies = [e for t in ('I', 'II', 'EL', 'BOSS') for e in g.enemies_of(t)]
    for cid, d in sorted(g.cards.items()):
        if not d.variants:
            continue
        for e in enemies[:: max(1, len(enemies) // 4)]:
            for vi in range(len(d.variants)):
                for off in (0, 1, 3):
                    for planning in (False, True):
                        f = fight_with(g, e, seed=n)
                        if planning:
                            f = f.plan_copy()
                        h = f.H[d.hero]
                        h.mana = 10; f.charges = 3; f.H[f.P].faith = 6; f.E.porcha = 2
                        c = CardInst(d, d.hero); h.hand.append(c)
                        n += 1
                        try:
                            ok = f.play(d.hero, c, vi, off)
                            if not ok:
                                errs.append(f'{cid} [{vi}] не сыгралась')
                            if not planning:
                                f.finish_round()
                                if not f.over:
                                    f.start_round()
                        except Exception as ex:
                            errs.append(f'{cid} [{vi}] off={off} plan={planning} {e.eid}: {ex!r}\n' +
                                        ''.join(traceback.format_exc().splitlines(True)[-4:]))
    print(f'карт {len(g.cards)}, проверок {n}, ошибок {len(errs)}')
    seen = set()
    for x in errs:
        k = x.split(' off=')[0]
        if k not in seen:
            seen.add(k); print(x)
    return not errs


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
