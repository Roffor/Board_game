# Стенд коротких сессий: бои с колодами той стадии забега, где встречается враг.
import sys, random, copy, json
from multiprocessing import Pool
from engine import *
from cards import *

def scaled(ed, hp=None, atk=1.0, sh=None):
    d = copy.deepcopy(ed)
    if hp: d['hp'] = hp
    if sh is not None: d['shield0'] = sh
    seq = d.get('cycle') or d.get('deck')
    for it in seq:
        it['acts'] = [(a[0], max(1, int(round(a[1] * atk))), a[2], a[3]) if a[0] == 'atk' else a for a in it['acts']]
    return d

def build(g, nup, legend, rs):
    for k, U, LG in (('M', M_upgrades(), M_LEGENDS), ('P', P_upgrades(), P_LEGENDS)):
        rs.shuffle(U); h = g.H[k]; i = 0
        for _ in range(nup):
            offer = U[:3]; U = U[3:] + U[:3]
            best = max(offer, key=lambda c: c.value)
            old = min(h.deck, key=lambda c: c.value)
            if best.value > old.value:
                h.deck.remove(old); h.deck.append(best); U.remove(best)
        if legend:
            n, t = rs.choice(LG); old = min(h.deck, key=lambda c: c.value)
            h.deck.remove(old); h.deck.append(legend_card(k, n, t)); h.legend = n

def one(job):
    ed, tier, nup, legend, seed = job
    g = Game(seed, []); rs = random.Random(seed)
    build(g, nup, legend, rs)
    loc = LOCATIONS[seed % len(LOCATIONS)]
    r = g.fight(ed, tier, loc)
    return (ed['name'], tier, r['won'], r['rounds'], r['hp_loss']['M'] + r['hp_loss']['P'])

VERBOSE = False
def run(groups, reps=10):
    jobs = []
    for (label, pool, tier, nup, legend, hp, atk, *rest) in groups:
        for ed in pool:
            e2 = scaled(ed, hp(ed) if hp else None, atk, rest[0] if rest else None)
            for s in range(reps):
                jobs.append((e2, tier, nup, legend, hash((label, ed['name'], s)) % 10**6 + s))
    with Pool(4) as p:
        res = p.map(one, jobs)
    out = {}
    idx = 0
    for (label, pool, tier, nup, legend, hp, atk, *rest) in groups:
        n = len(pool) * reps; chunk = res[idx:idx + n]; idx += n
        rounds = [c[3] for c in chunk]; loss = [c[4] for c in chunk]; wins = sum(c[2] for c in chunk)
        out[label] = dict(rounds=sum(rounds) / n, loss=sum(loss) / n, win=wins / n,
                          dist={r: rounds.count(r) for r in sorted(set(rounds))})
        if VERBOSE:
            names = {}
            for c in chunk: names.setdefault(c[0], []).append((c[3], c[4]))
            print('   ' + '; '.join(f'{k}: {sum(x[0] for x in v)/len(v):.1f}р/{sum(x[1] for x in v)/len(v):.1f}hp' for k, v in names.items()))
        print(f'{label:28s} раунды {out[label]["rounds"]:.2f}  потери {out[label]["loss"]:.1f}  победы {wins}/{n}  {out[label]["dist"]}')
    return out
