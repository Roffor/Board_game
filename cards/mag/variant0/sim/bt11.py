# -*- coding: utf-8 -*-
"""Длинный тест мага (серия №10), методика cards/mag/15 + ответы Никиты 2026-09-29.
- 4 ситуации поровну; у мага в базе случайные апгрейды: I 0, II 3, элита 3, босс 5 (одинаковые для базы и варианта);
- сиды случайные в каждом прогоне (seed0 пишется в результаты), внутри прогона бои парные;
- по 60 боёв на ситуацию, «неясным» картам добор по 30 до 120;
- апгрейд заменяет стартовую карту из списка целей (пилот: лучшая из 3 слабейших и карты своей роли).
Вариант: {"label", "cards": [...], "P": {...}, "n": боёв (необяз.), "noup": bool}.
python3 bt11.py out.json variants.json [--n 60] [--max 120] [--seed0 N] [--no-extra] [--targets targets.json]"""
import sys, os, json, random, time, zlib, signal
from multiprocessing import Pool
from cards import LOCATIONS
import burn2, burn10
from burn10 import B10Game, M_start, M_bank, DEFAULTS, pools, CFG, ETALON
from bt import pdeck

SIT = [('I', 1, 0), ('II', 2, 4), ('EL', 'elite', 3), ('BOSS', 'boss', 6)]
SITS = [s[0] for s in SIT]
MUP = {'I': 0, 'II': 3, 'EL': 3, 'BOSS': 5}
TARGETS = {}
EXTRA_BANK = []   # функции add(...) для смелых идей текущей итерации (burn10.M_bank(extra))
W_T = 1 / 1.5     # вес потерь; подбирается по эталонам и пишется в weight.json
HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(HERE, 'weight.json')):
    W_T = json.load(open(os.path.join(HERE, 'weight.json')))['w_t']


def bank():
    return M_bank(EXTRA_BANK)


def mdeck(cards):
    d = M_start(); start = list(d)
    B = {c.cid: c for c in bank()}
    for cid in cards:
        c = B[cid]
        left = [x for x in d if any(x is s for s in start)]
        tgt = None
        for t in TARGETS.get(cid, []) + [c.grp]:
            tgt = next((x for x in left if x.cid == t), None)
            if tgt is not None:
                break
        if tgt is None:
            tgt = min(left, key=lambda x: x.value)
        d.remove(tgt); d.append(c)
    return d


def _one(job):
    v, sit, i, seed0 = job
    burn2.P.clear(); burn2.P.update(DEFAULTS); burn2.P.update(v.get('P', {}))
    _, tier, nup = next(s for s in SIT if s[0] == sit)
    cfg = dict(CFG)
    pool = pools(cfg)[sit]
    seed = seed0 + zlib.crc32(sit.encode()) % 997 * 1000 + i
    rs = random.Random(seed)
    pd = pdeck(nup, rs); ed = rs.choice(pool); loc = rs.choice(LOCATIONS)
    own = v.get('cards', [])
    TG = dict(BASE_T); TG.update(v.get('tgt', {}))
    TARGETS.clear(); TARGETS.update(TG)
    ups = []
    if not v.get('noup') and not v['label'].startswith('build_'):
        ru = random.Random(seed * 31 + 5)
        cand = sorted(c.cid for c in bank() if c.cid not in ETALON and c.cid in POOL); ru.shuffle(cand)
        ups = [c for c in cand if c not in own][:MUP[sit]]
    g = B10Game(seed, mdeck(own + ups), pd, cfg=cfg)
    r = g.fight(ed, tier, loc)
    names = {c.name for c in bank() if c.cid in own}
    return dict(v=v['label'], sit=sit, i=i, seed=seed, won=r['won'], rounds=r['rounds'], taken=sum(r['taken'].values()),
                played=sum(1 for n in r['plays']['M'] if n in names), stuck=getattr(g, 'stuck', False), enemy=ed['name'],
                **{k: x for k, x in g.bstats.items() if isinstance(x, (int, float))})


def one(job):
    def _to(*a): raise TimeoutError()
    signal.signal(signal.SIGALRM, _to); signal.alarm(90)
    try:
        return _one(job)
    except Exception as ex:
        return dict(v=job[0]['label'], sit=job[1], i=job[2], error=repr(ex))
    finally:
        signal.alarm(0)


BASE_T = {}
POOL = set()   # банк случайных апгрейдов базы (cid); задаётся в main


def paired(res, label):
    ok = [r for r in res if 'error' not in r]
    base = {(r['sit'], r['i']): r for r in ok if r['v'] == 'base'}
    out = {}
    for s in SITS:
        d = [(r['rounds'] - base[(s, r['i'])]['rounds'], r['taken'] - base[(s, r['i'])]['taken'])
             for r in ok if r['v'] == label and r['sit'] == s and (s, r['i']) in base]
        out[s] = d
    return out


def strength(res, label, w_t=None):
    """Сила: среднее по ситуациям от (−Δраундов/0,3 − Δпотерь·w_t), и погрешность."""
    import math, statistics as st
    w_t = W_T if w_t is None else w_t
    pr = paired(res, label); S = []; se2 = 0
    for s in SITS:
        c = [-a / 0.3 - b * w_t for a, b in pr[s]]
        if not c:
            return None, None
        S.append(sum(c) / len(c)); se2 += (st.pstdev(c) / math.sqrt(len(c))) ** 2 if len(c) > 1 else 0
    return sum(S) / len(S), math.sqrt(se2) / len(SITS)


def run(jobs, t, res, total, log=True):
    with Pool(os.cpu_count()) as p:
        for r in p.imap_unordered(one, jobs, chunksize=2):
            res.append(r)
            if log and len(res) % 200 == 0:
                print('готово', len(res), 'из', total, 'сек', round(time.time() - t), flush=True)


def arg(name, d):
    return type(d)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else d


if __name__ == '__main__':
    out = sys.argv[1]; V = json.load(open(sys.argv[2]))
    N = arg('--n', 60); MAX = arg('--max', 120); seed0 = arg('--seed0', random.SystemRandom().randrange(10 ** 6, 10 ** 8))
    tf = arg('--targets', os.path.join(HERE, 'targets.json'))
    if os.path.exists(tf):
        BASE_T.update(json.load(open(tf))); TARGETS.update(BASE_T)
    burn2.P.update(DEFAULTS)
    POOL.update(json.load(open(os.path.join(HERE, 'pool.json'))) if os.path.exists(os.path.join(HERE, 'pool.json'))
                else [c.cid for c in bank() if c.cid not in ETALON])
    print('seed0', seed0, 'вес потерь', round(W_T, 3), flush=True)
    jobs = [(v, s, i, seed0) for v in V for s in SITS for i in range(v.get('n', N))]
    t = time.time(); res = []
    run(jobs, t, res, len(jobs))
    if '--no-extra' not in sys.argv and any(v['label'] == 'base' for v in V):
        # эталон задаёт полосу 70–130%; «неясные» карты (интервал ±1,5 погрешности пересекает границу) получают добор
        E = [strength(res, e)[0] for e in ('e_dmg', 'e_sh') if any(v['label'] == e for v in V)]
        E = [x for x in E if x is not None]
        if E:
            et = sum(E) / len(E); lo, hi = 0.7 * et, 1.3 * et
            n = N
            while n < MAX:
                more = []
                for v in V:
                    if v['label'] == 'base' or v['label'].startswith('build_') or v.get('n', N) != N:
                        continue
                    S, se = strength(res, v['label'])
                    if S is None:
                        continue
                    if (S - 1.5 * se < lo < S + 1.5 * se) or (S - 1.5 * se < hi < S + 1.5 * se):
                        more.append(v)
                if not more:
                    break
                more = [v for v in V if v['label'] == 'base'] + more
                print(f'добор {n}→{n + 30}:', len(more) - 1, 'вариантов', flush=True)
                jobs2 = [(v, s, i, seed0) for v in more for s in SITS for i in range(n, n + 30)]
                run(jobs2, t, res, len(jobs2))
                n += 30
    json.dump(dict(seed0=seed0, w_t=W_T, targets=TARGETS, res=res), open(out, 'w'), ensure_ascii=False)
    print('боёв', len(res), 'сек', round(time.time() - t), flush=True)
