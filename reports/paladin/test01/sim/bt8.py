# -*- coding: utf-8 -*-
"""Тест билда №8: 4 ситуации (I, II, элита, босс) по 30 боёв [С 8.7], добор ещё 30 картам с силой 0…+2.
Вариант: {"label", "cards": [cid...], "P": {параметр: число}, "CFG": {...}}.
Запуск: python3 bt8.py <боёв на ситуацию> out.json variants.json [--no-extra]"""
import sys, os, json, random, time, zlib, signal
from multiprocessing import Pool
from cards import LOCATIONS
import burn2, burn8
from burn8 import B8Game, M_start, M_bank, DEFAULTS, pools, CFG
from bt import pdeck

SIT = [('I', 1, 0), ('II', 2, 4), ('EL', 'elite', 3), ('BOSS', 'boss', 6)]   # ситуация, тип боя, апгрейдов у Жреца
SITS = [s[0] for s in SIT]


def mdeck(cards):
    d = M_start()
    bank = {c.cid: c for c in M_bank()}
    for cid in cards:
        c = bank[cid]; tgt = next(x for x in d if x.cid == c.grp); d.remove(tgt); d.append(c)
    return d


def _one(job):
    v, sit, i = job
    burn2.P.clear(); burn2.P.update(DEFAULTS); burn2.P.update(v.get('P', {}))
    _, tier, nup = next(s for s in SIT if s[0] == sit)
    cfg = dict(CFG); cfg.update(v.get('CFG', {}))
    pool = pools(cfg)[sit]
    seed = 7000 + zlib.crc32(sit.encode()) % 997 * 100 + i     # те же сиды, что в тестах №1–7
    rs = random.Random(seed)
    pd = pdeck(nup, rs); ed = rs.choice(pool); loc = rs.choice(LOCATIONS)
    g = B8Game(seed, mdeck(v.get('cards', [])), pd, cfg=cfg)
    r = g.fight(ed, tier, loc)
    names = {c.name for c in M_bank() if c.cid in v.get('cards', [])}
    return dict(v=v['label'], sit=sit, i=i, won=r['won'], rounds=r['rounds'], taken=sum(r['taken'].values()),
                taken_max=max(r['taken'].values()),
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


def strength(res, label):
    """Сила [С 8.8] по парным боям с базой."""
    ok = [r for r in res if 'error' not in r]
    base = {(r['sit'], r['i']): r for r in ok if r['v'] == 'base'}
    per = []
    for s in SITS:
        d = [(r['rounds'] - base[(s, r['i'])]['rounds'], r['taken'] - base[(s, r['i'])]['taken'])
             for r in ok if r['v'] == label and r['sit'] == s and (s, r['i']) in base]
        if d:
            per.append(sum(-a / 0.3 - b / 1.5 for a, b in d) / len(d))
    return sum(per) / len(per) if per else None


def run(jobs, t, res, total):
    with Pool(os.cpu_count()) as p:
        for r in p.imap_unordered(one, jobs, chunksize=2):
            res.append(r)
            if len(res) % 200 == 0:
                print('готово', len(res), 'из', total, 'сек', round(time.time() - t), flush=True)


if __name__ == '__main__':
    N = int(sys.argv[1]); out = sys.argv[2]; V = json.load(open(sys.argv[3]))
    extra = '--no-extra' not in sys.argv
    jobs = [(v, s, i) for v in V for s in SITS for i in range(N)]
    t = time.time(); res = []
    run(jobs, t, res, len(jobs))
    if extra and any(v['label'] == 'base' for v in V):
        more = [v for v in V if v['label'] == 'base' or (lambda S: S is not None and 0 <= S <= 2)(strength(res, v['label']))]
        print('добор у границы:', [v['label'] for v in more], flush=True)
        jobs2 = [(v, s, i) for v in more for s in SITS for i in range(N, 2 * N)]
        run(jobs2, t, res, len(jobs) + len(jobs2))
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    print('боёв', len(res), 'сек', round(time.time() - t), flush=True)
