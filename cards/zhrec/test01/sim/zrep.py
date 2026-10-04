# -*- coding: utf-8 -*-
"""Сводка теста Жреца: по вариантам — раунды и потери пары (% от 40) против коридоров, вклад Жреца, вера, Молитва, выбор;
по картам — парные изменения раундов и потерь относительно базы (объединение нескольких прогонов), частота розыгрыша.
python3 zrep.py [--cards] run.json [run2.json ...]"""
import json, sys, math, statistics as st
SITS = ['I', 'II', 'EL', 'BOSS']
COR = {'I': ((3.5, 4), (8, 15)), 'II': ((3, 3.5), (5, 12)), 'EL': ((4, 6), (20, 35)), 'BOSS': ((5, 8), (30, 60))}
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


def absolute(runs, v):
    o = {}
    for s in SITS:
        x = [a for f, by, _ in runs for a in by.get(v, {}).get(s, {}).values()]
        if not x:
            continue
        dm = sum(a.get('dmgM', 0) for a in x); dp = sum(a.get('dmgP', 0) for a in x); fn = max(1, sum(a.get('f_n', 0) for a in x))
        o[s] = dict(n=len(x), r=m([a['rounds'] for a in x]), t=m([a['taken'] for a in x]) / 40 * 100, w=m([a['won'] for a in x]),
                    share=dp / max(1, dm + dp), f=sum(a.get('f_sum', 0) for a in x) / fn, f6=sum(a.get('f_at6', 0) for a in x) / fn,
                    own=m([a.get('f_own', 0) for a in x]), ally=m([a.get('f_ally', 0) for a in x]), mir=m([a.get('miracles', 0) for a in x]),
                    pray=m([a.get('pray_play', 0) for a in x]), ch=m([a.get('choice', 0) for a in x]), tP=m([a.get('takenP', 0) for a in x]) / 20 * 100,
                    tM=m([a.get('takenM', 0) for a in x]) / 20 * 100)
    return o


def inside(s, o):
    (a, b), (c, d) = COR[s]
    return ('✓' if a <= o['r'] <= b else ('▲' if o['r'] > b else '▼')) + ('✓' if c <= o['t'] <= d else ('▲' if o['t'] > d else '▼'))


def delta(runs, v, base='base'):
    o = {s: dict(dr=[], dt=[], pl=[]) for s in SITS}
    for f, by, _ in runs:
        if v not in by or base not in by:
            continue
        for s in SITS:
            for i, r in by[v].get(s, {}).items():
                b = by[base].get(s, {}).get(i)
                if b is None:
                    continue
                o[s]['dr'].append(r['rounds'] - b['rounds']); o[s]['dt'].append((r['taken'] - b['taken']) / 40 * 100)
                o[s]['pl'].append(sum(r.get('own', {}).values()))
    return o


def se(x):
    return st.pstdev(x) / math.sqrt(len(x)) if len(x) > 1 else 0


if __name__ == '__main__':
    files = [f for f in sys.argv[1:] if not f.startswith('--')]
    runs = load(files)
    labels = []
    for f, by, err in runs:
        for v in by:
            if v not in labels:
                labels.append(v)
        if err:
            print('ошибок в', f, err)
    if '--cards' not in sys.argv:
        print('вариант            | ' + ' | '.join(f'{s}: р / пот% / поб / вклЖ / вера / на6 / Мол / выбор' for s in SITS[:1]))
        for v in labels:
            A = absolute(runs, v)
            for s in SITS:
                if s in A:
                    o = A[s]
                    print(f"{v:18s} {s:4s} n{o['n']:4d} {o['r']:.2f} / {o['t']:4.1f}% {inside(s, o)} поб {o['w']:.2f} вклЖ {o['share']:.2f} "
                          f"вера {o['f']:.1f} на6 {o['f6']:.2f} свои/союз {o['own']:.1f}/{o['ally']:.1f} Чудес {o['mir']:.2f} Мол {o['pray']:.2f} "
                          f"выбор {o['ch']:.2f} потЖ {o['tP']:.0f}% потМ {o['tM']:.0f}%")
    else:
        from priest import names
        N = names()
        rows = []
        for v in labels:
            if v == 'base':
                continue
            d = delta(runs, v)
            dr = [x for s in SITS for x in d[s]['dr']]
            if not dr:
                continue
            late = [x for s in ('II', 'EL', 'BOSS') for x in d[s]['dr']]
            latet = [x for s in ('II', 'EL', 'BOSS') for x in d[s]['dt']]
            pl = [x for s in SITS for x in d[s]['pl']]
            rows.append((m(late), v, m(late), se(late), m(latet), se(latet), m(pl), {s: (m(d[s]['dr']), m(d[s]['dt'])) for s in SITS}, len(dr)))
        rows.sort()
        print('вариант (карта)                     поздние Δр ± / Δпот% ± / розыгр. | I II EL BOSS: Δр/Δпот')
        for _, v, a, sa, b, sb, pl, S, n in rows:
            nm = N.get(v, v)
            print(f"{v:12s} {nm[:22]:22s} {a:+.2f}±{sa:.2f} {b:+5.1f}±{sb:.1f} {pl:4.2f} | " +
                  ' '.join(f"{S[s][0]:+.2f}/{S[s][1]:+.1f}" for s in SITS) + f" n{n}")
