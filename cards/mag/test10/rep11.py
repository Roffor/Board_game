# -*- coding: utf-8 -*-
"""Сводка длинного теста: сила в долях эталона (норма 70–130%), три состояния, ранняя/поздняя точка,
поражения отдельной строкой, частота розыгрыша, сложность.  python3 rep11.py run.json [--fit]"""
import json, sys, math, statistics as st
import burn2, burn10, bt11
burn2.P.update(burn10.DEFAULTS)
SITS = bt11.SITS
D = json.load(open(sys.argv[1])); R = [r for r in D['res'] if 'error' not in r]
ERR = [r for r in D['res'] if 'error' in r]
W = D.get('w_t', bt11.W_T)
names = {c.cid: c.name for c in burn10.M_bank()}
by = {}
for r in R:
    by.setdefault(r['v'], {}).setdefault(r['sit'], {})[r['i']] = r
base = by['base']
m = lambda x: sum(x) / len(x) if x else 0


def comp(v):
    d = by[v]; o = {}
    for s in SITS:
        ids = sorted(set(d.get(s, {})) & set(base.get(s, {})))
        o[s] = dict(ids=ids, dr=[d[s][i]['rounds'] - base[s][i]['rounds'] for i in ids],
                    dt=[d[s][i]['taken'] - base[s][i]['taken'] for i in ids],
                    dw=[d[s][i]['won'] - base[s][i]['won'] for i in ids],
                    pl=[d[s][i]['played'] for i in ids], r=[d[s][i]['rounds'] for i in ids],
                    t=[d[s][i]['taken'] for i in ids], w=[d[s][i]['won'] for i in ids],
                    stuck=sum(d[s][i].get('stuck', False) for i in ids))
    return o


def fit_w():
    R_ = {}; T_ = {}
    for e in ('e_dmg', 'e_sh'):
        o = comp(e)
        R_[e] = m([m([-a / 0.3 for a in o[s]['dr']]) for s in SITS]); T_[e] = m([m([-b for b in o[s]['dt']]) for s in SITS])
    den = T_['e_sh'] - T_['e_dmg']
    w = (R_['e_dmg'] - R_['e_sh']) / den if den else None
    return w, R_, T_


def strength(v, w=None):
    w = W if w is None else w
    o = comp(v); per = {}; se2 = 0
    for s in SITS:
        c = [-a / 0.3 - b * w for a, b in zip(o[s]['dr'], o[s]['dt'])]
        per[s] = m(c); se2 += (st.pstdev(c) / math.sqrt(len(c))) ** 2 if len(c) > 1 else 0
    S = m(list(per.values()))
    return dict(S=S, se=math.sqrt(se2) / len(SITS), per=per, early=per['I'], late=m([per[s] for s in SITS[1:]]),
                dwin=m([m(o[s]['dw']) for s in SITS]), dwin_boss=m(o['BOSS']['dw']),
                pl=m([m(o[s]['pl']) for s in SITS]), n=len(o['I']['ids']), o=o)


def state(x, lo, hi):
    a, b = x['S'] - 1.5 * x['se'], x['S'] + 1.5 * x['se']
    if a >= lo and b <= hi: return 'точно в норме'
    if b < lo: return 'точно ниже'
    if a > hi: return 'точно выше'
    return 'не ясно'


if __name__ == '__main__':
    if '--fit' in sys.argv:
        w, R_, T_ = fit_w()
        print('подбор веса потерь по эталонам:', w, R_, T_)
        if w and w > 0:
            W = w
    print(f"seed0 {D['seed0']}  вес потерь {W:.3f}  ошибок {len(ERR)}")
    for s in SITS:
        b = base[s].values()
        print(f"БАЗА {s}: {m([x['rounds'] for x in b]):.2f} р, потери {m([x['taken'] for x in b]) / 40 * 100:.0f}%, "
              f"побед {m([x['won'] for x in b]):.2f}, в пределе {sum(x.get('stuck', False) for x in b)}, боёв {len(b)}")
    et = [strength(e) for e in ('e_dmg', 'e_sh') if e in by]
    E = m([x['S'] for x in et]); lo, hi = 0.7 * E, 1.3 * E
    for e, x in zip(('e_dmg', 'e_sh'), et):
        print(f"эталон {e}: S={x['S']:+.2f}±{x['se']:.2f} ранняя {x['early']:+.2f} поздняя {x['late']:+.2f}")
    print(f"ЭТАЛОН {E:+.2f} → норма {lo:+.2f}…{hi:+.2f}\n")
    res = {}
    for v in by:
        if v == 'base' or v.startswith('build_') or v in ('e_dmg', 'e_sh') or v.startswith('draft_'):
            continue
        x = strength(v); x['pct'] = 100 * x['S'] / E if E else 0; x['st'] = state(x, lo, hi); res[v] = x
    cnt = {}
    for v, x in sorted(res.items(), key=lambda kv: -kv[1]['S']):
        cid = v.split('|')[0]
        cnt[x['st']] = cnt.get(x['st'], 0) + 1
        flag = ' НЕ РАСКРЫТ' if x['pl'] < 0.5 else ''
        print(f"{names.get(cid, cid)[:22]:22s} {v[len(cid):][:26]:26s} {burn10.BUILD.get(cid, '?'):4s} сл{burn10.CX.get(cid, '?')} "
              f"{x['pct']:4.0f}% S={x['S']:+.2f}±{x['se']:.2f} {x['st']:13s} ран {x['early']:+.1f} позд {x['late']:+.1f} "
              f"Δпобед босс {x['dwin_boss']:+.2f} розыгр {x['pl']:.2f} n={x['n']}{flag}")
    print('\nСостояния:', cnt)
    json.dump({v: {k: x[k] for k in ('S', 'se', 'pct', 'st', 'early', 'late', 'dwin', 'dwin_boss', 'pl', 'n', 'per')} for v, x in res.items()} |
              {'_etalon': E, '_w': W}, open(sys.argv[1] + '.sum.json', 'w'), ensure_ascii=False, indent=1)
    bl = [v for v in by if v.startswith('build_') or v.startswith('draft_')]
    if bl:
        print('\nСБОРКИ (раунды / потери / победы)')
        for v in sorted(bl):
            o = comp(v)
            print(f"{v:14s} " + ' '.join(f"{s}:{m(o[s]['r']):.2f}/{m(o[s]['t']) / 40 * 100:.0f}%/{m(o[s]['w']):.2f}" for s in SITS))
