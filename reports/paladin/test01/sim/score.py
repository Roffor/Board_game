# Оценка апгрейдов: ценность = −Δраунды − Δпотери/8 (1 раунд ≈ 8% потерь пары, ширина коридоров); поздние ситуации
import sys, json, zrep, priest
CH = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else set()
old = zrep.load([sys.argv[1]]); new = zrep.load([sys.argv[2]])
rows = []
for v in priest.UPGRADES:
    runs = new if v in CH else old + new
    d = zrep.delta(runs, v); L = ['II', 'EL', 'BOSS']
    dr = [x for s in L for x in d[s]['dr']]; dt = [x for s in L for x in d[s]['dt']]; pl = [x for s in L for x in d[s]['pl']]
    if not dr: continue
    R, T = zrep.m(dr), zrep.m(dt); val = -R - T / 8
    rows.append((val, v, priest.INFO[v][0], R, T, zrep.m(pl), len(dr), 'нов' if v in CH else 'объед'))
for val, v, nm, R, T, pl, n, k in sorted(rows, reverse=True):
    print(f"{v:12s} {nm:22s} ценн {val:+.2f}  Δр {R:+.2f} Δпот {T:+.1f}% розыгр {pl:.2f} n{n} {k}")
