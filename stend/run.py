#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единственная команда запуска стенда.

  python run.py plans/<план>.yaml            запустить план (или продолжить с чекпоинта)
  python run.py plans/<план>.yaml --git      то же, с коммитом после каждой фазы
  python run.py proverka                     проверить данные игры и тесты движка
  python run.py boj <ситуация> <номер> [сид]  сыграть один бой с подробным журналом (для разбора)

Ключи: --yader N (по умолчанию все), --bez-dyma (без дымового прогона),
--minut M (через M минут сохранить состояние и выйти с кодом 3; та же команда продолжит — для запуска кусками)."""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def proverka():
    import engine
    from engine.tests import test_karty, test_zolotye
    g = engine.load_game(os.path.join(ROOT, 'game'))
    print(f'данные игры в порядке: карт {len(g.cards)}, врагов {len(g.enemies)}, комнат {len(g.locations)}')
    ok = test_karty.run() and test_zolotye.run()
    print('проверка пройдена' if ok else 'ПРОВЕРКА НЕ ПРОЙДЕНА')
    return ok


def boj(sit, i, seed0):
    import engine
    from stend import situacii as S, worker
    from stend.bot import run_fight
    g = engine.load_game(os.path.join(ROOT, 'game'))
    worker._GAMES[()] = g
    seed = S.seed_of(seed0, sit, i)
    e, loc = S.pick(g, sit, seed)
    v = dict(metka='baza', geroi={h: dict(apgrejdy='sluchajno', pul='apgrejd', obyazatelno=[]) for h in g.heroes}, pravki={})
    decks = worker.decks_for(g, v, sit, seed)
    r, bot, f = run_fight(g, decks, e, loc, seed, log=True)
    print('\n'.join(f.log))
    print({k: r[k] for k in ('won', 'rounds', 'taken', 'end_hp')})


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'proverka':
        sys.exit(0 if proverka() else 1)
    if cmd == 'boj':
        boj(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
        sys.exit(0)
    from stend.runner import Run, Pauza
    n = arg('--yader'); m = arg('--minut')
    try:
        Run(ROOT, os.path.abspath(cmd), procs=int(n) if n else None, use_git='--git' in sys.argv,
            smoke='--bez-dyma' not in sys.argv, minut=float(m) if m else None).run()
    except Pauza:
        print('ПАУЗА: состояние сохранено, запусти ту же команду, чтобы продолжить')
        sys.exit(3)
