# -*- coding: utf-8 -*-
"""Собрать план контроля (этап 3 подгонки 2026-10-25): текущие файлы, старт из nabor: start, пул — банк без старта.
Варианты: база, чистые билды (пул из одного билда), каждая легендарка. python -m stend.kontrol_plan <файл.yaml> [боёв]"""
import sys, yaml
import engine

g = engine.load_game('../..')
n = int(sys.argv[2]) if len(sys.argv) > 2 else 800
geroi = {}
for h in g.heroes:
    st = [c.cid for c in g.start_deck(h)]
    geroi[h] = dict(start=st, pul=[c.cid for c in g.hero_cards(h, {'bank'}) if c.cid not in st])
V = [dict(metka='baza')]
for h, bs in (('mag', ('П', 'Р', 'Д')), ('zhrec', ('В', 'З', 'М'))):
    st = geroi[h]['start']
    for b in bs:
        V.append(dict(metka=f'{h}-chistyj-{b}', geroi={h: dict(start=st, pul=[c.cid for c in g.hero_cards(h, {'bank'}) if c.build == b and c.cid not in st])}))
    for c in g.hero_cards(h, {'legendarka'}):
        V.append(dict(metka=f'leg-{c.cid}', geroi={h: dict(start=st, pul=geroi[h]['pul'], obyazatelno=[c.cid])}))
P = dict(nazvanie=sys.argv[1].split('/')[-1][:-5], opisanie='Этап 3 подгонки: контроль без правок.', srok_chasov=0.4, seed0=26102026,
         tajmaut_boya_sek=30, geroi=geroi, fazy=[dict(id='kontrol', tip='progon', dolya=1.0, pervaya_volna=n, volna=200, varianty=V)])
open(sys.argv[1], 'w').write('# Этап 3 плана 2026-10-25-podgonka-16ch.md: контроль без правок (собран stend/kontrol_plan.py).\n'
                             + yaml.safe_dump(P, allow_unicode=True, sort_keys=False, width=250, default_flow_style=None))
print(len(V), 'вариантов')
