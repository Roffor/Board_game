# -*- coding: utf-8 -*-
"""Сводка фазы Г: группы (драфт, чистые билды Жреца, клетки пар) против коридоров; вклад Жреца, вера, победы.
python3 grep_g.py run.json [run.json.part]"""
import json, sys, re, statistics as st
from zrep import COR
m = lambda x: sum(x) / len(x) if x else float('nan')
R = []
for f in sys.argv[1:]:
    D = json.load(open(f)); R += [r for r in D['res'] if 'error' not in r]
err = 0
def grp(l):
    if '|' in l:
        a, b = l.split('|', 1); return a + ' ' + grp(b)
    if l.startswith('draft'): return 'драфт'
    if l == 'base': return 'база'
    mm = re.match(r'pure(.)_', l)
    if mm: return 'чистый ' + mm.group(1)
    mm = re.match(r'pair(.)(.)_', l)
    return f'пара Ж-{mm.group(1)} × М-{mm.group(2)}'
G = {}
for r in R:
    G.setdefault((grp(r['v']), r['sit']), []).append(r)
def line(k, x):
    s = k[1]; (a, b), (c, d) = COR[s]
    rr = m([y['rounds'] for y in x]); t = m([y['taken'] for y in x]) / 40 * 100
    dm = sum(y.get('dmgM', 0) for y in x); dp = sum(y.get('dmgP', 0) for y in x)
    fn = max(1, sum(y.get('f_n', 0) for y in x)); f = sum(y.get('f_sum', 0) for y in x) / fn
    ok = ('✓' if a <= rr <= b else ('▲' if rr > b else '▼')) + ('✓' if c <= t <= d else ('▲' if t > d else '▼'))
    # разброс по колодам: доля колод вне коридора раундов
    byd = {}
    for y in x: byd.setdefault(y['v'], []).append(y['rounds'])
    out = sum(1 for v in byd.values() if not (a - 0.5 <= m(v) <= b + 0.5)) / len(byd)
    return f"{k[0]:22s} {s:4s} n{len(x):5d} {rr:.2f} / {t:4.1f}% {ok} поб {m([y['won'] for y in x]):.2f} вклЖ {dp / max(1, dm + dp):.2f} вера {f:.1f} Чудес {m([y.get('miracles', 0) for y in x]):.2f} выбор {m([y['choice'] for y in x]):.2f} колод вне ±0,5: {out:.0%}"
order = lambda k: (k[0].split(' ')[-1] if '|' else '', k[0], ['I', 'II', 'EL', 'BOSS'].index(k[1]))
for k in sorted(G, key=order):
    print(line(k, G[k]))
