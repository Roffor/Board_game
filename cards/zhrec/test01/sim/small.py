# -*- coding: utf-8 -*-
"""Мелкие тесты «обычного теста»: по 10 боёв на группу, колоды собирает «средний игрок».
Запуск: python3 small.py <круг> [out.json]"""
import sys, json, random, zlib
from multiprocessing import Pool
from engine import *
from cards import *
import run as RUN

GROUPS = [
    # метка, пул, ярус, апгрейдов (мин, макс), легендарка
    ('Рядовые ранние (ярус I)', 'T1', 1, (0, 2), False),
    ('Рядовые поздние (ярус II)', 'T2', 2, (4, 6), True),
    ('Элиты ранние', 'EL', 'elite', (2, 3), False),
    ('Элиты поздние', 'EL', 'elite', (5, 6), True),
    ('Босс', 'BOSS', 'boss', (7, 8), True),
]
N = {'Элиты ранние': 5, 'Элиты поздние': 5}   # остальные по 10


def pools():
    return {'T1': TIER1, 'T2': TIER2, 'EL': ELITES, 'BOSS': [BOSS]}


def build(g, nup, legend, rs):
    prng = random.Random(rs.random())
    for k, U, LG in (('M', M_upgrades(), M_LEGENDS), ('P', P_upgrades(), P_LEGENDS)):
        rs.shuffle(U); h = g.H[k]
        for _ in range(nup):
            offer = U[:3]
            worst = min([c for c in h.deck if c.cid != 'leg'], key=lambda c: c.value)
            d = RUN.pick_upgrade(offer, worst, prng)
            U = U[3:] + U[:3]
            if d != 'нет':
                i = int(d.split(':')[0]); c = offer[i]
                h.deck.remove(worst); h.deck.append(c); U.remove(c)
        if legend:
            offer = rs.sample(LG, 2)
            r = sorted(offer, key=lambda x: -RUN.LEG_V[x[0]])
            n, t = r[1] if prng.random() < ERR_P else r[0]
            worst = min(h.deck, key=lambda c: c.value)
            h.deck.remove(worst); h.deck.append(legend_card(k, n, t)); h.legend = n


def one(job):
    label, pool, tier, lo, hi, legend, seed = job
    rs = random.Random(seed)
    g = Game(seed, [])
    nup = rs.randint(lo, hi)
    build(g, nup, legend, rs)
    ed = rs.choice(pools()[pool])
    loc = rs.choice(LOCATIONS) if tier != 'boss' else dict(name='Сердце катакомб', feats=[('discard', 'bones', 'Сброс карты: 1 урон врагу.')])
    r = g.fight(ed, tier, loc)
    return dict(group=label, enemy=ed['name'], loc=loc['name'], nup=nup, legend={k: g.H[k].legend for k in 'MP'},
                won=r['won'], min=r['sec'] / 60, rounds=r['rounds'], taken=r['taken'],
                end_hp=r['end_hp'], plays=r['plays'], var=r['var'], errors=r['errors'],
                minfrac=min(g.min_frac.values()), log=g.log)


def main(circle, out):
    jobs = []
    for label, pool, tier, (lo, hi), leg in GROUPS:
        for i in range(N.get(label, 10)):
            jobs.append((label, pool, tier, lo, hi, leg, circle * 100000 + zlib.crc32(label.encode()) % 9973 * 10 + i))
    with Pool(4) as p:
        res = p.map(one, jobs)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    summary(res)


def mm(xs, f='{:.1f}'):
    return (f + ' ({}–{})').format(sum(xs) / len(xs), f.format(min(xs)), f.format(max(xs)))


def summary(res):
    groups = []
    for r in res:
        if r['group'] not in groups:
            groups.append(r['group'])
    for gname in groups:
        rs = [r for r in res if r['group'] == gname]
        wins = sum(r['won'] for r in rs)
        print(f"{gname}: победы {wins}/{len(rs)}; раунды {mm([r['rounds'] for r in rs])}; "
              f"мин {mm([r['min'] for r in rs])}; потери {mm([r['taken']['M'] + r['taken']['P'] for r in rs])}; "
              f"мин.здоровье {mm([100 * r['minfrac'] for r in rs], '{:.0f}')}%; "
              f"карт М {mm([len(r['plays']['M']) for r in rs])}, Ж {mm([len(r['plays']['P']) for r in rs])}; "
              f"близких {sum(v[0] for r in rs for v in r['var']) / max(1, sum(len(r['var']) for r in rs)):.1f}, "
              f"раундов с другим путём {100 * sum(1 for r in rs for v in r['var'] if v[1]) / max(1, sum(len(r['var']) for r in rs)):.0f}%")
        for r in rs:
            print(f"    {r['enemy']:24s} {'W' if r['won'] else 'L'} р{r['rounds']} {r['min']:.1f}м потери М{r['taken']['M']} Ж{r['taken']['P']} "
                  f"мин{100 * r['minfrac']:.0f}% апгр{r['nup']} {r['legend']['M'] or ''}/{r['legend']['P'] or ''}")


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else f'small{sys.argv[1]}.json')
