# -*- coding: utf-8 -*-
"""Ситуации теста: какой враг, какая комната, сколько апгрейдов у героев.
Схема сидов как в старом симуляторе (zt.py): один номер боя даёт одного и того же врага, комнату
и одни и те же случайные апгрейды для всех вариантов колод — варианты сравниваются на равных."""
import random, zlib

APGREJDOV = {'I': 0, 'II': 3, 'EL': 3, 'BOSS': 5}
SITUACII = list(APGREJDOV)


def seed_of(seed0, sit, i):
    return seed0 + zlib.crc32(sit.encode()) % 997 * 1000 + i


def pick(game, sit, seed):
    """Враг и комната для боя."""
    rs = random.Random(seed)
    enemy = rs.choice(game.enemies_of(sit))
    loc = rs.choice(sorted(game.locations.values(), key=lambda l: l.lid))
    return enemy, loc


def random_upgrades(pool, n, seed, salt, exclude=()):
    """n случайных апгрейдов из пула (один и тот же набор для всех вариантов на этом сиде)."""
    mul, add = salt
    r = random.Random(seed * mul + add)
    cand = sorted(pool); r.shuffle(cand)
    return [c for c in cand if c not in exclude][:n]


SOL_MAG = (31, 5)      # соль сида для случайных апгрейдов мага (как в старом симуляторе)
SOL_ZHREC = (17, 3)
