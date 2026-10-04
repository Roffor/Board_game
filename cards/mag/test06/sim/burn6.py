# -*- coding: utf-8 -*-
"""Тест билда №6: цель длины боёв +1 раунд (Никита 2026-09-29). Рычаги (CFG):
cut — урон каждого попадания стартовых карт обоих героев меньше на cut (не ниже 1);
sh0 — стартовый щит рядовых по ярусам; elite_cap — здоровье элиты не больше 40 [С 4.1];
hp — здоровье героев (≤ 20 [С 3.1]). Числовые правки теста №5 приняты (решение Никиты: числа — на мне)."""
import copy
import engine as E
import cards as C
from burn5 import B5Game, M_start, M_bank, DEFAULTS as D5

DEFAULTS = dict(D5)
DEFAULTS.update({'blood5.cost': 1, 'sac.sh': 8, 'blade.b': 7, 'hands.b': 7, 'alien.n': 6, 'rag.b': 4,
                 'sh2.b': 4, 'spirit.m': 7, 'whirl.cost': 0})
CFG = dict(cut=1, sh0={'I': 4, 'II': 2}, rank_hp={'I': 20, 'II': 18}, elite_hp=35, ehp_k=1.0, hp={'M': 20, 'P': 20})


def pools(cfg=None):
    cfg = cfg or CFG
    def sc(pool, sit):
        out = []
        for e in pool:
            e = copy.deepcopy(e)
            if sit in ('I', 'II'):
                e['shield0'] = cfg['sh0'][sit]
                e['hp'] = min(e['hp'], cfg.get('rank_hp', {}).get(sit, 20))
            else:
                if not e.get('traits', {}).get('golem'):
                    e['hp'] = min(cfg['elite_hp'], round(e['hp'] * cfg['ehp_k']))
            out.append(e)
        return out
    return {'I': sc(C.TIER1, 'I'), 'II': sc(C.TIER2, 'II'), 'EL': sc(C.ELITES, 'EL')}


class B6Game(B5Game):
    def __init__(self, seed, mdeck, pdeck=None, cfg=None):
        self.cfg = cfg or CFG
        E.MAXHP['M'] = self.cfg['hp']['M']; E.MAXHP['P'] = self.cfg['hp']['P']
        super().__init__(seed, mdeck, pdeck)
        self.cur_start = False

    def play(self, hk, card, opt, want_off):
        prev = self.cur_start
        self.cur_start = (getattr(card, 'cat', 'А') == 'С') if hk == 'M' else (card.cid in START_P)
        try:
            return super().play(hk, card, opt, want_off)
        finally:
            self.cur_start = prev

    def burn(self, hk, n, src='hand'):
        prev = self.cur_start; self.cur_start = False     # эффекты сожжённого топлива — не стартовая атака
        try:
            return super().burn(hk, n, src)
        finally:
            self.cur_start = prev

    def hit(self, h, n, pierce=False):
        if self.cur_start and n > 0:
            n = max(1, n - self.cfg['cut'])
        return super().hit(h, n, pierce)

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B6Game
        return g


START_P = {c.cid for c in C.P_cards()}
