#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единственная команда запуска стенда.

  python run.py plans/<план>.yaml            запустить план (или продолжить с чекпоинта)
  python run.py plans/<план>.yaml --git      то же, с коммитом после каждой фазы
  python run.py proverka                     проверить данные игры и тесты движка
  python run.py tablica                      обновить таблицы карт в документах героев (heroes/<герой>/<герой>.md)
  python run.py boj <ситуация> <номер> [сид]  сыграть один бой с подробным журналом (для разбора)
  python run.py uchitel plans/<конфиг>.yaml  один проход подбора весов оценки бота (stend/uchitel.py)
  python run.py podgonka plans/<конфиг>.yaml подгонка кругами: бои → правка карт и врагов → новый круг (stend/podgonka.py)

Ключи: --yader N (по умолчанию все), --bez-dyma (без дымового прогона),
--minut M (через M минут сохранить состояние и выйти с кодом 3; та же команда продолжит — для запуска кусками)."""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.normpath(os.path.join(ROOT, '..', '..'))  # корень репозитория: design/, heroes/, dungeons/
RUNS = os.path.join(GAME, 'reports', 'progony')
sys.path.insert(0, ROOT)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def proverka():
    import engine
    from engine.tests import test_karty, test_zolotye, test_paladin, test_mag2
    g = engine.load_game(GAME)
    print(f'данные игры в порядке: карт {len(g.cards)}, врагов {len(g.enemies)}, комнат {len(g.locations)}')
    ok = test_karty.run() and test_zolotye.run() and test_paladin.run() and test_mag2.run()
    print('проверка пройдена' if ok else 'ПРОВЕРКА НЕ ПРОЙДЕНА')
    return ok


def tablica():
    import engine
    from stend import tablica as T
    done = T.update(engine.load_game(GAME), GAME)
    print('обновил: ' + ', '.join(done) if done else 'таблицы уже актуальны')


def boj(sit, i, seed0):
    import engine
    from stend import situacii as S, worker
    from stend.bot import run_fight
    g = engine.load_game(GAME)
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
    if cmd == 'tablica':
        tablica(); sys.exit(0)
    if cmd == 'boj':
        boj(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
        sys.exit(0)
    n = arg('--yader'); m = arg('--minut')
    if cmd == 'uchitel':
        from stend.uchitel import Uchitel
        Uchitel(os.path.abspath(sys.argv[2]), GAME, RUNS, procs=int(n) if n else None).run()
        sys.exit(0)
    if cmd == 'podgonka':
        from stend.podgonka import Podgonka, Pauza as P2
        try:
            Podgonka(GAME, os.path.abspath(sys.argv[2]), GAME, RUNS, procs=int(n) if n else None,
                     minut=float(m) if m else None, use_git='--git' in sys.argv).run()
        except P2:
            print('ПАУЗА: состояние сохранено, запусти ту же команду, чтобы продолжить')
            sys.exit(3)
        sys.exit(0)
    from stend.runner import Run, Pauza
    try:
        Run(ROOT, os.path.abspath(cmd), game_dir=GAME, runs_dir=RUNS, procs=int(n) if n else None, use_git='--git' in sys.argv,
            smoke='--bez-dyma' not in sys.argv, minut=float(m) if m else None).run()
    except Pauza:
        print('ПАУЗА: состояние сохранено, запусти ту же команду, чтобы продолжить')
        sys.exit(3)
