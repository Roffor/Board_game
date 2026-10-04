# -*- coding: utf-8 -*-
"""Прогонщик длинного теста Жреца (по образцу bt12 серии №11 мага).
4 ситуации поровну: I (стартовые колоды обоих), II и элита (по 3 апгрейда), босс (по 5).
Маг — концепт серии №11 + новая Кукла, у мага всегда случайные апгрейды из своего концепта (MUP).
У Жреца в базе случайные апгрейды из пула PPOOL (кроме своих карт варианта).
Вариант: {"label", "cards": [cid Жреца], "start": [15 cid] (необяз.), "P": {...}, "n", "noup", "draft", "sits"}.
python3 zt.py out.json variants.json [--n 60] [--seed0 N] [--pool pool.json]"""
import sys, os, json, random, time, zlib, signal
from multiprocessing import Pool
from cards import LOCATIONS
import burn2
import priest
from priest import PGame, DEFAULTS, pools, CFG, M_CONCEPT, P_deck, UPGRADES
import bt12

SIT = [('I', 1), ('II', 2), ('EL', 'elite'), ('BOSS', 'boss')]
SITS = [s[0] for s in SIT]
MUP = {'I': 0, 'II': 3, 'EL': 3, 'BOSS': 5}
PPOOL = list(UPGRADES)
SEED0 = None
PART = None
NAMES = priest.names()


def _one(job):
    v, sit, i, seed0 = job
    burn2.P.clear(); burn2.P.update(DEFAULTS); burn2.P.update(v.get('P', {}))
    tier = dict(SIT)[sit]
    cfg = dict(CFG)
    pool = pools(cfg)[sit]
    seed = seed0 + zlib.crc32(sit.encode()) % 997 * 1000 + i + v.get('sid', 0) * 7919   # sid: своя серия врагов у каждой колоды
    rs = random.Random(seed)
    ed = rs.choice(pool); loc = rs.choice(LOCATIONS)
    # маг: случайные апгрейды концепта (одинаковые для всех вариантов на этом сиде)
    ru = random.Random(seed * 31 + 5)
    mc = sorted(M_CONCEPT); ru.shuffle(mc)
    bt12.EXTRA_BANK[:] = []
    bt12.bank = lambda: priest.M_bank()
    mown = list(v.get('mcards', []))
    if v.get('draft'):
        mown = mown[:MUP[sit]]
    md = bt12.mdeck((mown + [c for c in mc if c not in mown])[:MUP[sit]])
    own = list(v.get('cards', []))
    if v.get('draft'):
        own = own[:MUP[sit]]
    ups = []
    if not v.get('noup'):
        rp = random.Random(seed * 17 + 3)
        cand = sorted(c for c in v.get('pool', PPOOL)); rp.shuffle(cand)
        ups = [c for c in cand if c not in own][:MUP[sit]]
    pd = P_deck(own + ups, v.get('start'))
    if v.get('oldp'):
        import burn, cards as C
        pd = burn.no_heal_priest(C.P_cards())
    g = PGame(seed, md, pd, cfg=cfg)
    r = g.fight(ed, tier, loc)
    pl = {}
    for n in r['plays']['P']:
        pl[n] = pl.get(n, 0) + 1
    ownp = {c: pl.get(NAMES[c], 0) for c in set(own)}
    var = r.get('var') or []
    return dict(v=v['label'], sit=sit, i=i, seed=seed, won=r['won'], rounds=r['rounds'], taken=sum(r['taken'].values()),
                takenM=r['taken']['M'], takenP=r['taken']['P'], stuck=getattr(g, 'stuck', False), enemy=ed['name'],
                own=ownp, choice=(sum(1 for a in var if a[1] > 0) / len(var)) if var else 0,
                **{k: x for k, x in g.bstats.items() if isinstance(x, (int, float))})


def one(job):
    def _to(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM, _to); signal.alarm(90)
    try:
        return _one(job)
    except Exception as ex:
        import traceback
        return dict(v=job[0]['label'], sit=job[1], i=job[2], error=repr(ex), tb=traceback.format_exc()[-800:])
    finally:
        signal.alarm(0)


def run(jobs, t, res, total):
    done = {(r['v'], r['sit'], r['i']) for r in res}
    jobs = [j for j in jobs if (j[0]['label'], j[1], j[2]) not in done]
    with Pool(os.cpu_count()) as p:
        for r in p.imap_unordered(one, jobs, chunksize=2):
            res.append(r)
            if len(res) % 200 == 0:
                print('готово', len(res), 'из', total, 'сек', round(time.time() - t), flush=True)
                if PART:
                    json.dump(dict(seed0=SEED0, res=res), open(PART + '.tmp', 'w'), ensure_ascii=False)
                    os.replace(PART + '.tmp', PART)


def arg(name, d):
    return type(d)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else d


if __name__ == '__main__':
    out = sys.argv[1]; V = json.load(open(sys.argv[2]))
    N = arg('--n', 60); seed0 = arg('--seed0', random.SystemRandom().randrange(10 ** 6, 10 ** 8))
    if '--pool' in sys.argv:
        PPOOL[:] = json.load(open(arg('--pool', '')))
    PART = out + '.part'; res = []
    if os.path.exists(PART):
        pd_ = json.load(open(PART)); seed0 = pd_['seed0']; res = pd_['res']
        print('продолжаю с чекпойнта:', len(res), 'боёв', flush=True)
    SEED0 = seed0
    print('seed0', seed0, flush=True)
    jobs = [(v, s, i, seed0) for v in V for s in v.get('sits', SITS) for i in range(v.get('n', N))]
    t = time.time()
    run(jobs, t, res, len(jobs))
    json.dump(dict(seed0=seed0, res=res), open(out, 'w'), ensure_ascii=False)
    if os.path.exists(PART):
        os.remove(PART)
    print('боёв', len(res), 'ошибок', sum(1 for r in res if 'error' in r), 'сек', round(time.time() - t), flush=True)
