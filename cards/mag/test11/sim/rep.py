# -*- coding: utf-8 -*-
import json, sys, statistics as st
from burn import M_bank
R = json.load(open(sys.argv[1]))
SITS = ['I', 'II', 'EL']
HP = 34
COR = {'I': ((2.5, 3), (0.08, 0.15)), 'II': ((2, 2.5), (0.05, 0.12)), 'EL': ((3, 5), (0.20, 0.35))}
by = {}
for r in R:
    by.setdefault((r['v'], r['sit']), []).append(r)
name = {c.cid: c.name for c in M_bank()}
grp = {c.cid: c.grp for c in M_bank()}
def m(xs): return sum(xs) / len(xs)
def row(v):
    out = {}
    for s in SITS:
        xs = by[(v, s)]; b = by[('None' if False else None, s)] if (None, s) in by else None
        out[s] = dict(r=m([x['rounds'] for x in xs]), t=m([x['taken'] for x in xs]), w=m([x['won'] for x in xs]),
                      var=m([x['var'] for x in xs]), pl=m([x['played'] for x in xs]),
                      burned=m([x.get('burned', 0) for x in xs]), spent=m([x.get('spent', 0) for x in xs]),
                      free=m([x.get('free', 0) for x in xs]))
    return out
base = row(None)
print('БАЗА (новая стартовая колода):')
for s in SITS:
    b = base[s]; c = COR[s]
    print(f"  {s}: раундов {b['r']:.2f} (цель {c[0][0]}–{c[0][1]}), потери {b['t']:.1f} = {100*b['t']/HP:.0f}% (цель {int(c[1][0]*100)}–{int(c[1][1]*100)}%), побед {100*b['w']:.0f}%, вариативность {100*b['var']:.0f}%, сожжено/бой {b['burned']:.1f}, заряды потрачено {b['spent']:.1f}, бесплатных {b['free']:.1f}")
old = row('old')
print('СТАРОЕ ПРАВИЛО (колода теста №1):')
for s in SITS:
    b = old[s]; print(f"  {s}: раундов {b['r']:.2f}, потери {b['t']:.1f}, побед {100*b['w']:.0f}%, вариативность {100*b['var']:.0f}%")
rows = []
for v in sorted({r['v'] for r in R if r['v'] not in (None, 'old')}):
    x = row(v)
    dr = {s: x[s]['r'] - base[s]['r'] for s in SITS}; dt = {s: x[s]['t'] - base[s]['t'] for s in SITS}
    S = m([-dr[s] / 0.3 - dt[s] / 1.5 for s in SITS])
    rows.append((v, x, dr, dt, S))
single = [r for r in rows if '+' not in r[0]]
med = st.median([r[4] for r in single])
print(f'\nМедиана силы апгрейдов: {med:.2f}')
print('карта | заменяет | ΔраундI ΔраундII ΔраундEL | ΔпотериI II EL | сыграна/бой | сила')
for v, x, dr, dt, S in sorted(rows, key=lambda r: -r[4]):
    nm = ' + '.join(name[c] for c in v.split('+'))
    print(f"{nm} | {grp.get(v,'—')} | {dr['I']:+.2f} {dr['II']:+.2f} {dr['EL']:+.2f} | {dt['I']:+.1f} {dt['II']:+.1f} {dt['EL']:+.1f} | "
          f"{m([x[s]['pl'] for s in SITS]):.2f} | {S:+.2f}")
json.dump(dict(base=base, old=old, rows=[(v, x, dr, dt, S) for v, x, dr, dt, S in rows], med=med),
          open(sys.argv[1] + '.sum.json', 'w'), ensure_ascii=False, indent=1)
