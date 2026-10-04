# -*- coding: utf-8 -*-
"""Сводка по нескольким прогонам: одинаковые настройки карты (с учётом того, какие числа стояли по умолчанию
в каждом прогоне) объединяются. Сила — в % эталона своего прогона, объединение с весами 1/погрешность².
python3 pool11.py run1.json:ovr1.json run2.json ...   (ovr — числа по умолчанию, отличавшиеся в том прогоне)"""
import json, sys, math
import burn2, burn10
burn2.P.update(burn10.DEFAULTS)
ARGS = sys.argv[1:]
R0 = None

KNOB = {'x_rot': 'rot', 'n_phoenix': 'phx', 'x_shoulder': 'shoulder', 'x_last': 'last', 'x_whisp': 'whisp', 'x_rip': 'rip',
        'a_blood': 'blood5', 'x_hunt': 'hunt', 'a_rite': 'rite', 'a_ash2': 'ash2', 'a_pyre': 'pyre', 'n_hands': 'hands',
        'a_sacshield': 'sac', 'x_retal': 'retal', 'n_answer': 'ans', 'x_uni': 'uni', 'n_mark': 'mark', 'a_ember': 'ember', 'x_evil': 'evil',
        'x_toad': 'toad', 'a_wrath': 'wrath', 'n_rag': 'rag', 'a_tar': 'tar', 'x_wave': 'wave', 'x_cshield': 'cshield', 'x_doom': 'doom', 'x_delay': 'delay',
        'x_doll': 'doll', 'x_glass': 'glass', 'x_madness': 'mad', 'x_nowlater': 'nl', 'x_wisp': 'wisp', 'x_prolif': 'prolif',
        'x_storm': 'storm', 'x_ashecho': 'ashecho', 'x_kick': 'kick', 'x_cascade': 'casc', 'x_grow': 'grow', 'x_xwall': 'xwall'}
import os
ANCHOR = float(os.environ.get('ANCHOR', 0))
# в итерации 2 Буря, Тройной и Стекло вытесняли другую стартовую карту — не смешиваем
SKIP = {'it2.json': {'x_storm', 'x_triple', 'x_glass'}}
names = {c.cid: c.name for c in burn10.M_bank()}


def load(path):
    global R0
    import importlib
    sys.argv = ['rep11.py', path]
    if R0 is None:
        import rep11 as m; R0 = m
    else:
        importlib.reload(R0)
    R0.W = 4.5
    return R0


rows = {}   # сигнатура -> список (pct, se_pct, n, run)
for spec in ARGS:
    path, ovr = (spec.split(':') + [None])[:2]
    ov = json.load(open(ovr)) if ovr else {}
    V = {}
    R = load(path)
    et = [R.strength(e) for e in ('e_dmg', 'e_sh') if e in R.by]
    E = ANCHOR or sum(x['S'] for x in et) / len(et)
    for v in R.by:
        if v == 'base' or v in ('e_dmg', 'e_sh') or v.startswith(('build_', 'draft_')):
            continue
        cid = v.split('|')[0]
        if cid in SKIP.get(path, ()):
            continue
        P = {}
        if '|' in v:
            for kv in v.split('|')[1].split(','):
                k, x = kv.split('='); P[k] = float(x)
        pref = set(k.split('.')[0] for k in P) | ({KNOB[cid]} if cid in KNOB else set())
        eff = {}
        for k in set(list(burn10.DEFAULTS) + list(ov) + list(P)):
            if k.split('.')[0] in pref:
                eff[k] = float(P.get(k, ov.get(k, burn10.DEFAULTS.get(k, -1))))
        x = R.strength(v)
        sig = cid + '|' + ','.join(f'{k}={eff[k]:g}' for k in sorted(eff))
        rows.setdefault(sig, []).append((100 * x['S'] / E, 100 * x['se'] / E, x['n'], path, x['pl']))
out = {}
for sig, L in sorted(rows.items()):
    w = [1 / max(1e-6, s) ** 2 for _, s, *_ in L]
    pct = sum(a * b for a, (b, *_) in zip(w, L)) / sum(w); se = 1 / math.sqrt(sum(w))
    out[sig] = dict(pct=pct, se=se, n=sum(r[2] for r in L), runs=len(L), per=[round(r[0]) for r in L], pl=L[-1][4])
for sig, x in sorted(out.items(), key=lambda kv: -kv[1]['pct']):
    cid = sig.split('|')[0]
    print(f"{names.get(cid, cid)[:22]:22s} {sig[len(cid):][:40]:40s} {x['pct']:5.0f}% ±{x['se']:.0f}  прогонов {x['runs']} {x['per']}  боёв {x['n']} розыгр {x['pl']:.2f}")
json.dump(out, open('pool11.sum.json', 'w'), ensure_ascii=False, indent=1)
