# -*- coding: utf-8 -*-
"""Тест билда №6 (бои на 1 раунд длиннее). Вариант: {"label", "cards": [cid...], "P": {параметр: число}}.
Запуск: python3 bt6.py <боёв на ситуацию> out.json variants.json"""
import sys, os, json, random, time, zlib, signal
from multiprocessing import Pool
from cards import TIER1, TIER2, ELITES, LOCATIONS
import burn2, burn6
from burn6 import B6Game, M_start, M_bank, DEFAULTS, pools, CFG
from bt import pdeck

SIT = [('I', TIER1, 0), ('II', TIER2, 4), ('EL', ELITES, 3)]


def mdeck(cards):
    d = M_start()
    bank = {c.cid: c for c in M_bank()}
    for cid in cards:
        c = bank[cid]; tgt = next(x for x in d if x.cid == c.grp); d.remove(tgt); d.append(c)
    return d


def _one(job):
    v, sit, i = job
    burn2.P.clear(); burn2.P.update(DEFAULTS); burn2.P.update(v.get('P', {}))
    _, pool, nup = next(s for s in SIT if s[0] == sit)
    cfg = dict(CFG); cfg.update(v.get('CFG', {}))
    pool = pools(cfg)[sit]
    seed = 7000 + zlib.crc32(sit.encode()) % 997 * 100 + i     # те же сиды, что в тесте №1
    rs = random.Random(seed)
    pd = pdeck(nup, rs); ed = rs.choice(pool); loc = rs.choice(LOCATIONS)
    g = B6Game(seed, mdeck(v.get('cards', [])), pd, cfg=cfg)
    r = g.fight(ed, 1 if sit == 'I' else 2 if sit == 'II' else 'elite', loc)
    names = {c.name for c in M_bank() if c.cid in v.get('cards', [])}
    return dict(v=v['label'], sit=sit, i=i, won=r['won'], rounds=r['rounds'], taken=sum(r['taken'].values()),
                played=sum(1 for n in r['plays']['M'] if n in names), stuck=getattr(g, 'stuck', False),
                var=sum(1 for x in r['var'] if x[1] > 0) / max(1, len(r['var'])), **g.bstats)


def one(job):
    def _to(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM, _to); signal.alarm(60)
    try:
        return _one(job)
    except Exception as ex:
        return dict(v=job[0]['label'], sit=job[1], i=job[2], error=repr(ex))
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    N = int(sys.argv[1]); out = sys.argv[2]; V = json.load(open(sys.argv[3]))
    jobs = [(v, s[0], i) for v in V for s in SIT for i in range(N)]
    t = time.time(); res = []
    with Pool(os.cpu_count()) as p:
        for k, r in enumerate(p.imap_unordered(one, jobs, chunksize=4)):
            res.append(r)
            if k % 200 == 0:
                print('готово', k, 'из', len(jobs), 'сек', round(time.time() - t), flush=True)
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    print('боёв', len(res), 'сек', round(time.time() - t), flush=True)
