# -*- coding: utf-8 -*-
"""План теста: чтение и проверка. Формат — в plans/PRIMER.yaml и AGENTS.md."""
import yaml

from .situacii import SITUACII

TIPY = {'progon', 'test_bilda', 'podbor'}
CELI = {'sila', 'koridory'}


class PlanError(ValueError):
    pass


def _deck(spec, w):
    spec = dict(spec or {})
    ap = spec.get('apgrejdy', 'sluchajno')
    if ap != 'sluchajno' and not isinstance(ap, list):
        raise PlanError(f'{w}: apgrejdy — «sluchajno» или список id карт')
    spec.setdefault('apgrejdy', 'sluchajno')
    spec.setdefault('pul', 'apgrejd')
    spec.setdefault('obyazatelno', [])
    return spec


def load(path, game):
    with open(path, encoding='utf-8') as f:
        p = yaml.safe_load(f) or {}
    for k in ('nazvanie', 'srok_chasov', 'fazy'):
        if k not in p:
            raise PlanError(f'в плане нет поля {k}')
    p.setdefault('seed0', 'sluchajno')
    p.setdefault('tajmaut_boya_sek', 120)
    p.setdefault('pravki', {})
    p['geroi'] = {h: _deck((p.get('geroi') or {}).get(h), f'geroi.{h}') for h in game.heroes}
    total = 0.0
    ids = set()
    for i, ph in enumerate(p['fazy']):
        w = f'фаза {i + 1} ({ph.get("id")})'
        if ph.get('id') in ids or not ph.get('id'):
            raise PlanError(f'{w}: нужен уникальный id')
        ids.add(ph['id'])
        if ph.get('tip') not in TIPY:
            raise PlanError(f'{w}: tip — один из {sorted(TIPY)}')
        ph.setdefault('dolya', 1.0 / len(p['fazy']))
        total += ph['dolya']
        ph.setdefault('situacii', list(SITUACII))
        for s in ph['situacii']:
            if s not in SITUACII:
                raise PlanError(f'{w}: ситуация {s} не из {SITUACII}')
        ph.setdefault('pervaya_volna', 60)
        ph.setdefault('volna', 30)
        if ph['tip'] == 'progon':
            vs = ph.get('varianty') or [{'metka': 'baza'}]
            for v in vs:
                if 'metka' not in v:
                    raise PlanError(f'{w}: у варианта нет metka')
            ph['varianty'] = vs
        if ph['tip'] == 'test_bilda':
            hid = ph.get('geroj')
            if hid not in game.heroes:
                raise PlanError(f'{w}: geroj — один из {sorted(game.heroes)}')
            cards = ph.get('karty')
            if cards is None and ph.get('bild'):
                cards = [c.cid for c in game.hero_cards(hid, {'apgrejd'}) if c.build == ph['bild']]
            if not cards:
                raise PlanError(f'{w}: укажи karty (список id) или bild')
            for c in cards:
                if c not in game.cards or game.cards[c].hero != hid:
                    raise PlanError(f'{w}: карта {c} не найдена у героя {hid}')
            ph['karty'] = cards
        if ph['tip'] == 'podbor':
            if ph.get('cel') not in CELI:
                raise PlanError(f'{w}: cel — одна из {sorted(CELI)}')
            prm = ph.get('parametry') or []
            if not prm:
                raise PlanError(f'{w}: нет parametry')
            for x in prm:
                if 'chislo' not in x or 'granicy' not in x:
                    raise PlanError(f'{w}: у параметра нужны chislo и granicy')
                x.setdefault('shag', 1)
                if ph['cel'] == 'sila':
                    parts = x['chislo'].split('.')
                    if parts[0] != 'karta' or parts[1] not in game.cards:
                        raise PlanError(f'{w}: для cel: sila параметр — число карты (karta.<id>.<число>)')
                    x['karta'] = parts[1]
            ph.setdefault('zapisyvat', True)
    if abs(total - 1.0) > 0.01:
        raise PlanError(f'сумма долей времени фаз = {total:.2f}, должна быть 1')
    return p
