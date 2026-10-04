# -*- coding: utf-8 -*-
"""20 своих сборок по 6 апгрейдов: чистые С, П, М; пары С–П, С–М, П–М; смесь всех.
Для каждого сочетания: сильнейшая, случайная и слабейшая подходящая шестёрка (по силе карт из sum.json).
python3 mkbuilds.py sum.json cards.json out.json [боёв на ситуацию]"""
import json, sys, random
import burn2, burn10
burn2.P.update(burn10.DEFAULTS)
burn10.M_bank()
S = json.load(open(sys.argv[1])); cards = json.load(open(sys.argv[2])); nf = int(sys.argv[4]) if len(sys.argv) > 4 else 30
B = burn10.BUILD
rng = random.Random(777)
L = lambda c: set(ch for ch in B.get(c, '') if ch in 'СПМ')
st = lambda c: S.get(c, {}).get('S', 0)
V = []
for combo in ['С', 'П', 'М', 'СП', 'СМ', 'ПМ', 'СПМ']:
    want = set(combo)
    fit = [c for c in cards if L(c) and L(c) <= want]      # только карты этих билдов
    fit.sort(key=lambda c: -st(c))
    kinds = [('сильн', fit[:6]), ('случ', rng.sample(fit, min(6, len(fit)))), ('слаб', fit[-6:])]
    for k, deck in kinds:
        if len(V) >= 20:
            break
        if len(deck) < 6:
            continue
        # сборка из нескольких билдов должна содержать карты каждого из них
        V.append({'label': f'build_{combo}_{k}', 'cards': deck, 'noup': True, 'n': nf})
json.dump(V, open(sys.argv[3], 'w'), ensure_ascii=False)
for v in V:
    print(v['label'], v['cards'])
