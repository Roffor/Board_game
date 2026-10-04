# -*- coding: utf-8 -*-
"""Финальная фаза: драфт, сборки, пары против базы (критерий п.21 методики).
python3 ana5.py it5.json"""
import json, sys, statistics as st
sys.argv = ['rep11.py', sys.argv[1]]
import rep11 as R
m = R.m
COR = {'I': (3.5, 4.0), 'II': (3.0, 3.5), 'EL': (4.0, 6.0), 'BOSS': (5.0, 8.0)}   # [С 2.1–2.5], 2026-09-29
et = [R.strength(e) for e in ('e_dmg', 'e_sh')]
E = m([x['S'] for x in et])


def absr(v):
    o = R.comp(v)
    return {s: (m(o[s]['r']), m(o[s]['t']) / 40 * 100, m(o[s]['w'])) for s in R.SITS}


out = {}
print(f'эталон {E:.2f}')
b = absr('base')
print('БАЗА ' + ' '.join(f"{s}:{b[s][0]:.2f}р/{b[s][1]:.0f}%/{b[s][2]:.2f}" for s in R.SITS))
for grp in ('draft_', 'build_', 'pair_'):
    vs = [v for v in R.by if v.startswith(grp)]
    if not vs:
        continue
    rows = []
    for v in vs:
        x = R.strength(v); a = absr(v)
        rows.append((v, x['S'], x['se'], a))
    rows.sort(key=lambda r: r[1])
    print(f'\n=== {grp} ({len(rows)}) ===')
    Ss = [r[1] for r in rows]
    print(f'сила против базы: мин {min(Ss):+.2f}, 10% {Ss[len(Ss) // 10]:+.2f}, медиана {st.median(Ss):+.2f}, 90% {Ss[len(Ss) * 9 // 10]:+.2f}, макс {max(Ss):+.2f}; слабее базы: {sum(s < 0 for s in Ss)}')
    k = max(1, len(rows) // 10)
    for name, part in (('худшие 10%', rows[:k]), ('лучшие 10%', rows[-k:])):
        avg = {s: (m([r[3][s][0] for r in part]), m([r[3][s][1] for r in part]), m([r[3][s][2] for r in part])) for s in R.SITS}
        print(f'{name}: ' + ' '.join(f"{s}:{avg[s][0]:.2f}р/{avg[s][1]:.0f}%/{avg[s][2]:.2f}" for s in R.SITS) +
              '  коридоры: ' + ' '.join(f"{s}{'✓' if COR[s][0] <= avg[s][0] <= COR[s][1] else ('↓' if avg[s][0] < COR[s][0] else '↑')}" for s in R.SITS))
    if grp != 'draft_':
        for v, S, se, a in rows[::-1]:
            print(f"{v[:60]:60s} {100 * S / E:5.0f}% S={S:+.2f}±{se:.2f}  " + ' '.join(f"{s}:{a[s][0]:.2f}/{a[s][1]:.0f}%/{a[s][2]:.2f}" for s in R.SITS))
    out[grp] = [dict(v=v, S=S, se=se, pct=100 * S / E, abs=a) for v, S, se, a in rows]
json.dump(out, open(sys.argv[1] + '.final.json', 'w'), ensure_ascii=False, indent=1)
