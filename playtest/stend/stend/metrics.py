# -*- coding: utf-8 -*-
"""Метрики по строкам боёв: средние по ситуациям, коридоры соглашения, сила карт [С 8.8–8.9]."""
import math
from collections import defaultdict


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


def se(xs):
    xs = list(xs); n = len(xs)
    if n < 2:
        return float('nan')
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def ok_rows(rows):
    return [r for r in rows if 'error' not in r]


def by(rows, *keys):
    out = defaultdict(list)
    for r in rows:
        out[tuple(r[k] for k in keys) if len(keys) > 1 else r[keys[0]]].append(r)
    return out


def summary(rows, sog):
    """Сводка одного варианта по ситуациям: средние и попадание в коридоры."""
    out = {}
    order = {'I': 0, 'II': 1, 'EL': 2, 'BOSS': 3}
    for sit, rr in sorted(by(ok_rows(rows), 'sit').items(), key=lambda kv: order.get(kv[0], 9)):
        n = len(rr)
        loss = [100.0 * r['taken'] / r['hp_pair'] for r in rr]
        d = dict(n=n, rounds=mean(r['rounds'] for r in rr), rounds_se=se(r['rounds'] for r in rr),
                 loss=mean(loss), loss_se=se(loss), won=mean(r['won'] for r in rr),
                 stuck=sum(r['stuck'] for r in rr), choice=mean(r['choice'] for r in rr),
                 plays=mean(r['plays'] / max(1, r['rounds']) for r in rr),
                 dmg_mag=mean(r['dmg_share_mag'] for r in rr if r['dmg_share_mag'] is not None),
                 min_frac=mean(r['min_frac'] for r in rr), sec=mean(r['sec'] for r in rr))
        hm = sog.get('poteri_geroya_maks_proc', {}).get(sit)
        if hm is not None:
            d['hero_over'] = mean(any(100.0 * t / r['maxhp'][k] > hm for k, t in r['taken_h'].items()) for r in rr)
        zt = sog.get('zatyazhnye', {}).get(sit)
        if zt:
            d['long'] = mean(r['rounds'] > zt['dolshe'] for r in rr)
        d['rounds_k'] = sog['raundy'].get(sit); d['loss_k'] = sog['poteri_pary_proc'].get(sit)
        out[sit] = d
    return out


def corridor_dist(x, k):
    """Расстояние от центра коридора в долях полуширины: 0 — центр, 1 — граница."""
    if k is None or x != x:
        return 0.0
    c = (k[0] + k[1]) / 2; h = max(1e-9, (k[1] - k[0]) / 2)
    return abs(x - c) / h


def corridor_score(summ):
    """Чем меньше, тем ближе средние к центрам коридоров (раунды и потери пары по всем ситуациям)."""
    return sum(corridor_dist(d['rounds'], d['rounds_k']) ** 2 + corridor_dist(d['loss'], d['loss_k']) ** 2
               for d in summ.values())


def in_k(x, k):
    return k is None or (k[0] <= x <= k[1])


# ---------------------------------------------------------------- сила карт [С 8.8]
def paired(rows, base, var, sits):
    """Парные разности вариант − база по ситуациям: {sit: [(d_rounds, d_loss_hp), ...]}."""
    idx = {(r['sit'], r['i']): r for r in ok_rows(rows) if r['v'] == base}
    out = {}
    for s in sits:
        out[s] = []
    for r in ok_rows(rows):
        if r['v'] != var or r['sit'] not in out:
            continue
        b = idx.get((r['sit'], r['i']))
        if b is not None:
            out[r['sit']].append((r['rounds'] - b['rounds'], r['taken'] - b['taken']))
    return out


def raw_parts(pairs, noise_r):
    """A = среднее по ситуациям (−Δраунды/шум), B = среднее по ситуациям Δпотерь."""
    sits = [s for s, x in pairs.items() if x]
    if not sits:
        return None
    A = mean(-mean(d[0] for d in pairs[s]) / noise_r for s in sits)
    B = mean(mean(d[1] for d in pairs[s]) for s in sits)
    return A, B


def weight_w(rows, base, etalons, sits, noise_r):
    """Вес потерь w: эталон урона и эталон щита должны иметь равную силу."""
    pu = raw_parts(paired(rows, base, etalons[0], sits), noise_r)
    ps = raw_parts(paired(rows, base, etalons[1], sits), noise_r)
    if not pu or not ps or abs(pu[1] - ps[1]) < 1e-9:
        return 1.0
    w = (pu[0] - ps[0]) / (pu[1] - ps[1])
    return w if w > 0 else 1.0


def strength(rows, base, var, sits, noise_r, w):
    """Сила варианта и её погрешность (в очках), плюс ранняя (I) и поздняя (остальные) точки."""
    pr = paired(rows, base, var, sits)
    per = {}
    for s, ds in pr.items():
        if ds:
            xs = [-d[0] / noise_r - w * d[1] for d in ds]
            per[s] = (mean(xs), se(xs), len(xs))
    if not per:
        return None
    m = mean(v[0] for v in per.values())
    e = math.sqrt(sum((v[1] if v[1] == v[1] else 0) ** 2 for v in per.values())) / len(per)
    late = [per[s][0] for s in per if s != 'I']
    return dict(s=m, se=e, early=per.get('I', (float('nan'),))[0], late=mean(late) if late else float('nan'),
                n=min(v[2] for v in per.values()),
                d_won=mean(r['won'] for r in ok_rows(rows) if r['v'] == var) - mean(r['won'] for r in ok_rows(rows) if r['v'] == base))


def verdict(pct, pct_err, norm):
    lo, hi = pct - pct_err, pct + pct_err
    if norm[0] <= lo and hi <= norm[1]:
        return 'точно в норме'
    if hi < norm[0] or lo > norm[1]:
        return 'точно вне нормы'
    return 'не ясно'


def card_table(rows, base, cards, etalons, sits, sog):
    """Сила каждой карты в % от средней силы эталонов, с вердиктом [С 8.9]."""
    noise = sog['shum']['raundy']; norm = sog['apgrejd_norma_proc']
    w = weight_w(rows, base, etalons, sits, noise)
    et = [strength(rows, base, e, sits, noise, w) for e in etalons]
    ref = mean(x['s'] for x in et if x) if all(et) else float('nan')
    out = []
    for c in list(etalons) + list(cards):
        st = strength(rows, base, c, sits, noise, w)
        if not st or not ref or ref != ref or ref <= 0:
            out.append(dict(karta=c, pct=float('nan'), err=float('nan'), verdict='нет данных', n=0)); continue
        pct = 100.0 * st['s'] / ref; err = 1.5 * 100.0 * st['se'] / ref
        plays = mean(r['karty'].get(r.get('kt') or c, 0) for r in ok_rows(rows) if r['v'] == c) if c not in etalons else float('nan')
        v = verdict(pct, err, norm)
        if plays == plays and plays < sog.get('redko_razygryvaetsya', 0.5):
            v += '; бот не раскрывает'
        out.append(dict(karta=c, pct=pct, err=err, early=100.0 * st['early'] / ref, late=100.0 * st['late'] / ref,
                        d_won=st['d_won'], plays=plays, n=st['n'], verdict=v))
    return out, w, ref
