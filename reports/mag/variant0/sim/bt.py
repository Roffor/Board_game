# -*- coding: utf-8 -*-
"""Тест билда: билд сжигания мага. Парные сиды: база и вариант играют одни и те же бои."""
import sys, json, random, time, zlib
from multiprocessing import Pool
import engine as EN
from engine import Game
from cards import TIER1, TIER2, ELITES, LOCATIONS, P_upgrades, M_cards, P_cards
import run as RUN
from burn import BGame, M_start, M_bank, no_heal_priest

SIT = [('I', 'Рядовые ранние', TIER1, 0), ('II', 'Рядовые поздние', TIER2, 4), ('EL', 'Элиты', ELITES, 3)]


def pdeck(nup, rs):
    deck = P_cards(); U = P_upgrades(); rs.shuffle(U); prng = random.Random(rs.random())
    for _ in range(nup):
        offer = U[:3]; worst = min(deck, key=lambda c: c.value)
        d = RUN.pick_upgrade(offer, worst, prng); U = U[3:] + U[:3]
        if d != 'нет':
            c = offer[int(d.split(':')[0])]; deck.remove(worst); deck.append(c); U.remove(c)
    return deck


def mdeck(variant):
    """variant: None — стартовая; список (cid апгрейда) — каждый заменяет свою карту по роли; 'old' — старое правило."""
    d = M_start()
    if not variant:
        return d
    bank = {c.cid: c for c in M_bank()}
    for cid in variant:
        c = bank[cid]; tgt = next(x for x in d if x.cid == c.grp); d.remove(tgt); d.append(c)
    return d


def one(job):
    import signal
    def _to(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM, _to); signal.alarm(60)
    try:
        return _one(job)
    except Exception as ex:
        if not isinstance(ex, TimeoutError):
            return dict(v=job[0] if isinstance(job[0], str) or job[0] is None else '+'.join(job[0]), sit=job[1], error=repr(ex), i=job[2])
        return dict(v=job[0] if isinstance(job[0], str) or job[0] is None else '+'.join(job[0]), sit=job[1], timeout=True, i=job[2])
    finally:
        signal.alarm(0)


def _one(job):
    variant, sit, i = job
    code, _, pool, nup = next(s for s in SIT if s[0] == sit)
    seed = 7000 + zlib.crc32(sit.encode()) % 997 * 100 + i
    rs = random.Random(seed)
    pd = pdeck(nup, rs); ed = rs.choice(pool); loc = rs.choice(LOCATIONS)
    if variant == 'old':
        g = Game(seed, []); g.H['P'] = EN.Hero('P', no_heal_priest(pd))
    else:
        g = BGame(seed, mdeck(variant), pd)
    r = g.fight(ed, 1 if sit == 'I' else 2 if sit == 'II' else 'elite', loc)
    names = [c.name for c in M_bank() if variant and variant != 'old' and c.cid in variant]
    played = sum(1 for n in r['plays']['M'] if n in names)
    near = [v[1] > 0 for v in r['var']]
    bs = getattr(g, 'bstats', None) or {}
    return dict(v=variant if isinstance(variant, str) or variant is None else '+'.join(variant), sit=sit, won=r['won'],
                rounds=r['rounds'], taken=sum(r['taken'].values()), played=played,
                mplays=len(r['plays']['M']), stuck=getattr(g, 'stuck', False), var=sum(near) / max(1, len(near)), **bs)


if __name__ == '__main__':
    N = int(sys.argv[1]); out = sys.argv[2]
    variants = json.loads(sys.argv[3])
    jobs = [(v if not isinstance(v, list) else v, s[0], i) for v in variants for s in SIT for i in range(N)]
    t = time.time()
    res = []
    with Pool(4) as p:
        for k, r in enumerate(p.imap_unordered(one, [(tuple(v) if isinstance(v, list) else v, s, i) for v, s, i in jobs], chunksize=4)):
            res.append(r)
            if k % 200 == 0:
                print('готово', k, 'из', len(jobs), 'сек', round(time.time() - t), flush=True)
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    print('боёв', len(res), 'сек', round(time.time() - t))
