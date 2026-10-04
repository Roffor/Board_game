# -*- coding: utf-8 -*-
"""Серия №11 (шлифовка мага, 2026-09-30): поверх burn10.
Решения Никиты (cards/mag/20 §5): баланс по длине боя и потерям ХП; бюджет апгрейда +2 вместо +3;
карты в рамках [С 5.2–5.4]; враги заморожены.
Правки карт:
- Стеклянный огонь: при проигрыше броска сгорает БЕЗ заряда подношения (glass.chg = 0);
- Шёпот безумия: при сжигании слабее (mad.bn);
- Искра с доплатой: переделка — цена kick.cost, обычный урон kick.d, доплата kick.extra → kick.big и 1 Порча;
- Полная горсть: fist.k за карту в руке + fist.b;
- Тройной обряд: бонус triple.b;
- Отложенное заклинание, Обряд предков, Масляная тряпка, Последнее пламя — из концепта убраны;
  добавлены утренние Чистое пламя, Полная горсть, Искры-осколки, Общая цель.
- эталоны бюджета +2: e2_dmg (Искра +2 урона), e2_sh (Оберег +2 щита)."""
import json, os
import burn2
from burn2 import p
from burn import BCard, one
import burn10
from burn10 import B10Game, M_start, CFG, pools, BUILD, CX
from burn9 import B9Game

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(burn10.DEFAULTS)
DEFAULTS.update(json.load(open(os.path.join(HERE, 'final_defaults.json'))))
# принятые утром числа кандидатов
DEFAULTS.update({'clash.d': 5, 'clash.low': 0, 'fist.k': 2, 'shard.n': 3, 'aim.b': 5, 'twice.cost': 0, 'fear.n': 3})
# новые параметры (по умолчанию = поведение серии №10)
DEFAULTS.update({'glass.chg': 1, 'mad.bn': 2, 'kick.cost': 1, 'kick.d': 4, 'fist.b': 0, 'triple.b': 6})
ETALON = {'e_dmg', 'e_sh', 'e2_dmg', 'e2_sh'}

CONCEPT = ['a_ash2', 'a_pyre', 'a_tar', 'a_ember', 'a_wrath', 'a_blood', 'a_spirit', 'a_sacshield', 'n_hands', 'n_mark',
           'n_answer', 'n_shield2', 'n_alien', 'n_phoenix', 'x_rot', 'x_rip', 'x_wave', 'x_evil', 'x_toad', 'x_whisp',
           'x_cshield', 'x_echo', 'x_retal', 'x_uni', 'x_shoulder', 'x_hunt', 'x_doom', 'x_storm', 'x_triple', 'x_glass',
           'x_wisp', 'x_prolif', 'x_doll', 'x_madness', 'x_nowlater', 'x_kick', 'x_ashecho',
           'x_clash', 'x_fist', 'x_shards', 'x_aim']
REMOVED = ['x_delay', 'a_rite', 'n_rag', 'x_last']


def M_bank(extra=None):
    U = burn10.M_bank(extra)
    for c in U:
        if c.cid == 'x_madness':
            c.on_burn = lambda g: (g.porcha(p('mad.bn', 2)), g.bst('mad_burn') if not g.sim else None)
            c.text = f"1 мана. {p('mad.n', 2)} Порчи. Если эту карту сжигают — {p('mad.bn', 2)} Порчи бесплатно."
        elif c.cid == 'x_kick':
            c.cost = p('kick.cost', 1)
            c.text = (f"{p('kick.cost', 1)} маны. {p('kick.d', 4)} урона. Доплата: ещё {p('kick.extra', 1)} мана — "
                      f"вместо этого {p('kick.big', 8)} урона и 1 Порча.")
        elif c.cid == 'x_shards':
            c.cost = p('shards.cost', 1)
        elif c.cid == 'x_wave':
            c.opts = one(lambda g, h, o: (g.porcha(p('wave.n', 1)), g.porcha(g.E.porcha)))
        elif c.cid == 'x_fist':
            c.opts = one(lambda g, h, o: g.hit(h, p('fist.k', 1) * len(g.H['M'].hand) + p('fist.b', 0)))
    def add(cid, name, kind, text, opts, grp, build, **k):
        c = BCard(cid, name, kind, text, opts, grp=grp, **k); U.append(c); BUILD[cid] = build; CX[cid] = 1
    add('e2_dmg', 'Эталон: Искра +2', 'атака', '1 мана. 4 урона. Подношение: +2 урона.',
        one(lambda g, h, o: g.hit(h, 4 + 2 * o)), 'spark', 'эталон', cost=1, off='1', value=6)
    add('e2_sh', 'Эталон: Оберег +2', 'защита', '1 мана. 4 щита себе ИЛИ союзнику. Подношение: обоим.',
        [('себе', lambda g, h, o: (g.shield('M', 4), g.shield('P', 4) if o else None)),
         ('союзнику', lambda g, h, o: (g.shield('P', 4), g.shield('M', 4) if o else None))],
        'ward', 'эталон', cost=1, off='1', value=6)
    return U


class B11Game(B10Game):
    def play(self, hk, card, opt, want_off):
        if card.cid != 'x_glass' or hk != 'M':
            return super().play(hk, card, opt, want_off)
        gp = burn2.P.get('glass.p', 0.5); burn2.P['glass.p'] = 0
        try:
            ok = super().play(hk, card, opt, want_off)
        finally:
            burn2.P['glass.p'] = gp
        if ok and not self.sim and self.rng.random() < gp:
            m = self.H['M']
            if any(c is card for c in m.disc):
                m.disc = [c for c in m.disc if c is not card]; m.exiled.append(card); m.exiled_n += 1
                self.charges += p('glass.chg', 1); self.burned_rnd += 1; self.bst('burned'); self.bst('glass_broke')
        return ok

    def triple(self, h):
        full = (int(self.burned_rnd > 0) + int(self.E.porcha > 0) + int(self.ally_shielded_rnd > 0)) >= p('triple.need', 3)
        self.hit(h, 2 + (p('triple.b', 6) if full else 0))
        if full:
            self.draw(h, 1); self.bst('triple')

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B11Game
        return g


# ---- шаг 1: бюджет +2 и рамки [С 5.2–5.4] (старые значения серии №10 — в OLD10)
OLD10 = {'ash2.d': 2, 'pyre.per': 6, 'wrath.per': 5, 'phx.dmg': 1, 'glass.chg': 1, 'wisp.d': 4, 'ashecho.d': 5,
         'clash.d': 5, 'fist.k': 2, 'fist.b': 0, 'rip.k': 6, 'cshield.b': 8, 'cshield.k': 2, 'doll.porcha': 2,
         'spirit.m': 6, 'sac.sh': 6, 'echo.cost': 0, 'shoulder.sh': 5, 'nl.sh': 5, 'ember.n': 7, 'mad.bn': 2,
         'kick.cost': 1, 'kick.d': 4, 'kick.big': 8, 'hands.b': 9, 'triple.b': 6}
STEP1 = {'ash2.d': 1, 'pyre.per': 4, 'wrath.per': 4, 'phx.dmg': 0, 'glass.chg': 0, 'wisp.d': 3, 'ashecho.d': 4,
         'clash.d': 4, 'fist.k': 1, 'fist.b': 2, 'rip.k': 4, 'cshield.b': 4, 'cshield.k': 2, 'doll.porcha': 1,
         'spirit.m': 5, 'sac.sh': 5, 'echo.cost': 1, 'shoulder.sh': 4, 'nl.sh': 4, 'ember.n': 6, 'mad.bn': 1,
         'kick.cost': 0, 'kick.d': 3, 'kick.big': 7, 'hands.b': 6, 'triple.b': 4}
DEFAULTS.update(STEP1)


# ---- шаг 2 (11:20): колоды на шаге 1 всё ещё сильно короче коридоров → второй срез у карт с большим эффектом
STEP2 = {'glass.p': 0.67, 'shard.n': 2, 'shards.cost': 0, 'alien.n': 4, 'alien.draw': 2, 'wave.n': 0, 'whisp.n': 4,
         'fist.b': 1, 'ember.n': 4, 'kick.d': 2, 'kick.big': 6, 'blood5.cost': 1, 'sh2.b': 3, 'ans.b': 4, 'tar.porcha': 1,
         'uni.b': 2, 'ashecho.d': 3, 'nl.sh': 3, 'nl.d': 4, 'aim.b': 4, 'mark.cost': 1, 'toad.d': 2, 'wrath.per': 3,
         'spirit.m': 4, 'sac.sh': 4, 'pyre.per': 3, 'hands.b': 8, 'rip.cost': 0}
DEFAULTS.update(STEP2)


# ---- рядовые II: усиление механиками, а не здоровьем (Никита 2026-09-30 11:31)
# «Броня N»: каждое попадание по врагу слабее на N (Порча пробивает броню: прибавка от Порчи не режется);
# «Панцирь N»: в начале каждого раунда героев враг получает N щита.
def pools(cfg=None):
    P = burn10.pools(cfg)
    a, r = p('r2.armor', 0), p('r2.regen', 0)
    if a or r:
        out = []
        for e in P['II']:
            e = dict(e); t = dict(e.get('traits', {}))
            if a: t['armor'] = a
            if r: t['regen'] = r
            e['traits'] = t; out.append(e)
        P['II'] = out
    return P


def _hit11(self, h, n, pierce=False):
    a = self.E.traits.get('armor', 0) if self.E else 0
    if a and n > 0:
        n = max(0, n - a)
        if not self.sim:
            self.bstats['armor'] = self.bstats.get('armor', 0) + 1
    return B10Game.hit(self, h, n, pierce)


def _hero11(self):
    if not self.sim and self.E and self.E.hp > 0 and self.E.traits.get('regen'):
        self.E.shield += self.E.traits['regen']
    return B10Game.hero_phase(self)


B11Game.hit = _hit11
B11Game.hero_phase = _hero11


# ---- шаг 3 (11:50): колоды элиты и босса уже в коридорах (у нижней границы); точечно правлю выбивающиеся
STEP3 = {'kick.cost': 1, 'kick.d': 3, 'kick.big': 6, 'rip.cost': 1, 'hands.b': 7}
DEFAULTS.update(STEP3)


# ---- итог серии №11: Броня 1 у рядовых II по умолчанию
DEFAULTS['r2.armor'] = 1
