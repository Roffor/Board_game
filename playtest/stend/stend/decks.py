# -*- coding: utf-8 -*-
"""Сборка колод: стартовая колода героя + апгрейды. Каждый апгрейд заменяет одну стартовую карту:
ту, что указана в zamenyaet (если она ещё в колоде), иначе самую слабую оставшуюся стартовую своего вида,
иначе самую слабую оставшуюся стартовую. Если стартовых не осталось — карта добавляется."""


def build_deck(game, hid, upgrades, start=None):
    """upgrades: список id карт (апгрейды, банк). start: свой список id стартовой колоды (необязательно)."""
    if start is None:
        deck = list(game.start_deck(hid))
    else:
        deck = [game.cards[c] for c in start]
    left = list(deck)                     # стартовые карты, которые ещё в колоде (по позициям)
    for cid in upgrades:
        c = game.cards[cid]
        if c.hero != hid:
            raise ValueError(f'карта {cid} — не карта героя {hid}')
        if not left:
            deck.append(c); continue
        tgt = next((x for x in left if x.cid == c.replaces), None) if c.replaces else None
        if tgt is None:
            same = [x for x in left if x.kind == c.kind]
            tgt = min(same or left, key=lambda x: (x.value, x.cid))
        left.remove(tgt)
        deck.remove(tgt); deck.append(c)
    return deck


def upgrade_pool(game, hid, sets=('apgrejd',)):
    """Пул апгрейдов героя: карты из набора (по умолчанию apgrejd), кроме отклонённых."""
    return [c.cid for c in game.hero_cards(hid, set(sets)) if c.status != 'ubrana']
