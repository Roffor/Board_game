# -*- coding: utf-8 -*-
"""Сводка серии №11: главное — раунды и потери пары (% от 40) против коридоров [С 2], [С 3.2];
по картам — изменение раундов и потерь относительно базы (парные бои) и подсказка «сила в % эталона +2».
python3 rep12.py run.json [run2.json ...]  (несколько файлов объединяются по меткам вариантов)"""
import json, sys, math, statistics as st
import burn2, burn11, bt12
burn2.P.update(burn11.DEFAULTS)
SITS = bt12.SITS
COR = {'I': ((3.5, 4), (8, 15)), 'II': ((3, 3.5), (5, 12)), 'EL': ((4, 6), (20, 35)), 'BOSS': ((5, 8), (30, 60))}
W = 4.5
names = {c.cid: c.name for c in burn11.M_bank()}
m = lambda x: sum(x) / len(x) if x else float('nan')


def load(files):
    runs = []
    for f in files:
        D = json.load(open(f)); R = [r for r in D['res'] if 'error' not in r]
        by = {}
        for r in R:
            by.setdefault(r['v'], {}).setdefault(r['sit'], {})[r['i']] = r
        runs.append((f, by, len(D['res']) - len(R)))
    return runs


def absolute(by, v):
    o = {}
    for s in SITS:
        x = list(by.get(v, {}).get(s, {}).values())
        if x:
            o[s] = dict(r=m([a['rounds'] for a in x]), t=m([a['taken'] for a in x]) / 40 * 100, w=m([a['won'] for a in x]),
                        long=m([a['rounds'] > (5 if s in ('I', 'II') else 7 if s == 'EL' else 99) for a in x]), n=len(x))
    return o


def delta(runs, v):
    """Парные разности с базой своего прогона, объединённые по всем прогонам."""
    o = {s: dict(dr=[], dt=[], pl=[]) for s in SITS}
    for f, by, _ in runs:
        if v not in by or 'base' not in by:
            continue
        for s in SITS:
            b = by['base'].get(s, {}); d = by[v].get(s, {})
            for i in set(b) & set(d):
                o[s]['dr'].append(d[i]['rounds'] - b[i]['rounds']); o[s]['dt'].append(d[i]['taken'] - b[i]['taken'])
                o[s]['pl'].append(d[i]['played'])
    return o


def score(o):
    S = []
    for s in SITS:
        c = [-a / 0.3 - b * W for a, b in zip(o[s]['dr'], o[s]['dt'])]
        S.append(m(c))
    return m(S)


def mark(x, lo, hi):
    return '' if lo <= x <= hi else (' ↓' if x < lo else ' ↑')


if __name__ == '__main__':
    runs = load(sys.argv[1:])
    for f, by, err in runs:
        print(f'{f}: ошибок {err}')
    print('\nКОЛОДЫ (раунды | потери пары | победы | затяжные):')
    labels = []
    for f, by, _ in runs:
        labels += [v for v in by if (v.startswith('base') or v.startswith('deck')) and v not in labels]
    for v in labels:
        for f, by, _ in runs:
            if v not in by:
                continue
            a = absolute(by, v)
            row = []
            for s in SITS:
                if s in a:
                    (r0, r1), (t0, t1) = COR[s]; x = a[s]
                    row.append(f"{s} {x['r']:.2f}{mark(x['r'], r0, r1)} | {x['t']:.0f}%{mark(x['t'], t0, t1)} | {x['w']:.2f} | {x['long']:.0%}")
            print(f'  {v:<14} ' + ';  '.join(row))
    for pref, title in (('draft_', 'ДРАФТ (случайные колоды, держатся билда)'), ('buildС', 'Чистое Сжигание'), ('buildП', 'Чистый Проклинатель'), ('buildМ', 'Чистый Медиум')):
        rows = {s: [] for s in SITS}
        for f, by, _ in runs:
            for v in by:
                if v.startswith(pref):
                    for s in SITS:
                        x = list(by[v].get(s, {}).values())
                        if x:
                            rows[s].append((m([a['rounds'] for a in x]), m([a['taken'] for a in x]) / 40 * 100, m([a['won'] for a in x])))
        if not rows['II']:
            continue
        out = []
        for s in SITS:
            if rows[s]:
                (r0, r1), (t0, t1) = COR[s]; X = rows[s]
                rs = sorted(a[0] for a in X); q = lambda p_: rs[min(len(rs) - 1, int(p_ * len(rs)))]
                mr = m([a[0] for a in X]); mt = m([a[1] for a in X])
                out.append(f"{s} {mr:.2f}{mark(mr, r0, r1)} (10–90%: {q(0.1):.1f}–{q(0.9):.1f}) | {mt:.0f}%{mark(mt, t0, t1)} | побед {m([a[2] for a in X]):.2f}")
        print(f'\n{title}, колод {len(rows["II"])}:\n  ' + '\n  '.join(out))
    E = [score(delta(runs, e)) for e in ('e2_dmg', 'e2_sh')]
    E = m([x for x in E if x == x]) if any(x == x for x in E) else float('nan')
    print(f'\nЭталон +2 (подсказка): сила {E:+.2f}')
    for e in ('e2_dmg', 'e2_sh'):
        o = delta(runs, e)
        print(f"  {e}: " + '  '.join(f"{s} Δр {m(o[s]['dr']):+.2f} Δпот {m(o[s]['dt']):+.1f}" for s in SITS))
    print('\nКАРТЫ (Δ раундов и Δ потерь пары в здоровье против базы; ранняя I / поздняя II–EL–BOSS; % эталона +2 — подсказка):')
    rows = []
    for v in sorted({v for _, by, _ in runs for v in by}):
        if v.startswith('base') or v.startswith('deck') or v in ('e2_dmg', 'e2_sh', 'e_dmg', 'e_sh') or v.startswith('draft') or v.startswith('build'):
            continue
        o = delta(runs, v)
        n = len(o['I']['dr'])
        if not n:
            continue
        early = (m(o['I']['dr']), m(o['I']['dt']))
        late = (m([m(o[s]['dr']) for s in SITS[1:]]), m([m(o[s]['dt']) for s in SITS[1:]]))
        S = score(o); pct = 100 * S / E if E == E and E else float('nan')
        cid = v.split('|')[0]
        rows.append((pct, v, cid, early, late, m([m(o[s]['pl']) for s in SITS]), n))
    for pct, v, cid, early, late, pl, n in sorted(rows, key=lambda x: -x[0]):
        print(f"  {names.get(cid, cid)[:22]:<22} {v[len(cid):][:34]:<34} ран Δр {early[0]:+.2f} Δпот {early[1]:+.1f} | "
              f"позд Δр {late[0]:+.2f} Δпот {late[1]:+.1f} | {pct:4.0f}% | розыгр {pl:.2f} n={n}")
