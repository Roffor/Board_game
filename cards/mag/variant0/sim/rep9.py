# -*- coding: utf-8 -*-
"""Сводка трёх билдов: сила [С 8.8] по парным боям с базой, полоса +0,5…+1,5 [С 8.9], сборки.
python3 rep9.py run.json [run_base.json] — база берётся из первого файла, если во втором её нет."""
import json, sys, math, statistics as st
import burn2, burn9
burn2.P.update(burn9.DEFAULTS)
names = {c.cid: c.name for c in burn9.M_bank()}
BUILD = dict(burn9.BUILD)
SITS = ['I', 'II', 'EL', 'BOSS']
R = []
for f in sys.argv[1:]:
    R += [r for r in json.load(open(f)) if 'error' not in r]
by = {}
for r in R:
    by.setdefault(r['v'], {}).setdefault(r['sit'], {})[r['i']] = r
base = by['base']


def m(x): return sum(x) / len(x) if x else 0


def summ(v):
    d = by[v]; out = {}; comb_all = []
    for s in SITS:
        ids = sorted(set(d.get(s, {})) & set(base.get(s, {})))
        dr = [d[s][i]['rounds'] - base[s][i]['rounds'] for i in ids]
        dt = [d[s][i]['taken'] - base[s][i]['taken'] for i in ids]
        comb = [-a / 0.3 - b / 1.5 for a, b in zip(dr, dt)]
        out[s] = dict(n=len(ids), dr=m(dr), dt=m(dt), S=m(comb), se=(st.pstdev(comb) / math.sqrt(len(comb))) if len(comb) > 1 else 0,
                      r=m([d[s][i]['rounds'] for i in ids]), t=m([d[s][i]['taken'] for i in ids]) / 40 * 100,
                      w=m([d[s][i]['won'] for i in ids]), pl=m([d[s][i]['played'] for i in ids]),
                      stuck=sum(d[s][i].get('stuck', False) for i in ids))
    S = m([out[s]['S'] for s in SITS]); se = math.sqrt(sum(out[s]['se'] ** 2 for s in SITS)) / len(SITS)
    return dict(sits=out, S=S, se=se, pl=m([out[s]['pl'] for s in SITS]))


def band(S):
    if 1.5 <= S <= 2.5: return 'норма'
    if 1.2 <= S < 1.5: return 'чуть ниже'
    if 2.5 < S <= 2.8: return 'чуть выше'
    return 'НИЖЕ' if S < 1.2 else 'ВЫШЕ'


if __name__ == '__main__':
    res = {v: summ(v) for v in by if v != 'base'}
    json.dump(res, open(sys.argv[1] + '.sum.json', 'w'), ensure_ascii=False, indent=1)
    for s in SITS:
        b = base[s].values()
        print(f"БАЗА {s}: {m([x['rounds'] for x in b]):.2f} раунда, потери {m([x['taken'] for x in b]) / 40 * 100:.0f}%, "
              f"побед {m([x['won'] for x in b]):.2f}, в пределе {sum(x.get('stuck', False) for x in b)}, боёв {len(b)}")
    cards = [(v, x) for v, x in res.items() if not v.startswith('build_')]
    cnt = {}
    print('\nКАРТЫ')
    for v, x in sorted(cards, key=lambda kv: -kv[1]['S']):
        b = band(x['S']); cnt[b] = cnt.get(b, 0) + 1
        print(f"{names.get(v, v):24s} {BUILD.get(v, '?'):4s} S={x['S']:+.2f}±{x['se']:.2f} {b:9s} pl={x['pl']:.2f} n={x['sits']['I']['n']} " +
              ' '.join(f"{s}:{x['sits'][s]['S']:+.1f}" for s in SITS))
    tot = len(cards)
    print('\nПолосы:', cnt, f"вне нормы {100 * (tot - cnt.get('норма', 0)) / max(1, tot):.0f}%, далеко вне {cnt.get('НИЖЕ', 0) + cnt.get('ВЫШЕ', 0)}")
    print('\nСБОРКИ')
    for v, x in sorted(((v, x) for v, x in res.items() if v.startswith('build_')), key=lambda kv: kv[0]):
        print(f"{v:12s} S={x['S']:+.2f}±{x['se']:.2f} " + ' '.join(
            f"{s}:{x['sits'][s]['r']:.2f}р/{x['sits'][s]['t']:.0f}%/в{x['sits'][s]['w']:.2f}/пр{x['sits'][s]['stuck']}" for s in SITS))
