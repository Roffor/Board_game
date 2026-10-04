# -*- coding: utf-8 -*-
"""Решения игроков внутри эффектов карт. Движок спрашивает их у объекта choices.
Здесь простые решения по умолчанию; бот стенда переопределяет то, что требует оценки хода (Молитва)."""


class Choices:
    def burn_pick(self, f, hid, cands):
        """Какую карту сжечь: сначала топливо, потом самую слабую."""
        return min(cands, key=lambda c: (0 if c.d.fuel else 1, c.value))

    def ally_burn_pick(self, f, hid, cands):
        return min(cands, key=lambda c: c.value)

    def discard_pick(self, f, hid, cands):
        return min(cands, key=lambda c: c.value)

    def restore_pick(self, f, pool):
        """Какую сожжённую карту вернуть: из трёх самых ценных — лучшую под этот ход."""
        top = sorted(pool, key=lambda kc: -kc[1].value)[:3]
        return max(top, key=lambda kc: self._rscore(f, *kc))

    def _danger(self, f, k):
        it = f.E.intent
        if not it:
            return False
        return sum(a[1] * a[3] for a in it['acts'] if a[0] == 'atk') > f.H[k].shield

    def _rscore(self, f, k, c):
        s = c.value
        if k == f.M and c.cost <= f.H[f.M].mana:
            s += 2
        if self._danger(f, k) and c.kind == 'защита':
            s += 3
        if not self._danger(f, k) and c.kind == 'атака':
            s += 2
        return s

    def echo_pick(self, f, played):
        return max(played, key=lambda co: co[0].value)

    def take_hit(self, f, cands, n):
        """Кто из героев принимает удар: тот, кто потеряет меньше здоровья."""
        def loss(k):
            h = f.H[k]; x = max(0, n - (f.bless_n if h.blessed else 0) - h.shield)
            return (x >= h.hp, x, -h.hp)
        return min(cands, key=loss)

    def pray_pick(self, f, cards, uselimit):
        """Что сыграть Молитвой: по умолчанию — первую открытую карту, первый вариант."""
        return (cards[0], 0) if cards else None
