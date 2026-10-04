# -*- coding: utf-8 -*-
"""Эталонные («золотые») бои движка. Играются на замороженной копии данных engine/tests/igra/,
поэтому правки карт в game/ их не ломают — ломает только изменение правил в коде движка.

  python -m engine.tests.test_zolotye            проверить
  python -m engine.tests.test_zolotye --zapisat  перезаписать эталон (только осознанно, с записью в журнал движка)

Бой играет простой детерминированный игрок ниже (не бот стенда), чтобы тест движка не зависел от стенда."""
import json, os, sys
from engine import load_game, Fight, Choices, RULES_VERSION

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, 'igra')
OUT = os.path.join(HERE, 'zolotye.json')


def greedy_round(f):
    """Простой игрок: маг играет карты слева направо, пока хватает маны; Жрец — первые карты до лимита."""
    for hid in f.order:
        h = f.H[hid]
        progress = True
        while progress and not f.over and f.E.hp > 0 and h.alive:
            progress = False
            for c in list(h.hand):
                if f.play(hid, c, len(c.d.variants) - 1, 1):
                    progress = True
                    break
            if f.E.hp <= 0:
                break


def play(g, ei, li, seed):
    enemies = sorted(g.enemies.values(), key=lambda e: e.eid)
    locs = sorted(g.locations.values(), key=lambda l: l.lid)
    decks = {}
    for hid in sorted(g.heroes):
        d = g.start_deck(hid)
        ups = g.hero_cards(hid, {'apgrejd'})
        k = seed % 5
        for c in ups[seed % len(ups):][:k]:
            d = d[1:] + [c]
        decks[hid] = d
    f = Fight(g, decks, enemies[ei % len(enemies)], locs[li % len(locs)], seed, Choices())
    while not f.over:
        f.start_round()
        if f.over:
            break
        greedy_round(f)
        f.check_over()
        f.finish_round()
    r = f.result()
    return dict(won=r['won'], rounds=r['rounds'], end_hp=r['end_hp'], enemy=r['enemy'], ehp=f.E.hp,
                stats={k: v for k, v in sorted(r['stats'].items()) if k != 'karty'})


CASES = [(ei, ei * 3 + 1, 1000 + ei * 17 + j) for ei in range(13) for j in range(3)]


def run(write=False):
    g = load_game(DATA)
    got = {f'{ei}-{li}-{s}': play(g, ei, li, s) for ei, li, s in CASES}
    if write:
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(dict(rules=RULES_VERSION, boi=got), f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f'эталон записан: {len(got)} боёв, правила {RULES_VERSION}')
        return True
    with open(OUT, encoding='utf-8') as f:
        ref = json.load(f)
    bad = [k for k in got if got[k] != ref['boi'].get(k)]
    print(f'золотые бои: {len(got)}, расхождений {len(bad)}' + (f' (эталон для правил {ref["rules"]}, сейчас {RULES_VERSION})' if bad else ''))
    for k in bad[:3]:
        print('  ', k, 'было', ref['boi'].get(k, {}).get('rounds'), ref['boi'].get(k, {}).get('end_hp'),
              'стало', got[k]['rounds'], got[k]['end_hp'])
    return not bad


if __name__ == '__main__':
    sys.exit(0 if run('--zapisat' in sys.argv) else 1)
